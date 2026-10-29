"""The cost view: what each part cost to land at the Moty plant, in reais.

Project 01 writes the department's report into data/cost/: one line per
order line and part on each shipment, one row per shipment, the documents
a person must read, and the desk's targets. This reads it, joins each line
to its shipment's carrier and month and to its part's name, and sums it.

Every figure is computed here by code. The page and the assistant only
show them.
"""

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ZERO = Decimal('0.00')
CENT = Decimal('0.01')
UNIT = Decimal('0.0001')
ONE = Decimal('0.1')

#: A shipment whose international freight has no invoice yet has no
#: carrier and no mode. Saying so beats an empty label.
NOT_BILLED = 'freight not billed yet'

#: The filters the cost view accepts.
FILTERS = ('carrier', 'mode', 'status', 'month', 'product')

#: The seven parts of a landed cost, as the report names them and as a
#: reader names them.
COMPONENTS = (
    ('goods', 'goods_brl', 'Goods'),
    ('freight', 'freight_brl', 'International freight'),
    ('truck', 'inland_brl', 'Truck to Moty plant'),
    ('broker', 'broker_brl', 'Customs broker'),
    ('duty', 'duty_brl', 'Import duty (II)'),
    ('afrmm', 'afrmm_brl', 'AFRMM'),
    ('siscomex', 'siscomex_brl', 'Siscomex'),
)


class Line:
    """One order line and part on one shipment, costed."""

    def __init__(self, shipment, order, code, product, quantity, parts,
                 credits, landed, status, carrier, mode, month):
        self.shipment = shipment
        self.order = order
        self.code = code
        self.product = product
        self.quantity = quantity
        self.parts = parts
        self.credits = credits
        self.landed = landed
        self.status = status
        self.carrier = carrier
        self.mode = mode
        self.month = month


def _dec(text):
    try:
        return Decimal(str(text)) if str(text).strip() else ZERO
    except InvalidOperation:
        return ZERO


def _read(path):
    if not Path(path).exists():
        return []
    with open(path, encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def load(folder):
    """Every costed line; an empty list when no report was written yet."""
    folder = Path(folder)
    names = {row['code']: row['name']
             for row in _read(folder / 'vendors.csv')}
    parts = {row['code']: row['description']
             for row in _read(folder / 'items.csv')}
    shipments = {row['shipment_id']: row
                 for row in _read(folder / 'operations.csv')}
    found = []
    for row in _read(folder / 'landed_cost.csv'):
        trip = shipments.get(row['shipment_id'], {})
        carrier = trip.get('carrier', '')
        found.append(Line(
            shipment=row['shipment_id'],
            order=row['order_number'],
            code=row['code'],
            product=parts.get(row['code'], row['code']),
            quantity=_dec(row['quantity']),
            parts={key: _dec(row[column]) for key, column, _ in COMPONENTS},
            credits=_dec(row['credits_brl']),
            landed=_dec(row['landed_brl']),
            status=row['status'],
            carrier=names.get(carrier, carrier) or NOT_BILLED,
            mode=trip.get('mode') or NOT_BILLED,
            month=trip.get('month', ''),
        ))
    return found


def only(lines, **chosen):
    """The lines matching every filter given; an empty value means any."""
    unknown = set(chosen) - set(FILTERS)
    if unknown:
        raise ValueError(f'unknown filter: {sorted(unknown)}')
    kept = lines
    for key, value in chosen.items():
        if value:
            kept = [line for line in kept if getattr(line, key) == value]
    return kept


def choices(lines):
    """What each filter can be set to, read off the lines themselves."""
    return {key: sorted({getattr(line, key) for line in lines})
            for key in FILTERS}


# ---------------------------------------------------------------- totals


def _sum(values):
    return sum(values, ZERO)


def landed_total(lines):
    return _sum(line.landed for line in lines)


def final_total(lines):
    return _sum(line.landed for line in lines if line.status == 'final')


def provisional_total(lines):
    return _sum(line.landed for line in lines if line.status != 'final')


def provisional_share(lines):
    """The share of the landed cost still provisional, in percent."""
    whole = landed_total(lines)
    if not whole:
        return None
    return (provisional_total(lines) * 100 / whole).quantize(ONE)


def credits_total(lines):
    """IPI, PIS, COFINS and ICMS: recovered, so kept beside the cost."""
    return _sum(line.credits for line in lines)


def shipment_count(lines):
    return len({line.shipment for line in lines})


def line_count(lines):
    return len(lines)


# --------------------------------------------------------------- groupings


def _ranked(lines, key):
    grouped = {}
    for line in lines:
        grouped[key(line)] = grouped.get(key(line), ZERO) + line.landed
    return sorted(grouped.items(), key=lambda pair: (-pair[1], pair[0]))


def by_component(lines):
    """(part, money): what the landed cost is made of, biggest first."""
    found = [(label, _sum(line.parts[key] for line in lines))
             for key, _, label in COMPONENTS]
    return sorted(found, key=lambda pair: -pair[1])


def by_carrier(lines):
    """The landed cost of what each carrier moved, biggest first."""
    return _ranked(lines, lambda line: line.carrier)


def by_mode(lines):
    """By operation: air, ocean, or freight not billed yet."""
    return _ranked(lines, lambda line: line.mode)


def by_product(lines):
    return _ranked(lines, lambda line: line.product)


def unit_cost(lines):
    """(part, landed cost per unit), weighted by quantity, dearest first."""
    money, units = {}, {}
    for line in lines:
        money[line.product] = money.get(line.product, ZERO) + line.landed
        units[line.product] = units.get(line.product, ZERO) + line.quantity
    found = [(name, (money[name] / units[name]).quantize(UNIT))
             for name in money if units[name]]
    return sorted(found, key=lambda pair: (-pair[1], pair[0]))


def by_month(lines):
    """(month, final, provisional), oldest first. The month is the one
    the goods were billed in, so the cost falls in that month's close."""
    months = {}
    for line in lines:
        final, provisional = months.get(line.month, (ZERO, ZERO))
        if line.status == 'final':
            final += line.landed
        else:
            provisional += line.landed
        months[line.month] = (final, provisional)
    return [(month, final, provisional)
            for month, (final, provisional) in sorted(months.items())]


def finance_month(lines):
    """The finance desk's five monthly figures, for the latest month
    costed, the month before it, and the month a quarter back.

    The cost desk closes a month, not a week, so this view compares
    months. The month before is the previous month that holds a costed
    line, not the previous name on the calendar.
    """
    months = {}
    for line in lines:
        months.setdefault(line.month, []).append(line)
    if not months:
        return None
    order = sorted(months)

    def figures(month):
        here = months.get(month, [])
        landed = _sum(line.landed for line in here)
        final = _sum(line.landed for line in here if line.status == 'final')
        return {
            'landed': landed,
            'final': final,
            'provisional': landed - final,
            'share': (Decimal(100) * (landed - final) / landed
                      ).quantize(Decimal('0.1')) if landed else None,
            'credits': _sum(line.credits for line in here),
        }

    latest = order[-1]
    before = order[-2] if len(order) > 1 else None
    quarter = order[-4] if len(order) > 3 else None
    return {'month': latest,
            'now': figures(latest),
            'before': figures(before) if before else None,
            'quarter': figures(quarter) if quarter else None}


def by_shipment(lines):
    """(shipment, carrier, mode, month, status, landed), dearest first."""
    trips = {}
    for line in lines:
        held = trips.setdefault(line.shipment, [line.carrier, line.mode,
                                                line.month, line.status,
                                                ZERO])
        held[4] += line.landed
    found = [(shipment, *held) for shipment, held in trips.items()]
    return sorted(found, key=lambda row: (-row[5], row[0]))


# ------------------------------------------------------- the desk's targets


def desk_week(folder, today=None):
    """Sandbox: the desk's four weekly figures, for the latest week and the
    week before. A week is the ISO week of the issue date. An invoice is
    analysed when the reader found no problem in it; an automation error
    is an invoice the reader flagged."""
    from datetime import date
    rows = _read(Path(folder).parent / 'invoices.csv')
    today = (today or date.today()).isoformat()
    weeks = {}
    for row in rows:
        # The reader does not always find a date on the page, and it
        # sometimes reads a year that has not happened. Neither belongs on
        # a weekly axis: one misread year would make itself the latest
        # week and leave the whole row reading one invoice.
        if not row.get('issue_date') or row['issue_date'] > today:
            continue
        week = date.fromisoformat(row['issue_date']).isocalendar()[:2]
        weeks.setdefault(week, []).append(row)
    if not weeks:
        return None
    order = sorted(weeks)

    # Supplier errors: project 02's flags on a supplier's or carrier's
    # invoice that the analyst confirmed, by the ISO week of the invoice.
    supplier = {}
    for row in _read(Path(folder).parent / 'anomalies.csv'):
        if (row.get('origin') == 'client'
                and row.get('decision') == 'confirmed'
                and row.get('issue_date')):
            week = date.fromisoformat(row['issue_date']).isocalendar()[:2]
            supplier[week] = supplier.get(week, 0) + 1

    def figures(upto):
        current = weeks.get(upto, [])
        seen = [row for week in order if week <= upto for row in weeks[week]]
        done = [row for row in seen if not row.get('problems')]
        completed = Decimal(100) * len(done) / len(seen) if seen else None
        flagged = [row for row in current if row.get('problems')]
        errors = Decimal(100) * len(flagged) / len(current) if current else None
        return {'processed': len(current), 'completed': completed,
                'remaining': Decimal(100) - completed
                if completed is not None else None,
                'errors': errors, 'supplier': supplier.get(upto, 0)}

    latest = order[-1]
    earlier = order[-2] if len(order) > 1 else None
    # A month back is the same weekday four weeks earlier.
    from datetime import timedelta
    month = (date.fromisocalendar(*latest, 1)
             - timedelta(weeks=4)).isocalendar()[:2]
    return {'week': '%d-W%02d' % latest,
            'now': figures(latest),
            'before': figures(earlier) if earlier else None,
            'month': figures(month) if month in weeks else None}


def targets(folder):
    """The three operational targets project 01 measured, and how many
    documents wait for a person. The latest month stands for the close."""
    folder = Path(folder)
    path = folder / 'kpis.json'
    written = json.loads(path.read_text(encoding='utf-8')) \
        if path.exists() else {}
    closes = written.get('known_before_close') or {}
    month = max(closes) if closes else None

    def number(value):
        return Decimal(str(value)) if value not in (None, '') else None

    waiting = [row for row in _read(folder / 'exceptions.csv')
               if row.get('invoice_number')]
    return {
        'analysed_same_day': number(written.get('analysed_same_day')),
        'our_error_rate': number(written.get('our_error_rate')),
        'close_month': month,
        'known_before_close': number(closes.get(month)) if month else None,
        'for_a_person': len(waiting),    }
