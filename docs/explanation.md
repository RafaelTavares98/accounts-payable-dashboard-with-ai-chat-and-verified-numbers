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
computed ones, and the lying sentence is replaced by code. If that
test passed while the design broke somewhere else, the rule would be
decorative. It is the test the whole project stands on.

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

## Why a small model routes and a large one writes

Naming panels off a menu of seven is a classification. It needs no
prose and no judgement, so it takes `deepseek-flash`, at a quarter of
the price and a fraction of the wait. The sentence is the one place
where wording matters, so it keeps `deepseek-v4-pro`.

With the large model on both calls, a question took twenty seconds
with nothing on screen. It read as a broken button. Now it takes about
6.5, behind a waiting bubble.

## Why the model is handed a brief

A sentence written from three figures can only restate them. "The
total is 1,117,819.58" is true and useless.

`answering.brief` hands the model the whole filtered slice as computed
text: both weekly series, every week-on-week move, the sharpest one,
and the top suppliers, items and orders. The model can now say why a
figure moved, not only what it is. Every number in the brief came from
code, so the guard accepts a number quoted from it and nothing else.

## Why every row opens its invoice

The page can say 195,468.00 is overdue. Without the rows, nobody can
find out which bills that is. The documents table lists every one, and
each opens the PDF it was read from. A total is then something to
check, not something to believe.

## Why a chip costs nothing

The video's demo works because the user never types. He clicks. A chip
already knows its panels, so it needs no model, no key and no network.
That is what makes the demo repeatable, and what keeps the page alive
when the API is down. The model is only needed when somebody types
something nobody wrote down.

## Why the refusal exists

A dashboard that always produces a number is worse than one that
sometimes says no, because the reader cannot tell the two apart.

Four cases are refused instead of answered with a guess:

- the question needs a column the data does not have, like cost
  centre. An invoice carries none, and guessing it from the supplier
  would be inventing data;
- the filters left nothing to say;
- a trend was asked over one document, where no trend exists;
- the model could not be reached.

Each refusal is a sentence, in plain words, ending in a period. It
opens no panels and carries no second message, because two messages
are two answers to one question.

## Why the data is the invoice pipeline's CSV

The reference video invents 15,000 rows. This portfolio does not
invent data: an invoice Moty receives is an account payable, so the
other project's real output is this project's subject. Every figure in
the demo can be traced to a document that exists in `data/`.

The trade: three of the video's filters cannot exist here. An invoice
carries no category, no cost centre and no branch. They are dropped
rather than faked. Payment status becomes open or overdue, measured
against a date somebody supplies, because nothing in an invoice says
it was paid.

## Why money is Decimal

A float cannot hold 0.10 exactly. A payables total that is wrong in
the fourth decimal is still wrong. `Decimal` holds every cent, and the
tests pin the type, not just the value.

## Why the date comes from outside the code

Overdue means nothing without a date. Freezing the date in the source
means the only way to change it is to edit and redeploy.
`PAYABLES_TODAY` sets it from outside, and the Docker compose file
pins the demo to one day so it never ages.

## Why the reader never sees a row in the prompts

Sending the data would let the model answer from it, and then the
figure would be its opinion rather than a calculation. The prompts
carry the question, the menu, and the computed figures. Nothing else.
