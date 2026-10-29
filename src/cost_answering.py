"""One question on the cost view, from the click to the sentence.

The same order as every assistant here: the model names panels off the
cost menu, code computes every figure, and only then is the model handed
those figures to write one sentence. A sentence carrying a number nobody
computed is replaced by one written by code.
"""

import cost
import cost_panels
import routing
from answering import (Answer, Figure, _invented_numbers, _money,
                       allowed_from)

#: A trend needs two points. One line has no spread, no trend and no
#: average worth printing.
ENOUGH_FOR_A_TREND = 2

TREND_PANELS = {'by_month'}


def brief(lines):
    """Everything true about the lines on screen, as text the model reads."""
    out = [
        f'Landed cost: {_money(cost.landed_total(lines))} in reais, over '
        f'{cost.shipment_count(lines)} shipments and '
        f'{cost.line_count(lines)} order lines. '
        f'Final {_money(cost.final_total(lines))}, provisional '
        f'{_money(cost.provisional_total(lines))}, '
        f'{cost.provisional_share(lines)}% still provisional. '
        f'Recoverable taxes kept apart: {_money(cost.credits_total(lines))}.',
        'Made of: ' + ', '.join(f'{name} {_money(value)}'
                                for name, value in cost.by_component(lines)),
        'By carrier: ' + ', '.join(f'{name} {_money(value)}'
                                   for name, value in cost.by_carrier(lines)),
        'By operation: ' + ', '.join(f'{name} {_money(value)}'
                                     for name, value in cost.by_mode(lines)),
        'By part: ' + ', '.join(f'{name} {_money(value)}'
                                for name, value in cost.by_product(lines)[:6]),
        'Per unit: ' + ', '.join(f'{name} {value}'
                                 for name, value in cost.unit_cost(lines)[:6]),
        'By month: ' + ', '.join(
            f'{month} final {_money(final)} provisional {_money(provisional)}'
            for month, final, provisional in cost.by_month(lines)),
        'Dearest shipments: ' + ', '.join(
            f'{shipment} ({carrier}, {status}) {_money(landed)}'
            for shipment, carrier, _mode, _month, status, landed
            in cost.by_shipment(lines)[:5]),
    ]
    return '\n'.join(out)


def _top(panel, opening, unit=False):
    if not panel.rows:
        return 'Nothing in the current filter.'
    label, value = panel.rows[0]
    shown = f'{value} a unit' if unit else _money(value)
    return f'{opening} {label}, with {shown}.'


def _code_sentence(built, lines):
    """Written by code, so it can only carry computed figures."""
    for panel in built:
        if panel.name == 'landed':
            return (f'The landed cost in the current filter is '
                    f'{_money(cost.landed_total(lines))} across '
                    f'{cost.shipment_count(lines)} shipments; '
                    f'{_money(cost.provisional_total(lines))} of it is '
                    'still provisional.')
        if panel.name == 'by_month':
            return (f'{_money(cost.provisional_total(lines))} of '
                    f'{_money(cost.landed_total(lines))} is still '
                    f'provisional, {cost.provisional_share(lines)}%.')
        if panel.name == 'by_component':
            return _top(panel, 'Most of the cost is')
        if panel.name == 'by_carrier':
            return _top(panel, 'The carrier that moved the most cost is')
        if panel.name == 'by_mode':
            return _top(panel, 'Most of the cost came by')
        if panel.name == 'by_product':
            return _top(panel, 'The part with the most cost is')
        if panel.name == 'unit_cost':
            return _top(panel, 'The dearest part to land is', unit=True)
        if panel.name == 'by_shipment':
            return _top(panel, 'The dearest shipment is')
    return 'The figures are shown in the panels above.'


def _chat(question, lines, today, model, history):
    """Small talk, answered by the model. Nothing was computed, so every
    digit it writes is invented by definition and the guard catches it."""
    prompt = (
        routing._said_before(history) +
        'You are the assistant beside a dashboard of what imported parts '
        'cost to land at the Moty plant, in reais. Reply in one or two short '
        'sentences, in English. Do not state any number at all: you have '
        'not been given any. If it fits, say what can be asked: the '
        'landed cost, what it is made of, a carrier, a part, what is '
        'still provisional.\n'
        f'Person: {question}'
    )
    try:
        said = model(prompt)
    except Exception:
        said = ''
    if not said or _invented_numbers(said, set()):
        said = ('Ask about the landed cost, what it is made of, a '
                'carrier, a part, or what is still provisional.')
    return Answer(sentence=said.strip(), rows_used=len(lines), as_of=today)


def _sentence_prompt(question, built, digest):
    listed = '; '.join(f'{panel.title}: ' + ', '.join(
        f'{label} {value}' for label, value in panel.rows[:6])
        for panel in built)
    return (
        'This is what the person is looking at:\n'
        f'{routing._what_is_on_screen(cost_panels.BOARD)}\n\n'
        'Everything true about those lines, computed by code:\n'
        f'{digest}\n\n'
        f'The panels now open show: {listed}.\n\n'
        f'The question was: {question}\n'
        'Answer it in one or two short sentences. Money is in reais. Use '
        'only the figures given: every one of them was computed, and any '
        'other number would be invented. Do not apologise and do not '
        'describe the panels. Use commas for thousands and a dot for '
        'decimals.'
    )


def _figures(built, lines):
    """Which function made each panel, over how many lines."""
    return [Figure(panel.name, f'cost.{cost_panels.MENU[panel.name].figures[0]}',
                   len(lines), panel.rows) for panel in built]


def answer(question, lines, today=None, model=None, history=None):
    """One question, two model calls, no invented figure."""
    if not lines:
        return Answer(rows_used=0, as_of=today,
                      refusal='Nothing matches the current filter.')
    routed = routing.route(question, model=model, history=history,
                           board=cost_panels.BOARD)
    if routed.small_talk:
        return _chat(question, lines, today, model, history)
    if routed.refusal:
        return Answer(rows_used=len(lines), as_of=today,
                      refusal=routed.refusal)
    if any(name in TREND_PANELS for name in routed.panels) and \
            len(lines) < ENOUGH_FOR_A_TREND:
        return Answer(rows_used=len(lines), as_of=today,
                      refusal='Fewer than two lines matched the filter, so '
                              'there is no trend to show.')

    built = [cost_panels.build(name, lines) for name in routed.panels]
    figures = _figures(built, lines)
    digest = brief(lines)
    try:
        sentence = model(_sentence_prompt(question, built, digest))
    except Exception:
        return Answer(panels=built, sentence=_code_sentence(built, lines),
                      rejected=True, rows_used=len(lines), as_of=today,
                      figures=figures)

    if _invented_numbers(sentence, allowed_from(figures, built, digest)):
        return Answer(panels=built, sentence=_code_sentence(built, lines),
                      rejected=True, rows_used=len(lines), as_of=today,
                      figures=figures)
    return Answer(panels=built, sentence=sentence.strip(), rejected=False,
                  rows_used=len(lines), as_of=today, figures=figures)


class Chip:
    """One ready-made question, with the panels it opens."""

    def __init__(self, question, panel_names):
        self.question = question
        self.panels = panel_names


CHIPS = [
    Chip('What did the parts cost to land?', ['landed']),
    Chip('What is the cost made of?', ['by_component']),
    Chip('Which carrier moved the most cost?', ['by_carrier']),
    Chip('Which part is dearest per unit?', ['unit_cost']),
    Chip('How much is still provisional?', ['by_month']),
]


def click(chip, lines, today=None):
    """One chip, no model call, one sentence written by code."""
    if not lines:
        return Answer(rows_used=0, as_of=today,
                      refusal='Nothing matches the current filter.')
    opening = routing._three_to_five(list(chip.panels), cost_panels.BOARD)
    built = [cost_panels.build(name, lines) for name in opening]
    lead = [panel for panel in built if panel.name == chip.panels[0]]
    return Answer(panels=built, sentence=_code_sentence(lead, lines),
                  rejected=False, rows_used=len(lines), as_of=today,
                  figures=_figures(built, lines))
