"""The surface the page talks to.

The dashboard is one page. Everything it shows arrives over these few
endpoints, as data. The browser draws it. The server says what to draw.
"""

import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import answering
import filtering
import metrics
import model
import payables
import panels
import suggestions

ROOT = Path(__file__).resolve().parent.parent

_FILTER_KEYS = {'supplier', 'since', 'until', 'order', 'shipment', 'state',
                'item', 'band', 'category'}


def as_of():
    """The day the dashboard pretends it is. It comes from outside the
    code, so a demo can be frozen without editing the source."""
    chosen = os.environ.get('PAYABLES_TODAY')
    if chosen:
        return date.fromisoformat(chosen)
    return date.today()


def _data_folder():
    chosen = os.environ.get('PAYABLES_DATA')
    if chosen:
        return Path(chosen)
    return ROOT / 'data'


def _rows():
    return payables.payable(payables.load(_data_folder()))


def _filters_from(request):
    params = dict(request.query_params)
    unknown = set(params) - _FILTER_KEYS
    if unknown:
        raise HTTPException(400, f'unknown filter: {sorted(unknown)}')
    built = {}
    for key, value in params.items():
        built[key] = value
    if 'since' in built:
        built['since'] = date.fromisoformat(built['since'])
    if 'until' in built:
        built['until'] = date.fromisoformat(built['until'])
    return built


def _apply(request):
    try:
        return filtering.apply(_rows(), **_filters_from(request),
                               today=as_of())
    except filtering.NeedsADate as error:
        raise HTTPException(400, str(error))
    except ValueError as error:
        raise HTTPException(400, str(error))


def _rows_given(given):
    """The loaded rows, filtered by a dict. Both endpoints that take a
    body share this one door, so they cannot drift apart."""
    unknown = set(given) - _FILTER_KEYS
    if unknown:
        raise HTTPException(400, f'unknown filter: {sorted(unknown)}')
    try:
        return filtering.apply(_rows(), **given, today=as_of())
    except filtering.NeedsADate as error:
        raise HTTPException(400, str(error))


def _panel_dict(panel):
    return {
        'name': panel.name,
        'kind': panel.kind,
        'title': panel.title,
        'rows': [[label, _row_value(label, value)]
                 for label, value in panel.rows],
    }


def _row_value(label, value):
    if isinstance(value, Decimal):
        if label.startswith('Share'):
            return f'{value}%'
        if label.startswith('Average days'):
            return f'{value} days'
        return _money_text(value)
    return str(value)


def _answer_dict(answer):
    return {
        'panels': [_panel_dict(panel) for panel in answer.panels],
        'sentence': answer.sentence,
        'refusal': answer.refusal,
        'rows_used': answer.rows_used,
        'as_of': answer.as_of.isoformat() if answer.as_of else None,
    }


def _money_text(value):
    """Money for a person: thousands comma, two places."""
    return f'{value:,.2f}'


def _figure_value(name, rows):
    """One figure, turned into JSON. Formatting belongs here, at the
    edge, never inside the metric."""
    value = metrics.compute(name, rows, today=as_of())
    if name == 'oldest_overdue':
        return value.number if value else None
    if name == 'overdue_rate':
        return f'{value}%' if value is not None else None
    if name == 'average_days_overdue':
        return f'{value} days' if value is not None else None
    if name in ('total_owed', 'ticket_average', 'overdue_total'):
        return _money_text(value) if value is not None else None
    if isinstance(value, list) and value and isinstance(value[0], tuple):
        if len(value[0]) == 3:
            return [[label, count, _money_text(amount)]
                    for label, count, amount in value]
        return [[label, _money_text(amount)] for label, amount in value]
    return value


app = FastAPI()

#: The chart library is served from here rather than a CDN, so the page
#: draws the same inside Docker, on a plane, and in the test browser.
app.mount('/static',
          StaticFiles(directory=Path(__file__).resolve().parent / 'static'),
          name='static')

app.state.model = None


def model_for_this_request():
    """The model for a typed question. The state holds the test
    override. Otherwise it is built from the key, wherever it is."""
    if app.state.model is not None:
        return app.state.model
    found = model.key()
    if found:
        return model.deepseek(key=found)
    return None


@app.get('/', response_class=HTMLResponse)
def page():
    """Read from disk on every request.

    Holding it in memory means an edit to the page needs a restart, and a
    restart in the middle of looking at something is how a difference gets
    blamed on the wrong change.
    """
    return _PAGE_FILE.read_text(encoding='utf-8')


@app.get('/api/overview')
def overview(request: Request):
    rows = _apply(request)
    payload = {
        'total_owed': str(metrics.total_owed(rows)),
        'documents': metrics.count(rows),
    }
    for name in metrics.FIGURES:
        payload[name] = _figure_value(name, rows)
    return payload


@app.get('/api/documents')
def documents(request: Request):
    """The rows themselves, not a roll-up of them.

    Every figure on the page is a sum over these. Without them the
    reader can see that 195,468.00 is overdue and has no way to find out
    which bills that is.
    """
    today = as_of()
    rows = sorted(_apply(request),
                  key=lambda row: (row.due is None, row.due))
    return {'documents': [_document(row, today) for row in rows]}


def _document(row, today):
    if row.is_credit:
        state, days = 'credit', None
    elif row.due and row.due < today:
        state, days = 'overdue', (today - row.due).days
    else:
        state, days = 'open', None
    return {
        'number': row.number,
        'supplier': row.supplier,
        'issued': row.issued.isoformat() if row.issued else '',
        'due': row.due.isoformat() if row.due else '',
        'total': _money_text(row.total),
        'state': state,
        'days': days,
        'paper': row.source,
    }


@app.get('/paper/{name}')
def paper(name: str):
    """The invoice itself.

    Clicking a row opens the page the figures were read off. A total
    nobody can trace back to a document is a total they have to believe
    rather than check.
    """
    from fastapi.responses import FileResponse

    if '/' in name or '\\' in name or not name.endswith('.pdf'):
        raise HTTPException(400, 'not a document name')
    found = _data_folder() / 'pdf' / name
    if not found.exists():
        raise HTTPException(404, 'that document is not on file')
    return FileResponse(found, media_type='application/pdf',
                        filename=name)


@app.get('/api/filters')
def filters():
    return {
        'suppliers': filtering.suppliers(_rows()),
        'states': filtering.STATES,
        'model_connected': model.key() is not None,
    }


@app.get('/api/suggestions')
def chips():
    return {
        'chips': [{'question': chip.question, 'panels': chip.panels}
                  for chip in suggestions.CHIPS],
    }


@app.post('/api/chip')
def click_chip(body: dict):
    index = body.get('chip')
    if not isinstance(index, int) or not 0 <= index < len(suggestions.CHIPS):
        raise HTTPException(400, 'unknown chip')
    rows = _rows_given(body.get('filters') or {})
    answer = suggestions.click(suggestions.CHIPS[index], rows,
                               today=as_of())
    return _answer_dict(answer)


@app.post('/api/ask')
def ask(body: dict):
    question = (body.get('question') or '').strip()
    if not question:
        raise HTTPException(400, 'the question is empty')

    chosen = model_for_this_request()
    if chosen is None:
        return _answer_dict(answering.Answer(
            rows_used=0, as_of=as_of(),
            refusal='No API key is connected. Set DEEPSEEK_API_KEY or '
                    'put the key in the keyring under payables-panel.'))

    rows = _rows_given(body.get('filters') or {})

    history = body.get('history') or []
    if not isinstance(history, list):
        raise HTTPException(400, 'history must be a list of turns')

    answer = answering.answer(question, rows, today=as_of(),
                              model=chosen, history=history[-6:])
    return _answer_dict(answer)



_PAGE_FILE = Path(__file__).resolve().parent / 'page.html'
