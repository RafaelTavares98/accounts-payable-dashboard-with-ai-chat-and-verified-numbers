# Explanation

[README](../README.md) · [Tutorial](tutorial.md) · [How-to](how-to.md) ·
[Reference](reference.md) · **Explanation**

Why the project is built the way it is. One argument per section, each
against the alternative.

## Why the model never computes

A model can write a plausible number. That is the whole danger: the
number looks right and is not.

So the model gets one job. It reads the question and names panels.
Code computes every figure. Only then does the model see the figures,
to write a sentence around them.

`test_answering.py` proves the rule with a model that lies on purpose.
It hands back figures nobody computed. The answer must still carry the
computed ones, and the lying sentence is replaced by code. It is the
test the whole project stands on.

## Why the sentence is checked, not trusted

Telling the model "use only the figures given" is weak. It is still in
the prompt, because it costs nothing. The real gate is code: every
number in the sentence is compared against the computed figures. A
number that matches nothing means the sentence is thrown away and code
writes the replacement. The panels survive, because they were always
right.

Years like 2026 are not treated as figures. A date is not a total.

## Why two calls, and in that order

The first call names the panels. The figures do not exist yet, so the
model cannot invent around them. The figures exist before the second
call, so the model is handed facts, not a blank page.

A test counts the calls. A third call means something is asking twice.

The invoice view makes one call, not two. Its answers are seven fixed
sentences about the week, so the model has nothing to word: it only has
to say which of the seven the question is. Code writes the rest. Where
the shape of the answer is known in advance, a second call buys nothing
and can only introduce a number nobody computed.

## Why a small model routes and a large one writes

Naming panels off a menu of eight is a classification. It needs no
prose and no judgement, so it takes `deepseek-flash`, at a quarter of
the price and a fraction of the wait. The sentence is the one place
where wording matters, so it keeps `deepseek-v4-pro`.

## Why the model is handed a brief

A sentence written from three figures can only restate them. "The
landed cost is 26,483,864.42" is true and useless.

`cost_answering.brief` hands the model the whole filtered slice as
computed text: the seven parts of the cost, every carrier, operation and
month, the top parts and unit costs, the dearest shipments. The model can
now say why a figure is what it is, not only what it is. Every number in
the brief came from code, so the guard accepts a number quoted from it
and nothing else.

## Why the page reads the cost report and costs nothing itself

The rules that split freight by weight and duty by value live in
project 01, beside the tests that check them to the cent. A second copy
here would drift from the first the day a rule changed. So this page
only reads `data-live/cost/` and sums it. A figure on the page is a sum
over lines project 01 wrote, and nothing else.

## Why the payment figures left the page

The department is Production and Logistics Cost Management. It costs
what the invoices say; another team pays them. The page once showed
what was owed, what was overdue and how many days late. Those are a
payables desk's questions, not this department's, so they left with the
view. The assistant refuses a question about payments, because nothing
in the data says when anything was paid.

## Why final and provisional are always apart

A line is provisional until its shipment has the goods, the
international freight, the duty statement and the truck. Before that,
its cost can still move: the duty is not in, or the rate is still the
PTAX of the invoice date. Adding the two together without saying so
would present a guess as a fact. Every total on the page names its
provisional part.

Over the whole run, 2,944,468.30 of 26,483,864.42 is provisional, 11.1%.
It is not spread evenly: the early months are closed and October is
provisional down to the last line, because the run stopped on the 14th
with that month's goods still on the water. The finance view reads one
month at a time, so it shows October at 100% rather than the year at
11.1%. Both are true, and the one that matters at the close is the
month's.

## Why the recoverable taxes stand beside the cost

IPI, PIS, COFINS and ICMS come back to a manufacturer as credits. Put
inside the landed cost, they would make every part look a third dearer
than it is. Left out without a word, they would vanish from the page. So
they stand beside it, in a tile of their own.

## Why the month is the goods' month

A cost belongs to the close of the month its goods were billed, not the
month the truck arrived. That is how the department closes, on the 6th
business day of the month after. Months are drawn as columns, final at
the bottom and provisional on top: two months as a line is a straight
stroke that tells nobody anything.

## Why the cost per unit keeps four places

A cap that lands at 0.4577 a unit is not 0.46 to a team that multiplies
it by a hundred thousand. Every other figure stops at two places; this
one carries four, and its own class on the page, so the test that
forbids a third decimal can still catch a float that slipped through.

## Why our errors and the client's are apart

The two need different fixes. Ours are documents the reader could not
read or close: the fix is in the reader. The client's are a supplier's
or a carrier's mistakes, a price above the contract or a duty at a rate
not in force: the fix is a claim to the client. The anomaly view counts
the client's errors from flags the analyst confirmed, not from flags
alone, because a dismissed flag was an honest invoice.

Our count comes from the cost report, over the whole period: the model
never sees a document nobody could read, so it cannot flag one.

## Why a chip costs nothing

The video's demo works because the user never types. He clicks. A chip
already knows its panels, so it needs no model, no key and no network.
That is what makes the demo repeatable, and what keeps the page alive
when the API is down.

## Why a typed question opens one panel and a chip opens five

A chip is a request for an overview. The reader clicked "show me an
overview of this week" and expects the week laid out, so five panels
open over the dashboard with a line to each, the way the video does it.

A typed question is not that. It is one question with one answer, and
three pictures beside a one-line answer bury the dashboard the reader
was looking at. So a typed question opens one panel, and a question
whose answer is a single figure opens none: a sentence does not need a
picture beside it.

`plot_answers.wants_a_plot` is the test. "How many were flagged" is a
figure. "Show the flags by week" is a picture.

## Why the refusal exists

A dashboard that always produces a number is worse than one that
sometimes says no, because the reader cannot tell the two apart.

Four cases are refused instead of answered with a guess:

- the question needs a column the data does not have, like a cost
  centre or a payment date;
- the filters left nothing to say;
- a trend was asked over one line, where no trend exists;
- the model could not be reached.

Each refusal is a sentence, in plain words, ending in a period. It
opens no panels and carries no second message.

The last one is kept apart from the first three on purpose. A question
nobody understood and a model that is down look the same to the reader
unless the page says which happened, and the reader's next move is
different in each case: reword the question, or wait. So the answer
names the failure, down to the status the model replied with.

## Why money is Decimal

A float cannot hold 0.10 exactly. A cost that is wrong in the fourth
decimal is still wrong. `Decimal` holds every cent, and the tests pin
the type, not just the value.

## Why the reader never sees a line in the prompts

Sending the data would let the model answer from it, and then the
figure would be its opinion rather than a calculation. The prompts
carry the question, the menu, and the computed figures. Nothing else.
