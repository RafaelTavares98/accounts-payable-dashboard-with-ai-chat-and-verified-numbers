# Runbook

How the code gets written, one test at a time, until the project is done.
The tests are the specification and the order. They were written by the
IA above and are never changed here.

## The order

One red at a time. Each file assumes the ones above it pass.

| # | Test file | Module to write | What it pins |
|---|---|---|---|
| 1 | `test_payables.py` | `src/payables.py` | load the two CSVs, rows and lines, what is owed |
| 2 | `test_filtering.py` | `src/filtering.py` | the filters, how they stack, what data lacks |
| 3 | `test_metrics.py` | `src/metrics.py` | every figure, by name, and nothing else |
| 4 | `test_panels.py` | `src/panels.py` | the fixed menu of panels |
| 5 | `test_routing.py` | `src/routing.py` | the one call the model is allowed |
| 6 | `test_answering.py` | `src/answering.py` | question to sentence, two calls, no invented figure |
| 7 | `test_refusals.py` | `src/answering.py` again | the honest no |
| 8 | `test_suggestions.py` | `src/suggestions.py` | chips that need no model |
| 9 | `test_web.py` | `src/web.py` | the FastAPI surface |
| 10 | `test_end_to_end.py` | nothing new | the parts join up |

## The rules that cannot break

- The model never produces a number. Code computes every figure.
- The model is always an argument. Tests pass a fake one.
- No test reaches the network. No test needs an API key.
- Money is `Decimal`. Dates are `date`. Never float, never text.
- A chip costs no model call. A typed question costs exactly two.
- `routing.py` cannot import `metrics`. The test reads the file.
- Tests, fixtures and `conftest.py` are untouchable. Disagreements are
  reported in the chat and obeyed anyway.

## What each module must do

### 1. `payables.py`

Reads `invoices.csv` and `invoice_lines.csv` from one folder.

- `load(folder)` returns 12 rows, nothing dropped.
- A row: `number`, `status`, `revises`, `issuer`, `issued`, `due`,
  `subtotal`, `discount`, `total`, `order_number`, `shipment_id`,
  `line_count`, `problems`, `lines`, `is_credit`.
- Lines join on the sha256 hash, never on the number.
- `by_number(rows, number)` finds one row.
- `payable(rows)` drops superseded and unreadable. Ten remain.
- `needs_a_person(rows)` keeps the unreadable ones.

### 2. `filtering.py`

- `apply(owed, supplier=None, since=None, until=None, order=None,
  shipment=None, state=None, today=None)`. Any other keyword must
  raise `TypeError`.
- `state` in `STATES = ['open', 'overdue', 'credit']`. Never `paid`.
- `overdue` with no `today` raises `NeedsADate`. Due today is open.
- Credits sit in neither open nor overdue.
- `suppliers(owed)` and `period(owed)` feed the page.

### 3. `metrics.py`

One function per figure. All money in `Decimal`.

- `total_owed`, `count`, `ticket_average`, `overdue_total`,
  `overdue_count`, `overdue_rate`, `average_days_overdue`,
  `oldest_overdue`, `overdue_buckets`, `by_supplier`, `by_month`,
  `by_order`, `by_item`.
- `FIGURES` is the closed menu. `compute(name, owed, today=None)`.
- Unknown name raises `NoSuchFigure`.
- Empty lists: totals zero, averages `None`.
- `by_month` fills empty months. `overdue_buckets` always has 4 bands.

### 4. `panels.py`

- `MENU` holds 7 specs: `balance`, `overdue`, `by_band`,
  `by_supplier`, `by_month`, `by_item`, `by_order`.
- A spec: `kind`, `title`, `figures`. Kinds are cards, bar, line,
  table.
- `build(name, owed, today=None)` returns a filled panel: `name`,
  `kind`, `title`, `rows`, `empty`.
- Unknown name raises `NoSuchPanel`, message names the menu.
- Every figure a panel asks for must be in `metrics.FIGURES`.

### 5. `routing.py`

The model names panels. Nothing else.

- `route(question, model, owed=None)` calls the model once.
- The prompt carries the question, the menu names, and the word json.
- The prompt carries no row and no figure.
- A bad panel is dropped and recorded in `ignored`. All bad is a
  refusal. Non-JSON is a refusal. A raising model is a refusal.
- Figures in the reply are thrown away. Always.

### 6. `answering.py`

One question, from click to sentence. Two model calls.

1. Route: the model names panels.
2. Compute: code fills every panel and records every figure.
3. Write: the model gets the figures and writes the sentence.

- The sentence is checked against the computed figures. A number that
  matches none is rejected, the sentence is replaced by code, and the
  panels stay.
- Years like 2026 are not figures.
- The answer names the slice: `rows_used`, `as_of`, `figures`.
- `ENOUGH_FOR_A_TREND` is at least 2 and is written down.

### 7. The refusals, in `answering.py`

- A column the data lacks: refusal names it, no panels, no sentence.
- A filter that leaves nothing: refusal names the filter.
- A trend over fewer than two rows: refusal.
- A model that cannot be reached: refusal, page keeps working.
- A refusal ends with a period and carries no sentence of its own.

### 8. `suggestions.py`

- `CHIPS`: five, each a question ending in `?`, each naming panels
  that exist.
- `click(chip, owed, today=None, model=None)`: no model call, sentence
  written by code, real figure in it, respects the filters.

### 9. `web.py`

FastAPI. The browser draws, the server says what.

- `GET /`: the page, `text/html`, opens with no key.
- `GET /api/overview`: opening numbers, honors filters, unknown
  filter is 400.
- `GET /api/filters`: suppliers and states. No cost centre, no branch.
- `GET /api/suggestions`, `POST /api/chip`: chips, no model.
- `POST /api/ask`: question and filters, `app.state.model`, panels as
  data, refusal as a normal answer, empty question is 400.
- The key never appears in any response or error.

## When it is finished

`python -m pytest` green from the project root, in the order above.
One test at a time: red, then code, then green, then the next.
