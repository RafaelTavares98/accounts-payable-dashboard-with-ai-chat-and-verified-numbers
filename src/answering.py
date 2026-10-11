"""One question, from the click to the sentence.

The order matters: the model names panels, code computes every figure, and
only then is the model handed those figures to write a sentence around.
"""

import re
from decimal import Decimal

import metrics
import panels
import routing

ENOUGH_FOR_A_TREND = 2

TREND_PANELS = {'by_month'}

_NUMBER = re.compile(r'\d[\d,.]*')

_YEAR = re.compile(r'^(19|20)\d{2}$')


class Figure:
    """One computed number, traced to the function that made it."""

    def __init__(self, name, function, rows, value):
        self.name = name
        self.function = function
        self.rows = rows
        self.value = value


class Answer:
    """Everything the chat shows for one question."""

    def __init__(self, panels=None, sentence='', rejected=False,
                 refusal='', rows_used=0, as_of=None, figures=None):
        self.panels = panels or []
        self.sentence = sentence
        self.rejected = rejected
        self.refusal = refusal
        self.rows_used = rows_used
        self.as_of = as_of
        self.figures = figures or []


def _plain(value):
    """The form a figure takes in a prompt: no thousands commas."""
    return str(value)


def _money(value):
    """The form a figure takes in a sentence: thousands commas."""
    return f'{value:,.2f}'


def _computed_values(figures, built_panels):
    allowed = {_plain(figure.value) for figure in figures}
    for panel in built_panels:
        for _label, value in panel.rows:
            if isinstance(value, (Decimal, int, float)) and \
                    not isinstance(value, bool):
                allowed.add(_plain(value))
    return allowed


def _invented_numbers(sentence, allowed):
    """Every numeric token in the sentence that matches no computed
    figure. Years do not count as figures."""
    tokens = _NUMBER.findall(sentence)
    invented = []
    for token in tokens:
        # The matcher is greedy over dots, so a figure that ends a
        # sentence arrives as "31,750.00." and matched nothing. Every
        # sentence that ended on its own figure was being thrown away.
        token = token.rstrip('.,')
        clean = token.replace(',', '')
        if _YEAR.match(clean):
            continue
        if clean not in allowed:
            invented.append(token)
    return invented


def _code_sentence(routed, built_panels, owed, today):
    """Written by code, so it can only carry computed figures."""
    for panel in built_panels:
        if panel.name == 'overdue':
            overdue = metrics.overdue_total(owed, today)
            count = metrics.overdue_count(owed, today)
            return f'{_money(overdue)} is overdue across {count} documents.'
        if panel.name == 'balance':
            total = metrics.total_owed(owed)
            count = metrics.count(owed)
            return f'The total owed in the current filter is ' \
                   f'{_money(total)} across {count} documents.'
        if panel.name == 'by_supplier':
            return _biggest(panel, 'The largest balance is')
        if panel.name == 'by_item':
            return _biggest(panel, 'The most is owed on')
        if panel.name == 'by_order':
            return _biggest(panel, 'The costliest order is')
        if panel.name == 'by_band':
            return _biggest(panel, 'Most of what is late sits in')
        if panel.name == 'by_month':
            return _biggest(panel, 'The heaviest month is')
    return 'The figures are shown in the panels above.'


def _series(name, pairs, most=14):
    """One series as a line of text, newest weeks last."""
    shown = pairs[-most:]
    body = ', '.join(f'{label} {_money(value)}' for label, value in shown)
    return f'{name}: {body}'


def brief(owed, today):
    """The whole slice, computed by code, as text the model can read.

    Four figures are enough to restate a total and nowhere near enough
    to explain a fall. This is everything that is true about the rows
    on screen: the headline, who and what they are, the two weekly
    series, and the steps that moved most. Every number in here came
    out of a function, so quoting one back is not inventing it.
    """
    lines = [
        f'Documents: {metrics.count(owed)} documents, '
        f'{_money(metrics.total_owed(owed))} in all, '
        f'average {_money(metrics.ticket_average(owed))}.',
        f'Overdue: {metrics.overdue_count(owed, today)} documents, '
        f'{_money(metrics.overdue_total(owed, today))}, '
        f'{metrics.overdue_rate(owed, today)}% of them, '
        f'{metrics.average_days_overdue(owed, today)} days late on '
        'average.',
    ]

    bands = metrics.overdue_buckets(owed, today)
    lines.append('Overdue by band: ' + ', '.join(
        f'{label} {count} documents {_money(value)}'
        for label, count, value in bands))

    for name, rows in (('Top suppliers', metrics.by_supplier(owed)),
                       ('Top items', metrics.by_item(owed)),
                       ('Top orders', metrics.by_order(owed))):
        lines.append(f'{name}: ' + ', '.join(
            f'{label} {_money(value)}' for label, value in rows[:5]))

    due = metrics.by_due_week(owed)
    arrived = metrics.by_issue_week(owed)
    lines.append(_series('Falling due by week', due))
    lines.append(_series('Arrived by week', arrived))

    for name, pairs in (('falling due', due), ('arrived', arrived)):
        # Every step, with its own difference. Without these the model
        # has to subtract two weeks itself to talk about a fall, and
        # the guard is right to throw that away: arithmetic is the one
        # thing it is not allowed to do.
        moves = metrics.changes(pairs)[-12:]
        if moves:
            lines.append(
                f'Week on week change in {name}: ' + ', '.join(
                    f'{label} {"up" if delta >= 0 else "down"} '
                    f'{_money(abs(delta))}'
                    for label, _before, _after, delta in moves))
        fall = metrics.sharpest(pairs, rising=False)
        rise = metrics.sharpest(pairs, rising=True)
        if fall:
            lines.append(
                f'Sharpest fall in {name}: week of {fall[0]}, from '
                f'{_money(fall[1])} to {_money(fall[2])}, a drop of '
                f'{_money(abs(fall[3]))}.')
        if rise:
            lines.append(
                f'Sharpest rise in {name}: week of {rise[0]}, from '
                f'{_money(rise[1])} to {_money(rise[2])}, a rise of '
                f'{_money(abs(rise[3]))}.')

    return '\n'.join(lines)


def _chat(question, owed, today, model, history):
    """Small talk, answered by the model rather than by a fixed string.

    A canned paragraph is the same paragraph the second time, which is
    how "hi" and "I just said hi" got identical replies. The model can
    hold a conversation; what it cannot do is produce a figure, and
    since nothing was computed here, every digit it writes is invented
    by definition and the guard catches all of them.
    """
    prompt = (
        routing._said_before(history) +
        'You are the assistant beside a dashboard of supplier invoices. '
        'Reply in one or two short sentences, in English. '
        'Do not state any number at all: you have not been given any. '
        'If it fits, say what can be asked: a total, a supplier, an '
        'order, what is overdue, how late it is.\n'
        f'Person: {question}'
    )
    try:
        said = model(prompt)
    except Exception:
        said = ''

    if not said or _invented_numbers(said, set()):
        said = ('Ask about a total, a supplier, an order, what is '
                'overdue, or how late it is.')
    return Answer(sentence=said.strip(), rows_used=len(owed), as_of=today)


def _biggest(panel, opening):
    """The top row of a ranking, said as a sentence.

    Written by code, so it can only carry a figure the panel already
    holds. The generic line it replaces told the reader nothing.
    """
    if not panel.rows:
        return 'Nothing in the current filter.'
    label, value = max(panel.rows, key=lambda pair: abs(pair[1]))
    return f'{opening} {label}, with {_money(value)}.'


def answer(question, owed, today=None, model=None, history=None):
    """One question, two model calls, no invented figure."""
    if not owed:
        return Answer(rows_used=0, as_of=today,
                      refusal='Nothing matches the current filter.')

    routed = routing.route(question, model=model, owed=owed,
                           history=history)

    if routed.small_talk:
        return _chat(question, owed, today, model, history)

    if routed.refusal:
        return Answer(rows_used=len(owed), as_of=today,
                      refusal=routed.refusal)

    if any(name in TREND_PANELS for name in routed.panels) and \
            len(owed) < ENOUGH_FOR_A_TREND:
        return Answer(rows_used=len(owed), as_of=today,
                      refusal='Fewer than two documents matched the '
                              'filter, so there is no trend to show.')

    built_panels = [panels.build(name, owed, today=today)
                    for name in routed.panels]

    figures = []
    for panel in built_panels:
        for figure_name in panels.MENU[panel.name].figures:
            value = metrics.compute(figure_name, owed, today=today)
            figures.append(Figure(figure_name, figure_name, len(owed),
                                  value))

    digest = brief(owed, today)
    prompt = _sentence_prompt(question, figures, digest)
    try:
        sentence = model(prompt)
    except Exception:
        sentence = _code_sentence(routed, built_panels, owed, today)
        return Answer(panels=built_panels, sentence=sentence, rejected=True,
                      rows_used=len(owed), as_of=today, figures=figures)

    # Everything in the brief was computed too, so a figure quoted out
    # of it is not an invention.
    allowed = _computed_values(figures, built_panels)
    allowed |= set(_NUMBER.findall(digest))
    allowed |= {token.replace(',', '') for token in _NUMBER.findall(digest)}
    invented = _invented_numbers(sentence, allowed)
    if invented:
        sentence = _code_sentence(routed, built_panels, owed, today)
        return Answer(panels=built_panels, sentence=sentence, rejected=True,
                      rows_used=len(owed), as_of=today, figures=figures)

    return Answer(panels=built_panels, sentence=sentence, rejected=False,
                  rows_used=len(owed), as_of=today, figures=figures)


def _sentence_prompt(question, figures, digest=''):
    lines = [f'{figure.name}: {_plain(figure.value)}' for figure in figures]
    listed = '; '.join(lines) if lines else 'nothing'
    return (
        'This is what the person is looking at:\n'
        f'{routing._what_is_on_screen()}\n'
        'They will describe what they see, not the names. The yellow '
        'dotted line is what arrived each week; the bright blue line '
        'is what falls due each week.\n\n'
        'Everything true about those rows, computed by code:\n'
        f'{digest}\n\n'
        f'The panels now open show: {listed}.\n\n'
        f'The question was: {question}\n'
        'Answer it in one or two short sentences. Where the question '
        'asks why something rose or fell, say which week it moved and '
        'what the figures above show about it. '
        'Use only the figures given: every one of them was computed, '
        'and any other number would be invented. '
        'Do not apologise and do not describe the panels. '
        'Use commas for thousands and a dot for decimals.'
    )
