"""Sandbox: an answer drawn as a plot that looks made for the question.

The plots are templates made in advance, three per category of question.
A question is sorted into a category; its words, cleaned up, become a key;
the key picks one of the category's three plots, so the same question
always shows the same plot and a new one usually shows another. Code then
fills the plot with real figures from the data files. Nothing is drawn by
the model and no figure is invented.
"""

import csv
import hashlib
import re
from datetime import date
from pathlib import Path

CATEGORIES = ['volume', 'target', 'errors', 'ranking', 'trend', 'mix',
              'lookup', 'overview']

#: The three plots of each category, in the order the page draws them.
PLOTS = {
    'volume': ['columns', 'weekday heatmap', 'cumulative area'],
    'target': ['bullets', 'gauge', 'line with target'],
    'errors': ['bars by type', 'days to decide', 'type by week'],
    'ranking': ['bars', 'treemap', 'catplot'],
    'trend': ['two lines', 'waterfall', 'stacked area'],
    'mix': ['donut', 'status share', 'nested treemap'],
    'lookup': ['table', 'timeline', 'detail card'],
    'overview': ['attention list', 'sparkline tiles', 'target matrix'],
}

#: Words that send a question to a category when no model is at hand. The
#: first category with a match wins, so the narrower ones come first.
KEYWORDS = [
    # `find` on its own sent "how many supplier errors did we find?" to a
    # timeline of one document. A lookup names a document, so the word
    # has to carry one.
    ('lookup', r'\b(status of|history|show me|list|replaced|'
               r'find (the )?invoice|which invoices)\b'),
    ('target', r'\b(target|on track|goal|hit|met|meet)\b'),
    ('errors', r'\b(error|errors|mistake|wrong|problem|problems|fail)\b'),
    ('ranking', r'\b(most|top|who|which supplier|which issuer|which actor|biggest|slowest)\b'),
    ('trend', r'\b(trend|compared|compare|vs|versus|up or down|than usual|last month)\b'),
    ('mix', r'\b(share|split|mix|type|types|kind|freight|customs|goods|percent)\b'),
    ('overview', r'\b(summary|overview|worry|attention|anything|how are we|recap)\b'),
    ('volume', r'\b(how many|how much|count|volume|came in|received|processed)\b'),
]

INVOICE_NUMBER = re.compile(r'\b[A-Z]{2,4}-(?:CN-)?\d{4}-\d{4}(?:-R\d)?\b',
                            re.IGNORECASE)

#: A question whose whole answer is one number. "How many came in?" is
#: answered by the sentence; a chart beside it is decoration, and the
#: panel that holds it is in the way.
PLAIN = re.compile(r'^\s*(how many|how much|what is|what was|is it|are we|'
                   r'did we|was it|who|which)\b', re.IGNORECASE)

#: Words that ask to see a shape rather than a figure.
WANTS_A_PLOT = re.compile(r'\b(trend|over time|per week|by week|by type|'
                          r'by issuer|by supplier|breakdown|split|share|'
                          r'compare|compared|distribution|chart|graph|'
                          r'show|history|each|every)\b', re.IGNORECASE)


def wants_a_plot(question):
    """True when the question asks for a shape, not a single figure."""
    if INVOICE_NUMBER.search(question):
        return True
    if WANTS_A_PLOT.search(question):
        return True
    return not PLAIN.match(question or '')


#: An overview answers with five plots from five categories. The subject
#: named in the question picks which five; anything else gets the first.
OVERVIEW_SETS = [
    (re.compile(r'\b(error|errors|mistake|problem)', re.IGNORECASE),
     ['errors', 'target', 'trend', 'ranking', 'overview']),
    (re.compile(r'\b(issuer|issuers|supplier|suppliers|carrier)', re.IGNORECASE),
     ['ranking', 'volume', 'errors', 'mix', 'trend']),
    (re.compile(r'\b(target|targets|goal|desk|performance)', re.IGNORECASE),
     ['target', 'overview', 'volume', 'errors', 'trend']),
    (re.compile(r'.'), ['volume', 'target', 'ranking', 'mix', 'trend']),
]

OVERVIEW = re.compile(r'\boverview\b', re.IGNORECASE)


def wants_an_overview(question):
    """True for 'show me an overview of...' and for a simple question
    whose answer is one number: both get five plots."""
    if INVOICE_NUMBER.search(question or ''):
        return False
    return bool(OVERVIEW.search(question or '')) or not wants_a_plot(question)


def overview_set(question):
    """The five categories an overview of this subject shows."""
    for pattern, categories in OVERVIEW_SETS:
        if pattern.search(question or ''):
            return categories
    return OVERVIEW_SETS[-1][1]


def clean(question):
    """The key: lower case, no punctuation, single spaces."""
    text = re.sub(r'[^a-z0-9\- ]+', ' ', question.lower())
    return re.sub(r'\s+', ' ', text).strip()


def category_by_words(question):
    if INVOICE_NUMBER.search(question):
        return 'lookup'
    lowered = question.lower()
    for name, pattern in KEYWORDS:
        if re.search(pattern, lowered):
            return name
    return 'overview'


def category_by_model(question, model):
    """Ask the model for one category name; anything else falls back to
    the keyword rules.

    `lookup` is the one category the model may not invent. It means a
    named invoice, and without a number on the page it sent a question
    about supplier errors to a timeline of one document.
    """
    if INVOICE_NUMBER.search(question):
        return 'lookup'
    menu = ', '.join(CATEGORIES)
    prompt = ('Sort this question about invoices into exactly one category. '
              f'Reply with one word from: {menu}.\n'
              'volume: how many came in or were processed. target: whether '
              'a goal was met. errors: errors found, their rate. ranking: who '
              'or what leads. trend: up or down against another period. mix: '
              'the share of a type or status. lookup: one invoice or a list '
              'of them. overview: a summary or what needs attention.\n'
              f'Question: {question}')
    try:
        said = re.sub(r'[^a-z]', '', (model(prompt) or '').strip().lower().split()[0])
    except Exception:
        said = ''
    if said == 'lookup' or said not in CATEGORIES:
        return category_by_words(question)
    return said


class Picker:
    """Same key, same plot. A new key gets the plot its hash points to,
    unless that is the plot this category showed last; then the next one.
    Each choice is kept, so asking again shows the same plot."""

    def __init__(self):
        self.chosen = {}
        self.last = {}

    def pick(self, category, key):
        remembered = self.chosen.get((category, key))
        if remembered is not None:
            return remembered, True
        count = len(PLOTS[category])
        index = int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16) % count
        if index == self.last.get(category):
            index = (index + 1) % count
        self.chosen[(category, key)] = index
        self.last[category] = index
        return index, False


# ------------------------------------------------------------ the figures

_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
           'Oct', 'Nov', 'Dec']

SHORT = {
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
    'Santos Comissaria Aduaneira Ltda.': 'Santos Comissaria',
    'Terminal Valongo Alfandegado Ltda.': 'Valongo',
    'Transportes Lima Vieira Ltda.': 'Lima Vieira',
}


def _short(name):
    return SHORT.get(name, name.split(' ')[0])


def _read(path):
    if not Path(path).exists():
        return []
    with open(path, encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def _week(day):
    return date.fromisoformat(day).isocalendar()[:2]


def _week_name(week):
    thursday = date.fromisocalendar(week[0], week[1], 4)
    return f'{_MONTHS[thursday.month - 1]} - Week {(thursday.day - 1) // 7 + 1}'


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def figures(data_folder, year_file):
    """Every figure the 24 plots can show, from the files on disk."""
    # The real run holds a few invoices it could not read a date from, or
    # read one in the future from; neither belongs on a weekly axis.
    today = date.today().isoformat()
    invoices = [r for r in _read(Path(data_folder) / 'invoices.csv')
                if r.get('issue_date') and r['issue_date'] <= today]
    anomalies = _read(Path(data_folder) / 'anomalies.csv')
    year = _read(year_file)

    weeks = sorted({_week(r['issue_date']) for r in invoices})[-8:]
    names = [_week_name(w) for w in weeks]
    span = set(weeks)
    rows = [r for r in invoices if _week(r['issue_date']) in span]
    by_week = {w: [r for r in rows if _week(r['issue_date']) == w] for w in weeks}
    counts = [len(by_week[w]) for w in weeks]

    weekday = [[sum(1 for r in by_week[w]
                    if date.fromisoformat(r['issue_date']).weekday() == d)
                for w in weeks] for d in range(7)]

    completed = [round(100 * sum(1 for r in by_week[w] if not r.get('problems'))
                       / len(by_week[w]), 1) if by_week[w] else 100.0 for w in weeks]
    automation = [round(100 * sum(1 for r in by_week[w] if r.get('problems'))
                        / len(by_week[w]), 1) if by_week[w] else 0.0 for w in weeks]
    revised = [sum(1 for r in by_week[w] if r['status'] == 'revised') for w in weeks]
    superseded = [sum(1 for r in by_week[w] if r['status'] == 'superseded') for w in weeks]

    # The real run records every supplier error in labels.csv, with the
    # days it took to find. Without it, the errors the client confirmed.
    labels = _read(Path(data_folder) / 'labels.csv')
    if labels:
        confirmed = [r for r in labels if r.get('anomaly') and _week(r['issue_date']) in span]
        decide = [[weeks.index(_week(r['issue_date'])), int(r['found_after_days'])]
                  for r in confirmed if r.get('found_after_days')]
    else:
        confirmed = [r for r in anomalies if r.get('origin') == 'client'
                     and r.get('decision') == 'confirmed' and _week(r['issue_date']) in span]
        decide = [[weeks.index(_week(r['issue_date'])), _days(r['issue_date'], r['decided_on'])]
                  for r in confirmed if r.get('decided_on')]
    supplier = [sum(1 for r in confirmed if _week(r['issue_date']) == w) for w in weeks]
    in_week = sum(1 for _, d in decide if d <= 7)
    found_in_7 = round(100 * in_week / len(decide), 1) if decide else 100.0

    issuers = {}
    for r in rows:
        issuers[r['issuer']] = issuers.get(r['issuer'], 0) + 1
    ranked = sorted(issuers.items(), key=lambda item: -item[1])
    half = weeks[len(weeks) // 2:], weeks[:len(weeks) // 2]
    top4 = [name for name, _ in ranked[:4]]
    lines_now = [[int(r['line_count']) for r in rows if r['issuer'] == n
                  and _week(r['issue_date']) in half[0]] for n in top4]
    lines_before = [[int(r['line_count']) for r in rows if r['issuer'] == n
                     and _week(r['issue_date']) in half[1]] for n in top4]

    year_rows = [r for r in year if r.get('issue_date') and _week(r['issue_date']) in span]
    kinds = {}
    for r in year_rows:
        kinds[r.get('kind') or 'other'] = kinds.get(r.get('kind') or 'other', 0) + 1
    kind_order = [k for k, _ in sorted(kinds.items(), key=lambda item: -item[1])]
    top_kinds = kind_order[:3]
    kind_weeks = {k: [sum(1 for r in year_rows if (r.get('kind') or 'other') == k
                          and _week(r['issue_date']) == w) for w in weeks] for k in top_kinds}
    kind_weeks['other'] = [sum(1 for r in year_rows if (r.get('kind') or 'other') not in top_kinds
                               and _week(r['issue_date']) == w) for w in weeks]
    kind_status = {}
    for r in year_rows:
        key = r.get('kind') or 'other'
        key = key if key in top_kinds else 'other'
        kind_status.setdefault(key, {})
        kind_status[key][r['status']] = kind_status[key].get(r['status'], 0) + 1

    status_share = {s: [round(100 * sum(1 for r in by_week[w] if r['status'] == s)
                              / len(by_week[w]), 1) if by_week[w] else 0 for w in weeks]
                    for s in ('new', 'revised', 'superseded')}

    latest = sorted(rows, key=lambda r: (r['issue_date'], r['invoice_number']), reverse=True)
    table = [[r['invoice_number'], _short(r['issuer']), r['status']] for r in
             sorted(latest, key=lambda r: r['status'] == 'new')[:7]]

    total = counts[-1]
    previous = counts[-2] if len(counts) > 1 else None
    month_back = counts[-5] if len(counts) > 4 else None

    return {
        'weeks': names, 'counts': counts, 'weekday': weekday,
        'total': total,
        'vs_week': None if not previous else round(100 * (total - previous) / previous),
        'vs_month': None if not month_back else round(100 * (total - month_back) / month_back),
        'completed': completed, 'automation': automation, 'revised': revised,
        'superseded': superseded, 'supplier': supplier, 'decide': decide,
        'found_in_7': found_in_7,
        'bullets': [['Processed', completed[-1], 100, completed[-1] >= 100],
                    ['Automation errors · under 1%', automation[-1], 1, automation[-1] < 1],
                    ['Supplier errors found in 7 days', found_in_7, 100, found_in_7 >= 100],
                    ['No revised invoices', 100.0 if revised[-1] == 0 else 0.0, 100,
                     revised[-1] == 0]],
        'error_types': [['Supplier errors', sum(supplier)], ['Automation errors', 0],
                        ['Revised invoices', sum(revised)], ['Superseded invoices', sum(superseded)]],
        'error_matrix': [supplier, [0] * len(weeks), revised, superseded],
        'issuers': [[_short(n), c] for n, c in ranked],
        'catplot': {'actors': [_short(n) for n in top4], 'now': lines_now,
                    'before': lines_before},
        'this_month': counts[len(counts) // 2:], 'last_month': counts[:len(counts) // 2],
        'kinds': [[k, kinds[k]] for k in kind_order],
        'kind_weeks': kind_weeks,
        'kind_status': kind_status,
        'status_share': status_share,
        'table': table,
        'invoices': {r['invoice_number']: r for r in rows},
        'matrix_kpis': ['Processed', 'Automation', 'Supplier', 'Revised'],
        'matrix': [[1 if c >= 100 else 0 for c in completed],
                   [1 if a < 1 else 0 for a in automation],
                   [1 if s == 0 else 0 for s in supplier],
                   [1 if v == 0 else 0 for v in revised]],
    }


def lookup(fig, question):
    """The object a lookup question names, or the latest revised one, with
    its history and its card."""
    found = INVOICE_NUMBER.search(question)
    invoices = fig['invoices']
    number = found.group(0).upper() if found else None
    if number not in invoices:
        revised = [n for n, r in invoices.items() if r['status'] == 'revised']
        number = sorted(revised)[-1] if revised else sorted(invoices)[-1]
    row = invoices[number]
    original = row.get('revises') or ''
    steps = []
    if original and original in invoices:
        first = invoices[original]
        steps.append(['Issued by ' + _short(first['issuer']), first['issue_date'], ''])
        steps.append(['Revised version received', row['issue_date'], 'warn'])
        steps.append(['First version superseded', row['issue_date'], ''])
    else:
        steps.append(['Issued by ' + _short(row['issuer']), row['issue_date'], ''])
        steps.append(['Read into the ledger', row['first_seen'][:10], ''])
        if row['status'] != 'new':
            steps.append([row['status'].capitalize(), row['issue_date'], 'warn'])
    replaced_by = next((n for n, r in invoices.items() if r.get('revises') == number), '')
    card = [['Actor', _short(row['issuer'])], ['Issued', row['issue_date']],
            ['Due', row['due_date']], ['Status', row['status']],
            ['Lines', row['line_count']], ['Total', row['grand_total']],
            ['Revises', original or '-'], ['Replaced by', replaced_by or '-']]
    return {'number': number, 'steps': steps, 'card': card}


def attention(fig):
    items = []
    total = fig['total']
    items.append(['met' if fig['completed'][-1] >= 100 else 'missed',
                  f"{total} invoices came in; {fig['completed'][-1]:.0f}% processed."])
    if fig['revised'][-1]:
        items.append(['warn', f"{fig['revised'][-1]} object revised this week."])
    items.append(['met' if fig['supplier'][-1] == 0 else 'missed',
                  f"{fig['supplier'][-1]} supplier errors confirmed this week."])
    if fig['vs_week'] is not None:
        arrow = '▲' if fig['vs_week'] >= 0 else '▼'
        items.append(['volume', f"Volume {arrow} {abs(fig['vs_week'])}% on last week."])
    items.append(['met' if fig['found_in_7'] >= 100 else 'missed',
                  f"Supplier errors decided within 7 days: {fig['found_in_7']:.0f}%."])
    return items
