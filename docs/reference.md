# Reference

[README](../README.md) · [Tutorial](tutorial.md) · [How-to](how-to.md) ·
**Reference** · [Explanation](explanation.md)

The facts. Endpoints, columns, figures, panels and the exact order of one
answer.

## The modules

| File | What it does |
|---|---|
| `src/cost.py` | reads the cost report, joins each line to its shipment and part, every cost figure |
| `src/anomalies.py` | reads the scored invoices, every anomaly figure, whose error each is |
| `src/panels.py` | what a panel is, shared by both menus |
| `src/cost_panels.py` | the closed menu of the cost view |
| `src/anomaly_panels.py` | the closed menu of the anomaly view |
| `src/routing.py` | the one call that turns a question into panel names |
| `src/answering.py` | the answer and the number guard, shared by both views |
| `src/cost_answering.py` | the brief, the two calls, the refusals and the chips of the cost view |
| `src/anomaly_answering.py` | the same for the anomaly view |
| `src/plot_answers.py` | every figure the 24 plots can draw, and whether a question wants a picture at all |
| `src/model.py` | the DeepSeek client, the only file that knows it exists |
| `src/web.py` | the FastAPI surface |
| `src/page.html` | the dashboard, its three views, the assistant and the overlay, in one file |
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
| `PAYABLES_DATA` | the data folder. Default `data-live/`, the real run. The cost report sits in its `cost/` |
| `PAYABLES_TODAY` | the day each answer says it was given on. Default today |
| `DEEPSEEK_API_KEY` | the model key. The keyring `payables-panel` is the fallback |

## The endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | the dashboard page |
| `GET /api/cost/overview` | the week's five tiles, the issuers, the status split |
| `GET /api/cost/invoices` | the invoices behind those figures |
| `GET /api/cost/invoice-list` | one row per document, for the middle table |
| `GET /api/cost/invoice-pdf/{name}` | the page a figure was read off |
| `GET /api/cost/finance` | the month's five tiles, the monthly series, the dearest parts |
| `GET /api/cost/shipments` | every shipment behind the figures, dearest first |
| `GET /api/cost/filters` | carriers, statuses, and whether a key is connected |
| `GET /api/cost/suggestions` | the four invoice chips |
| `POST /api/cost/chip` | one chip's answer, no model call |
| `POST /api/cost/ask` | a typed question's answer, one model call |
| `GET /api/finance/suggestions` | the five landed cost chips |
| `POST /api/finance/chip` | one chip's answer, no model call |
| `POST /api/finance/ask` | a typed question's answer, two model calls |
| `GET /api/anomalies/overview` | the week's five tiles and every anomaly figure |
| `GET /api/anomalies/list` | every scored invoice, flagged first |
| `GET /api/anomalies/filters` | suppliers, stages, and whether a key is connected |
| `GET /api/anomalies/suggestions` | the five anomaly chips |
| `POST /api/anomalies/chip` | one chip's answer, no model call |
| `POST /api/anomalies/ask` | a typed question's answer, two model calls |
| `GET /api/plot-figures` | every figure the 24 plots draw from |
| `POST /api/plot-answer` | the plots one question is allowed to open |

The `ask` endpoints take `question`, `filters` and `history`. Only the
last six turns of `history` are used.

The cost endpoints take the filter keys `carrier`, `mode`, `status`,
`month` and `product`. The anomaly endpoints take `supplier` and `stage`.
An unknown key is a 400.

## The cost figures

Every one is a function in `src/cost.py`, over a list of lines.

| Function | Returns |
|---|---|
| `landed_total` | the landed cost in reais |
| `final_total` | the part whose shipment has every document |
| `provisional_total` | the part still waiting for a document |
| `provisional_share` | the provisional part, in percent, one place |
| `credits_total` | IPI, PIS, COFINS and ICMS, kept beside the cost |
| `shipment_count`, `line_count` | how many shipments and order lines |
| `by_component` | the seven parts of the cost, biggest first |
| `by_carrier` | the cost of what each carrier moved |
| `by_mode` | by operation: air, ocean, or freight not billed yet |
| `by_product` | the cost of each part |
| `unit_cost` | cost per unit, weighted by quantity, four places |
| `by_month` | final and provisional by the goods' month |
| `by_shipment` | one row per shipment, dearest first |
| `targets(folder)` | the desk's three targets and the documents for a person |

The seven parts of a landed cost: goods, international freight, the truck
to the Moty plant, the customs broker, import duty (II), AFRMM and Siscomex.
How project 01 splits each one over the parts:
[the rules](../../01-invoice-pipeline/docs/reference.md#cost).

A shipment with no international freight invoice has no carrier and no
operation yet. Its lines say `freight not billed yet`.

Money is `Decimal` everywhere. A float never touches a total.

## The cost panels

`cost_panels.MENU` is the closed menu the model picks from.

| Name | Kind | Title |
|---|---|---|
| `landed` | cards | Landed cost |
| `by_component` | bar | What the cost is made of |
| `by_carrier` | bar | Cost by carrier |
| `by_mode` | bar | Cost by operation |
| `by_product` | bar | Cost by part |
| `unit_cost` | bar | Cost per unit |
| `by_month` | line | Cost by month |
| `by_shipment` | table | Dearest shipments |

A name off the menu is a `NoSuchPanel`.

## The anomaly figures

Every one is a function in `src/anomalies.py`.

| Function | Returns |
|---|---|
| `flagged_count`, `flagged_total`, `flag_rate`, `reviewed` | the headline |
| `by_stage`, `by_check`, `by_supplier`, `by_week`, `worst` | where the flags sit |
| `by_decision` | confirmed, pending and dismissed, all three always |
| `client_errors` | confirmed flags only |
| `our_errors(folder)` | documents the reader left for a person, from `exceptions.csv` |
| `by_origin` | ours beside the client's, four figures |

The anomaly menu adds `by_origin`, "Whose error", to `flags`, `by_stage`,
`by_check`, `flagged_by_supplier`, `flags_by_week` and `worst_flags`.

## The chips

Invoices, four: an overview of this week, of the targets, of the issuers,
of the errors.

Finance, five: what the parts cost to land, what the cost is made of,
which carrier moved the most, which part is dearest per unit, how much
is still provisional.

Anomalies, five: how many were flagged, whose errors they are, at which
stage, which check finds the most, which to check first.

Each names its topic or its panels up front, so a click costs no model
call and no key.

## The topics of the invoice view

The invoice assistant does not route panels. The model is asked for one
word, the name of a topic, and code writes the whole sentence from the
desk's own figures. A reply that is not one of these is treated as
"none".

| Topic | Answers |
|---|---|
| `intake` | how many invoices came in |
| `target` | whether the desk is on target, and what remains |
| `issuer` | which issuer sent the most |
| `attention` | which invoices need a look, revised or with a problem |
| `supplier` | supplier or carrier errors found |
| `automation` | the invoices the reader flagged |
| `status` | how the invoices split by status |

A question carrying an invoice number skips the model entirely: the row
is looked up by its key.

## One typed answer on the finance and anomaly views, in order

1. `routing.route` sends the question, the view's menu, what each panel
   looks like, and the last six turns to `deepseek-flash`. The reply is
   json naming panels. A reply that is not json gets one repair prompt.
   A panel off the menu is dropped and recorded in `ignored`. All off
   the menu is a refusal.
2. One panel is opened, the first the model named, and none at all when
   the question's answer is a single figure. `plot_answers.wants_a_plot`
   decides which it is.
3. A greeting is small talk. `deepseek-v4-pro` replies with no number
   at all, and any digit it writes is thrown away.
4. `anomaly_answering.brief` writes the filtered rows as text: the
   headline, whose error, the flags by stage, by check, by supplier and
   by week, and the highest scores. All of it computed.
5. `deepseek-v4-pro` gets the panel, the brief and the question, and
   writes the sentence. Every number in it is checked against the panel
   and the brief. One that matches nothing means code writes the
   sentence instead. The panel stays.

Two model calls per question there, three with a repair; one on the
invoice view. The prompts carry no lines, and the first prompt carries
no figures.

## The refusals

An answer is a refusal, a sentence ending in a period, when:

- the model named panels the menu does not hold;
- the model answered without json, or could not be reached;
- the data lacks the column the question asks for, like a cost centre or
  a payment date;
- the filters left nothing to say;
- a trend was asked over fewer than two lines.

A refusal carries no sentence and opens no panels. The base view never
needs the model, so it works with no key at all.

## The data files

`data-live/cost/`, as project 01 writes it with `python run.py cost` and
`refresh_live_data.py` copies in:

- `landed_cost.csv`: `shipment_id`, `order_number`, `code`, `ncm`,
  `quantity`, `fx`, `fx_source`, `goods_brl`, `freight_brl`,
  `inland_brl`, `broker_brl`, `duty_brl`, `afrmm_brl`, `siscomex_brl`,
  `credits_brl`, `status`, `landed_brl`, `unit_landed_brl`.
- `operations.csv`: `shipment_id`, `month`, `mode`, `origin`, `carrier`,
  and the shipment's freight, truck, broker and duties.
- `exceptions.csv`: `invoice_number`, `origin`, `reason`.
- `kpis.json`: `analysed_same_day`, `our_error_rate`,
  `known_before_close` by month.
- `items.csv` and `vendors.csv`: the desk's part and vendor names.

`data-live/anomalies.csv`, as project 02 writes it with `python run.py watch`:
`number`, `supplier`, `kind`, `issue_date`, `week`, `grand_total`,
`score`, `check`, `stage`, `checks`, `flagged`, `origin`, `decision`.
An older file without the last two still loads.

## The tests

Twenty files, 367 tests. `test_look.py` opens the page in Chromium
through Playwright and reads colour, size, the overlay and overflow back
out of it, across all three views. The values it checks are in
[the look](look.md). `tests/fixtures/` holds hand-written files whose
figures can be checked by eye. No test touches the network.

## The demo numbers

With the fixtures: 4 lines on 3 shipments, 24,659.00 landed, 1,100.00 of
it provisional, 3,147.50 of credits kept apart.

The real run, in `data-live/`: 1,003 invoices read between 2026-01-02
and 2026-10-14, 3,940 lines on them, 22 left for a person. 309 cost
lines on 112 shipments, 26,483,864.42 landed. 786 invoices scored, 163
flagged, 5,905,553.98 between them.
