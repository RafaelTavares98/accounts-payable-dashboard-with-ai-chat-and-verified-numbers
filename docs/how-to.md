# How-to guide

[README](../README.md) · [Tutorial](tutorial.md) · **How-to** ·
[Reference](reference.md) · [Explanation](explanation.md)

Recipes for the tasks that come up again. Each one assumes you know the
project and want one thing done.

## Run the tests

```bash
cd Portfolio/manual/02-payables-panel
python -m pytest
```

`306 passed` is the healthy state. The tests never touch the network.

## Serve without Docker

```bash
$env:PAYABLES_DATA = "$PWD\data"
$env:PAYABLES_TODAY = "2026-06-01"
python -m uvicorn web:app --app-dir src --port 8000
```

## Serve with Docker

```bash
docker compose up -d --build
docker compose logs --tail 20
```

Stop it with `docker compose down`. The image carries `src/` and
`data/` only.

## Connect the DeepSeek key

Two doors, both read by `model.key()`:

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
```

or the Windows keyring, the same place the invoice pipeline keeps its
mail password:

```bash
python -m keyring set payables-panel deepseek
```

A key the earlier projects stored under `deepseek` / `api-key` is
found too, so it never has to be pasted twice.

The environment wins when both exist. The page says under its title
whether the model is connected.

## Change the demo date

Overdue only means something against a date. The demo date comes from
outside the code:

```powershell
$env:PAYABLES_TODAY = "2026-06-01"
```

In Docker it is pinned in `docker-compose.yml`. Without the variable
the page uses the real today.

## Point at another data folder

```powershell
$env:PAYABLES_DATA = "C:\somewhere\else"
```

The folder must hold `invoices.csv` and `invoice_lines.csv` in the
shape the invoice pipeline writes:
[the columns](reference.md#the-data-files).

## Add a panel

Four steps, all tested by the existing suite.

1. Add the figure to `src/metrics.py` and to `FIGURES`.
2. Add the spec to `panels.MENU` with its kind, title and figures.
3. Add its rows to `_rows` in `src/panels.py`.
4. Watch `test_panels.py` and `test_metrics.py` confirm the menu and
   the figures still close.

## Add a chip

One entry in `suggestions.CHIPS`, with a question ending in `?` and the
panels it opens. `test_suggestions.py` refuses any chip that names a
panel off the menu or that refuses on the demo data.

## Show the invoice behind a figure

Put the PDFs the invoice pipeline wrote into `data/pdf/`. Each row of
the documents table then opens its own page through `/paper/{name}`.
The name is the `source` column of `invoices.csv`.

## Check every link in the docs

```bash
python check_links.py
```

It exits with 1 and names the file when a link or an anchor points
nowhere. Run it after any change to a heading.

## Rebuild the PDF of the reference

The step-by-step PDF in `reference/` was printed from
`reference/comportamento.html`. Change the HTML and print again with
Chrome:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless `
  --print-to-pdf="reference\comportamento-passo-a-passo.pdf" `
  "reference\comportamento.html"
```
