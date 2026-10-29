"""The surface the page talks to, on the cost view.

The dashboard is one page. Everything it shows arrives over these few
endpoints, as data. No HTML is built on the server beyond the page
itself, because a chart drawn in Python and a chart drawn in the browser
cannot both be the chart.

The model is replaced here the same way it is everywhere else.
"""

import json

import pytest

import web


@pytest.fixture(autouse=True)
def fixture_data(monkeypatch, fixtures):
    """The web tests use the hand-written files and a frozen date. The
    defaults are the real data and today, and a test that moves when the
    data moves is not a test."""
    monkeypatch.setenv('PAYABLES_DATA', str(fixtures))
    monkeypatch.setenv('PAYABLES_TODAY', '2026-06-01')
    yield
    web.app.state.model = None


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(web.app)


def plan(*names):
    return json.dumps({'panels': list(names), 'reason': 'because'})


class TestThePage:
    def test_the_root_serves_the_dashboard(self, client):
        got = client.get('/')

        assert got.status_code == 200
        assert 'text/html' in got.headers['content-type']

    def test_the_page_needs_no_key_to_open(self, client, monkeypatch):
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)

        assert client.get('/').status_code == 200

    def test_the_payables_endpoints_are_gone(self, client):
        """The department does not pay invoices. Nothing on the surface
        still serves what is overdue."""
        assert client.get('/api/overview').status_code == 404
        assert client.get('/api/documents').status_code == 404


class TestTheCostView:
    def test_it_hands_over_the_opening_numbers(self, client):
        got = client.get('/api/cost/overview').json()

        assert got['landed_total'] == '24,659.00'
        assert got['final_total'] == '23,559.00'
        assert got['provisional_total'] == '1,100.00'
        assert got['provisional_share'] == '4.5%'
        assert got['credits_total'] == '3,147.50'
        assert got['shipments'] == 3

    def test_the_groupings_carry_money_as_text(self, client):
        got = client.get('/api/cost/overview').json()

        assert got['by_carrier'][0] == ['Marsk Line Agencies B.V.',
                                        '16,484.50']
        assert got['by_component'][0] == ['Goods', '12,600.00']
        assert got['by_month'][1] == ['2026-05', '7,074.50', '1,100.00']

    def test_the_unit_cost_keeps_four_places(self, client):
        got = client.get('/api/cost/overview').json()

        assert ['Screw cap, 24 mm', '0.4577'] in got['unit_cost']

    def test_it_carries_the_desk_s_targets(self, client):
        targets = client.get('/api/cost/overview').json()['targets']

        assert targets == {'analysed_same_day': '96.0%',
                           'our_error_rate': '2.5%',
                           'close_month': '2026-05',
                           'known_before_close': '100.0%',
                           'for_a_person': 1}

    def test_the_filters_reach_the_numbers(self, client):
        got = client.get('/api/cost/overview', params={'mode': 'air'})

        assert got.json()['landed_total'] == '7,074.50'

    def test_an_unknown_filter_is_a_bad_request(self, client):
        got = client.get('/api/cost/overview',
                         params={'cost_centre': 'Logistica'})

        assert got.status_code == 400

    def test_it_says_what_can_be_filtered_on(self, client):
        got = client.get('/api/cost/filters').json()

        assert 'Marsk Line Agencies B.V.' in got['carriers']
        assert got['statuses'] == ['final', 'provisional']


class TestTheShipments:
    def test_the_shipments_themselves_can_be_read(self, client):
        got = client.get('/api/cost/shipments').json()['shipments']

        assert len(got) == 3
        assert got[0] == {'shipment': 'B/L MRK7000001',
                          'carrier': 'Marsk Line Agencies B.V.',
                          'mode': 'ocean', 'month': '2026-04',
                          'status': 'final', 'landed': '16,484.50'}

    def test_they_obey_the_filters(self, client):
        got = client.get('/api/cost/shipments',
                         params={'status': 'provisional'})

        assert len(got.json()['shipments']) == 1


class TestTheChips:
    def test_they_are_served_to_the_page(self, client):
        """Four ready questions, one per topic the desk reads every
        morning: the week, the target, the issuers, the errors."""
        got = client.get('/api/cost/suggestions').json()

        assert len(got['chips']) == 4

    def test_a_chip_needs_no_model(self, client):
        """The demo has to run with no key and no network. A chip
        already knows its topic, so code writes the whole answer."""
        web.app.state.model = None

        got = client.post('/api/cost/chip', json={'chip': 0})

        assert got.status_code == 200
        assert got.json()['sentence']
        assert not got.json()['refusal']

    def test_every_chip_answers(self, client):
        for index in range(4):
            got = client.post('/api/cost/chip', json={'chip': index}).json()

            assert got['sentence'], index
            assert not got['refusal'], index

    def test_a_chip_carries_a_figure_from_the_data(self, client):
        """The chip about the week says how many came in. A sentence
        with no figure in it is a sentence nobody needed."""
        got = client.post('/api/cost/chip', json={'chip': 0}).json()

        assert any(ch.isdigit() for ch in got['sentence'])

    def test_an_unknown_chip_is_a_bad_request(self, client):
        assert client.post('/api/cost/chip',
                           json={'chip': 99}).status_code == 400


class TestAsking:
    """A typed question on the invoice view. The model does one thing:
    it names the topic. Code writes every word of the answer, so no
    figure can be invented, and a model that answers nonsense costs
    nothing."""

    def test_the_model_names_a_topic_and_code_answers(self, client,
                                                      fake_model):
        web.app.state.model = fake_model('intake')

        got = client.post('/api/cost/ask',
                          json={'question': 'how many came in?'}).json()

        assert 'invoices came in during' in got['sentence']

    def test_the_answer_opens_the_panels_of_that_topic(self, client,
                                                       fake_model):
        web.app.state.model = fake_model('issuer')

        got = client.post('/api/cost/ask',
                          json={'question': 'who sent the most?'}).json()

        assert got['panels']
        for panel in got['panels']:
            assert panel['kind'] in ('bar', 'column', 'pie', 'tiles')

    def test_a_panel_arrives_as_data_not_as_a_picture(self, client,
                                                      fake_model):
        web.app.state.model = fake_model('issuer')

        got = client.post('/api/cost/ask',
                          json={'question': 'who?'}).json()
        rows = got['panels'][0]['rows']

        assert rows
        assert all(len(row) == 2 for row in rows)

    def test_an_invoice_number_needs_no_model_at_all(self, client):
        """A number is looked up directly. Asking a model to find a row
        by its key is paying for a dictionary lookup."""
        web.app.state.model = None

        got = client.post('/api/cost/ask',
                          json={'question': 'NCL-2026-3001'}).json()

        assert got['rows_used'] == 1
        assert got['sentence']

    def test_an_empty_question_is_a_bad_request(self, client):
        assert client.post('/api/cost/ask',
                           json={'question': '   '}).status_code == 400

    def test_a_topic_nobody_wrote_down_gets_the_help_line(self, client,
                                                          fake_model):
        """The model is told to answer 'none' when nothing fits. Anything
        else it says that is not a topic is treated the same way."""
        web.app.state.model = fake_model('weather')

        got = client.post('/api/cost/ask',
                          json={'question': 'will it rain?'}).json()

        assert got['sentence'] == web.OPS_HELP
        assert got['panels'] == []

    def test_a_model_that_cannot_be_reached_says_so(self, client,
                                                    fake_model):
        """Not the help line. A question nobody understood and a model
        that is down are different problems, and the reader has to be
        able to tell which one happened."""
        class Dead:
            def __call__(self, prompt):
                raise RuntimeError('the model answered with status 402')

        web.app.state.model = Dead()

        got = client.post('/api/cost/ask', json={'question': 'what?'})

        assert got.status_code == 200
        assert 'could not be reached' in got.json()['refusal']


class TestTheKeyIsNeverExposed:
    def test_it_is_not_in_any_response(self, client, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-do-not-leak-this')

        for path in ('/', '/api/cost/overview', '/api/cost/filters',
                     '/api/cost/suggestions', '/api/anomalies/overview'):
            assert 'sk-do-not-leak-this' not in client.get(path).text

    def test_it_is_not_in_an_error(self, client, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-do-not-leak-this')

        got = client.post('/api/cost/ask', json={'question': '   '})

        assert 'sk-do-not-leak-this' not in got.text


class TestTheDate:
    def test_the_answer_says_which_day_it_was_given(self, client):
        got = client.post('/api/cost/chip', json={'chip': 0}).json()

        assert got['as_of'] == '2026-06-01'

    def test_without_the_variable_it_uses_today(self, monkeypatch):
        from datetime import date
        monkeypatch.delenv('PAYABLES_TODAY', raising=False)

        assert web.as_of() == date.today()


class TestTheModelIsConnected:
    def test_a_key_in_the_environment_connects_the_model(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-test')

        assert web.model_for_this_request() is not None

    def test_no_key_gives_a_sentence_not_a_500(self, client, monkeypatch):
        """Both doors have to be shut: the environment and the keyring."""
        import model
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring', lambda: None)
        web.app.state.model = None

        got = client.post('/api/cost/ask', json={'question': 'what?'})

        assert got.status_code == 200
        assert 'key' in got.json()['refusal'].lower()


class TestWhereTheDataComesFrom:
    def test_the_default_folder_is_the_real_run(self, monkeypatch):
        """A dashboard that ships pointing at its own test fixtures
        shows four hand-written rows to a real reader. The default is
        the whole run of project 01, filed by the reader; the 93-invoice
        sample stays in data/, for the tests."""
        monkeypatch.delenv('PAYABLES_DATA', raising=False)

        assert web._data_folder().name == 'data-live'

    def test_the_cost_report_sits_in_its_own_folder(self, monkeypatch):
        monkeypatch.delenv('PAYABLES_DATA', raising=False)

        assert web._cost_folder().parts[-2:] == ('data-live', 'cost')
