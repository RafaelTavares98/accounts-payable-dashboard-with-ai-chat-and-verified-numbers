"""What the finance view asks the server for."""

import pytest
from fastapi.testclient import TestClient

import web


@pytest.fixture
def finance():
    return TestClient(web.app).get('/api/cost/finance').json()


class TestTheRow:

    def test_there_are_five_tiles(self, finance):
        assert len(finance['desk']) == 5

    def test_they_are_named_as_the_desk_reads_them(self, finance):
        assert [t['name'] for t in finance['desk']] == [
            'Landed cost', 'Final', 'Provisional', 'Provisional share',
            'Recoverable taxes']

    def test_every_tile_carries_the_same_keys(self, finance):
        for tile in finance['desk']:
            assert set(tile) == {'name', 'value', 'target', 'icon',
                                 'change', 'month'}

    def test_the_icon_is_a_file_the_page_can_fetch(self, finance):
        page = TestClient(web.app)
        for tile in finance['desk']:
            assert page.get(tile['icon']).status_code == 200


class TestWhatTheTilesSay:

    def test_the_month_is_named(self, finance):
        assert finance['month'].count('-') == 1

    def test_a_money_value_is_grouped(self, finance):
        landed = finance['desk'][0]
        assert ',' in landed['value']

    def test_the_share_is_a_percentage(self, finance):
        share = next(t for t in finance['desk']
                     if t['name'] == 'Provisional share')
        assert share['value'].endswith('%')

    def test_each_change_names_what_it_compares_with(self, finance):
        for tile in finance['desk']:
            assert 'last month' in tile['change']
            assert 'last quarter' in tile['month']

    def test_a_money_change_stays_short(self, finance):
        for tile in finance['desk'][:3]:
            figure = tile['change'].split(' ')[1]
            assert len(figure) <= 5, tile['change']


class TestTheMonthlySeries:

    def test_every_month_carries_four_figures(self, finance):
        for row in finance['months']:
            assert len(row) == 4

    def test_the_months_run_oldest_first(self, finance):
        names = [row[0] for row in finance['months']]
        assert names == sorted(names)

    def test_the_latest_month_is_the_one_the_tiles_show(self, finance):
        assert finance['months'][-1][0] == finance['month']


class TestTheRankedParts:

    def test_each_part_carries_three_months(self, finance):
        for row in finance['parts']:
            assert len(row) == 4

    def test_the_dearest_part_comes_first(self, finance):
        costs = [float(row[1].replace(',', '')) for row in finance['parts']]
        assert costs == sorted(costs, reverse=True)

    def test_a_part_absent_from_a_month_reads_as_nothing(self, finance):
        """Never missing: a part nobody bought last month cost zero, and
        the bar beside it has to be able to say so."""
        for row in finance['parts']:
            assert row[2] is not None and row[3] is not None


class TestItFollowsTheFilters:

    def test_a_carrier_filter_narrows_it(self):
        page = TestClient(web.app)
        whole = page.get('/api/cost/finance').json()
        one = page.get('/api/cost/finance',
                       params={'carrier': 'COSMO Shipping Lines Co., Ltd.'}
                       ).json()
        assert one['desk'][0]['value'] != whole['desk'][0]['value']

    def test_an_unknown_filter_is_refused(self):
        page = TestClient(web.app)
        assert page.get('/api/cost/finance',
                        params={'nonsense': 'x'}).status_code == 400
