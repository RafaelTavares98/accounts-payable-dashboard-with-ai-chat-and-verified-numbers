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
    def test_the_rail_holds_nothing_yet(self, page):
        """Five buttons that went nowhere said less than none. The
        strip stays, so the layout does not move when it earns its
        contents."""
        assert page.locator('.rail .rail-item').count() == 0

    def test_the_rail_is_fifty_six_wide(self, page):
        assert page.locator('.rail').bounding_box()['width'] == 56

    def test_the_top_bar_is_seventy_six_tall(self, page):
        assert page.locator('.topbar').bounding_box()['height'] == 76

    def test_the_two_headings_sit_on_one_line(self, page):
        """The dashboard title and the chat title are the same rank, so
        one floating above the other reads as a seam down the page."""
        left = page.locator('.topbar').bounding_box()
        right = page.locator('.chat-head').bounding_box()

        assert left['y'] == right['y']
        assert left['height'] == right['height']

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

    def test_no_figure_is_cut_off(self, page):
        """195,468.00 reached the page as 195,46... A tile narrower than
        its own number is worse than no tile."""
        cut = page.evaluate("""
            [...document.querySelectorAll('.tile .value')]
              .filter(e => e.scrollWidth > e.clientWidth + 1)
              .map(e => e.textContent)
        """)

        assert cut == []

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
