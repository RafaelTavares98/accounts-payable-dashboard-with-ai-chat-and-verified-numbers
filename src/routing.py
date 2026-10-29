"""The one step the model is allowed to take.

It reads the question and names panels. That is all. It does not see a row,
it does not see a figure, and it does not do arithmetic. Each view hands in
its own Board: the menu, what each panel looks like, and what it is about.
"""

import json


class Routed:
    """What the model answered with, after the menu checked it."""

    def __init__(self, question, panels=None, ignored=None, refusal='',
                 small_talk=False):
        self.question = question
        self.panels = panels or []
        self.ignored = ignored or []
        self.refusal = refusal
        self.small_talk = small_talk


class Board:
    """One view's menu, and the words the model is shown about it."""

    def __init__(self, menu, looks, fill, about, holds):
        self.menu = menu
        #: What each panel looks like on screen, in the words a reader
        #: would use. Nobody types by_component; they say "the ring".
        self.looks = looks
        #: The order panels are added in when the model names too few.
        self.fill = fill
        #: What a question must be about, said in the prompt.
        self.about = about
        #: What the data holds, said when a question is out of reach.
        self.holds = holds


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


def _what_is_on_screen(board):
    return '\n'.join(f'- {name}: {looks}'
                     for name, looks in board.looks.items())


def _prompt(question, history, board):
    menu = ', '.join(board.menu)
    return (
        _said_before(history) +
        'You are shown a fixed menu of dashboard panels. This is what '
        'each one looks like on the screen in front of the person:\n'
        f'{_what_is_on_screen(board)}\n'
        'They will describe what they see, not the names. "The ring", '
        '"the line", "the bars" are all panels above. '
        f'The names you may use are: {menu}. '
        'Read the question and answer in json, naming between three and '
        'five panels to open, most relevant first, and a short reason: '
        '{"panels": ["name", ...], "reason": "why"}. '
        'One panel only repeats the sentence; three to five show the '
        'figure from more than one side. '
        'If it is a greeting or anything else that is not a question '
        f'about {board.about}, answer '
        '{"panels": [], "small_talk": true} instead. '
        'Do not compute anything. Only pick from the menu. '
        f'Question: {question}'
    )


def _repair(question, bad, board):
    """A model that forgets the format usually remembers when it is
    shown its own answer beside the shape again."""
    return (
        'That was not json. You answered:\n'
        f'{bad[:400]}\n'
        'Answer again, json only, nothing else, in this shape: '
        '{"panels": ["name", ...], "reason": "why"}. '
        'The menu is: ' + ', '.join(board.menu) + '. '
        f'Question: {question}'
    )


FEWEST = 3
MOST = 5


def _three_to_five(chosen, board):
    """The model's own picks, topped up to three and cut at five.

    One panel is the sentence again in a box. More than five and the
    overlay is a second dashboard nobody asked for.
    """
    panels_open = list(chosen[:MOST])
    for name in board.fill:
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


def route(question, model, board, history=None):
    """Ask the model, and keep only what the menu allows.

    One retry when the reply is not json. Not a loop: every attempt
    costs a second of the reader's time.
    """
    try:
        reply = model(_prompt(question, history, board))
        data = _read(reply)
        if data is None:
            reply = model(_repair(question, str(reply), board))
            data = _read(reply)
    except Exception as error:
        return Routed(question,
                      refusal=f'The model could not be reached: {error}.')

    if data is None:
        return Routed(question,
                      refusal='I could not turn that into a question '
                              f'about {board.about}. Try naming what you '
                              'want to see.')

    names = data.get('panels')
    if not names:
        if data.get('small_talk'):
            return Routed(question, small_talk=True)
        return Routed(question,
                      refusal='That is not something this data can '
                              f'answer. It holds {board.holds}.')
    kept, ignored = [], []
    for name in names:
        if name in board.menu and name not in kept:
            kept.append(name)
        elif name not in board.menu and name not in ignored:
            ignored.append(name)
    if kept:
        return Routed(question, panels=_three_to_five(kept, board),
                      ignored=ignored)
    readable = ', '.join(name.replace('_', ' ') for name in ignored)
    return Routed(question, ignored=ignored,
                  refusal=f'No such panel: {readable}. Nothing opened.')
