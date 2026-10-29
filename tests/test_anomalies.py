"""The anomaly view's figures, over eight hand-written rows.

Two weeks. Four invoices flagged, two each week: a price above the
contract, a freight charge not on the rate card twice, and an account not
on file. One invoice no rule explains is unflagged.
"""

from decimal import Decimal

import pytest

import anomalies


@pytest.fixture
def scored(fixtures):
    return anomalies.load(fixtures)


class TestLoading:
    def test_every_row_loads(self, scored):
        assert len(scored) == 8

    def test_amounts_are_exact(self, scored):
        assert scored[6].total == Decimal('950.50')

    def test_a_flag_is_a_yes_or_no(self, scored):
        assert [row.flagged for row in scored].count(True) == 4

    def test_a_missing_file_is_an_empty_view(self, tmp_path):
        assert anomalies.load(tmp_path) == []


class TestFiltering:
    def test_by_supplier(self, scored):
        kept = anomalies.only(scored, supplier='Marsk Line')

        assert {row.number for row in kept} == {'MRK-2026-3003', 'MRK-2026-3006'}

    def test_by_stage(self, scored):
        kept = anomalies.only(scored, stage='billing')

        assert [row.number for row in kept] == ['NCL-2026-3001']

    def test_an_unknown_filter_is_refused(self, scored):
        with pytest.raises(ValueError):
            anomalies.only(scored, colour='red')


class TestFigures:
    def test_how_many_were_flagged(self, scored):
        assert anomalies.flagged_count(scored) == 4

    def test_the_money_on_flagged_invoices(self, scored):
        assert anomalies.flagged_total(scored) == Decimal('8200.00')

    def test_the_share_flagged(self, scored):
        assert anomalies.flag_rate(scored) == Decimal('50.0')

    def test_how_many_were_reviewed(self, scored):
        assert anomalies.reviewed(scored) == 8

    def test_by_stage_counts_flagged_only(self, scored):
        assert anomalies.by_stage(scored) == [
            ('freight billing', 2, Decimal('4000.00')),
            ('billing', 1, Decimal('1200.00')),
            ('vendor master', 1, Decimal('3000.00')),
        ]

    def test_by_check(self, scored):
        assert anomalies.by_check(scored)[0] == ('charge not on the rate card', 2)

    def test_by_supplier(self, scored):
        assert anomalies.by_supplier(scored)[0] == ('Marsk Line', 2, Decimal('4000.00'))

    def test_by_week_counts_flags_and_invoices(self, scored):
        assert [week[:3] for week in anomalies.by_week(scored)] == [
            ('2026-04-06', 2, 4), ('2026-04-13', 2, 4)]

    def test_by_week_carries_the_money_flagged(self, scored):
        """A desk flags its top five every week, so the count is flat by
        design; the money on them is what moves."""
        assert [week[3] for week in anomalies.by_week(scored)] == [
            Decimal('3300.00'), Decimal('4900.00')]

    def test_the_worst_first(self, scored):
        assert [row.number for row in anomalies.worst(scored, 2)] == [
            'HCV-2026-3005', 'NCL-2026-3001']

    def test_the_highest_scores_carry_a_reason(self, scored):
        assert anomalies.worst(scored, 1)[0].check == 'account not on file'

    def test_nothing_flagged_is_zero_not_an_error(self, scored):
        calm = [row for row in scored if not row.flagged]

        assert anomalies.flag_rate([]) is None
        assert anomalies.flagged_total(calm) == Decimal('0.00')


class TestWhoseErrorItIs:
    """Ours: a document the reader could not read or close, listed in the
    cost report's exceptions. The client's: a supplier's or a carrier's
    mistake, flagged by the model, then confirmed or dismissed by the
    analyst."""

    def test_a_flag_carries_its_origin_and_the_decision(self, scored):
        first = scored[0]

        assert first.origin == 'client'
        assert first.decision == 'confirmed'

    def test_an_older_file_without_the_columns_still_loads(self, tmp_path):
        (tmp_path / 'anomalies.csv').write_text(
            'number,supplier,kind,issue_date,week,grand_total,score,check,'
            'stage,checks,flagged\n'
            'A-1,S,goods,2026-04-06,2026-04-06,1.00,0.9,x,billing,x,1\n',
            encoding='utf-8')

        row = anomalies.load(tmp_path)[0]

        assert row.origin == 'client'
        assert row.decision == ''

    def test_the_analyst_s_decisions(self, scored):
        assert anomalies.by_decision(scored) == [
            ('confirmed', 2, Decimal('3300.00')),
            ('pending', 1, Decimal('3000.00')),
            ('dismissed', 1, Decimal('1900.00')),
        ]

    def test_client_errors_found_counts_confirmed_only(self, scored):
        """A dismissed flag was an honest invoice; it is no error."""
        assert anomalies.client_errors(scored) == 2

    def test_our_errors_come_from_the_cost_report(self, fixtures):
        assert anomalies.our_errors(fixtures / 'cost') == 1

    def test_no_report_means_none_of_ours_counted(self, tmp_path):
        assert anomalies.our_errors(tmp_path) == 0

    def test_by_origin_puts_ours_beside_the_client_s(self, scored):
        assert anomalies.by_origin(scored, ours=1) == [
            ('Our errors, read by a person', 1),
            ('Client errors, confirmed', 2),
            ('Client, waiting for the analyst', 1),
            ('Dismissed, invoice was right', 1),
        ]
