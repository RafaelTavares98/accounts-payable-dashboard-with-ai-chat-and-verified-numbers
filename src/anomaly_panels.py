"""The fixed menu of panels on the anomaly view.

Same rules as the cost menu: the model picks from here and nothing else,
and a panel is data, not a picture. The names differ from the cost menu
on purpose, so a panel can never open on the wrong view.
"""

import anomalies
import routing
from panels import NoSuchPanel, Panel, Spec

__all__ = ['MENU', 'BOARD', 'NoSuchPanel', 'build']

MENU = {
    'flags': Spec('cards', 'Flagged', ['flagged_count', 'flagged_total',
                                        'flag_rate', 'reviewed']),
    'by_stage': Spec('bar', 'Flags by stage', ['by_stage']),
    'by_check': Spec('bar', 'Flags by check', ['by_check']),
    'flagged_by_supplier': Spec('bar', 'Flags by supplier', ['by_supplier']),
    'flags_by_week': Spec('line', 'Money flagged by week', ['by_week']),
    'worst_flags': Spec('table', 'Highest scores', ['worst']),
    'by_origin': Spec('cards', 'Whose error', ['by_origin']),
}

LOOKS_LIKE = {
    'flags': 'four big figures: how many invoices were flagged, the money '
             'on them, the share flagged, how many were reviewed',
    'by_stage': 'a ring split by the stage of the process: '
                'purchasing, vendor master, receiving, billing, freight '
                'billing',
    'by_check': 'a bar chart of flags by the check that points at them, '
                'such as a price above the contract',
    'flagged_by_supplier': 'a horizontal bar chart, one bar per supplier, '
                           'most flags at the top',
    'flags_by_week': 'a line chart of the money on flagged invoices, '
                     'week by week',
    'worst_flags': 'a table of the flagged invoices with the highest '
                   'scores',
    'by_origin': 'four figures on whose error it is: ours, documents the '
                 'reader could not read; the client\'s, confirmed by the '
                 'analyst; flags still waiting; and flags dismissed',
}

FILL_ORDER = ('flags', 'by_origin', 'by_stage', 'flags_by_week',
              'by_check', 'flagged_by_supplier', 'worst_flags')

BOARD = routing.Board(
    MENU, LOOKS_LIKE, FILL_ORDER,
    about='the flagged invoices',
    holds='invoices scored by the checking model: what was flagged, at '
          'which stage of the process, by which check, from which '
          'supplier, in which week, and whose error it is')


def _rows(name, scored, ours):
    if name == 'by_origin':
        return anomalies.by_origin(scored, ours=ours)
    if name == 'flags':
        return [
            ('Flagged', anomalies.flagged_count(scored)),
            ('Amount flagged', anomalies.flagged_total(scored)),
            ('Share flagged', anomalies.flag_rate(scored)),
            ('Invoices reviewed', anomalies.reviewed(scored)),
        ]
    if name == 'by_stage':
        return [(stage, count) for stage, count, _ in anomalies.by_stage(scored)]
    if name == 'by_check':
        return anomalies.by_check(scored)
    if name == 'flagged_by_supplier':
        return [(who, count) for who, count, _ in anomalies.by_supplier(scored)]
    if name == 'flags_by_week':
        return [(week, amount)
                for week, _, _, amount in anomalies.by_week(scored)]
    if name == 'worst_flags':
        return [(f'{row.number}, {row.check}', row.total)
                for row in anomalies.worst(scored)]
    raise NoSuchPanel(f'no panel called {name}')


def build(name, scored, ours=0):
    """Fill one panel from the anomaly menu over the given rows. `ours`
    is how many documents the reader left for a person."""
    if name not in MENU:
        available = ', '.join(sorted(MENU))
        raise NoSuchPanel(
            f'no panel called {name}; the menu holds {available}')
    spec = MENU[name]
    return Panel(name, spec.kind, spec.title, _rows(name, scored, ours))
