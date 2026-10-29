# How-to guide

[README](../README.md) · [Tutorial](tutorial.md) · **How-to** ·
[Reference](reference.md) · [Explanation](explanation.md)

Recipes for the tasks that come up again. Each one assumes you know the
project and want one thing done.

## Run the tests

```bash
cd Portfolio/manual/03-payables-panel
python -m pytest --ignore=tests/test_look.py
```

`320 passed` is the healthy state. The tests never touch the network.
The 47 look tests need the page served on port 8000 first; then run
`python -m pytest tests/test_look.py` for `367 passed` in all.

## Serve without Docker

```bash
$env:PAYABLES_TODAY = "2026-06-01"
python -m uvicorn web:app --app-dir src --port 8000
```

## Serve with Docker

```bash
docker compose up -d --build
docker compose logs --tail 20
```

Stop it with `docker compose down`. The image carries `src/`, `data/`
and `data-live/`, and the compose file points `PAYABLES_DATA` at
`data-live`.

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

The environment wins when both exist. The chat says under its title
whether the model is connected.

## Refresh the data from the other two projects

One command, from this folder:

```bash
python refresh_live_data.py
```

It runs project 01's `cost` command, then copies ten files into
`data-live/`: the invoices and their lines, the labels, project 02's
scores, the four cost files, and the part and vendor names from the ERP.
It writes nothing if a source file is missing, and says which. The
columns: [the data files](reference.md#the-data-files).

Project 02's scores are only as fresh as its last run. To rescore
first, from `02-invoice-anomalies`:

```bash
python run.py prepare
python run.py watch --state data/watch-state.json
```

`watch` is the only writer of `anomalies.csv`. It walks the run week by
week from where it left off, so running it twice costs nothing.

## Point at another data folder

```powershell
$env:PAYABLES_DATA = "C:\somewhere\else"
```

The folder holds `invoices.csv`, `invoice_lines.csv`, `anomalies.csv`
and a `cost/` folder, in the shape the other two projects write.

## Add a panel

Four steps, all tested by the existing suite.

1. Add the figure to `src/cost.py`, as one function over lines.
2. Add the spec to `cost_panels.MENU` with its kind, title and figure.
3. Add its rows to `_rows` and its words to `LOOKS_LIKE` in
   `src/cost_panels.py`.
4. Give it a shape in `PANEL_SHAPE` in `src/page.html`.

`test_cost_panels.py` refuses a panel whose figure does not exist or
whose words are missing.

## Add a chip

One entry in `cost_answering.CHIPS`, with a question ending in `?` and
the panels it opens. `test_cost_chips.py` refuses any chip that names a
panel off the menu or that refuses on the demo data.

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
