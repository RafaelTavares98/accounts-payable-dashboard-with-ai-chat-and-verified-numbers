# Reference

[README](../README.md) · [Tutorial](tutorial.md) · [How-to](how-to.md) ·
**Reference** · [Explanation](explanation.md)

The facts. Commands, columns, endpoints, figures, panels and the exact
order of one answer.

## The modules

| File | What it does |
|---|---|
| `src/payables.py` | loads the two CSVs, joins lines by hash, keeps what is owed |
| `src/filtering.py` | the filters, and the states open, overdue, credit |
| `src/metrics.py` | every figure the page can show |
| `src/panels.py` | the fixed menu of panels |
| `src/routing.py` | the one call that turns a question into panel names |
| `src/answering.py` | the two calls, the check, and the refusals |
| `src/suggestions.py` | the five chips and their sentences |
| `src/model.py` | the DeepSeek client, the only file that knows it exists |
| `src/web.py` | the FastAPI surface, the documents and their PDFs |
| `src/page.html` | the dashboard, the chat and the overlay, in one file |
| `src/static/echarts.min.js` | the chart library, served locally |
| `check_links.py` | every link and anchor in the markdown, checked |

## The two models

| Constant | Model | Job |
|---|---|---|
| `model.ROUTING_MODEL` | `deepseek-flash` | names the panels |
| `model.MODEL` | `deepseek-v4-pro` | writes the sentence, and small talk |

Each call waits at most `model.TIMEOUT_SECONDS`, 20 seconds.

The key is looked for in this order: `DEEPSEEK_API_KEY`, then the
keyring entry `payables-panel` / `deepseek`, then `deepseek` /
`api-key`, the one the earlier projects wrote.

## The environment

| Variable | What it sets |
|---|---|
| `PAYABLES_DATA` | the folder holding the two CSVs. Default `data/` |
| `PAYABLES_TODAY` | the day the dashboard pretends it is. Default today |
| `DEEPSEEK_API_KEY` | the model key. The keyring `payables-panel` is the fallback |

## The endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | the dashboard page |
| `GET /api/overview` | every figure, over the given filters |
| `GET /api/documents` | every document behind the figures, by due date |
| `GET /paper/{name}` | one invoice PDF, out of `data/pdf/` |
| `GET /api/filters` | suppliers, states, and whether a key is connected |
| `GET /api/suggestions` | the five chips |
| `POST /api/chip` | one chip's answer, no model call |
| `POST /api/ask` | a typed question's answer, two model calls |

`/paper/{name}` refuses any name with a slash or not ending in `.pdf`,
with a 400. A name not on file is a 404.

`POST /api/ask` takes `question`, `filters` and `history`. Only the
last six turns of `history` are used.

`/api/overview`, `/api/documents`, `/api/chip` and `/api/ask` take the
same filter keys:
`supplier`, `since`, `until`, `order`, `shipment`, `state`. An unknown
key is a 400. `state` is `open`, `overdue` or `credit`, never `paid`.

## The figures

`metrics.FIGURES` is the closed menu. `compute(name, owed, today)`
computes one by name.

| Name | Returns |
|---|---|
| `total_owed` | the sum of the documents owed, credit notes subtracting |
| `count` | how many documents |
| `ticket_average` | the average document |
| `overdue_total` | how much is past its due date |
| `overdue_count` | how many are past their due date |
| `overdue_rate` | the share that is overdue, in percent |
| `average_days_overdue` | the mean days late |
| `oldest_overdue` | the document most late |
| `overdue_buckets` | four bands: 1-30, 31-60, 61-90, over 90 days |
| `by_supplier` | owed per supplier, biggest first |
| `by_month` | owed per issue month, gaps filled |
| `by_order` | owed per purchase order, freight out |
| `by_item` | owed per line description |
| `by_category` | owed per kind of item, read from the description |
| `by_issue_week` | owed per week the invoice arrived |
| `by_due_week` | owed per week the invoice falls due |

Money is `Decimal` everywhere. A float never touches a total.

## The panels

`panels.MENU` is the closed menu the model picks from.

| Name | Kind | Title | Figures |
|---|---|---|---|
| `balance` | cards | Balance | total_owed, count, ticket_average |
| `overdue` | cards | Overdue | overdue_total, overdue_count, overdue_rate, average_days_overdue |
| `by_band` | bar | Overdue by band | overdue_buckets |
| `by_supplier` | bar | Owed by supplier | by_supplier |
| `by_month` | line | Owed by month | by_month |
| `by_item` | bar | Owed by item | by_item |
| `by_order` | table | Owed by order | by_order |

A name off the menu is a `NoSuchPanel`. A figure a panel asks for must
be on `FIGURES` or the tests fail.

## The chips

Five, in order: the total, what is still open, which supplier is owed
most, what is overdue, and how late on average. Each names its panels
up front, so a click costs no model call and no key.

## One typed answer, in order

1. `routing.route` sends the question, the menu, what each panel looks
   like, and the last six turns to `deepseek-flash`. The reply is json
   naming panels. A reply that is not json gets one repair prompt.
   A panel off the menu is dropped and recorded in `ignored`. All off
   the menu is a refusal.
2. The picks are topped up to three and cut at five. One panel is the
   sentence again in a box. Six is a second dashboard.
3. A greeting is small talk. `deepseek-v4-pro` replies with no number
   at all, and any digit it writes is thrown away.
4. `answering.answer` builds every panel and records every figure,
   with its function and its row count.
5. `answering.brief` writes the filtered slice as text: both weekly
   series, every week-on-week move, the sharpest one, the top
   suppliers, items and orders. All of it is computed.
6. `deepseek-v4-pro` gets the figures, the brief and the question, and
   writes the sentence. Every number in it is checked against the
   figures and the brief. One that matches nothing means code writes
   the sentence instead. The panels stay.

Two model calls per question, three with a repair. The prompts carry no
rows, and the first prompt carries no figures.

## The refusals

An answer is a refusal, a sentence ending in a period, when:

- the model named panels the menu does not hold;
- the model answered without json, or could not be reached;
- the data lacks the column the question asks for;
- the filters left nothing to say;
- a trend was asked over fewer than two documents.

A refusal carries no sentence and opens no panels. The base view never
needs the model, so it works with no key at all.

## The data files

The two CSVs the page reads, as the invoice pipeline writes them:

- `invoices.csv`: `invoice_number`, `status`, `revises`, `issuer`,
  `issue_date`, `due_date`, `subtotal`, `discount`, `grand_total`,
  `order_number`, `shipment_id`, `line_count`, `decimal_mark`,
  `date_order`, `source`, `sha256`, `first_seen`, `problems`.
- `invoice_lines.csv`: `invoice_number`, `sha256`, `row`,
  `description`, `quantity`, `unit_price`, `net`.

Lines join on the sha256 hash, never on the number, because a revision
shares its number with the document it replaces.

## The tests

Twelve files, 306 tests. `test_look.py` opens the page in Chromium
through Playwright and reads colour, size and overflow back out of it.
The values it checks are in [the look](look.md). `tests/fixtures/` holds twelve hand-written
rows whose figures can be checked by eye. No test touches the network.
The order to make them pass is in `tests/README.md`.

## The demo numbers

With the fixtures, on 2026-06-01: 10 documents owed, 67,450.00 total,
31,750.00 overdue across 4 documents, an average of 31.5 days late.
The real data holds 90 documents and 1,117,819.58.
