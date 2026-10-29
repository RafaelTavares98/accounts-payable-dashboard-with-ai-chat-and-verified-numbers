"""The fixed menu of panels on the cost view.

The model picks from here and nothing else, and a panel is data, not a
picture. The names differ from the anomaly menu, so a panel can never
open on the wrong view.
"""

import cost
import routing
from panels import NoSuchPanel, Panel, Spec

__all__ = ['MENU', 'BOARD', 'NoSuchPanel', 'build']

MENU = {
    'landed': Spec('cards', 'Landed cost',
                   ['landed_total', 'final_total', 'provisional_total',
                    'provisional_share', 'credits_total']),
    'by_component': Spec('bar', 'What the cost is made of', ['by_component']),
    'by_carrier': Spec('bar', 'Cost by carrier', ['by_carrier']),
    'by_mode': Spec('bar', 'Cost by operation', ['by_mode']),
    'by_product': Spec('bar', 'Cost by part', ['by_product']),
    'unit_cost': Spec('bar', 'Cost per unit', ['unit_cost']),
    'by_month': Spec('line', 'Cost by month', ['by_month']),
    'by_shipment': Spec('table', 'Dearest shipments', ['by_shipment']),
}

LOOKS_LIKE = {
    'landed': 'big figures: the landed cost in reais, how much is final, '
              'how much is still provisional and its share, and the '
              'recoverable taxes kept apart',
    'by_component': 'a ring split into what the cost is made of: goods, '
                    'international freight, the truck to the Moty plant, the '
                    'customs broker, import duty, AFRMM and Siscomex',
    'by_carrier': 'a horizontal bar chart, one bar per carrier, the '
                  'landed cost of what it moved',
    'by_mode': 'a bar chart by operation: air, ocean, or freight not '
               'billed yet',
    'by_product': 'a horizontal bar chart, one bar per part, the landed '
                  'cost of each',
    'unit_cost': 'what one unit of each part cost to land, dearest '
                 'first',
    'by_month': 'a line chart of the landed cost by month, a bright blue '
                'line for what is final and a yellow dotted line for what '
                'is still provisional',
    'by_shipment': 'a table of the shipments with the highest landed '
                   'cost',
}

FILL_ORDER = ('landed', 'by_component', 'by_carrier', 'by_month',
              'by_product', 'by_mode', 'unit_cost', 'by_shipment')

BOARD = routing.Board(
    MENU, LOOKS_LIKE, FILL_ORDER,
    about='the landed cost',
    holds='the landed cost of each imported part in reais: what it is '
          'made of, by carrier, by operation, by part, by month, final '
          'or provisional')


def _rows(name, lines):
    if name == 'landed':
        return [
            ('Landed cost', cost.landed_total(lines)),
            ('Final', cost.final_total(lines)),
            ('Provisional', cost.provisional_total(lines)),
            ('Share provisional', cost.provisional_share(lines)),
            ('Recoverable taxes, apart', cost.credits_total(lines)),
        ]
    if name == 'by_component':
        return cost.by_component(lines)
    if name == 'by_carrier':
        return cost.by_carrier(lines)
    if name == 'by_mode':
        return cost.by_mode(lines)
    if name == 'by_product':
        return cost.by_product(lines)
    if name == 'unit_cost':
        return cost.unit_cost(lines)
    if name == 'by_month':
        return [(month, final + provisional)
                for month, final, provisional in cost.by_month(lines)]
    if name == 'by_shipment':
        return [(shipment, landed)
                for shipment, *_rest, landed in cost.by_shipment(lines)[:10]]
    raise NoSuchPanel(f'no panel called {name}')


def build(name, lines):
    """Fill one panel from the cost menu over the given lines."""
    if name not in MENU:
        available = ', '.join(sorted(MENU))
        raise NoSuchPanel(
            f'no panel called {name}; the menu holds {available}')
    spec = MENU[name]
    return Panel(name, spec.kind, spec.title, _rows(name, lines))
