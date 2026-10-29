"""The five tiles the anomaly view puts above its charts."""

import pytest
from fastapi.testclient import TestClient

import web


@pytest.fixture
def tiles():
    return TestClient(web.app).get('/api/anomalies/overview').json()['desk']


class TestTheRow:

    def test_there_are_five_of_them(self, tiles):
        assert len(tiles) == 5

    def test_they_are_named_as_the_desk_reads_them(self, tiles):
        assert [t['name'] for t in tiles] == [
            'Scored', 'Flagged', 'Money flagged', 'Confirmed', 'Waiting']

    def test_every_tile_carries_the_same_five_keys(self, tiles):
        for tile in tiles:
            assert set(tile) == {'name', 'value', 'target', 'icon',
                                 'change', 'month'}


class TestWhatEachOneSays:

    def test_the_value_is_never_empty(self, tiles):
        assert all(t['value'] for t in tiles)

    def test_the_target_is_never_empty(self, tiles):
        assert all(t['target'] for t in tiles)

    def test_the_icon_is_a_file_the_page_can_fetch(self, tiles):
        page = TestClient(web.app)
        for tile in tiles:
            assert page.get(tile['icon']).status_code == 200

    def test_the_money_tile_is_not_a_bare_number(self, tiles):
        money = next(t for t in tiles if t['name'] == 'Money flagged')
        assert ',' in money['value'] or '.' in money['value']

    def test_a_money_change_is_short_enough_for_one_line(self, tiles):
        """292,402 does not fit beside the value; 292k does."""
        money = next(t for t in tiles if t['name'] == 'Money flagged')
        for text in (money['change'], money['month']):
            figure = text.split(' ')[1]
            assert len(figure) <= 5, text


class TestTheChanges:

    def test_each_change_names_the_period_it_compares_with(self, tiles):
        for tile in tiles:
            assert 'last week' in tile['change']
            assert 'last month' in tile['month']

    def test_a_change_is_an_arrow_or_the_word_no(self, tiles):
        for tile in tiles:
            assert tile['change'][0] in '▲▼=n'
