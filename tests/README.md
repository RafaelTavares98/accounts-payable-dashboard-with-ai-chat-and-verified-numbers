# The tests, and the order they were made to pass

These tests are the specification. The code was written against them,
one red at a time, and the project is healthy when all of them pass:

```bash
python -m pytest -q
```

202 tests, none touching the network and none needing a key.

## Where the data comes from

The tests read `tests/fixtures/`: a small hand-written copy of the two
files the invoice pipeline writes, twelve invoices, so every figure
can be checked by eye. The web tests pin themselves to it with an
autouse fixture; the live default is `data/`, the real output.

## What the reference has and this data does not

The video filters by category, cost centre, branch and payment status.
None of those columns exist in an invoice. Inventing them would mean
inventing data, which this portfolio does not do.

| Reference filter | What replaces it here |
|---|---|
| category | the family of goods on the line items |
| cost centre | nothing. Dropped |
| branch | nothing. Dropped |
| payment status | derived from the due date: open or overdue |
| period | the issue date, which is real |

Payment status is the sharp one. Nothing in an invoice says it was paid,
so "paid" cannot be claimed. Only "due" and "overdue" can, and only
against a date somebody supplies. `test_metrics.py` pins that.

## The order the code was written in

| # | Test file | The module it drove |
|---|---|---|
| 1 | `test_payables.py` | `src/payables.py` |
| 2 | `test_filtering.py` | `src/filtering.py` |
| 3 | `test_metrics.py` | `src/metrics.py` |
| 4 | `test_panels.py` | `src/panels.py` |
| 5 | `test_routing.py` | `src/routing.py` |
| 6 | `test_answering.py` | `src/answering.py` |
| 7 | `test_refusals.py` | `src/answering.py`, again |
| 8 | `test_suggestions.py` | `src/suggestions.py` |
| 9 | `test_web.py` | `src/web.py` |
| 10 | `test_model.py` | `src/model.py` |
| 11 | `test_end_to_end.py` | nothing new. It proves the parts join up |

## The rule every file defends

The model never produces a number.

It reads the question and names which panels to open. Code computes
every figure over the filtered rows, and only then is the model given
those figures to write a sentence around.

`test_answering.py` enforces this with a model that lies: it returns
figures that are wrong on purpose. The answer must still carry the
right ones.

## The model is a seam, not a dependency

Every function that would call DeepSeek takes the model as an
argument. The tests pass a function that returns a canned string, or a
fake transport that records the request. `src/model.py` is the only
file that knows DeepSeek exists.

A test that cannot run on a plane is a test nobody runs.
