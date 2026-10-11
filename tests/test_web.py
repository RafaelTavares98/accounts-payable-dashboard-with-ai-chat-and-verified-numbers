"""The surface the page talks to.

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
    """The web tests use the twelve hand-written rows and the frozen
    demo date. The defaults are the real data and today, and a test
    that moves when the data moves is not a test."""
    monkeypatch.setenv('PAYABLES_DATA', str(fixtures))
    monkeypatch.setenv('PAYABLES_TODAY', '2026-06-01')


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
        """The base view is computed by code. It must open with no API
        key set at all."""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)

        assert client.get('/').status_code == 200


class TestTheBaseView:
    def test_it_hands_over_the_opening_numbers(self, client):
        got = client.get('/api/overview').json()

        assert got['total_owed'] == '67,450.00'
        assert got['documents'] == 10

    def test_money_is_formatted_for_a_person(self, client):
        got = client.get('/api/overview').json()

        assert got['total_owed'] == '67,450.00'

    def test_the_overview_carries_every_figure_by_name(self, client):
        """The page and the metrics drift apart when the page is a
        second, smaller list. Every figure must arrive by its own
        name."""
        import metrics

        got = client.get('/api/overview').json()

        for name in metrics.FIGURES:
            assert name in got

    def test_it_says_what_can_be_filtered_on(self, client):
        got = client.get('/api/filters').json()

        assert 'Marsk Line Agencies B.V.' in got['suppliers']
        assert got['states'] == ['open', 'overdue', 'credit']

    def test_it_does_not_offer_filters_this_data_lacks(self, client):
        got = client.get('/api/filters').json()

        assert 'cost_centres' not in got
        assert 'branches' not in got

    def test_the_filters_reach_the_numbers(self, client):
        got = client.get('/api/overview',
                         params={'supplier': 'Marsk Line Agencies B.V.'})

        assert got.json()['total_owed'] == '5,500.00'

    def test_an_unknown_filter_is_a_bad_request(self, client):
        got = client.get('/api/overview', params={'cost_centre': 'Logistica'})

        assert got.status_code == 400


class TestTheDocuments:
    def test_the_rows_themselves_can_be_read(self, client):
        """A payables panel without the payables on it is a panel about
        nothing. Every figure on the page is a roll-up of these."""
        got = client.get('/api/documents').json()

        assert len(got['documents']) == 10

    def test_a_row_carries_what_a_person_needs(self, client):
        row = client.get('/api/documents').json()['documents'][0]

        assert set(row) == {'number', 'supplier', 'issued', 'due',
                            'total', 'state', 'days', 'paper'}

    def test_a_row_points_at_its_own_paper(self, client):
        """A figure a reader cannot trace back to a page is a figure
        they have to take on faith."""
        row = client.get('/api/documents').json()['documents'][0]

        assert row['paper'].endswith('.pdf')

    def test_the_money_is_formatted(self, client):
        row = client.get('/api/documents').json()['documents'][0]

        assert row['total'].count('.') == 1
        assert row['total'].endswith('.00') or len(row['total']) > 4

    def test_the_latest_comes_first(self, client):
        """Nobody opens a payables list to read the oldest bill."""
        rows = client.get('/api/documents').json()['documents']
        dues = [row['due'] for row in rows if row['due']]

        assert dues == sorted(dues)

    def test_each_row_says_which_state_it_is_in(self, client):
        states = {row['state']
                  for row in client.get('/api/documents').json()['documents']}

        assert states <= {'open', 'overdue', 'credit'}

    def test_it_obeys_the_filters(self, client):
        got = client.get('/api/documents',
                         params={'supplier': 'Marsk Line Agencies B.V.'})

        assert len(got.json()['documents']) == 2

    def test_an_unknown_filter_is_a_bad_request(self, client):
        got = client.get('/api/documents', params={'branch': 'Matriz'})

        assert got.status_code == 400


class TestTheChips:
    def test_they_are_served_to_the_page(self, client):
        got = client.get('/api/suggestions').json()

        assert len(got['chips']) == 5
        assert got['chips'][0]['question'].endswith('?')

    def test_clicking_one_needs_no_model(self, client):
        got = client.post('/api/chip', json={'chip': 0})

        assert got.status_code == 200
        assert got.json()['panels']

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


class TestAsking:
    def test_a_typed_question_comes_back_with_panels(self, client,
                                                     fake_model):
        web.app.state.model = fake_model(plan('overdue'),
                                         '31,750.00 is overdue.')

        got = client.post('/api/ask', json={'question': 'how much is late?'})

        assert got.json()['panels'][0]['name'] == 'overdue'

    def test_the_sentence_comes_back_too(self, client, fake_model):
        web.app.state.model = fake_model(plan('overdue'),
                                         '31,750.00 is overdue.')

        got = client.post('/api/ask', json={'question': 'how much is late?'})

        assert got.json()['sentence'] == '31,750.00 is overdue.'

    def test_a_panel_arrives_as_data_not_as_a_picture(self, client,
                                                      fake_model):
        """The browser draws it. The server says what to draw."""
        web.app.state.model = fake_model(plan('by_supplier'), 'Some words.')

        panel = got_panel(client, 'who do we owe?')

        assert panel['kind'] == 'bar'
        assert panel['rows'][0] == ['Guangzhou Verrelia Glassworks Co., Ltd.',
                                    '25,500.00']

    def test_the_question_is_answered_over_the_filters_on_screen(
            self, client, fake_model):
        """The page sends its filter state with every question. Without
        it the answer would be about rows the reader cannot see."""
        web.app.state.model = fake_model(plan('balance'), '5,500.00 is owed.')

        got = client.post('/api/ask', json={
            'question': 'what do we owe?',
            'filters': {'supplier': 'Marsk Line Agencies B.V.'},
        })

        rows = dict(got.json()['panels'][0]['rows'])
        assert rows['Total owed'] == '5,500.00'

    def test_an_empty_question_is_a_bad_request(self, client):
        got = client.post('/api/ask', json={'question': '   '})

        assert got.status_code == 400

    def test_a_refusal_comes_back_as_a_normal_answer(self, client,
                                                     fake_model):
        """Not a 500. The chat has something to say, so the request
        worked."""
        web.app.state.model = fake_model('not json')

        got = client.post('/api/ask', json={'question': 'how much is late?'})

        assert got.status_code == 200
        assert got.json()['refusal']


class TestTheKeyIsNeverExposed:
    def test_it_is_not_in_any_response(self, client, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-do-not-leak-this')

        for path in ('/', '/api/overview', '/api/filters',
                     '/api/suggestions'):
            assert 'sk-do-not-leak-this' not in client.get(path).text

    def test_it_is_not_in_an_error(self, client, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-do-not-leak-this')

        got = client.post('/api/ask', json={'question': '   '})

        assert 'sk-do-not-leak-this' not in got.text


def got_panel(client, question):
    """The first panel of an answer, for tests that only care about one."""
    reply = client.post('/api/ask', json={'question': question})
    return reply.json()['panels'][0]


class TestTheDate:
    def test_the_date_can_be_set_from_outside(self, monkeypatch, client):
        """Overdue means nothing without a date. Freezing it in the
        source means the only way to change it is to edit and redeploy.

        Worked out from tests/fixtures/invoices.csv: the earliest due
        date is 2026-04-11, so on 2026-04-01 nothing is overdue and the
        count is zero. With the real today it would be eight."""
        monkeypatch.setenv('PAYABLES_TODAY', '2026-04-01')

        got = client.get('/api/overview', params={'state': 'overdue'})

        assert got.json()['documents'] == 0

    def test_without_the_variable_it_uses_today(self, monkeypatch):
        from datetime import date
        import web
        monkeypatch.delenv('PAYABLES_TODAY', raising=False)

        assert web.as_of() == date.today()


class TestTheModelIsConnected:
    def test_a_key_in_the_environment_connects_the_model(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'sk-test')
        import web

        assert web.model_for_this_request() is not None

    def test_no_key_gives_a_sentence_not_a_500(self, client, monkeypatch):
        """503 is a status code. A reader needs a sentence.

        Both doors have to be shut. Clearing the environment alone left
        the keyring open, and on a machine that really has a key stored
        this test passed or failed depending on whose machine it was.
        """
        import model
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(model, '_from_keyring', lambda: None)
        web.app.state.model = None

        got = client.post('/api/ask', json={'question': 'what do we owe?'})

        assert got.status_code == 200
        assert 'key' in got.json()['refusal'].lower()


class TestWhereTheDataComesFrom:
    def test_the_default_folder_is_not_the_fixtures(self, monkeypatch):
        """A dashboard that ships pointing at its own test data shows
        twelve invented invoices to a real reader."""
        monkeypatch.delenv('PAYABLES_DATA', raising=False)
        import web

        assert web._data_folder().name != 'fixtures'

    def test_the_default_folder_is_the_data_folder(self, monkeypatch):
        monkeypatch.delenv('PAYABLES_DATA', raising=False)
        import web

        assert web._data_folder().name == 'data'
