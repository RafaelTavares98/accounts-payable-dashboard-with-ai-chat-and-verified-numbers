"""The filters on top of the dashboard.

Every number on the page is computed over whatever the filters left. So the
filters have to be boring, predictable, and able to stack.
"""

STATES = ['open', 'overdue', 'credit']


class NeedsADate(Exception):
    """Overdue means nothing without the day it was measured from."""


def _overdue(row, today):
    return (not row.is_credit and row.due is not None and row.due < today)


def _open(row, today):
    return (not row.is_credit and row.due is not None and row.due >= today)


_STATE_CHECKS = {
    'overdue': _overdue,
    'open': _open,
    'credit': lambda row, today: row.is_credit,
}

#: The ageing bands, with the number of days each one ends at. They are
#: the labels the chart draws, so clicking a slice and naming a filter
#: are the same string.
BANDS = {
    '1 to 30 days': (1, 30),
    '31 to 60 days': (31, 60),
    '61 to 90 days': (61, 90),
    'over 90 days': (91, None),
}


def _in_band(row, band, today):
    if not _overdue(row, today):
        return False
    days = (today - row.due).days
    first, last = BANDS[band]
    return days >= first and (last is None or days <= last)


def apply(owed, *, supplier=None, since=None, until=None, order=None,
          shipment=None, state=None, item=None, band=None, category=None,
          today=None):
    """Return the rows that match every given filter. The original list is
    never changed, and a keyword this data has no column for is a
    TypeError, not a silent pass."""
    if state == 'overdue' and today is None:
        raise NeedsADate('overdue needs a date to be measured from')
    if band is not None:
        if today is None:
            raise NeedsADate('a band needs a date to be measured from')
        if band not in BANDS:
            raise ValueError(f'no band called {band}')
    kept = list(owed)
    if supplier is not None:
        kept = [row for row in kept if row.supplier == supplier]
    if since is not None:
        kept = [row for row in kept if row.issued and row.issued >= since]
    if until is not None:
        kept = [row for row in kept if row.issued and row.issued <= until]
    if order is not None:
        kept = [row for row in kept if row.order_number == order]
    if shipment is not None:
        kept = [row for row in kept if row.shipment_id == shipment]
    if state is not None:
        kept = [row for row in kept if _STATE_CHECKS[state](row, today)]
    if item is not None:
        kept = [row for row in kept
                if any(line.description == item for line in row.lines)]
    if band is not None:
        kept = [row for row in kept if _in_band(row, band, today)]
    if category is not None:
        import metrics
        kept = [row for row in kept
                if any(metrics.category_of(line.description) == category
                       for line in row.lines)]
    return kept


def suppliers(owed):
    """The supplier names the data holds, sorted, each once."""
    return sorted({row.supplier for row in owed})


def period(owed):
    """The first and the last issue date in the rows."""
    issued = [row.issued for row in owed if row.issued is not None]
    return (min(issued), max(issued))
