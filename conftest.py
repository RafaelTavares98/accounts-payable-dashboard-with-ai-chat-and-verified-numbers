"""Point pytest at the source, and hand every test the same data.

The fixtures live here rather than in each file, because a figure that two
tests disagree about is worse than a figure neither of them checks.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'src'))

#: The day every test pretends it is. Nothing in an invoice says whether it
#: was paid, so overdue only means anything against a date somebody
#: supplies. Supplying it here keeps the tests from aging.
TODAY = date(2026, 6, 1)


@pytest.fixture
def fixtures():
    """The folder holding the two small CSV files."""
    return HERE / 'tests' / 'fixtures'


@pytest.fixture
def rows(fixtures):
    """The twelve invoices, loaded, with nothing filtered out yet."""
    import payables
    return payables.load(fixtures)


@pytest.fixture
def owed(rows):
    """The ten invoices that are actually owed.

    A superseded document was replaced and must never be paid. An
    unreadable one is not a bill yet; it is a job for a person.
    """
    import payables
    return payables.payable(rows)


@pytest.fixture
def today():
    return TODAY


class FakeModel:
    """Stands in for DeepSeek.

    It records every call, so a test can say how many were made, and it
    replies with whatever the test told it to reply. No network, no key,
    no waiting.
    """

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, prompt):
        self.calls.append(prompt)
        if not self.replies:
            raise AssertionError('the model was called more times than the '
                                 'test expected')
        return self.replies.pop(0)


@pytest.fixture
def fake_model():
    return FakeModel
