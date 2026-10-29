"""The About view: who built this, the three projects, and where to find
them. Checked as text, because a portfolio page with a broken link is
worse than none."""

import pytest

import web

GITHUB = 'https://github.com/RafaelTavares98'
LINKEDIN = 'https://www.linkedin.com/in/rafaeltavares1998'


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(web.app)


@pytest.fixture
def page(client):
    return client.get('/').text


def test_the_rail_has_an_about_button(page):
    assert 'id="go-about"' in page


def test_the_profile_links_are_on_the_page(page):
    assert LINKEDIN in page
    assert GITHUB in page


def test_each_published_project_links_its_repository(page):
    assert f'{GITHUB}/invoice-pipeline' in page
    assert f'{GITHUB}/invoice-anomalies' in page
    assert f'{GITHUB}/accounts-payable-dashboard-with-ai-chat-and-verified-numbers' in page


def test_no_project_still_says_it_is_being_published(page):
    assert 'being published' not in page


def test_all_three_projects_are_named(page):
    for name in ('Invoice pipeline', 'Invoice anomalies',
                 'Landed cost dashboard'):
        assert name in page


def test_the_anomaly_figure_is_the_one_that_was_measured(page):
    """0.53 is the clerk's checks on the real hold-out. 0.89 and 0.90
    came from five years of invented invoices and are gone."""
    assert '<b>0.53</b>' in page
    assert '0.89' not in page
    assert '0.90' not in page


def test_the_anomaly_card_does_not_claim_the_model_won(page):
    """The clerk's checks led. Saying otherwise on a portfolio page is
    the one thing this project was rebuilt to stop."""
    assert 'LightGBM at 0.03' in page
    assert 'not proven' in page


def test_no_project_says_the_department_pays(page):
    """The department is Production and Logistics Cost Management. It
    costs what the invoices say; it does not pay them."""
    assert 'Accounts payable' not in page
    assert 'what it owes' not in page.lower()


def test_the_photo_is_served(client):
    got = client.get('/static/profile.jpg')

    assert got.status_code == 200
    assert got.headers['content-type'] == 'image/jpeg'


def test_no_project_is_described_as_fraud_work(page):
    assert 'fraud' not in page.lower()
