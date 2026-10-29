"""The anomaly view: invoices the checking model scored, read into rows.

Project 02 scores every invoice and writes data/anomalies.csv. Each row
says how unusual the invoice is, whether it landed in its week's top
five, and the stage of the process where the error most likely sits:
purchasing, the vendor master, receiving, billing or freight billing.

Every figure here is computed from those rows by code. The page and the
assistant only show them.
"""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

FILE = 'anomalies.csv'

#: The filters the anomaly view accepts.
FILTERS = ('supplier', 'stage')


class Scored:
    """One invoice, as the checking model saw it."""

    def __init__(self, number, supplier, kind, issued, week, total, score,
                 check, stage, checks, flagged, origin='', decision=''):
        self.number = number
        self.supplier = supplier
        self.kind = kind
        self.issued = issued
        self.week = week
        self.total = total
        self.score = score
        self.check = check
        self.stage = stage
        self.checks = checks
        self.flagged = flagged
        #: Whose error a flag points at. The model only scores what a
        #: supplier or a carrier billed, so every flag is the client's.
        self.origin = origin
        #: What the analyst made of the flag: confirmed, dismissed, or
        #: pending while it waits.
        self.decision = decision


def _money(text):
    try:
        return Decimal(text).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError):
        return Decimal('0.00')


def load(folder):
    """Every scored invoice; an empty list when nothing was scored yet."""
    path = Path(folder) / FILE
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as text:
        return [_scored(record) for record in csv.DictReader(text)]


def _scored(record):
    flagged = record['flagged'] == '1'
    return Scored(
        number=record['number'],
        supplier=record['supplier'],
        kind=record['kind'],
        issued=record['issue_date'],
        week=record['week'],
        total=_money(record['grand_total']),
        score=Decimal(record['score'] or '0'),
        check=record['check'],
        stage=record['stage'],
        checks=record['checks'],
        flagged=flagged,
        origin=record.get('origin') or ('client' if flagged else ''),
        decision=record.get('decision') or '',
    )


def only(rows, **chosen):
    """The rows matching every filter given; an empty value means any."""
    unknown = set(chosen) - set(FILTERS)
    if unknown:
        raise ValueError(f'unknown filter: {sorted(unknown)}')
    kept = rows
    for key, value in chosen.items():
        if value:
            kept = [row for row in kept if getattr(row, key) == value]
    return kept


def _flagged(rows):
    return [row for row in rows if row.flagged]


def reviewed(rows):
    return len(rows)


def flagged_count(rows):
    return len(_flagged(rows))


def flagged_total(rows):
    return sum((row.total for row in _flagged(rows)), Decimal('0.00'))


def flag_rate(rows):
    """The share flagged, in percent, one decimal; None with no rows."""
    if not rows:
        return None
    share = Decimal(flagged_count(rows) * 100) / Decimal(len(rows))
    return share.quantize(Decimal('0.1'))


def _grouped(rows, key):
    groups = {}
    for row in _flagged(rows):
        count, amount = groups.get(key(row), (0, Decimal('0.00')))
        groups[key(row)] = (count + 1, amount + row.total)
    return sorted(((name, count, amount)
                   for name, (count, amount) in groups.items()),
                  key=lambda item: (-item[1], item[0]))


def by_stage(rows):
    """(stage, flagged invoices, their money), most flagged first."""
    return _grouped(rows, lambda row: row.stage)


def by_supplier(rows):
    return _grouped(rows, lambda row: row.supplier)


def by_check(rows):
    """(check, flagged invoices), most frequent first."""
    return [(name, count) for name, count, _ in
            _grouped(rows, lambda row: row.check)]


def by_week(rows):
    """(week, flagged, invoices that week, money flagged), oldest first.

    A desk checks its top five every week, so the count is flat by
    design; the money on those five is what moves."""
    weeks = {}
    for row in rows:
        flagged, total, amount = weeks.get(row.week, (0, 0, Decimal('0.00')))
        weeks[row.week] = (flagged + row.flagged, total + 1,
                           amount + (row.total if row.flagged else 0))
    return [(week, flagged, total, amount)
            for week, (flagged, total, amount) in sorted(weeks.items())]


def desk_week(rows, today=None):
    """The desk's five weekly figures, for the latest week scored, the
    week before it, and the week four weeks back.

    A week is the one project 02 wrote on the row. The week before is the
    previous week that holds a scored invoice, not the previous date on
    the calendar, so a quiet week is skipped rather than shown as zero.
    """
    # A week that has not started holds a misread year, not business. One
    # of them would make itself the latest week and leave the row reading
    # a single invoice.
    today = (today or date.today()).isoformat()
    weeks = {}
    for row in rows:
        if row.week and row.week <= today:
            weeks.setdefault(row.week, []).append(row)
    if not weeks:
        return None
    order = sorted(weeks)

    def figures(week):
        here = weeks.get(week, [])
        flagged = [row for row in here if row.flagged]
        return {
            'scored': len(here),
            'flagged': len(flagged),
            'money': sum((row.total for row in flagged), Decimal('0.00')),
            'confirmed': sum(1 for row in flagged
                             if row.decision == 'confirmed'),
            'waiting': sum(1 for row in flagged
                           if row.decision in ('', 'pending')),
        }

    latest = order[-1]
    before = order[-2] if len(order) > 1 else None
    month = order[-5] if len(order) > 4 else None
    return {'week': latest,
            'now': figures(latest),
            'before': figures(before) if before else None,
            'month': figures(month) if month else None}


def worst(rows, most=10):
    """The flagged invoices, highest score first."""
    return sorted(_flagged(rows), key=lambda row: -row.score)[:most]


#: The analyst's three answers to a flag, in the order a desk reads them.
DECISIONS = ('confirmed', 'pending', 'dismissed')


def by_decision(rows):
    """(decision, flags, their money), all three always, so an empty one
    reads as none rather than as missing. A flag with no decision is
    still waiting."""
    groups = {name: (0, Decimal('0.00')) for name in DECISIONS}
    for row in _flagged(rows):
        name = row.decision or 'pending'
        count, amount = groups[name]
        groups[name] = (count + 1, amount + row.total)
    return [(name, *groups[name]) for name in DECISIONS]


def client_errors(rows):
    """Client errors found: confirmed flags only. A dismissed flag was an
    honest invoice."""
    return sum(1 for row in _flagged(rows) if row.decision == 'confirmed')


def our_errors(folder):
    """Our errors: documents the reader could not read or close, as the
    cost report of project 01 lists them in exceptions.csv."""
    path = Path(folder) / 'exceptions.csv'
    if not path.exists():
        return 0
    with open(path, encoding='utf-8') as text:
        return sum(1 for record in csv.DictReader(text)
                   if record.get('invoice_number')
                   and record.get('origin') == 'ours')


def by_origin(rows, ours=0):
    """Whose error each one is: ours beside the client's, and what the
    analyst decided about the client's."""
    decided = {name: count for name, count, _ in by_decision(rows)}
    return [
        ('Our errors, read by a person', ours),
        ('Client errors, confirmed', decided['confirmed']),
        ('Client, waiting for the analyst', decided['pending']),
        ('Dismissed, invoice was right', decided['dismissed']),
    ]


def suppliers(rows):
    return sorted({row.supplier for row in rows})


def stages(rows):
    return sorted({row.stage for row in rows})
