# Tutorial: the dashboard, end to end

[README](../README.md) · **Tutorial** · [How-to](how-to.md) ·
[Reference](reference.md) · [Explanation](explanation.md)

By the end of this lesson you will have served the dashboard, seen the
week's invoices over the real data, clicked a ready question, watched the
panels open over the page with a connecting line, read the anomalies the
checking model found, and closed the month on the finance view.

No key is needed for any of it. Only a typed question needs the model.

Allow fifteen minutes.

## Before you start

You need Python 3.10 or newer. Check it:

```bash
python --version
```

Move into the project and install what it needs:

```bash
cd Portfolio/manual/03-payables-panel
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m playwright install chromium
```

Four libraries serve the page: `fastapi`, `uvicorn`, `httpx` and
`keyring`. `pytest` runs the tests. `playwright` drives the browser
that checks the look.

## Step 1: prove the project works

```bash
python -m pytest --ignore=tests/test_look.py
```

You should see `320 passed`. If anything fails, stop here. The other 47,
the look tests, need the page served; they run in step 2.

What the twenty test files cover: [the tests](reference.md#the-tests).

## Step 2: serve the page

```bash
$env:PAYABLES_TODAY = "2026-06-01"
python -m uvicorn web:app --app-dir src --port 8000
```

Or with Docker, one command:

```bash
docker compose up -d --build
```

Open http://localhost:8000. Then run the rest of the tests:

```bash
python -m pytest tests/test_look.py
```

`PAYABLES_TODAY` freezes the day the page thinks it is, so the demo shows
the same week every time. Without it the page uses the real date, and the
week it opens on will be empty once the run is a few months old.

## Step 3: read the Invoices view

The rail on the left has four buttons. The first one opens on the real
run: 1,003 documents read between January and October 2026.

Across the top, five tiles say how the desk did this week: how many came
in, the share the reader closed on its own, what remains against the
target, supplier errors, and the reader's own errors. Under them, the
week against the target. Then the top issuers, the invoices themselves,
and two donuts: what kind of document, and what state each is in.

Nothing on that screen needed the model.

## Step 4: click a ready question

The assistant on the right offers four. Click "Show me an overview of
this week".

Panels open over the base view. One animated line connects the answer to
each panel. The page dims behind them. A button in the corner says
"Close panels". Click it and the base view is untouched.

The chip already knows its topic, so this worked with no key and no
network. Why: [a chip costs nothing](explanation.md#why-a-chip-costs-nothing).

## Step 5: filter

Click the period button in the top bar. Pick a carrier or a status and
every figure moves. A ready question clicked now answers over what is
left. Clearing the filters puts everything back.

## Step 6: type a question

Type "how many invoices came in?" and press Send.

Without a key the assistant answers with a sentence saying so. The page
keeps working. Connect a key the way
[the how-to](how-to.md#connect-the-deepseek-key) describes and ask again.

On this view the model does one thing: it answers with the name of a
topic, one word. Code writes every word of the sentence from the desk's
own figures. If the model cannot be reached, the answer says so rather
than listing what can be asked.

## Step 7: the anomalies

Click Anomalies on the rail. The same layout, over project 02's scores:
786 invoices scored, 163 flagged, 5,905,553.98 between them.

The middle table is the scored invoices. The Decision column is coloured
by what the analyst did: confirmed, pending, dismissed, or never flagged
at all. Down the right, where the flags sit in the process, and what the
analyst decided in the end.

Click "Whose errors are they?" in the assistant. The answer separates
ours, the 22 documents the reader could not close, from the client's.

A typed question here works differently: the model names the panels,
code computes every figure, and the model writes one sentence around the
figures it was handed. The sentence is checked against those figures
before it is shown:
[the two calls](explanation.md#why-two-calls-and-in-that-order).

One question opens one panel here, and a question whose answer is a
single figure opens none.

## Step 8: close the month

Click Finance. The five tiles are the month, not the week: what it cost
to land, how much of that is final, how much is still provisional, the
provisional share, and the recoverable taxes.

October is 100% provisional, because the goods had not all reached the
plant when the run stopped. The chart under the tiles shows the same
thing month by month: the landed line keeps rising while the final line
falls away at the end.

## What you just saw

The whole contract in one run: the model picks, code computes, and every
answer names the lines it came from.
