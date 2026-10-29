"""The cost report of project 01, read into lines and summed.

Every figure is checked against tests/fixtures/cost, worked out by hand:

    caps   on B/L MRK7000001, ocean, Marsk, April, final    5,307.50
    pumps  on B/L MRK7000001, ocean, Marsk, April, final   11,177.00
    bottles on AWB 138-1,     air,   DHI,   May,   final    7,074.50
    caps   on B/L CSM7000009, freight not billed, May,
                                             provisional    1,100.00
                                                           ---------
                                                           24,659.00
"""

import json
from decimal import Decimal

import pytest

import cost

D = Decimal


class TestLoading:
    def test_one_line_per_row_of_the_report(self, lines):
        assert len(lines) == 4

    def test_a_line_carries_its_shipment_s_operation(self, lines):
        """The report keeps the carrier on operations.csv; a line needs it
        to be summed by carrier."""
        bottles = [l for l in lines if l.code == 'GB-030A'][0]

        assert bottles.carrier == 'DHI Global Forwarding (HK) Ltd.'
        assert bottles.mode == 'air'
        assert bottles.month == '2026-05'

    def test_a_line_carries_the_name_of_its_part(self, lines):
        """CP-024F means nothing to a reader; a screw cap does."""
        assert lines[0].product == 'Screw cap, 24 mm'

    def test_freight_not_billed_yet_says_so(self, lines):
        """No freight invoice, no carrier. An empty bar label reads as a
        bug; this reads as what it is."""
        waiting = [l for l in lines if l.shipment == 'B/L CSM7000009'][0]

        assert waiting.carrier == cost.NOT_BILLED
        assert waiting.mode == cost.NOT_BILLED

    def test_money_is_decimal(self, lines):
        assert lines[0].landed == D('5307.50')
        assert isinstance(lines[0].parts['goods'], Decimal)

    def test_a_missing_report_is_no_lines(self, tmp_path):
        assert cost.load(tmp_path) == []


class TestTheTotals:
    def test_the_landed_cost(self, lines):
        assert cost.landed_total(lines) == D('24659.00')

    def test_final_and_provisional_apart(self, lines):
        assert cost.final_total(lines) == D('23559.00')
        assert cost.provisional_total(lines) == D('1100.00')

    def test_the_share_still_provisional(self, lines):
        """1,100.00 of 24,659.00 is 4.46%, shown to one place."""
        assert cost.provisional_share(lines) == D('4.5')

    def test_no_share_of_nothing(self):
        assert cost.provisional_share([]) is None

    def test_the_recoverable_taxes_stay_apart(self, lines):
        """IPI, PIS, COFINS and ICMS are credits, never inside the cost."""
        assert cost.credits_total(lines) == D('3147.50')
        assert cost.landed_total(lines) == D('24659.00')

    def test_counts(self, lines):
        assert cost.shipment_count(lines) == 3
        assert cost.line_count(lines) == 4


class TestWhatTheCostIsMadeOf:
    def test_the_seven_parts_add_up_to_the_landed_cost(self, lines):
        parts = cost.by_component(lines)

        assert sum(value for _, value in parts) == D('24659.00')

    def test_each_part_by_name(self, lines):
        parts = dict(cost.by_component(lines))

        assert parts['Goods'] == D('12600.00')
        assert parts['International freight'] == D('3500.00')
        assert parts['Truck to Moty plant'] == D('4300.00')
        assert parts['Customs broker'] == D('2200.00')
        assert parts['Import duty (II)'] == D('1510.00')
        assert parts['AFRMM'] == D('120.00')
        assert parts['Siscomex'] == D('429.00')

    def test_biggest_first(self, lines):
        assert cost.by_component(lines)[0][0] == 'Goods'


class TestByOperationOperatorAndProduct:
    def test_by_carrier(self, lines):
        assert cost.by_carrier(lines) == [
            ('Marsk Line Agencies B.V.', D('16484.50')),
            ('DHI Global Forwarding (HK) Ltd.', D('7074.50')),
            (cost.NOT_BILLED, D('1100.00')),
        ]

    def test_by_mode(self, lines):
        assert dict(cost.by_mode(lines)) == {
            'ocean': D('16484.50'), 'air': D('7074.50'),
            cost.NOT_BILLED: D('1100.00')}

    def test_by_product(self, lines):
        assert cost.by_product(lines) == [
            ('Lotion pump, 24 mm', D('11177.00')),
            ('Glass bottle, round, 30 ml, flint', D('7074.50')),
            ('Screw cap, 24 mm', D('6407.50')),
        ]

    def test_the_cost_per_unit_is_weighted_by_quantity(self, lines):
        """Caps on two shipments: 6,407.50 over 14,000 units, not the
        average of 0.5308 and 0.2750."""
        units = dict(cost.unit_cost(lines))

        assert units['Screw cap, 24 mm'] == D('0.4577')
        assert units['Lotion pump, 24 mm'] == D('11.1770')

    def test_by_month_final_and_provisional_apart(self, lines):
        assert cost.by_month(lines) == [
            ('2026-04', D('16484.50'), D('0.00')),
            ('2026-05', D('7074.50'), D('1100.00')),
        ]

    def test_by_shipment(self, lines):
        top = cost.by_shipment(lines)[0]

        assert top == ('B/L MRK7000001', 'Marsk Line Agencies B.V.', 'ocean',
                       '2026-04', 'final', D('16484.50'))


class TestTheFilters:
    def test_one_carrier(self, lines):
        kept = cost.only(lines, carrier='Marsk Line Agencies B.V.')

        assert cost.landed_total(kept) == D('16484.50')

    def test_one_status(self, lines):
        assert len(cost.only(lines, status='provisional')) == 1

    def test_two_at_once(self, lines):
        kept = cost.only(lines, month='2026-05', mode='air')

        assert cost.landed_total(kept) == D('7074.50')

    def test_an_empty_value_means_any(self, lines):
        assert len(cost.only(lines, carrier='')) == 4

    def test_an_unknown_filter_is_refused(self, lines):
        with pytest.raises(ValueError):
            cost.only(lines, cost_centre='Logistica')

    def test_the_choices_come_from_the_data(self, lines):
        assert cost.choices(lines)['status'] == ['final', 'provisional']
        assert cost.NOT_BILLED in cost.choices(lines)['carrier']


class TestTheDesksTargets:
    def test_they_are_read_as_written(self, fixtures):
        kpis = cost.targets(fixtures / 'cost')

        assert kpis['analysed_same_day'] == D('96.0')
        assert kpis['our_error_rate'] == D('2.5')

    def test_the_latest_month_known_before_its_close(self, fixtures):
        kpis = cost.targets(fixtures / 'cost')

        assert kpis['close_month'] == '2026-05'
        assert kpis['known_before_close'] == D('100.0')

    def test_documents_for_a_person(self, fixtures):
        assert cost.targets(fixtures / 'cost')['for_a_person'] == 1

    def test_no_report_no_targets(self, tmp_path):
        kpis = cost.targets(tmp_path)

        assert kpis['analysed_same_day'] is None
        assert kpis['for_a_person'] == 0

    def test_an_empty_exceptions_file_is_zero(self, tmp_path):
        """The report writes one empty row when nobody needs to look."""
        (tmp_path / 'exceptions.csv').write_text(
            'invoice_number,origin,reason\n,,\n', encoding='utf-8')
        (tmp_path / 'kpis.json').write_text(json.dumps(
            {'analysed_same_day': '100.0', 'our_error_rate': '0.0',
             'known_before_close': {}}), encoding='utf-8')

        assert cost.targets(tmp_path)['for_a_person'] == 0
