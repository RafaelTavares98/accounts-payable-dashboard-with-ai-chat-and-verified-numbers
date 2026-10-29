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
SHORT = re.compile(r'^-?\d+(\.\d+)?[ ]?[MKk]$')
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')

#: The six places every view lays its cards in, in reading order.
REGIONS = ['targets', 'region-time', 'region-left', 'region-center',
           'region-right-top', 'region-right-bottom']

#: The rail, in the order the buttons sit in it.
VIEWS = {'go-cost': '#grid', 'go-anomalies': '#agrid',
         'go-reports': '#rgrid'}


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


def _open(page, button):
    """Click a rail button and wait for its cards to be drawn."""
    page.locator(f'#{button}').click()
    page.wait_for_timeout(1200)


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
        drift the day somebody changes the theme. An id selector carries
        a hash too, so the hash alone is not the thing to look for."""
        rules = page.evaluate(
            "[...document.styleSheets[0].cssRules].map(r => r.cssText)")
        body = [text for text in rules if not text.startswith(':root')]

        assert [text for text in body if HEX.search(text)] == []


class TestTheLayout:
    def test_the_rail_holds_its_four_views(self, page):
        """Invoices, Anomalies, Finance and About. The strip was empty
        while none of them existed; each button arrived with its view."""
        assert page.locator('.rail .rail-item').count() == 4

    def test_the_rail_is_fifty_five_wide(self, page):
        assert page.locator('.rail').bounding_box()['width'] == 55

    def test_the_top_bar_is_fifty_five_tall(self, page):
        """One line: the view's name on the left, the period on the
        right. The second line went when the filters moved behind a
        button."""
        assert page.locator('.topbar').bounding_box()['height'] == 55

    def test_the_top_bar_starts_where_the_rail_ends(self, page):
        rail = page.locator('.rail').bounding_box()
        bar = page.locator('.topbar').bounding_box()

        assert bar['x'] == rail['x'] + rail['width']

    def test_the_filter_button_sits_in_the_top_bar(self, page):
        """The four filters live behind it. On screen at all times is
        the period they are set to."""
        bar = page.locator('.topbar').bounding_box()
        button = page.locator('.filter-button').bounding_box()

        assert bar['y'] <= button['y']
        assert button['y'] + button['height'] <= bar['y'] + bar['height']

    def test_the_filter_panel_holds_every_filter(self, page):
        assert page.locator('.filter-panel select').count() >= 2

    def test_the_chat_is_a_column_on_the_right(self, page):
        """It runs from under the top bar to the floor, down the right."""
        chat = page.locator('.chat').bounding_box()
        bar = page.locator('.topbar').bounding_box()
        width = page.evaluate('window.innerWidth')
        height = page.evaluate('window.innerHeight')

        assert chat['x'] > width / 2
        assert chat['y'] >= bar['height']
        assert chat['x'] + chat['width'] >= width - 16
        assert chat['y'] + chat['height'] >= height - 16

    def test_the_cards_fill_what_is_left(self, page):
        """The grid starts under the top bar and beside the rail, and
        reaches the floor. A gap under the cards is wasted screen."""
        grid = page.locator('#grid').bounding_box()
        bar = page.locator('.topbar').bounding_box()
        height = page.evaluate('window.innerHeight')

        assert grid['y'] == bar['height']
        assert round(grid['y'] + grid['height']) == height


class TestEveryViewIsLaidOutTheSame:
    """One layout, three views. The Anomalies and Finance views were
    built by copying the Invoices one, so a card that moves in one and
    not the others is a mistake, not a choice."""

    @pytest.mark.parametrize('button,grid', list(VIEWS.items()))
    def test_the_view_fills_its_six_regions(self, page, button, grid):
        _open(page, button)
        found = page.evaluate(
            f"[...document.querySelectorAll('{grid} [data-panel]')]"
            ".map(e => e.dataset.panel)")

        assert found == REGIONS

    @pytest.mark.parametrize('button,grid', list(VIEWS.items()))
    def test_the_view_draws_three_charts(self, page, button, grid):
        """The week over time, and the two donuts down the right."""
        _open(page, button)
        drawn = page.evaluate(
            f"[...document.querySelectorAll('{grid} [data-panel]')]"
            ".map(e => [e.dataset.panel, e.querySelectorAll('canvas').length])"
            ".filter(p => p[1] > 0).map(p => p[0])")

        assert drawn == ['region-time', 'region-right-top',
                         'region-right-bottom']

    @pytest.mark.parametrize('button,grid', list(VIEWS.items()))
    def test_the_middle_card_is_a_table(self, page, button, grid):
        """Rows a person reads one by one: the invoices, the scored
        invoices, the shipments. A chart would hide the numbers."""
        _open(page, button)

        assert page.locator(f'{grid} [data-panel="region-center"] table'
                            ).count() == 1

    @pytest.mark.parametrize('button,grid', list(VIEWS.items()))
    def test_the_view_shows_five_tiles(self, page, button, grid):
        _open(page, button)

        assert page.locator(f'{grid} [data-panel="targets"] .tile'
                            ).count() == 5


class TestNothingOverflows:
    def test_no_card_spills_past_its_own_edge(self, page):
        """A long table once ran off the bottom of the page."""
        _open(page, 'go-cost')
        spilling = page.evaluate("""
            [...document.querySelectorAll('#grid .card')]
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
        _open(page, 'go-cost')

        assert page.locator('#grid .card canvas').count() == 3

    def test_no_payment_figure_is_on_the_page(self, page):
        """The department does not pay invoices."""
        text = page.evaluate('document.body.innerText').lower()

        for gone in ('overdue', 'days late', 'owed'):
            assert gone not in text


class TestTheNumbers:
    def test_every_tile_value_is_formatted(self, page):
        """A tile carries a count, a percentage or short money. A raw
        Decimal with twenty places reached one of them once."""
        _open(page, 'go-cost')
        values = page.evaluate(
            "[...document.querySelectorAll('#grid .tile .value')]"
            ".map(e => e.textContent.trim())")

        assert values
        for figure in values:
            assert (figure.isdigit() or MONEY.match(figure)
                    or SHORT.match(figure)
                    or re.match(r'^-?\d+(\.\d)?%$', figure)
                    or re.match(r'^\d{1,3}(,\d{3})*$', figure)), figure

    def test_no_figure_runs_past_two_decimals(self, page):
        """12420.2175555555555555556 reached the page once."""
        _open(page, 'go-cost')
        text = page.evaluate(
            "document.querySelector('#grid').innerText")

        assert not re.search(r'\d\.\d{3,}', text)

    def test_no_figure_is_cut_off(self, page):
        """195,468.00 reached the page as 195,46... A tile narrower than
        its own number is worse than no tile."""
        cut = page.evaluate("""
            [...document.querySelectorAll('.tile .value')]
              .filter(e => e.scrollWidth > e.clientWidth + 1)
              .map(e => e.textContent)
        """)

        assert cut == []

    @pytest.mark.parametrize('button,grid', list(VIEWS.items()))
    def test_no_figure_in_a_table_is_cut_off(self, page, button, grid):
        """1,142,660.34 reached the shipment table as 1,142,66... The
        money column had the width of a score. Only the name columns are
        allowed an ellipsis; they carry the whole name in a tooltip."""
        _open(page, button)
        cut = page.evaluate(f"""
            [...document.querySelectorAll('{grid} table td')]
              .filter(e => e.scrollWidth > e.clientWidth + 1)
              .filter(e => /^[\\d.,%-]+$/.test(e.textContent.trim()))
              .map(e => e.textContent.trim())
        """)

        assert cut == []

    def test_a_change_line_carries_its_sign(self, page):
        """Every tile says what it was last week. Without the arrow the
        reader cannot tell a rise from a fall."""
        _open(page, 'go-cost')
        changes = page.evaluate(
            "[...document.querySelectorAll('#grid .tile .kpi-change')]"
            ".map(e => e.textContent.trim())")

        assert changes
        for change in changes:
            assert change[0] in '▲▼=', change


class TestTheOverlay:
    """A ready question on the Invoices view opens its panels over the
    dashboard, each joined to the answer by a line, as in the video. The
    table cells carry the class `chip` too, so the ready questions have
    to be reached through the assistant column."""

    @classmethod
    @pytest.fixture(scope='class')
    def opened(cls, page):
        _open(page, 'go-cost')
        page.locator('.chat .chip').first.click()
        page.wait_for_selector('.overlay')
        return page

    def test_clicking_a_ready_question_opens_the_overlay(self, opened):
        assert opened.locator('.overlay').is_visible()

    def test_the_backdrop_is_see_through(self, opened):
        """A solid backdrop hides the dashboard instead of dimming it."""
        colour = opened.evaluate(
            "getComputedStyle(document.querySelector('.overlay'))"
            ".backgroundColor")

        assert colour.startswith('rgba')

    def test_the_backdrop_blurs_what_is_under_it(self, opened):
        assert 'blur' in opened.evaluate(
            "getComputedStyle(document.querySelector('.overlay'))"
            ".backdropFilter")

    def test_the_panels_are_blue_glass_not_white(self, opened):
        colour = opened.evaluate(
            "getComputedStyle(document.querySelector('.glass'))"
            ".backgroundColor")

        assert colour == 'rgba(14, 44, 61, 0.94)'

    def test_a_line_is_drawn_to_every_panel(self, opened):
        panels = opened.locator('.overlay .glass').count()
        lines = opened.locator('.overlay svg path').count()

        assert panels >= 1
        assert lines == panels

    def test_the_lines_do_not_swallow_clicks(self, opened):
        assert opened.evaluate(
            "getComputedStyle(document.querySelector('.overlay svg'))"
            ".pointerEvents") == 'none'

    def test_the_panels_do_not_sit_on_top_of_each_other(self, opened):
        boxes = opened.evaluate("""
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

    def test_the_close_button_closes_it(self, opened):
        opened.locator('.close-panels').click()
        opened.wait_for_timeout(600)

        assert opened.locator('.overlay').count() == 0


class TestTheDecisionChips:
    """What the analyst did with a flag, on the scored invoices table.
    The colour is the fastest way to read a column of them, so each
    decision keeps its own and no two share."""

    COLOURS = {
        'confirmed': 'rgb(255, 79, 123)',
        'pending': 'rgb(255, 197, 71)',
        'dismissed': 'rgb(91, 124, 147)',
        'not-flagged': 'rgb(159, 183, 201)',
    }

    @pytest.mark.parametrize('decision,colour', list(COLOURS.items()))
    def test_each_decision_keeps_its_own_colour(self, page, decision,
                                                colour):
        _open(page, 'go-anomalies')
        found = page.evaluate(f"""
            (() => {{
              const e = document.createElement('span');
              e.className = 'chip {decision}';
              document.body.appendChild(e);
              const c = getComputedStyle(e).color;
              e.remove();
              return c;
            }})()
        """)

        assert found == colour

    def test_no_two_decisions_look_alike(self, page):
        assert len(set(self.COLOURS.values())) == len(self.COLOURS)


class TestTheAboutView:
    def test_it_hides_the_assistant_and_the_filters(self, page):
        """About is a page to read. There is no figure on it to ask
        about and nothing to filter."""
        _open(page, 'go-about')
        hidden = page.evaluate("""
            ['.chat', '.filter-button'].map(s => {
              const e = document.querySelector(s);
              return !e || getComputedStyle(e).display === 'none';
            })
        """)

        assert hidden == [True, True]

    def test_it_fits_one_screen(self, page):
        _open(page, 'go-about')
        spills = page.evaluate(
            "document.documentElement.scrollHeight > window.innerHeight + 1")

        assert not spills

