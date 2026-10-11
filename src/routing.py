"""The one step the model is allowed to take.

It reads the question and names panels. That is all. It does not see a row,
it does not see a figure, and it does not do arithmetic.
"""

import json

import panels


class Routed:
    """What the model answered with, after the menu checked it."""

    def __init__(self, question, panels=None, ignored=None, refusal='',
                 small_talk=False):
        self.question = question
        self.panels = panels or []
        self.ignored = ignored or []
        self.refusal = refusal
        self.small_talk = small_talk


def _said_before(history):
    """The last few turns, as plain text.

    Questions and replies only. No figure ever travels in here, so the
    model still has nothing to do arithmetic with.
    """
    if not history:
        return ''
    recent = history[-6:]
    lines = '\n'.join(
        ('Person: ' if turn.get('role') == 'user' else 'You: ')
        + str(turn.get('text', ''))[:300] for turn in recent)
    return f'This is what was said before:\n{lines}\n'


#: What each panel looks like on screen, in the words a reader would
#: use. Nobody types by_issue_week; they say "the yellow line". Without
#: this the model is asked to match a question to a name it has only
#: ever seen as a name.
LOOKS_LIKE = {
    'balance': 'four big figures: the total owed, how many documents, '
               'the average document',
    'overdue': 'four big figures about what is late: the amount, how '
               'many, the share, the average days late',
    'by_band': 'a ring, a donut, split into four ageing bands: 1 to 30, '
               '31 to 60, 61 to 90 and over 90 days late',
    'by_month': 'a line chart of money by week, with a bright blue line '
                'for what is falling due and a yellow dotted line for '
                'what arrived',
    'by_supplier': 'a horizontal bar chart, one bar per supplier, '
                   'biggest at the top',
    'by_item': 'a horizontal bar chart, one bar per item bought, '
               'biggest at the top',
    'by_order': 'a table of purchase orders with a small bar in each '
                'row',
}


def _what_is_on_screen():
    return '\n'.join(f'- {name}: {looks}'
                     for name, looks in LOOKS_LIKE.items())


def _prompt(question, history=None):
    menu = ', '.join(panels.MENU)
    return (
        _said_before(history) +
        'You are shown a fixed menu of dashboard panels. This is what '
        'each one looks like on the screen in front of the person:\n'
        f'{_what_is_on_screen()}\n'
        'They will describe what they see, not the names. "The yellow '
        'line", "the ring", "the bars" are all panels above. '
        f'The names you may use are: {menu}. '
        'Read the question and answer in json, naming between three and '
        'five panels to open, most relevant first, and a short reason: '
        '{"panels": ["name", ...], "reason": "why"}. '
        'One panel only repeats the sentence; three to five show the '
        'figure from more than one side. '
        'If it is a greeting or anything else that is not a question '
        'about the accounts, answer '
        '{"panels": [], "small_talk": true} instead. '
        'Do not compute anything. Only pick from the menu. '
        f'Question: {question}'
    )


def _repair(question, bad):
    """A model that forgets the format usually remembers when it is
    shown its own answer beside the shape again."""
    return (
        'That was not json. You answered:\n'
        f'{bad[:400]}\n'
        'Answer again, json only, nothing else, in this shape: '
        '{"panels": ["name", ...], "reason": "why"}. '
        'The menu is: ' + ', '.join(panels.MENU) + '. '
        f'Question: {question}'
    )


#: The order panels are added in when the model names too few. The
#: figure first, then what is late, then who and when: the questions a
#: reader asks next, whatever they asked first.
FILL_ORDER = ('balance', 'overdue', 'by_supplier', 'by_month',
              'by_band', 'by_item', 'by_order')

FEWEST = 3
MOST = 5


def _three_to_five(chosen):
    """The model's own picks, topped up to three and cut at five.

    One panel is the sentence again in a box. More than five and the
    overlay is a second dashboard nobody asked for.
    """
    panels_open = list(chosen[:MOST])
    for name in FILL_ORDER:
        if len(panels_open) >= FEWEST:
            break
        if name not in panels_open:
            panels_open.append(name)
    return panels_open


def _read(reply):
    """The plan out of one reply, or None when it is not json."""
    try:
        data = json.loads(reply)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def route(question, model, owed=None, history=None):
    """Ask the model, and keep only what the menu allows.

    One retry when the reply is not json. Not a loop: every attempt
    costs a second of the reader's time.
    """
    try:
        reply = model(_prompt(question, history))
        data = _read(reply)
        if data is None:
            reply = model(_repair(question, str(reply)))
            data = _read(reply)
    except Exception as error:
        return Routed(question,
                      refusal=f'The model could not be reached: {error}.')

    if data is None:
        return Routed(question,
                      refusal='I could not turn that into a question '
                              'about the accounts. Try naming what you '
                              'want to see: a total, a supplier, what is '
                              'overdue.')

    names = data.get('panels')
    if not names:
        if data.get('small_talk'):
            return Routed(question, small_talk=True)
        return Routed(question,
                      refusal='That is not something this data can '
                              'answer. It holds supplier invoices: '
                              'totals, due dates, what is overdue, and '
                              'what was bought.')
    kept, ignored = [], []
    for name in names:
        if name in panels.MENU and name not in kept:
            kept.append(name)
        elif name not in panels.MENU and name not in ignored:
            ignored.append(name)
    if kept:
        return Routed(question, panels=_three_to_five(kept),
                      ignored=ignored)
    readable = ', '.join(name.replace('_', ' ') for name in ignored)
    return Routed(question, ignored=ignored,
                  refusal=f'No such panel: {readable}. Nothing opened.')
