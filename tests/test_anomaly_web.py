"""The anomaly view's endpoints. Same rules as the cost ones: data out,
the page draws it, the model replaced by a fake."""

import json

import pytest

import web


@pytest.fixture(autouse=True)
def fixture_data(monkeypatch, fixtures):
    monkeypatch.setenv('PAYABLES_DATA', str(fixtures))
    monkeypatch.setenv('PAYABLES_TODAY', '2026-06-01')


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(web.app)


class TestOverview:
    def test_the_headline(self, client):
        got = client.get('/api/anomalies/overview').json()

        assert got['reviewed'] == 8
        assert got['flagged_count'] == 4
        assert got['flagged_total'] == '8,200.00'
        assert got['flag_rate'] == '50.0%'

    def test_the_groupings_carry_money_as_text(self, client):
        got = client.get('/api/anomalies/overview').json()

        assert got['by_stage'][0] == ['freight billing', 2, '4,000.00']
        assert got['by_week'][0] == ['2026-04-06', 2, 4, '3,300.00']

    def test_whose_error_it_is(self, client):
        """Ours from the cost report's exceptions, the client's from the
        analyst's decisions on the flags."""
        got = client.get('/api/anomalies/overview').json()

        assert got['our_errors'] == 1
        assert got['client_errors'] == 2
        assert got['by_origin'][0] == ['Our errors, read by a person', 1]
        assert got['by_decision'][0] == ['confirmed', 2, '3,300.00']

    def test_a_flag_in_the_list_carries_the_decision(self, client):
        got = client.get('/api/anomalies/list').json()['invoices']

        assert got[0]['decision'] == 'pending'

    def test_a_filter_narrows_it(self, client):
        got = client.get('/api/anomalies/overview',
                         params={'stage': 'billing'}).json()

        assert got['reviewed'] == 1

    def test_an_unknown_filter_is_a_400(self, client):
        assert client.get('/api/anomalies/overview',
                          params={'colour': 'red'}).status_code == 400


class TestTheList:
    def test_flagged_first_highest_score_first(self, client):
        got = client.get('/api/anomalies/list').json()['invoices']

        assert got[0]['number'] == 'HCV-2026-3005'
        assert got[0]['flagged'] is True
        assert got[-1]['flagged'] is False
        assert len(got) == 8


class TestFiltersAndChips:
    def test_the_choices(self, client):
        got = client.get('/api/anomalies/filters').json()

        assert 'Marsk Line' in got['suppliers']
        assert 'billing' in got['stages']

    def test_a_chip_needs_no_model(self, client):
        got = client.post('/api/anomalies/chip', json={'chip': 0}).json()

        assert got['sentence'].startswith('4 of 8 invoices')
        # "How many were flagged?" is answered by the sentence alone.
        assert got['panels'] == []

    def test_an_unknown_chip_is_a_400(self, client):
        assert client.post('/api/anomalies/chip',
                           json={'chip': 99}).status_code == 400

    def test_the_chips_are_listed(self, client):
        got = client.get('/api/anomalies/suggestions').json()

        assert len(got['chips']) == len(__import__('anomaly_answering').CHIPS)


class TestAsking:
    def test_a_question_goes_through_the_anomaly_menu(self, client, fake_model):
        web.app.state.model = fake_model(
            json.dumps({'panels': ['by_stage']}), 'Freight billing leads.')
        try:
            got = client.post('/api/anomalies/ask',
                              json={'question': 'where?'}).json()
        finally:
            web.app.state.model = None

        assert got['panels'][0]['name'] == 'by_stage'
        assert got['sentence'] == 'Freight billing leads.'

    def test_an_empty_question_is_a_400(self, client):
        assert client.post('/api/anomalies/ask',
                           json={'question': ' '}).status_code == 400
