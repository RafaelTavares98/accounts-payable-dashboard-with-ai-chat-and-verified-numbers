"""The ready-made questions in the chat.

A chip already knows which panels it opens, so it needs no model, no key
and no network. The model is only needed when somebody types something.
"""

import answering
import metrics
import panels


class Chip:
    """One ready-made question, with the panels it opens."""

    def __init__(self, question, panel_names):
        self.question = question
        self.panels = panel_names


CHIPS = [
    Chip('What is the total owed in the current filter?', ['balance']),
    Chip('What is still open in the current filter?', ['balance']),
    Chip('Which supplier are we most in debt to?', ['by_supplier']),
    Chip('What is overdue in the current filter?', ['overdue', 'by_band']),
    Chip('How late are we on average?', ['overdue']),
]


def _sentence(chip, owed, today):
    if 'overdue' in chip.panels:
        total = metrics.overdue_total(owed, today)
        count = metrics.overdue_count(owed, today)
        return f'{metrics.format_money(total)} is overdue across ' \
               f'{count} documents.'
    if 'by_supplier' in chip.panels:
        rows = metrics.by_supplier(owed)
        name, value = rows[0]
        return f'The largest balance is {name}, with ' \
               f'{metrics.format_money(value)} owed.'
    total = metrics.total_owed(owed)
    count = metrics.count(owed)
    return f'The total owed in the current filter is ' \
           f'{metrics.format_money(total)} across {count} documents.'


def click(chip, owed, today=None, model=None):
    """One chip, no model call, one sentence written by code."""
    if not owed:
        return answering.Answer(rows_used=0, as_of=today,
                                refusal='Nothing matches the current filter.')

    # The same three to five a typed question opens. A chip is that
    # question with the typing already done.
    import routing
    opening = routing._three_to_five(list(chip.panels))
    built = [panels.build(name, owed, today=today) for name in opening]

    figures = []
    for panel in built:
        for figure_name in panels.MENU[panel.name].figures:
            value = metrics.compute(figure_name, owed, today=today)
            figures.append(answering.Figure(figure_name, figure_name,
                                            len(owed), value))

    return answering.Answer(panels=built, sentence=_sentence(chip, owed,
                                                             today),
                            rejected=False, rows_used=len(owed),
                            as_of=today, figures=figures)
