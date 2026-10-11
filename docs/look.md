# The look

The numbers are right. The page is not. This is the specification for the
page, written as values rather than adjectives, because the person building
it cannot see pictures.

Every colour below was sampled from the frames in `reference/frames/` with
Pillow, not guessed. Where a value says `#082231`, that hex was read off
pixel for pixel.

---

## Why this file exists

The last round of instructions said things like "a dimmed, blurred
backdrop" and "animate the line". Those were obeyed exactly and the result
looks nothing like the video, because an adjective cannot be checked.

So nothing here is an adjective. Every rule is a number, and every number
has a test that reads it back out of the browser. The loop is the same as
always: red, green, next.

---

## Part 1. The tokens

Put these on `:root` and use nothing else. A hex typed anywhere but here is
a bug.

```css
:root {
  --bg:            #061C28;
  --rail:          #021A26;
  --topbar:        #091F2D;
  --surface:       #0A2432;
  --surface-2:     #0E2C3D;
  --border:        #14384C;

  --text:          #E6F0F6;
  --muted:         #6B8296;

  --accent:        #75D6FF;
  --accent-strong: #007BBC;
  --bar:           #225A7F;

  --good:          #2E9E6B;
  --warn:          #C9A227;
  --bad:           #D1495B;

  --glass:         rgba(0, 60, 91, 0.55);
  --glass-edge:    rgba(79, 195, 247, 0.35);
  --backdrop:      rgba(3, 16, 25, 0.72);
  --line:          #4FC3F7;
}
```

Where each one came from:

| Token | Sampled at |
|---|---|
| `--bg` | `frame_00.0s.jpg`, the page behind the cards |
| `--rail` | the left icon strip, same frame |
| `--topbar` | the bar holding the filters |
| `--accent` | the "Perguntar aos dados" button |
| `--accent-strong` | the user's own chat bubble, `frame_10.0s.jpg` |
| `--bar` | the fill of a bar in "Contas por mês" |
| `--glass` | a panel floating over the base view, `frame_17.5s.jpg` |
| `--backdrop` | the dimmed dashboard under those panels |

The page today is `#f4f7fb`, near white. That is the single biggest
difference and it is one line.

---

## Part 2. The layout

### The whole window

```
┌──┬──────────────────────────────────────────┬───────────┐
│  │  top bar, 64px                           │           │
│  ├──────────────────────────────────────────┤  chat     │
│  │                                          │  380px    │
│56│  the grid, 12 columns, 16px gap          │  full     │
│px│                                          │  height   │
│  │                                          │           │
└──┴──────────────────────────────────────────┴───────────┘
```

| Part | Rule |
|---|---|
| Left rail | 56px wide, full height, `--rail`, five items stacked |
| Top bar | 64px tall, `--topbar`, 1px bottom border `--border` |
| Grid | 12 columns, 16px gap, 24px padding |
| Chat | 380px wide, fixed to the right edge, full height, `--surface` |
| Card | `--surface`, 1px `--border`, 10px radius, 16px padding |

The chat is a **column on the right**, not a box at the bottom. In
`frame_10.0s.jpg` it runs floor to ceiling down the right-hand side. That
is the second biggest difference.

### The top bar, left to right

1. The title, `Contas a Pagar`, 18px, `--text`.
2. Under it, 12px `--muted`: how many documents and what period.
3. The filters, as `<select>` elements, 13px.
4. The **Perguntar aos dados** button: `--accent` background, `#05202C`
   text, 999px radius, 8px by 16px padding.
5. The year pills on the far right.

Today there is one lone supplier `<select>` floating below the cards.

### The grid

| Panel | Columns | Rows | Chart |
|---|---|---|---|
| `balance` | 8 | 1 | cards, four across |
| `overdue` | 4 | 1 | cards, two across |
| `by_month` | 7 | 2 | line with a filled area |
| `by_band` | 5 | 2 | vertical bars |
| `by_supplier` | 6 | 2 | horizontal bars |
| `by_item` | 6 | 2 | horizontal bars |
| `by_order` | 12 | 2 | table, with a bar inside the row |

A row is 180px. `by_order` scrolls inside its own card and never grows past
it. Today it runs off the bottom of the page, which is defect zero.

---

## Part 3. The charts

Every panel except `balance`, `overdue` and `by_order` draws a chart. Not a
text table. The page draws text tables today because nobody ever said
otherwise.

Use **ECharts 5.5.1**, pinned:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.1/echarts.min.js"></script>
```

Shared options:

| Option | Value |
|---|---|
| `backgroundColor` | `transparent` |
| axis line and labels | `--muted`, 11px |
| split lines | `--border`, 1px, dashed |
| series colour | `--bar`, and `--accent` for the top item |
| `animationDuration` | 500 |
| `grid` | left 8, right 16, top 24, bottom 8, `containLabel: true` |

No tooltip library, no legend unless the chart has more than one series.

---

## Part 4. The numbers on the page

Two of these are Python bugs, not CSS.

### `12420.2175555555555555556`

`metrics.ticket_average` divides and never rounds. A Decimal division keeps
every place it can. Quantise to two.

**Red first**, in `tests/test_metrics.py`:

```python
    def test_the_average_is_two_decimal_places(self, owed):
        average = metrics.ticket_average(owed)

        assert average == average.quantize(Decimal('0.01'))
```

### `1117819.58`

The API returns `str(Decimal(...))`. Formatting belongs at the edge, where
the thing is being shown, not in the metric.

**Red first**, in `tests/test_web.py`:

```python
    def test_money_is_formatted_for_a_person(self, client):
        got = client.get('/api/overview').json()

        assert got['total_owed'] == '67,450.00'
```

The rules, all of them:

| Kind | Form | Example |
|---|---|---|
| Money | thousands comma, two places | `67,450.00` |
| Money, headline card | shortened at a million | `1.12 M` |
| Share | one place and a sign | `40.0%` |
| Days | one place and a word | `31.5 days` |
| Count | plain | `90` |
| A date | ISO | `2026-06-01` |

The headline shortening only happens in a `balance` or `overdue` card. A
table row always shows the full figure.

---

## Part 5. The overlay

This is steps 5, 6 and 7 of the video, and what exists today is one white
box with a short green line beside it.

| Piece | Rule |
|---|---|
| Backdrop | `position: fixed`, inset 0, `--backdrop`, `backdrop-filter: blur(3px)` |
| Panel | `--glass`, `backdrop-filter: blur(10px)`, 1px `--glass-edge`, 12px radius |
| Panel size | 280px wide, height by content, never more than 340px |
| Layout | the panels fan out from the answer, none overlapping another |
| Close | a button reading `Fechar painéis`, top right, 24px from each edge |
| Line layer | one `<svg>` over everything, `pointer-events: none` |
| Line | `--line`, 2px, 0.85 opacity, one path per panel |
| Animation | `stroke-dashoffset` from the path length to 0, 600ms, `ease-out` |

The panels in `frame_17.5s.jpg` are **blue glass**, not white. The line is
cyan and thick enough to read at a glance, not a hairline.

---

## Part 6. The tests, before any of the drawing

Create `tests/test_look.py`. It drives the real page with playwright and
reads values back out of the browser. Every assertion below is a number
somebody can check, which is the whole point of this file.

Write them all, watch them all fail, then build until they pass. One at a
time.

```python
"""The look, as numbers.

Nobody building this page can see it. So every rule in docs/look.md is
read back out of the browser here. A test that says "it looks right" is
not a test; a test that says the background is rgb(6, 28, 40) is.

These need the server running. Start it with:
    uvicorn web:app --app-dir src --port 8000
"""

import re

import pytest

PAGE = 'http://localhost:8000'

MONEY = re.compile(r'^-?\d{1,3}(,\d{3})*\.\d{2}$')
SHORT = re.compile(r'^-?\d+(\.\d+)? [MK]$')


@pytest.fixture(scope='module')
def page():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        open_page = browser.new_page(viewport={'width': 1600,
                                               'height': 900})
        open_page.goto(PAGE)
        open_page.wait_for_selector('.card')
        yield open_page
        browser.close()


class TestTheColours:
    def test_the_page_is_dark(self, page):
        """The single biggest difference from the reference."""
        colour = page.evaluate(
            "getComputedStyle(document.body).backgroundColor")

        assert colour == 'rgb(6, 28, 40)'

    def test_the_rail_is_darker_than_the_page(self, page):
        assert page.evaluate(
            "getComputedStyle(document.querySelector('.rail'))"
            ".backgroundColor") == 'rgb(2, 26, 38)'

    def test_the_ask_button_is_the_accent(self, page):
        assert page.evaluate(
            "getComputedStyle(document.querySelector('.ask'))"
            ".backgroundColor") == 'rgb(117, 214, 255)'

    def test_no_colour_is_written_outside_the_tokens(self, page):
        """A hex typed into a rule instead of taken from :root will
        drift the day somebody changes the theme."""
        styles = page.evaluate(
            "[...document.styleSheets[0].cssRules].map(r => r.cssText)"
            ".join('')")
        body = styles.split(':root')[-1].split('}', 1)[-1]

        assert '#' not in body


class TestTheLayout:
    def test_the_rail_holds_five_items(self, page):
        assert page.locator('.rail .rail-item').count() == 5

    def test_the_rail_is_fifty_six_wide(self, page):
        assert page.locator('.rail').bounding_box()['width'] == 56

    def test_the_top_bar_is_sixty_four_tall(self, page):
        assert page.locator('.topbar').bounding_box()['height'] == 64

    def test_the_ask_button_sits_in_the_top_bar(self, page):
        """Not below the cards, where it is today."""
        bar = page.locator('.topbar').bounding_box()
        button = page.locator('.ask').bounding_box()

        assert bar['y'] <= button['y']
        assert button['y'] + button['height'] <= bar['y'] + bar['height']

    def test_the_filters_sit_in_the_top_bar(self, page):
        bar = page.locator('.topbar').bounding_box()
        first = page.locator('.topbar select').first.bounding_box()

        assert bar['y'] <= first['y']

    def test_the_chat_is_a_column_on_the_right(self, page):
        """In the reference it runs floor to ceiling down the right.
        Today it is a box at the bottom."""
        chat = page.locator('.chat').bounding_box()
        width = page.evaluate('window.innerWidth')
        height = page.evaluate('window.innerHeight')

        assert chat['width'] == 380
        assert round(chat['x'] + chat['width']) == width
        assert chat['height'] >= height - 1


class TestNothingOverflows:
    def test_no_card_spills_past_its_own_edge(self, page):
        """`Owed by order` runs off the bottom of the page today."""
        spilling = page.evaluate("""
            [...document.querySelectorAll('.card')]
              .filter(c => c.scrollHeight > c.clientHeight + 1)
              .map(c => c.querySelector('h3')?.textContent)
        """)

        assert spilling == []

    def test_the_page_does_not_scroll_sideways(self, page):
        assert page.evaluate(
            'document.documentElement.scrollWidth'
        ) <= page.evaluate('window.innerWidth')


class TestTheCharts:
    def test_the_chart_panels_draw_charts(self, page):
        """ECharts renders into a canvas. A text table does not."""
        assert page.locator('.card canvas').count() >= 4

    def test_the_month_panel_is_a_chart(self, page):
        assert page.locator('[data-panel="by_month"] canvas').count() == 1

    def test_the_supplier_panel_is_a_chart(self, page):
        assert page.locator('[data-panel="by_supplier"] canvas').count() == 1

    def test_the_order_panel_stays_a_table(self, page):
        """Thirty rows of order numbers is a list, not a picture."""
        assert page.locator('[data-panel="by_order"] table').count() == 1


class TestTheNumbers:
    def test_every_money_figure_is_formatted(self, page):
        loose = page.evaluate("""
            [...document.querySelectorAll('.money')]
              .map(e => e.textContent.trim())
        """)

        assert loose
        for figure in loose:
            assert MONEY.match(figure) or SHORT.match(figure), figure

    def test_no_figure_runs_past_two_decimals(self, page):
        """12420.2175555555555555556 reached the page once."""
        text = page.evaluate('document.body.innerText')

        assert not re.search(r'\d\.\d{3,}', text)

    def test_a_share_carries_its_sign(self, page):
        shares = page.evaluate("""
            [...document.querySelectorAll('.share')]
              .map(e => e.textContent.trim())
        """)

        assert shares
        for share in shares:
            assert share.endswith('%')


class TestTheOverlay:
    def test_clicking_a_chip_opens_the_overlay(self, page):
        page.locator('.chip').first.click()
        page.wait_for_selector('.overlay')

        assert page.locator('.overlay').is_visible()

    def test_the_backdrop_is_see_through(self, page):
        """A solid backdrop hides the dashboard instead of dimming it."""
        colour = page.evaluate(
            "getComputedStyle(document.querySelector('.overlay'))"
            ".backgroundColor")

        assert colour.startswith('rgba')

    def test_the_backdrop_blurs_what_is_under_it(self, page):
        assert 'blur' in page.evaluate(
            "getComputedStyle(document.querySelector('.overlay'))"
            ".backdropFilter")

    def test_the_panels_are_blue_glass_not_white(self, page):
        colour = page.evaluate(
            "getComputedStyle(document.querySelector('.glass'))"
            ".backgroundColor")

        assert colour == 'rgba(0, 60, 91, 0.55)'

    def test_a_line_is_drawn_to_every_panel(self, page):
        panels = page.locator('.overlay .glass').count()
        lines = page.locator('.overlay svg path').count()

        assert panels >= 1
        assert lines == panels

    def test_the_lines_do_not_swallow_clicks(self, page):
        assert page.evaluate(
            "getComputedStyle(document.querySelector('.overlay svg'))"
            ".pointerEvents") == 'none'

    def test_the_panels_do_not_sit_on_top_of_each_other(self, page):
        boxes = page.evaluate("""
            [...document.querySelectorAll('.overlay .glass')]
              .map(e => e.getBoundingClientRect())
              .map(b => [b.left, b.top, b.right, b.bottom])
        """)

        for first in range(len(boxes)):
            for second in range(first + 1, len(boxes)):
                a, b = boxes[first], boxes[second]
                apart = a[2] <= b[0] or b[2] <= a[0] or \
                    a[3] <= b[1] or b[3] <= a[1]

                assert apart, f'panels {first} and {second} overlap'

    def test_the_close_button_closes_it(self, page):
        page.locator('.close-panels').click()

        assert page.locator('.overlay').count() == 0
```

Add playwright to the dev requirements:

```
playwright
```

and once:

```bash
python -m playwright install chromium
```

---

## Part 7. The order

Same as always. One red at a time, whole suite between each.

```
[ ] 1  the two Python number bugs, red first
[ ] 2  tests/test_look.py written, every test failing
[ ] 3  the tokens on :root, the page turns dark
[ ] 4  the rail, the top bar, the filters moved into it
[ ] 5  the chat becomes a 380px column on the right
[ ] 6  the grid, and nothing spilling out of a card
[ ] 7  ECharts, one panel at a time
[ ] 8  the overlay: backdrop, blue glass, fan, close button
[ ] 9  the lines, one per panel, 600ms
[ ] 10 the whole suite green, then the screenshots again
```

When it is green, save the three screenshots over the old ones in
`reference/screenshots/` and say so in `log_deepseek.md`. Rafael compares
them against `reference/frames/` with his own eyes. That comparison is the
only judge of this file that matters, and it is his, not yours.

---

## What not to do

- Do not change a value in this file because a test is hard to pass.
  The values came off the frames.
- Do not add a chart library other than ECharts.
- Do not draw a button that offers to load a local model. This version
  calls an API; the reference's green `Ativar IA local` button has no
  meaning here.
- Do not touch anything in `tests/` other than the files named above.
