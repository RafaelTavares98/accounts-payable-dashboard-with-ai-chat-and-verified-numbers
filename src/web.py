"""The surface the page talks to.

The dashboard is one page. Everything it shows arrives over these few
endpoints, as data. The browser draws it. The server says what to draw.
"""

import os
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import anomalies
import anomaly_answering
import cost
import cost_answering
import model
import plot_answers
from panels import Panel

ROOT = Path(__file__).resolve().parent.parent

NO_KEY = ('No API key is connected. Set DEEPSEEK_API_KEY or put the key in '
          'the keyring under payables-panel.')


def as_of():
    """The day each answer says it was given on. It comes from outside the
    code, so a demo can be frozen without editing the source."""
    chosen = os.environ.get('PAYABLES_TODAY')
    if chosen:
        return date.fromisoformat(chosen)
    return date.today()


def _data_folder():
    chosen = os.environ.get('PAYABLES_DATA')
    if chosen:
        return Path(chosen)
    # Sandbox: the real run of project 01 (Invoices/live, January to
    # October 2026) and project 02's scores on it. The 93-invoice sample
    # stays in data/.
    return ROOT / 'data-live'


def _cost_folder():
    """Where project 01 writes its cost report."""
    return _data_folder() / 'cost'


def _money_text(value):
    """Money for a person: thousands comma, two places."""
    return f'{value:,.2f}'


def _row_value(label, value):
    if isinstance(value, Decimal):
        if label.startswith('Share'):
            return f'{value}%'
        if value.as_tuple().exponent == -4:
            return f'{value:,.4f}'
        return _money_text(value)
    return str(value)


def _panel_dict(panel):
    return {
        'name': panel.name,
        'kind': panel.kind,
        'title': panel.title,
        'rows': [[label, _row_value(label, value)]
                 for label, value in panel.rows],
    }


def _answer_dict(answer):
    return {
        'panels': [_panel_dict(panel) for panel in answer.panels],
        'sentence': answer.sentence,
        'refusal': answer.refusal,
        'rows_used': answer.rows_used,
        'as_of': answer.as_of.isoformat() if answer.as_of else None,
    }


def _share_text(value):
    return f'{value}%' if value is not None else None


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


def _history(body):
    history = body.get('history') or []
    if not isinstance(history, list):
        raise HTTPException(400, 'history must be a list of turns')
    return history[-6:]


def _question(body):
    question = (body.get('question') or '').strip()
    if not question:
        raise HTTPException(400, 'the question is empty')
    return question


@app.get('/', response_class=HTMLResponse)
def page():
    """Read from disk on every request.

    Holding it in memory means an edit to the page needs a restart, and a
    restart in the middle of looking at something is how a difference gets
    blamed on the wrong change.
    """
    return _PAGE_FILE.read_text(encoding='utf-8')


# ---------------------------------------------------------- the cost view
#
# The view the page opens on. Project 01 writes the cost report into
# data/cost/; these endpoints serve it.


def _lines(given):
    unknown = set(given) - set(cost.FILTERS)
    if unknown:
        raise HTTPException(400, f'unknown filter: {sorted(unknown)}')
    return cost.only(cost.load(_cost_folder()), **given)


@app.get('/api/cost/overview')
def cost_overview(request: Request):
    lines = _lines(dict(request.query_params))
    kpis = cost.targets(_cost_folder())
    return {
        'landed_total': _money_text(cost.landed_total(lines)),
        'final_total': _money_text(cost.final_total(lines)),
        'provisional_total': _money_text(cost.provisional_total(lines)),
        'provisional_share': _share_text(cost.provisional_share(lines)),
        'credits_total': _money_text(cost.credits_total(lines)),
        'shipments': cost.shipment_count(lines),
        'lines': cost.line_count(lines),
        'by_component': [[name, _money_text(value)]
                         for name, value in cost.by_component(lines)],
        'by_carrier': [[name, _money_text(value)]
                       for name, value in cost.by_carrier(lines)],
        'by_mode': [[name, _money_text(value)]
                    for name, value in cost.by_mode(lines)],
        'by_product': [[name, _money_text(value)]
                       for name, value in cost.by_product(lines)],
        'unit_cost': [[name, f'{value:,.4f}']
                      for name, value in cost.unit_cost(lines)],
        'by_month': [[month, _money_text(final), _money_text(provisional)]
                     for month, final, provisional in cost.by_month(lines)],
        'targets': {
            'analysed_same_day': _share_text(kpis['analysed_same_day']),
            'our_error_rate': _share_text(kpis['our_error_rate']),
            'close_month': kpis['close_month'],
            'known_before_close': _share_text(kpis['known_before_close']),
            'for_a_person': kpis['for_a_person'],
        },
        'desk': _desk_tiles(cost.desk_week(_cost_folder(), as_of())),
    }


def _arrow(change, period, unit='%'):
    """Sandbox: the change against a past period, as an arrow and a number."""
    if change is None:
        return f'no {period}'
    mark = '▲' if change > 0 else '▼' if change < 0 else '='
    return f'{mark} {abs(change):.0f}{unit} {period}'


def _change(key, now, then):
    """Sandbox: a count changes in percent, a share in points."""
    if not then or now[key] is None or then.get(key) is None:
        return None
    if key == 'processed':
        if not then[key]:
            return None
        return Decimal(100) * (now[key] - then[key]) / then[key]
    return now[key] - then[key]


def _tile_icon(key):
    # A line-drawn SVG, where there is one, reads better than a PNG.
    svg = Path(__file__).parent / 'static' / f'icon-{key}.svg'
    return f'/static/icon-{key}.' + ('svg' if svg.exists() else 'png')


def _short_money(amount):
    """A change in money, on one line beside the value: thousands as k,
    millions as M. 292,402 does not fit a tile; 292k does."""
    amount = int(amount)
    if amount >= 1_000_000:
        return f'{amount / 1_000_000:.1f}M'
    if amount >= 1_000:
        return f'{amount // 1_000}k'
    return str(amount)


def _desk_tiles(week):
    """Sandbox: the four desk tiles, each with its value, its change
    against last week and last month, and its target."""
    if not week:
        return []
    now = week['now']

    def share(key):
        return f'{now[key]:.1f}%' if now[key] is not None else '-'

    def tile(name, key, value, target, unit='%'):
        return {'name': name, 'value': value, 'target': target,
                'icon': _tile_icon(key),
                'change': _arrow(_change(key, now, week['before']),
                                 'last week', unit),
                'month': _arrow(_change(key, now, week['month']),
                                'last month', unit)}

    return [
        tile('Processed', 'processed', str(now['processed']), '100%'),
        tile('Completed', 'completed', share('completed'), '100%'),
        tile('Remaining to target', 'remaining', share('remaining'), '0%'),
        # Supplier errors found that week, the change as a plain count.
        tile('Supplier errors', 'supplier', str(now['supplier']),
             'all found in 7 days', ''),
        tile('Automation errors', 'errors', share('errors'), 'under 1%'),
    ]


# Sandbox: the plot answer. One picker for the server's life, so asking
# the same question again shows the same plot until a restart.
_PICKER = plot_answers.Picker()


def _year_file():
    # The real run already carries each invoice's kind.
    return _data_folder() / 'invoices.csv'


@app.post('/api/plot-answer')
def plot_answer(body: dict):
    """A question in, a category, a key, a plot and its figures out. The
    model, when there is one, only names the category."""
    question = _question(body)
    key = plot_answers.clean(question)
    # "Show me an overview of..." and a simple question both get five
    # plots from five categories, picked by the subject named.
    if plot_answers.wants_an_overview(question):
        fig = plot_answers.figures(_data_folder(), _year_file())
        extra = {'attention': plot_answers.attention(fig)}
        fig.pop('invoices', None)
        plots = []
        for category in plot_answers.overview_set(question):
            index, _ = _PICKER.pick(category, key)
            plots.append({'category': category, 'plot': index,
                          'plot_name': plot_answers.PLOTS[category][index]})
        return {'question': question, 'key': key, 'plots': plots,
                'figures': fig, 'extra': extra}
    chosen = model_for_this_request()
    if chosen:
        category = plot_answers.category_by_model(question, chosen)
    else:
        category = plot_answers.category_by_words(question)
    index, again = _PICKER.pick(category, key)
    fig = plot_answers.figures(_data_folder(), _year_file())
    extra = {}
    if category == 'lookup':
        extra = plot_answers.lookup(fig, question)
    if category == 'overview':
        extra = {'attention': plot_answers.attention(fig)}
    fig.pop('invoices', None)
    return {'question': question, 'category': category, 'key': key,
            'plot': index, 'plot_name': plot_answers.PLOTS[category][index],
            'again': again, 'by_model': bool(chosen), 'figures': fig,
            'extra': extra}


@app.get('/api/plot-figures')
def plot_figures():
    """Every real figure the 24 plots need, for the preview page that
    shows all of them at once. The lookup plots show one revised invoice."""
    fig = plot_answers.figures(_data_folder(), _year_file())
    extra = {'attention': plot_answers.attention(fig)}
    extra.update(plot_answers.lookup(fig, ''))
    fig.pop('invoices', None)
    return {'figures': fig, 'extra': extra}


#: The finance tiles, in the order the desk reads them. A target here is
#: what the desk aims at when it closes a month, not a measurement.
FINANCE_TILES = [
    ('Landed cost', 'landed', 'processed', 'all lines costed'),
    ('Final', 'final', 'completed', 'all of it'),
    ('Provisional', 'provisional', 'remaining', 'none'),
    ('Provisional share', 'share', 'errors', '0%'),
    ('Recoverable taxes', 'credits', 'supplier', 'all claimed'),
]


def _finance_tiles(month):
    """The five finance tiles, each against last month and the month a
    quarter back. Money is grouped; the share is a percentage."""
    if not month:
        return []
    now = month['now']

    def moved(key, then):
        if not then or now[key] is None or then.get(key) is None:
            return None
        return now[key] - then[key]

    def arrow(key, then, period):
        change = moved(key, then)
        if change is None:
            return f'no {period}'
        mark = '▲' if change > 0 else '▼' if change < 0 else '='
        figure = (f'{abs(change):.1f}%' if key == 'share'
                  else _short_money(abs(change)))
        return f'{mark} {figure} {period}'

    tiles = []
    for name, key, icon, target in FINANCE_TILES:
        if key == 'share':
            value = f'{now[key]:.1f}%' if now[key] is not None else '-'
        else:
            value = f'{int(now[key]):,}'
        tiles.append({
            'name': name, 'value': value, 'target': target,
            'icon': _tile_icon(icon),
            'change': arrow(key, month['before'], 'last month'),
            'month': arrow(key, month['quarter'], 'last quarter'),
        })
    return tiles


@app.get('/api/cost/finance')
def cost_finance(request: Request):
    """The finance view: the month the desk is closing, its five tiles,
    and the whole run month by month."""
    lines = _lines(dict(request.query_params))
    month = cost.finance_month(lines)
    return {
        'month': month['month'] if month else None,
        'desk': _finance_tiles(month),
        # Month, landed, final, provisional: the wide chart reads these.
        'months': [[name, _money_text(landed), _money_text(final),
                    _money_text(landed - final)]
                   for name, landed, final in _by_month(lines)],
        'parts': _finance_parts(lines, month),
    }


def _finance_parts(lines, month):
    """(part, this month, last month, the quarter back), dearest first.

    A part nobody bought in one of those months costs nothing there,
    never nothing at all: the row has to be able to say zero."""
    if not month:
        return []
    names = {'now': month['month']}
    order = sorted({line.month for line in lines})
    names['before'] = order[-2] if len(order) > 1 else None
    names['quarter'] = order[-4] if len(order) > 3 else None

    def costs(when):
        found = {}
        if when is None:
            return found
        for line in lines:
            if line.month == when:
                found[line.product] = found.get(line.product,
                                                Decimal('0.00')) + line.landed
        return found

    now = costs(names['now'])
    before = costs(names['before'])
    quarter = costs(names['quarter'])
    zero = Decimal('0.00')
    return [[part, _money_text(amount),
             _money_text(before.get(part, zero)),
             _money_text(quarter.get(part, zero))]
            for part, amount in sorted(now.items(), key=lambda p: -p[1])]


def _by_month(lines):
    """(month, landed, final), oldest first, as Decimals."""
    months = {}
    for line in lines:
        landed, final = months.get(line.month, (Decimal('0.00'),
                                                Decimal('0.00')))
        months[line.month] = (landed + line.landed,
                              final + (line.landed
                                       if line.status == 'final' else 0))
    return [(name, landed, final)
            for name, (landed, final) in sorted(months.items())]


@app.get('/api/cost/invoices')
def cost_invoices():
    """Sandbox: every invoice's issuer and issue date, for the charts that
    follow the page's period filter."""
    rows = cost._read(_data_folder() / 'invoices.csv')
    return {'invoices': [[row['issuer'], row['issue_date'],
                          row.get('kind', '')] for row in rows
                         if row.get('issuer') and row.get('issue_date')]}


@app.get('/api/cost/invoice-list')
def cost_invoice_list():
    """Sandbox: the invoices this folder holds, each with its PDF, for the
    table where a person opens or downloads one."""
    rows = cost._read(_data_folder() / 'invoices.csv')
    return {'invoices': [
        {'number': row['invoice_number'], 'issuer': row['issuer'],
         'date': row['issue_date'], 'status': row['status'],
         'problem': bool(row.get('problems')), 'pdf': row['source']}
        for row in rows if row.get('invoice_number')]}


@app.get('/api/cost/invoice-pdf/{name}')
def cost_invoice_pdf(name: str, download: bool = False):
    """Sandbox: one invoice's PDF, inline to read or as a download. Only
    a file listed in invoices.csv and present in data/pdf is served."""
    listed = {row['source'] for row in
              cost._read(_data_folder() / 'invoices.csv')}
    path = _data_folder() / 'pdf' / name
    if name not in listed or not path.is_file():
        raise HTTPException(404, 'no such invoice')
    return FileResponse(path, media_type='application/pdf', filename=name,
                        content_disposition_type='attachment' if download
                        else 'inline')


@app.get('/api/cost/shipments')
def cost_shipments(request: Request):
    """The shipments themselves, dearest first. Every figure on the page
    is a sum over their lines."""
    lines = _lines(dict(request.query_params))
    return {'shipments': [{
        'shipment': shipment, 'carrier': carrier, 'mode': mode,
        'month': month, 'status': status, 'landed': _money_text(landed),
    } for shipment, carrier, mode, month, status, landed
        in cost.by_shipment(lines)]}


@app.get('/api/cost/filters')
def cost_filters():
    found = cost.choices(cost.load(_cost_folder()))
    return {'carriers': found['carrier'], 'statuses': found['status'],
            'model_connected': model.key() is not None}


# Sandbox: the page now follows the desk's own work, so its ready
# questions do too. Each answer is written by code from the same figures
# as the tiles: the latest week of invoices, the week before, and four
# weeks back.

def _ops_week():
    week = cost.desk_week(_cost_folder(), as_of())
    rows = cost._read(_data_folder() / 'invoices.csv')
    if not week:
        return None, []
    year, number = (int(part) for part in week['week'].split('-W'))
    latest = [row for row in _dated(rows) if date.fromisoformat(
        row['issue_date']).isocalendar()[:2] == (year, number)]
    return week, latest


def _ops_intake(week, latest):
    now, before = week['now'], week['before'] or {}
    said = f"{now['processed']} invoices came in during {_week_name(week['week'])}"
    if before.get('processed') is not None:
        said += f", against {before['processed']} the week before"
    return said + '.'


def _ops_target(week, latest):
    now = week['now']
    met = now['completed'] is not None and now['completed'] >= 100
    return (f"{now['completed']:.1f}% of the invoices so far are processed "
            f"against a target of 100%, so {now['remaining']:.1f}% remains; "
            + ('the target is met.' if met else 'the target is not met.'))


def _ops_issuer(week, latest):
    if not latest:
        return f"No invoices came in during {_week_name(week['week'])}."
    counts = {}
    for row in latest:
        counts[row['issuer']] = counts.get(row['issuer'], 0) + 1
    name, count = max(counts.items(), key=lambda item: item[1])
    return (f"{name} sent the most invoices in {_week_name(week['week'])}: {count} of "
            f"{len(latest)}.")


def _ops_attention(week, latest):
    look = [row['invoice_number'] for row in latest
            if row.get('problems') or row['status'] in ('revised',
                                                         'superseded')]
    if not look:
        return f"No invoice in {_week_name(week['week'])} needs a look."
    many = len(look) > 1
    return (f"{len(look)} invoice{'s' if many else ''} in {_week_name(week['week'])} "
            f"need{'' if many else 's'} a look: " + ', '.join(look) + '.')


def _ops_supplier(week, latest):
    """How many were confirmed. Nothing about four weeks ago, and
    nothing about the target: neither was asked for."""
    now = week['now']
    return (f"{now['supplier']} supplier or carrier errors were confirmed "
            f"for {_week_name(week['week'])}.")


def _ops_automation(week, latest):
    now = week['now']
    return (f"{now['errors']:.1f}% of the invoices in {_week_name(week['week'])} were "
            "flagged by the reader as automation errors, against a target "
            "under 1%.")


def _ops_status(week, latest):
    if not latest:
        return f"No invoices came in during {_week_name(week['week'])}."
    counts = {}
    for row in latest:
        kind = 'problem' if row.get('problems') else row['status']
        counts[kind] = counts.get(kind, 0) + 1
    parts = ', '.join(f'{count} {kind}' for kind, count in
                      sorted(counts.items(), key=lambda item: -item[1]))
    return f"Of the {len(latest)} invoices in {_week_name(week['week'])}: {parts}."


def _ops_invoice(number):
    """One invoice by its number: who sent it, when, and its status."""
    for row in cost._read(_data_folder() / 'invoices.csv'):
        if row['invoice_number'].upper() == number.upper():
            kind = 'flagged with a problem' if row.get('problems') \
                else row['status']
            return (f"{row['invoice_number']} came from {row['issuer']} on "
                    f"{row['issue_date']} and is {kind}.")
    return f'No invoice numbered {number} is on file.'


#: The topics a typed question can be about, each answered by code. The
#: model only picks the topic; it never writes a figure.
OPS_TOPICS = {
    'intake': ('how many invoices came in', _ops_intake),
    'target': ('whether the desk is on target, what remains', _ops_target),
    'issuer': ('which issuer sent the most invoices', _ops_issuer),
    'attention': ('which invoices need a look, revised or with a problem',
                  _ops_attention),
    'supplier': ('supplier or carrier errors found', _ops_supplier),
    'automation': ('automation errors, invoices the reader flagged',
                   _ops_automation),
    'status': ('how the invoices split by status', _ops_status),
}

_INVOICE_NUMBER = re.compile(r'\b[A-Z]{2,4}-(?:CN-)?\d{4}-\d{4}(?:-R\d)?\b',
                             re.IGNORECASE)

OPS_HELP = ('I answer questions about the desk\'s work: invoices that came '
            'in, the target, the top issuer, invoices that need a look, '
            'supplier errors, automation errors, the status split, or one '
            'invoice by its number.')


def _ops_topic(question, chosen):
    """Ask the model for one topic name, or 'none'. Anything else is none.

    A model that cannot be reached is not a question nobody understood.
    The failure travels up, so the answer says the model is down instead
    of listing what can be asked, as the anomaly view already does.
    """
    menu = '\n'.join(f'- {name}: {about}'
                     for name, (about, _) in OPS_TOPICS.items())
    prompt = ('A person asked a question on an invoice-processing dashboard.'
              ' Reply with exactly one word: the name of the topic below '
              "that the question is about, or 'none' if it fits none.\n"
              f'{menu}\nQuestion: {question}')
    said = (chosen(prompt) or '').strip().lower()
    said = re.sub(r'[^a-z]', '', said.split()[0]) if said else ''
    return said if said in OPS_TOPICS else None


#: Each ready question names its topic in OPS_TOPICS. Each is an
#: overview, so it opens five plots from five categories.
OPS_CHIPS = [
    ('Show me an overview of this week', 'intake'),
    ('Show me an overview of the targets', 'target'),
    ('Show me an overview of the issuers', 'issuer'),
    ('Show me an overview of the errors', 'supplier'),
]


# Sandbox: the panels each answer opens over the dashboard, as in the
# original assistant. Every row is counted here, from the same files as
# the tiles.

def _week_key(day):
    year, number, _ = date.fromisoformat(day).isocalendar()
    return f'{year}-W{number:02d}'


_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
           'Oct', 'Nov', 'Dec']


def _week_name(key):
    """No "W" on the dashboard: a week reads as its month and its place in
    it, "May - Week 3", by the month of its Thursday."""
    year, number = (int(part) for part in key.split('-W'))
    thursday = date.fromisocalendar(year, number, 4)
    place = (thursday.day - 1) // 7 + 1
    return f'{_MONTHS[thursday.month - 1]} - Week {place}'


_SHORT = {
    'Keuhne & Nager Logistics AG': 'Keuhne+Nager',
    'Marsk Line Agencies B.V.': 'Marsk',
    'COSMO Shipping Lines Co., Ltd.': 'COSMO',
    'Guangzhou Verrelia Glassworks Ltd.': 'Verrelia',
    'Hanil Cosmetic Vessels Co., Ltd.': 'Hanil',
    'Aravalli Labelworks Pvt. Ltd.': 'Aravalli',
    'Binh Duong Tubeworks JSC': 'Binh Duong',
    'Shantou Brightpack Packaging Co., Ltd.': 'Brightpack',
    'Ningbo Caplink Industrial Co., Ltd.': 'Caplink',
    'DHI Global Forwarding (HK) Ltd.': 'DHI',
}


def _short(issuer):
    return _SHORT.get(issuer, issuer.split(' ')[0])


def _last_weeks(week, many=8):
    """The latest week and the ones before it, oldest first."""
    year, number = (int(part) for part in week['week'].split('-W'))
    monday = date.fromisocalendar(year, number, 1)
    return [_week_key((monday - timedelta(weeks=back)).isoformat())
            for back in range(many - 1, -1, -1)]


def _count_by(rows, key):
    counts = {}
    for row in rows:
        counts[key(row)] = counts.get(key(row), 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])


def _dated(rows):
    """The rows a weekly axis can hold. The reader does not always find a
    date on the page, and it sometimes reads a year that has not happened.
    Neither belongs in a week."""
    today = as_of().isoformat()
    return [row for row in rows
            if row.get('issue_date') and row['issue_date'] <= today]


def _ops_panels(topic, week, latest):
    rows = _dated(cost._read(_data_folder() / 'invoices.csv'))
    weeks = _last_weeks(week)
    per_week = dict(_count_by(rows, lambda r: _week_key(r['issue_date'])))
    status = _count_by(latest, lambda r: 'problem' if r.get('problems')
                       else r['status'])
    issuers = _count_by(latest, lambda r: r['issuer'])
    named = _week_name(week['week'])
    received = Panel('ops_received', 'column', 'Invoices per week',
                     [[_week_name(w), per_week.get(w, 0)] for w in weeks])
    by_issuer = Panel('ops_issuers', 'bar', f'Issuers in {named}',
                      [[_short(name), count] for name, count in issuers])
    by_status = Panel('ops_status', 'pie', f'Status in {named}',
                      [[name, count] for name, count in status])
    now = week['now']
    desk = Panel('ops_desk', 'tiles', f'The desk in {named}', [
        ['Processed', now['processed']],
        ['Completed', f"{now['completed']:.1f}%"],
        ['Remaining to target', f"{now['remaining']:.1f}%"],
        ['Automation errors', f"{now['errors']:.1f}%"],
        ['Supplier errors', now['supplier']]])
    look = Panel('ops_attention', 'tiles', 'Invoices that need a look', [
        [row['invoice_number'], 'problem' if row.get('problems')
         else row['status']] for row in latest
        if row.get('problems') or row['status'] in ('revised', 'superseded')])
    supplier = {}
    for row in _dated(cost._read(_data_folder() / 'anomalies.csv')):
        if row.get('origin') == 'client' and row.get('decision') == 'confirmed':
            key = _week_key(row['issue_date'])
            supplier[key] = supplier.get(key, 0) + 1
    by_supplier = Panel('ops_supplier', 'column', 'Supplier errors per week',
                        [[_week_name(w), supplier.get(w, 0)] for w in weeks])
    return {
        'intake': [received, by_issuer, desk],
        'target': [desk, received],
        'issuer': [by_issuer, received],
        'attention': [look, by_status],
        'supplier': [by_supplier, desk],
        'automation': [desk, by_status],
        'status': [by_status, look],
    }[topic]


def _ops_answer(topic, week, latest):
    return _answer_dict(cost_answering.Answer(
        panels=_ops_panels(topic, week, latest),
        sentence=OPS_TOPICS[topic][1](week, latest), rows_used=len(latest),
        as_of=as_of()))


@app.get('/api/cost/suggestions')
def cost_chips():
    return {'chips': [{'question': question, 'panels': []}
                      for question, _ in OPS_CHIPS]}


@app.post('/api/cost/chip')
def cost_click(body: dict):
    index = body.get('chip')
    if not isinstance(index, int) or not 0 <= index < len(OPS_CHIPS):
        raise HTTPException(400, 'unknown chip')
    week, latest = _ops_week()
    if not week:
        return _answer_dict(cost_answering.Answer(
            rows_used=0, as_of=as_of(), refusal='No invoices to read yet.'))
    return _ops_answer(OPS_CHIPS[index][1], week, latest)


@app.post('/api/cost/ask')
def cost_ask(body: dict):
    """Sandbox: a typed question about the desk's work. An invoice number
    is looked up directly; anything else the model sorts into one topic,
    and code writes the answer, so no figure is invented."""
    question = _question(body)
    week, latest = _ops_week()
    found = _INVOICE_NUMBER.search(question)
    if found:
        return _answer_dict(cost_answering.Answer(
            sentence=_ops_invoice(found.group(0)), rows_used=1,
            as_of=as_of()))
    chosen = model_for_this_request()
    if chosen is None:
        return _answer_dict(cost_answering.Answer(
            rows_used=0, as_of=as_of(), refusal=NO_KEY))
    try:
        topic = _ops_topic(question, chosen)
    except Exception as failure:
        return _answer_dict(cost_answering.Answer(
            rows_used=0, as_of=as_of(),
            refusal=f'The model could not be reached: {failure}.'))
    if not topic or not week:
        return _answer_dict(cost_answering.Answer(
            sentence=OPS_HELP, rows_used=0, as_of=as_of()))
    return _ops_answer(topic, week, latest)


# ------------------------------------------------------- the anomaly view
#
# The second view on the rail. The checking model of project 02 scored
# every invoice into data/anomalies.csv; these endpoints serve it.


def _scored(given):
    unknown = set(given) - set(anomalies.FILTERS)
    if unknown:
        raise HTTPException(400, f'unknown filter: {sorted(unknown)}')
    return anomalies.only(anomalies.load(_data_folder()), **given)


def _ours():
    return anomalies.our_errors(_cost_folder())


#: The anomaly tiles, in the order the desk reads them: what the model
#: saw, what it raised, the money on it, and what the analyst did with it.
#: Each target is a sentence the desk is judged on, not a measurement.
ANOMALY_TILES = [
    ('Scored', 'scored', 'processed', 'every invoice'),
    ('Flagged', 'flagged', 'errors', 'five a week'),
    ('Money flagged', 'money', 'supplier', 'none'),
    ('Confirmed', 'confirmed', 'completed', 'all in 7 days'),
    ('Waiting', 'waiting', 'remaining', 'none left'),
]


def _anomaly_tiles(week):
    """The five anomaly tiles, each with its value, its change against
    last week and the week a month back, and its target."""
    if not week:
        return []
    now = week['now']

    def moved(key, then):
        if not then or then.get(key) is None:
            return None
        return now[key] - then[key]

    def whole(amount):
        """Money to the real, not the centavo. The tile is one line wide
        and nobody reads a centavo at this size."""
        return f'{int(amount):,}'

    short = _short_money

    def arrow(key, then, period):
        change = moved(key, then)
        if change is None or key != 'money':
            return _arrow(change, period, '')
        mark = '▲' if change > 0 else '▼' if change < 0 else '='
        return f'{mark} {short(abs(change))} {period}'

    tiles = []
    for name, key, icon, target in ANOMALY_TILES:
        value = whole(now[key]) if key == 'money' else str(now[key])
        tiles.append({
            'name': name, 'value': value, 'target': target,
            'icon': _tile_icon(icon),
            'change': arrow(key, week['before'], 'last week'),
            'month': arrow(key, week['month'], 'last month'),
        })
    return tiles


@app.get('/api/anomalies/overview')
def anomaly_overview(request: Request):
    rows = _scored(dict(request.query_params))
    rate = anomalies.flag_rate(rows)
    return {
        'desk': _anomaly_tiles(anomalies.desk_week(rows, as_of())),
        'reviewed': anomalies.reviewed(rows),
        'flagged_count': anomalies.flagged_count(rows),
        'flagged_total': _money_text(anomalies.flagged_total(rows)),
        'flag_rate': f'{rate}%' if rate is not None else None,
        'our_errors': _ours(),
        'client_errors': anomalies.client_errors(rows),
        'by_origin': [[label, count] for label, count
                      in anomalies.by_origin(rows, ours=_ours())],
        'by_decision': [[name, count, _money_text(amount)]
                        for name, count, amount in anomalies.by_decision(rows)],
        'by_stage': [[name, count, _money_text(amount)]
                     for name, count, amount in anomalies.by_stage(rows)],
        'by_check': [[name, count] for name, count in anomalies.by_check(rows)],
        'by_supplier': [[name, count, _money_text(amount)]
                        for name, count, amount in anomalies.by_supplier(rows)],
        'by_week': [[week, flagged, total, _money_text(amount)]
                    for week, flagged, total, amount in anomalies.by_week(rows)],
    }


@app.get('/api/anomalies/list')
def anomaly_list(request: Request):
    """Every scored invoice, flagged first, highest score first."""
    rows = sorted(_scored(dict(request.query_params)),
                  key=lambda row: (not row.flagged, -row.score))
    return {'invoices': [{
        'number': row.number,
        'supplier': row.supplier,
        'issued': row.issued,
        'total': _money_text(row.total),
        'score': float(row.score),
        'stage': row.stage,
        'check': row.check,
        'checks': row.checks,
        'flagged': row.flagged,
        'decision': row.decision,
    } for row in rows]}


@app.get('/api/anomalies/filters')
def anomaly_filters():
    rows = anomalies.load(_data_folder())
    return {'suppliers': anomalies.suppliers(rows),
            'stages': anomalies.stages(rows),
            'model_connected': model.key() is not None}


@app.get('/api/anomalies/suggestions')
def anomaly_chips():
    return {'chips': [{'question': chip.question, 'panels': chip.panels}
                      for chip in anomaly_answering.CHIPS]}


@app.post('/api/anomalies/chip')
def anomaly_click(body: dict):
    index = body.get('chip')
    if not isinstance(index, int) or not 0 <= index < len(anomaly_answering.CHIPS):
        raise HTTPException(400, 'unknown chip')
    rows = _scored(body.get('filters') or {})
    return _answer_dict(anomaly_answering.click(
        anomaly_answering.CHIPS[index], rows, today=as_of(), ours=_ours()))


@app.post('/api/anomalies/ask')
def anomaly_ask(body: dict):
    question = _question(body)
    chosen = model_for_this_request()
    if chosen is None:
        return _answer_dict(anomaly_answering.Answer(
            rows_used=0, as_of=as_of(), refusal=NO_KEY))
    history = _history(body)
    rows = _scored(body.get('filters') or {})
    return _answer_dict(anomaly_answering.answer(
        question, rows, today=as_of(), model=chosen, history=history,
        ours=_ours()))


# --------------------------------------------------------- the finance view
#
# The third view on the rail. It asks the landed cost questions, which is
# what `cost_answering` and `cost_panels` were built for: what the parts
# cost, what the cost is made of, which carrier moved the most, which part
# is dearest per unit, how much is still provisional. The invoice view has
# its own topics and does not use these.


@app.get('/api/finance/suggestions')
def finance_chips():
    return {'chips': [{'question': chip.question, 'panels': chip.panels}
                      for chip in cost_answering.CHIPS]}


@app.post('/api/finance/chip')
def finance_click(body: dict):
    index = body.get('chip')
    if not isinstance(index, int) or not 0 <= index < len(cost_answering.CHIPS):
        raise HTTPException(400, 'unknown chip')
    lines = _lines(body.get('filters') or {})
    return _answer_dict(cost_answering.click(
        cost_answering.CHIPS[index], lines, today=as_of()))


@app.post('/api/finance/ask')
def finance_ask(body: dict):
    question = _question(body)
    chosen = model_for_this_request()
    if chosen is None:
        return _answer_dict(cost_answering.Answer(
            rows_used=0, as_of=as_of(), refusal=NO_KEY))
    lines = _lines(body.get('filters') or {})
    return _answer_dict(cost_answering.answer(
        question, lines, today=as_of(), model=chosen,
        history=_history(body)))


_PAGE_FILE = Path(__file__).resolve().parent / 'page.html'
