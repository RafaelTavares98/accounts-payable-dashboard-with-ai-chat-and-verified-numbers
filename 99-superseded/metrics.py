"""Every figure the dashboard can show, and nothing else.

One function per figure. The model is never allowed to produce a number, so
every number in every answer has to come out of one of these.
"""

from decimal import Decimal

FIGURES = (
    'total_owed', 'count', 'ticket_average',
    'overdue_total', 'overdue_count', 'overdue_rate',
    'average_days_overdue', 'oldest_overdue',
    'overdue_buckets', 'by_supplier', 'by_month',
    'by_order', 'by_item', 'by_due_week', 'by_issue_week',
    'by_category',
)

NEEDS_TODAY = {
    'overdue_total', 'overdue_count', 'overdue_rate',
    'average_days_overdue', 'oldest_overdue', 'overdue_buckets',
}


class NoSuchFigure(Exception):
    """A figure name that is not on the menu was asked for."""


def format_money(value):
    """For sentences: thousands separated by comma, two decimals."""
    if isinstance(value, Decimal):
        return f'{value:,.2f}'
    return f'{value:,}'.replace(',', ' ')


def _late(owed, today):
    return [row for row in owed
            if not row.is_credit and row.due is not None and row.due < today]


def total_owed(owed):
    return sum((row.total for row in owed), Decimal('0.00'))


def count(owed):
    return len(owed)


def ticket_average(owed):
    if not owed:
        return None
    return (total_owed(owed) / count(owed)).quantize(Decimal('0.01'))


def overdue_total(owed, today):
    return sum((row.total for row in _late(owed, today)), Decimal('0.00'))


def overdue_count(owed, today):
    return len(_late(owed, today))


def overdue_rate(owed, today):
    if not owed:
        return None
    share = Decimal(overdue_count(owed, today)) / Decimal(count(owed)) * 100
    return share.quantize(Decimal('0.1'))


def average_days_overdue(owed, today):
    late = _late(owed, today)
    if not late:
        return None
    days = sum(((today - row.due).days for row in late), Decimal(0))
    return (days / Decimal(len(late))).quantize(Decimal('0.1'))


def oldest_overdue(owed, today):
    late = _late(owed, today)
    if not late:
        return None
    return max(late, key=lambda row: (today - row.due).days)


def overdue_buckets(owed, today):
    """Four bands, always, so a missing bar reads as an empty band."""
    bands = [(31, '1 to 30 days'), (61, '31 to 60 days'),
             (91, '61 to 90 days'), (None, 'over 90 days')]
    buckets = [(label, 0, Decimal('0.00')) for _, label in bands]
    for row in _late(owed, today):
        days = (today - row.due).days
        for index, (limit, _label) in enumerate(bands):
            if limit is None or days < limit:
                label, so_far, value = buckets[index]
                buckets[index] = (label, so_far + 1, value + row.total)
                break
    return buckets


def _group(owed, key):
    grouped = {}
    for row in owed:
        grouped.setdefault(key(row), Decimal('0.00'))
        grouped[key(row)] += row.total
    return grouped


def by_supplier(owed):
    grouped = _group(owed, lambda row: row.supplier)
    return sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))


def by_month(owed):
    """One label per month between the first and the last, gaps filled
    with zero, oldest first."""
    grouped = _group(owed, lambda row: row.issued.strftime('%Y-%m')
                    if row.issued else '')
    if not owed:
        return []
    first = min(row.issued for row in owed if row.issued)
    last = max(row.issued for row in owed if row.issued)
    labels = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        labels.append(f'{year:04d}-{month:02d}')
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return [(label, grouped.get(label, Decimal('0.00'))) for label in labels]


#: What a line is, read off its own words. An invoice carries no
#: category column, so this is a guess; the order matters, because the
#: first list whose word appears wins, and anything unplaced is Other
#: rather than pushed into the nearest bucket.
CATEGORIES = (
    ('Freight', ('ocean freight', 'air freight', 'inland haulage',
                 'road haulage', 'sea freight')),
    ('Surcharges and fees', ('surcharge', ' fee', 'handling', 'storage',
                             'brokerage', 'insurance', 'demurrage',
                             'documentation', 'clearance', 'adjustment')),
    ('Bottles and jars', ('bottle', 'jar', 'flacon', 'vial')),
    ('Closures and pumps', ('cap', 'pump', 'closure', 'dropper',
                            'sprayer', 'dispenser', 'applicator')),
    ('Labels and cartons', ('label', 'carton', 'sleeve', 'box',
                            'insert', 'leaflet')),
    ('Tubes', ('tube',)),
    ('Other', ()),
)


def category_of(description):
    """The category one line belongs to, from its words alone."""
    words = description.lower()
    for name, marks in CATEGORIES:
        if any(mark in words for mark in marks):
            return name
    return 'Other'


def by_category(owed):
    """What the money was spent on, biggest first."""
    grouped = {}
    for row in owed:
        for line in row.lines:
            name = category_of(line.description)
            grouped[name] = grouped.get(name, Decimal('0.00')) + line.net
    return sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))


def changes(series):
    """Every step in a series, as from, to and the difference.

    A question about a fall is a question about one of these. Without
    them the model is asked to explain a change nobody measured.
    """
    moves = []
    for (_, before), (label, after) in zip(series, series[1:]):
        moves.append((label, before, after, after - before))
    return moves


def sharpest(series, rising=False):
    """The one step that moved most, down by default."""
    moves = changes(series)
    if not moves:
        return None
    pick = max if rising else min
    return pick(moves, key=lambda move: move[3])


def _monday(day):
    from datetime import timedelta
    return day - timedelta(days=day.weekday())


def _weekly(owed, pick, weeks=None):
    """Money grouped into weeks, with no week missing in the middle.

    `weeks` pins the labels, so two series can be drawn on one axis
    instead of each one choosing its own.
    """
    from datetime import date, timedelta

    grouped = {}
    for row in owed:
        when = pick(row)
        if not when:
            continue
        grouped.setdefault(_monday(when), Decimal('0.00'))
        grouped[_monday(when)] += row.total

    if weeks is not None:
        return [(label, grouped.get(date.fromisoformat(label),
                                    Decimal('0.00'))) for label in weeks]
    if not grouped:
        return []

    week, last, out = min(grouped), max(grouped), []
    while week <= last:
        out.append((week.isoformat(), grouped.get(week, Decimal('0.00'))))
        week += timedelta(days=7)
    return out


def by_issue_week(owed, weeks=None):
    """What arrived each week. The companion to what falls due."""
    return _weekly(owed, lambda row: row.issued, weeks)


def by_due_week(owed):
    """What falls due each week, oldest week first.

    Grouping by the month a bill was issued gives two points over an
    eight week window, which draws a straight line and tells nobody
    anything. The week a bill comes due is the question a payables desk
    actually has.
    """
    from datetime import timedelta

    dated = [row for row in owed if row.due]
    if not dated:
        return []

    def monday(day):
        return day - timedelta(days=day.weekday())

    grouped = {}
    for row in dated:
        grouped.setdefault(monday(row.due), Decimal('0.00'))
        grouped[monday(row.due)] += row.total

    week = min(grouped)
    last = max(grouped)
    weeks = []
    while week <= last:
        weeks.append((week.isoformat(), grouped.get(week, Decimal('0.00'))))
        week += timedelta(days=7)
    return weeks


def by_order(owed):
    """Grouped by purchase order. Freight has none, and stays out."""
    grouped = _group(owed, lambda row: row.order_number)
    grouped.pop('', None)
    return sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))


def by_item(owed):
    """Grouped by the words on the line, because no part catalogue
    exists."""
    grouped = {}
    for row in owed:
        for line in row.lines:
            grouped[line.description] = \
                grouped.get(line.description, Decimal('0.00')) + line.net
    return sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))


def compute(name, owed, today=None):
    """A figure by its menu name. Unknown names are refused."""
    if name not in FIGURES:
        raise NoSuchFigure(f'no figure called {name}')
    function = globals()[name]
    if name in NEEDS_TODAY:
        return function(owed, today)
    return function(owed)
