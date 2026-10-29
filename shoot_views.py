"""Photograph each view of the running dashboard, into docs/.

The pictures in docs/ and in the Upwork post have to be the page as it
is, not as it was. Rebuild them whenever the page changes:

    python -m uvicorn web:app --app-dir src --port 8000
    python shoot_views.py

It takes nothing on trust: it waits for the cards of each view to be
drawn before it presses the shutter.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE = 'http://localhost:8000'
HERE = Path(__file__).parent
SHOTS = HERE / 'docs'

#: Each view: the rail button, the grid that proves it is drawn, and the
#: file it is saved as.
VIEWS = [
    ('go-cost', '#grid canvas', 'view-invoices.png'),
    ('go-anomalies', '#agrid canvas', 'view-anomalies.png'),
    ('go-reports', '#rgrid canvas', 'view-finance.png'),
    ('go-about', '.about', 'view-about.png'),
]


def shoot(page, button, ready, name):
    page.locator(f'#{button}').click()
    page.wait_for_selector(ready, state='attached')
    page.wait_for_timeout(1500)
    target = SHOTS / name
    page.screenshot(path=str(target))
    return target


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={'width': 1600, 'height': 900},
                                device_scale_factor=2)
        page.goto(PAGE)
        page.wait_for_selector('.card')
        for button, ready, name in VIEWS:
            print(shoot(page, button, ready, name))
        browser.close()


if __name__ == '__main__':
    main()
