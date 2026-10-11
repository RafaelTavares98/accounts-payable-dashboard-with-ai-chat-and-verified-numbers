# Tutorial: the dashboard, end to end

[README](../README.md) · **Tutorial** · [How-to](how-to.md) ·
[Reference](reference.md) · [Explanation](explanation.md)

By the end of this lesson you will have served the dashboard, seen the
base view over the real data, clicked a chip, watched the panels open
over the page with a connecting line, and closed them again.

No key is needed for any of it. Only a typed question needs the model.

Allow fifteen minutes.

## Before you start

You need Python 3.10 or newer. Check it:

```bash
python --version
```

Move into the project and install what it needs:

```bash
cd Portfolio/manual/02-payables-panel
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m playwright install chromium
```

Four libraries serve the page: `fastapi`, `uvicorn`, `httpx` and
`keyring`. `pytest` runs the tests. `playwright` drives the browser
that checks the look.

## Step 1: prove the project works

```bash
python -m pytest
```

You should see `306 passed`. If anything fails, stop here. The rest of
the lesson assumes a healthy project.

What the twelve test files cover:
[the tests](reference.md#the-tests).

## Step 2: serve the page

```bash
$env:PAYABLES_DATA = "$PWD\data"
$env:PAYABLES_TODAY = "2026-06-01"
python -m uvicorn web:app --app-dir src --port 8000
```

Or with Docker, one command:

```bash
docker compose up -d --build
```

Open http://localhost:8000.

The base view opens with the real figures: total owed, documents,
average ticket, the overdue block, and the breakdowns by supplier, month,
order and item. Nothing needed the model.

## Step 3: click a chip

The chat under the dashboard offers five ready questions. Click the one
about the total.

Panels open over the base view. One animated line connects the answer
to each panel. The page dims behind them. A button in the corner says
"Fechar painéis". Click it and the base view is untouched.

Each chip already knows its panels, so this worked with no key and no
network. Why: [a chip costs nothing](explanation.md#why-a-chip-costs-nothing).

## Step 4: type a question

Type "how much is late?" and press Ask.

Without a key the chat answers with a sentence saying so. The page keeps
working. Connect a key the way
[the how-to](how-to.md#connect-the-deepseek-key) describes and ask again.

Now two things happen, in order. The model names the panels, code
computes every figure, and the model writes one sentence around the
figures it was handed. The sentence is checked against the computed
figures before it is shown:
[the two calls](explanation.md#why-two-calls-and-in-that-order).

## Step 5: change the filters

Pick a supplier in the filter above the dashboard. Every figure moves.
A chip clicked now answers over the filtered rows only. The same
question you typed before answers over the filtered rows too, because
the page sends its filters with every question.

## What you just saw

The whole contract in one run: the model picks, code computes, and every
answer names the rows it came from.
