"""What every view's assistant shares: the answer, and the number guard.

The order matters on every view: the model names panels, code computes
every figure, and only then is the model handed those figures to write a
sentence around. A sentence carrying a number nobody computed is thrown
away, and code writes one instead.
"""

import re
from decimal import Decimal

_NUMBER = re.compile(r'\d[\d,.]*')

_YEAR = re.compile(r'^(19|20)\d{2}$')


class Figure:
    """One computed panel, traced to the function that made it."""

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
    allowed = {_plain(figure.value) for figure in figures
               if not isinstance(figure.value, list)}
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


def allowed_from(figures, built_panels, digest):
    """Every figure a sentence may carry: the panels' own values and
    everything in the brief, which was computed too."""
    allowed = _computed_values(figures, built_panels)
    tokens = _NUMBER.findall(digest)
    allowed |= set(tokens)
    allowed |= {token.replace(',', '') for token in tokens}
    allowed |= {token.rstrip('.,').replace(',', '') for token in tokens}
    return allowed
