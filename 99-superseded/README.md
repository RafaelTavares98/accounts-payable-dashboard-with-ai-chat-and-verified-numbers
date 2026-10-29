# Superseded

The first version of this project answered one question: **what does the
company owe, and how late is it?** It read the invoice pipeline's two CSV
files into bills, and the chat opened panels called `balance`, `overdue`
and `by_band`.

That was the wrong question. The department is Production and Logistics
Cost Management. It costs what the invoices say; it does not pay them. The
project was rebuilt around landed cost, and later grew the Anomalies and
Finance views.

These nine files are what the first version was made of. Nothing in `src/`
imports them and no test runs them. They are kept because they are the
record of a design that was tried and replaced, not a design that failed
to compile.

| File | What it did |
|---|---|
| `payables.py` | the two CSV files, read as bills to pay |
| `filtering.py` | the filters, over open, overdue and credit |
| `metrics.py` | one function per figure the old dashboard could show |
| `suggestions.py` | the five chips of the old chat |
| `test_payables.py` | 23 tests on the bills |
| `test_filtering.py` | the filters, stacked |
| `test_metrics.py` | every old figure, worked out by hand |
| `test_suggestions.py` | the chips, and the three-to-five panel rule |
| `test_panels.py` | the closed menu, when there was one menu |

What replaced each of them:

| Gone | Now |
|---|---|
| `payables.py` | `cost.py`, and `anomalies.py` beside it |
| `metrics.py` | the figure lives with its data, in `cost.py` or `anomalies.py` |
| `filtering.py` | `cost.FILTERS` and `anomalies.FILTERS`, one set per view |
| `suggestions.py` | `cost_answering.CHIPS` and `anomaly_answering.CHIPS` |
| `panels.MENU` | `cost_panels.py` and `anomaly_panels.py`, one menu per view |

The three-to-five panel rule went with them. A question now opens one
panel, and a question whose answer is a single figure opens none.
