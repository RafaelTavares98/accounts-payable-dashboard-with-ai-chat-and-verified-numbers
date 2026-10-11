# Finish the panel

What the build got right, what it got wrong, and every step left to the
end of the project.

Written 2026-10-10, after reading the eight modules, the Dockerfile, the
runbook and the two log entries, and after running the suite: **178
passed in 1.55s**.

The method does not change. One red test at a time. A fix with no failing
test in front of it is a fix nobody will notice when it breaks again.

---

## Part 1. The scoreboard

### What it got right

| Thing | Why it counts |
|---|---|
| All 178 tests pass | The specification was met, not argued with |
| It never edited a test to make it pass | The one way to cheat at TDD, and it did not |
| `routing.py` imports no metrics | The isolation holds, and a test enforces it |
| Money is `Decimal` everywhere | No float ever touched a total |
| The lying-model check works | `_invented_numbers` catches a figure nobody computed |
| `routing.route` catches every exception | A dead API refuses instead of crashing |
| Docker files written ahead of the engine | `restart: always` was the right call |
| It said what it could not do | The log admits the engine never came up |

### What it got wrong

Six defects. None of them break a test, which is the point: the tests
were mine, and these are the holes I left.

| # | Where | What is wrong |
|---|---|---|
| 1 | `src/web.py:34` | The live dashboard defaults to the **test fixtures**, twelve invented rows |
| 2 | `src/web.py:120` | `/api/chip` throws away the filters the page sends |
| 3 | `src/answering.py:137` | The second prompt never contains the question |
| 4 | `src/web.py:87` | `app.state.model` is `None` and nothing ever sets it. A typed question always gives 503 |
| 5 | `src/answering.py:124` | The second model call has no `try`. A dead API crashes the page here |
| 6 | `src/web.py:25` | The demo date is frozen inside the production module |

And one whole half missing: the page has no connecting lines, no panels
over the base dashboard, no close button. Those are steps 5, 6 and 7 of
the video, and `docs/replication-map.md` already said they were ours to
build because no public repository has them.

---

## Part 2. Fix the six, one red at a time

Work in the project folder. Everything below assumes:

```bash
cd "C:\Users\tavar\OneDrive\Ambiente de Trabalho\contexts\over_employment\Portfolio\manual\02-payables-panel"
```

Run the whole suite between every step:

```bash
python -m pytest -q
```

### Step 1. The live dashboard reads the real data

**Red.** Add to `tests/test_web.py`, in a new class:

```python
class TestWhereTheDataComesFrom:
    def test_the_default_folder_is_not_the_fixtures(self):
        """A dashboard that ships pointing at its own test data shows
        twelve invented invoices to a real reader."""
        import web

        assert web._data_folder().name != 'fixtures'

    def test_the_default_folder_is_the_data_folder(self):
        import web

        assert web._data_folder().name == 'data'
```

See it fail:

```bash
python -m pytest tests/test_web.py -k "data_comes_from" -q
```

**Green.** In `src/web.py:30`, make `_data_folder()` return `ROOT / 'data'`
when `PAYABLES_DATA` is unset.

**Then the other tests break**, because `/api/overview` now reads 90 real
rows and the tests expect `67450.00`. That is correct and it is the
second half of this step: the web tests must point themselves at the
fixtures rather than rely on the default. Add to `tests/test_web.py`,
above the `client` fixture:

```python
@pytest.fixture(autouse=True)
def fixture_data(monkeypatch, fixtures):
    """The web tests use the twelve hand-written rows. The default is
    the real data, and a test that moves when the data moves is not a
    test."""
    monkeypatch.setenv('PAYABLES_DATA', str(fixtures))
```

Green again:

```bash
python -m pytest -q
```

### Step 2. A chip obeys the filters on screen

This is the sharpest one. The page already sends the filters
(`src/web.py:310`, in the JavaScript) and the server drops them.

**Red.** Add to `tests/test_web.py`, class `TestTheChips`:

```python
    def test_a_chip_answers_over_the_filters_on_screen(self, client):
        """Filter to Marsk, click the total chip, and the answer must be
        5,500.00. Showing 67,450.00 under a filtered heading is the worst
        kind of wrong: it looks right."""
        got = client.post('/api/chip', json={
            'chip': 0,
            'filters': {'supplier': 'Marsk Line Agencies B.V.'},
        })

        assert '5,500.00' in got.json()['sentence']

    def test_a_chip_refuses_an_unknown_filter(self, client):
        got = client.post('/api/chip', json={
            'chip': 0,
            'filters': {'cost_centre': 'Logistica'},
        })

        assert got.status_code == 400
```

```bash
python -m pytest tests/test_web.py -k "filters_on_screen or unknown_filter" -q
```

**Green.** In `click_chip` (`src/web.py:120`), read `body.get('filters')`
and run it through the same validation and `filtering.apply` that
`/api/ask` uses. Pull that shared work into one helper so the two
endpoints cannot drift apart again.

### Step 3. The second prompt carries the question

Right now the model is told "write one sentence that answers the
question" and is never shown the question. The fake model in the tests
does not care. A real one will write about nothing.

**Red.** Add to `tests/test_answering.py`, class `TestTheSecondCall`:

```python
    def test_the_question_is_in_the_prompt(self, owed, today, fake_model):
        """It is asked to answer a question it was never shown."""
        model = fake_model(plan('overdue'), 'Some words.')

        answering.answer('how much is late?', owed, today=today,
                         model=model)

        assert 'how much is late?' in model.calls[1]
```

```bash
python -m pytest tests/test_answering.py -k "question_is_in_the_prompt" -q
```

**Green.** Pass `question` into `_sentence_prompt` and put it in the text.

### Step 4. The second call cannot crash the page

**Red.** Add to `tests/test_refusals.py`, class `TestTheModelCannotBeReached`:

```python
    def test_a_failure_on_the_second_call_is_a_refusal(self, owed, today):
        """The first call worked, the panels were built, and then the API
        went down. The panels are real and must survive."""
        calls = []

        def dies_on_the_second(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return plan('overdue')
            raise ConnectionError('deepseek is unreachable')

        answer = answering.answer('how much is late?', owed,
                                  today=today, model=dies_on_the_second)

        assert answer.panels
        assert answer.sentence
        assert not answer.refusal
```

Read that assertion carefully. The panels were computed by code, so they
are good. Only the words are missing, and code can write those. This is a
**degraded answer, not a refusal**.

```bash
python -m pytest tests/test_refusals.py -k "second_call" -q
```

**Green.** Wrap `src/answering.py:124` in `try`/`except Exception` and
fall back to `_code_sentence`.

### Step 5. The demo date comes from outside the code

**Red.** Add to `tests/test_web.py`:

```python
class TestTheDate:
    def test_the_date_can_be_set_from_outside(self, monkeypatch, client):
        """Overdue means nothing without a date. Freezing it in the
        source means the only way to change it is to edit and redeploy."""
        monkeypatch.setenv('PAYABLES_TODAY', '2026-04-01')

        got = client.get('/api/overview', params={'state': 'overdue'})

        assert got.json()['documents'] == 2

    def test_without_the_variable_it_uses_today(self, monkeypatch):
        from datetime import date
        import web
        monkeypatch.delenv('PAYABLES_TODAY', raising=False)

        assert web.as_of() == date.today()
```

On 2026-04-01 only NCL-2026-3001 (due 04-11) is not yet due, so the two
overdue are... work it out from `tests/fixtures/invoices.csv` before you
write the number. If the figure in the test is a guess, the test is a
guess.

**Green.** Replace the module constant with a function `as_of()` that
reads `PAYABLES_TODAY` and falls back to `date.today()`. Add
`PAYABLES_TODAY: "2026-06-01"` to `docker-compose.yml` so the demo stays
still.

### Step 6. The model is connected

This is defect 4, and it is the biggest, so it gets its own part.

---

## Part 3. The DeepSeek client

A new module, `src/model.py`. It is the only file in the project allowed
to know that DeepSeek exists.

### What the tests must pin, before the code

Create `tests/test_model.py`. No test here touches the network.

```python
"""The one place that knows DeepSeek exists.

Everything else takes a model as an argument. This builds the function
they take. It is tested against a fake transport, never against the real
API, because a test that needs a key and a signal is a test nobody runs.
"""

import json

import pytest

import model


class FakeTransport:
    """Stands in for httpx. Records the request, returns a canned body."""

    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.sent = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.sent.append({'url': url, 'json': json, 'headers': headers})
        return FakeReply(self.body, self.status)


class FakeReply:
    def __init__(self, body, status):
        self._body = body
        self.status_code = status
        self.text = json.dumps(body)

    def json(self):
        return self._body


def a_reply(content):
    return {'choices': [{'message': {'content': content}}]}


class TestTheRequest:
    def test_it_calls_the_documented_url(self):
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0]['url'] == \
            'https://api.deepseek.com/chat/completions'

    def test_it_sends_the_model_rafael_chose(self):
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0]['json']['model'] == 'deepseek-v4-pro'

    def test_the_key_travels_in_the_header_not_the_body(self):
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0]['headers']['Authorization'] == \
            'Bearer sk-test'
        assert 'sk-test' not in json.dumps(transport.sent[0]['json'])

    def test_a_prompt_asking_for_json_turns_json_mode_on(self):
        """DeepSeek needs both: the word json in the prompt and the
        response_format field. One without the other fails at runtime."""
        transport = FakeTransport(a_reply('{}'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('answer in json please')

        assert transport.sent[0]['json']['response_format'] == \
            {'type': 'json_object'}

    def test_a_prompt_not_asking_for_json_leaves_it_off(self):
        transport = FakeTransport(a_reply('words'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('write one sentence')

        assert 'response_format' not in transport.sent[0]['json']

    def test_it_gives_up_rather_than_hanging(self):
        """A dashboard that waits forever is a dashboard that is down,
        without saying so."""
        transport = FakeTransport(a_reply('hello'))
        ask = model.deepseek(key='sk-test', transport=transport)

        ask('a prompt')

        assert transport.sent[0] and model.TIMEOUT_SECONDS <= 30


class TestTheReply:
    def test_the_content_comes_back_as_a_string(self):
        transport = FakeTransport(a_reply('the answer'))
        ask = model.deepseek(key='sk-test', transport=transport)

        assert ask('a prompt') == 'the answer'

    def test_an_error_status_raises(self):
        """`routing` catches it and turns it into a refusal. It must be
        allowed to reach there."""
        transport = FakeTransport({'error': 'nope'}, status=401)
        ask = model.deepseek(key='sk-test', transport=transport)

        with pytest.raises(model.ModelFailed):
            ask('a prompt')

    def test_the_key_is_not_in_the_error(self):
        transport = FakeTransport({'error': 'nope'}, status=401)
        ask = model.deepseek(key='sk-do-not-leak-this',
                             transport=transport)

        try:
            ask('a prompt')
        except model.ModelFailed as failed:
            assert 'sk-do-not-leak-this' not in str(failed)

    def test_a_reply_with_no_choices_raises(self):
        transport = FakeTransport({'choices': []})
        ask = model.deepseek(key='sk-test', transport=transport)

        with pytest.raises(model.ModelFailed):
            ask('a prompt')


class TestWhereTheKeyComesFrom:
    def test_the_environment_is_read_first(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-from-env')

        assert model.key() == 'sk-from-env'

    def test_the_keyring_is_the_fallback(self, monkeypatch):
        """The same place the invoice pipeline keeps its mail password.
        An environment variable sits in plain text in the registry."""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring',
                            lambda: 'sk-from-keyring')

        assert model.key() == 'sk-from-keyring'

    def test_no_key_anywhere_is_not_a_crash(self, monkeypatch):
        """The dashboard opens without one. Only typing needs it."""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring', lambda: None)

        assert model.key() is None
```

```bash
python -m pytest tests/test_model.py -q
```

Then write `src/model.py` until it passes. Service name in the keyring:
`payables-panel`, to match the pipeline's `invoice-pipeline`.

### Wire it in

**Red.** In `tests/test_web.py`:

```python
class TestTheModelIsConnected:
    def test_a_key_in_the_environment_connects_the_model(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-test')
        import web

        assert web.model_for_this_request() is not None

    def test_no_key_gives_a_sentence_not_a_500(self, client, monkeypatch):
        """503 is a status code. A reader needs a sentence."""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        web.app.state.model = None

        got = client.post('/api/ask', json={'question': 'what do we owe?'})

        assert got.status_code == 200
        assert 'key' in got.json()['refusal'].lower()
```

**Green.** Replace `app.state.model = None` with a lookup that builds the
client from `model.key()`, keeps `app.state.model` as an override for the
tests, and turns a missing key into a refusal rather than a 503.

Put the key in the keyring once, by hand:

```bash
python -m keyring set payables-panel deepseek
```

---

## Part 4. The front end, the half that is missing

Three of the seven steps of the video are not built. They are the three
the replication map said no public repository has.

Nothing here can be covered by pytest, so the test is a screenshot taken
through the browser, compared against the frames in `reference/frames/`.
Write the check before the code anyway: decide what the screenshot must
show, then build until it shows it.

### Start the server

```bash
$env:PAYABLES_DATA = "$PWD\data"
$env:PAYABLES_TODAY = "2026-06-01"
python -m uvicorn web:app --app-dir src --port 8000
```

Run it in the background so the terminal stays free.

### Open it in the browser pane

Use the built-in browser, not Chrome. It is in the app, the user can
watch, and it does not touch his logged-in sessions.

```
mcp__Claude_Browser__preview_start   url: http://localhost:8000
mcp__Claude_Browser__read_page       filter: all
mcp__Claude_Browser__computer        action: screenshot
```

Compare that screenshot against `reference/frames/frame_00.0s.jpg`. Open
the frame with the `Read` tool to see it side by side.

### What is missing, in the order to build it

**1. The base view is one row of two cards. The video has eleven
figures.**

Open `reference/frames/frame_00.0s.jpg` and count them: value paid by
competence, period balance, documents, average ticket, overdue share,
open balance, largest maturity, accounts by month, status doughnut,
ageing gauge, category table, period indicators, recent accounts table.

`/api/overview` returns two. Extend it to return every figure in
`metrics.FIGURES`, and add a test in `tests/test_web.py` that asserts the
overview carries each one by name. That test is cheap and it stops the
page and the metrics drifting apart.

**2. The panels open over the dashboard, not beside it.**

Today `showAnswer` empties a `<div class="panels">` that sits in the page
flow. In the video the panels are absolutely positioned sheets over a
dimmed base view, with a `Fechar painéis` button.

- Give the overlay `position: fixed`, a dark translucent backdrop, and
  the three glass lines already in the stylesheet
  (`background: #ffffffcc`, `backdrop-filter: blur(8px)`, a light
  border). They are there at `src/web.py:171`; they are just on a card
  in the flow.
- Add the close button. It clears the overlay and leaves the base view
  untouched.

**3. The animated lines.**

One `<svg>` layer above everything, `pointer-events: none`. For each
panel, one `<path>` from the chat answer's bounding box to the panel's.
Animate it by setting `stroke-dasharray` to the path length and
animating `stroke-dashoffset` from that length to zero.

```javascript
const length = path.getTotalLength();
path.style.strokeDasharray = length;
path.style.strokeDashoffset = length;
path.animate([{strokeDashoffset: length}, {strokeDashoffset: 0}],
             {duration: 600, fill: 'forwards'});
```

Redraw them on resize, or they point at nothing.

### Check it the way the video is checked

After each of the three, take a screenshot and put it beside the frame
it is copying:

| Build step | The frame to match |
|---|---|
| Base view | `reference/frames/frame_00.0s.jpg` |
| Chat panel open | `reference/frames/frame_10.0s.jpg` |
| Lines drawn | `reference/frames/frame_32.5s.jpg` |
| Panels over the base | `reference/frames/frame_17.5s.jpg` |

```
mcp__Claude_Browser__computer   action: screenshot
mcp__Claude_Browser__computer   action: left_click, ref: <the chip>
mcp__Claude_Browser__read_page  filter: interactive
```

Use `read_page` rather than screenshots to check text and structure. A
screenshot is for the look only.

### One thing the video has that this must not copy

The reference loads Phi-3.5 in the browser behind a green button,
`Ativar IA local`. This version calls an API instead, so the button is
replaced by a plain line saying whether the model is connected. Do not
draw a button that pretends to load a local model.

---

## Part 5. Docker

The engine never came up. The log says a reboot was not done.

```bash
wsl --status
docker version
```

If the Linux engine still returns 500, reboot before anything else. Then:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail 40
```

Check it from outside the container:

```
mcp__Claude_Browser__preview_start   url: http://localhost:8000
```

**A red test for the container.** The Dockerfile at line 6 installs
`fastapi uvicorn httpx` by hand and ignores the `requirements.txt` it
copied at line 5. Those two lists will drift. Before touching anything
else:

```bash
docker compose build --no-cache
```

then change line 6 to `RUN pip install --no-cache-dir -r requirements.txt`
and build again. Both must succeed.

`requirements.txt` also carries `pytest`, which has no business inside a
production image. Split it:

- `requirements.txt`: fastapi, uvicorn, httpx
- `requirements-dev.txt`: `-r requirements.txt`, then pytest

---

## Part 6. The documents, and shipping it

### Update what is now untrue

| File | What is stale |
|---|---|
| `README.md` | says "No source code is written here yet" |
| `tests/README.md` | says "No code exists yet. These tests are the specification" |
| `docs/stack-decisions.md` | four open decisions, three of which are now closed |

Rewrite them in the same voice as
[the invoice pipeline's docs](../../01-invoice-pipeline/docs/). That
project's four documents are the model: tutorial, how-to, reference,
explanation, cross-linked, with a nav line at the top of each.

Check the links mechanically before shipping. The invoice pipeline has a
checker that validates every link **and every anchor after the `#`**; it
lives in that project's history and is worth copying rather than
rewriting.

### The folder name

`02-payables-panel` holds no mailbox. Rename it to
`02-payables-panel`, which says what is inside. Every link that points at
it has to move with it:

```bash
rg -n "02-payables-panel" "C:\Users\tavar\OneDrive\Ambiente de Trabalho\contexts\over_employment"
```

Rename last, after everything else passes, so a broken link is the only
thing that can be wrong.

### Push it

`git` is not on PATH. It lives inside GitHub Desktop:

```bash
$env:Path = "C:\Users\tavar\AppData\Local\GitHubDesktop\app-3.6.6\resources\app\git\cmd;$env:Path"
```

This project has no repository yet. Ask Rafael for the name before
creating one; do not guess. Then, from a clean copy outside the wiki
repository:

```bash
gh repo create <name> --public --source . --remote origin --push
```

Two things the invoice pipeline learned the hard way:

- A `.gitattributes` with `* text=auto eol=lf` and `*.pdf binary`. Git
  will otherwise rewrite the line endings inside `reference/*.pdf` and
  `reference/frames/*.jpg` and corrupt them.
- `reference/MUST REPLICATE NOW.mp4` is 7 MB of somebody else's video.
  It does not belong in a public repository. Add it to `.gitignore`.

### Then stop

Do not post it anywhere. Publishing is Rafael's call, every time, and he
says so in his own words when he wants it.

---

## The checklist

```
[ ] 1  web reads data/, not tests/fixtures/
[ ] 2  a chip obeys the filters
[ ] 3  the question reaches the second prompt
[ ] 4  a dead API on the second call degrades, not crashes
[ ] 5  the date comes from PAYABLES_TODAY
[ ] 6  src/model.py, tested against a fake transport
[ ] 7  the key comes from the keyring, never a 500
[ ] 8  /api/overview carries every figure
[ ] 9  panels overlay the base view, with a close button
[ ] 10 the animated lines
[ ] 11 Dockerfile installs from requirements.txt
[ ] 12 requirements split, dev from production
[ ] 13 docker compose up, checked in the browser
[ ] 14 the four documents, cross-linked
[ ] 15 the folder renamed, every link moved
[ ] 16 the repository, with .gitattributes and the video ignored
```

Fourteen of the sixteen start with a failing test. The two that do not
are the drawing, and those are checked against the frames in
`reference/frames/`.
