"""The fixed menu of panels, and what each one draws.

The model picks from this menu and nothing else. A panel is data, not a
picture: it says what to draw, and the page draws it.
"""

import metrics


class NoSuchPanel(Exception):
    """A panel name that is not on the menu was asked for."""


class Panel:
    """One panel, filled with the rows it will draw."""

    def __init__(self, name, kind, title, rows):
        self.name = name
        self.kind = kind
        self.title = title
        self.rows = rows
        self.empty = not rows


class Spec:
    """What one panel on the menu is made of."""

    def __init__(self, kind, title, figures):
        self.kind = kind
        self.title = title
        self.figures = figures


MENU = {
    'balance': Spec('cards', 'Balance',
                    ['total_owed', 'count', 'ticket_average']),
    'overdue': Spec('cards', 'Overdue',
                    ['overdue_total', 'overdue_count', 'overdue_rate',
                     'average_days_overdue']),
    'by_band': Spec('bar', 'Overdue by band', ['overdue_buckets']),
    'by_supplier': Spec('bar', 'Owed by supplier', ['by_supplier']),
    'by_month': Spec('line', 'Owed by month', ['by_month']),
    'by_item': Spec('bar', 'Owed by item', ['by_item']),
    'by_order': Spec('table', 'Owed by order', ['by_order']),
}


def _rows(name, owed, today):
    if name == 'balance':
        return [
            ('Total owed', metrics.total_owed(owed)),
            ('Documents', metrics.count(owed)),
            ('Average document', metrics.ticket_average(owed)),
        ]
    if name == 'overdue':
        return [
            ('Overdue', metrics.overdue_total(owed, today)),
            ('Documents overdue', metrics.overdue_count(owed, today)),
            ('Share overdue', metrics.overdue_rate(owed, today)),
            ('Average days late', metrics.average_days_overdue(owed, today)),
        ]
    if name == 'by_band':
        return [(label, value)
                for label, _count, value in metrics.overdue_buckets(owed,
                                                                    today)]
    if name == 'by_supplier':
        return metrics.by_supplier(owed)
    if name == 'by_month':
        return metrics.by_month(owed)
    if name == 'by_item':
        return metrics.by_item(owed)
    if name == 'by_order':
        return metrics.by_order(owed)
    raise NoSuchPanel(f'no panel called {name}')


def build(name, owed, today=None):
    """Fill one panel from the menu over the given rows."""
    if name not in MENU:
        available = ', '.join(sorted(MENU))
        raise NoSuchPanel(
            f'no panel called {name}; the menu holds {available}')
    spec = MENU[name]
    return Panel(name, spec.kind, spec.title, _rows(name, owed, today))
