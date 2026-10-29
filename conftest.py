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

#: The day every test pretends it is. An answer says which day it was
#: given on; supplying it here keeps the tests from aging.
TODAY = date(2026, 6, 1)


@pytest.fixture
def fixtures():
    """The folder holding the small hand-written files."""
    return HERE / 'tests' / 'fixtures'


@pytest.fixture
def lines(fixtures):
    """The four landed cost lines of tests/fixtures/cost, worked out by
    hand: two parts on an ocean shipment, one on an air shipment, and
    one whose freight is not billed yet."""
    import cost
    return cost.load(fixtures / 'cost')


@pytest.fixture
def real_lines():
    """Every landed cost line project 01 wrote for the real run."""
    import cost
    return cost.load(HERE / 'data-live' / 'cost')


@pytest.fixture
def anomaly_rows():
    """Every invoice the checking model scored in the real run."""
    import anomalies
    return anomalies.load(HERE / 'data-live')


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
