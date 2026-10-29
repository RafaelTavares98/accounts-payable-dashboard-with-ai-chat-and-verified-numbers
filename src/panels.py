"""What a panel is, shared by every view's menu.

The model picks from a fixed menu and nothing else. A panel is data, not a
picture: it says what to draw, and the page draws it. Each view keeps its
own menu, in cost_panels.py and anomaly_panels.py.
"""


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
    """What one panel on a menu is made of."""

    def __init__(self, kind, title, figures):
        self.kind = kind
        self.title = title
        self.figures = figures
