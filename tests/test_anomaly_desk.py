"""The anomaly view's weekly figures, the ones the five tiles show."""

from decimal import Decimal

import anomalies


def _row(week, flagged=False, decision='', total='100.00'):
    return anomalies.Scored(
        number='X-1', supplier='A', kind='goods', issued=week, week=week,
        total=Decimal(total), score=Decimal('0.5'), check='c', stage='s',
        checks='', flagged=flagged, origin='client' if flagged else '',
        decision=decision)


class TestNoRows:

    def test_no_rows_give_no_week(self):
        assert anomalies.desk_week([]) is None


class TestTheLatestWeek:

    def test_the_week_is_the_latest_one_scored(self):
        week = anomalies.desk_week([_row('2026-03-02'), _row('2026-03-09')])
        assert week['week'] == '2026-03-09'

    def test_scored_counts_every_invoice_that_week(self):
        rows = [_row('2026-03-09'), _row('2026-03-09'), _row('2026-03-02')]
        assert anomalies.desk_week(rows)['now']['scored'] == 2

    def test_flagged_counts_only_the_flagged(self):
        rows = [_row('2026-03-09', flagged=True), _row('2026-03-09')]
        assert anomalies.desk_week(rows)['now']['flagged'] == 1

    def test_money_adds_the_flagged_invoices_only(self):
        rows = [_row('2026-03-09', flagged=True, total='40.00'),
                _row('2026-03-09', total='900.00')]
        assert anomalies.desk_week(rows)['now']['money'] == Decimal('40.00')

    def test_confirmed_counts_the_analyst_s_yes(self):
        rows = [_row('2026-03-09', flagged=True, decision='confirmed'),
                _row('2026-03-09', flagged=True, decision='dismissed')]
        assert anomalies.desk_week(rows)['now']['confirmed'] == 1

    def test_a_flag_with_no_decision_is_waiting(self):
        rows = [_row('2026-03-09', flagged=True),
                _row('2026-03-09', flagged=True, decision='pending')]
        assert anomalies.desk_week(rows)['now']['waiting'] == 2

    def test_an_unflagged_invoice_is_not_waiting(self):
        assert anomalies.desk_week([_row('2026-03-09')])['now']['waiting'] == 0


class TestTheWeekBefore:

    def test_before_is_the_week_that_came_first(self):
        rows = [_row('2026-03-02'), _row('2026-03-02'), _row('2026-03-09')]
        assert anomalies.desk_week(rows)['before']['scored'] == 2

    def test_one_week_alone_has_nothing_before_it(self):
        assert anomalies.desk_week([_row('2026-03-09')])['before'] is None

    def test_a_gap_does_not_invent_a_week(self):
        """The week before is the previous week scored, not the previous
        date on the calendar."""
        rows = [_row('2026-01-05'), _row('2026-03-09')]
        assert anomalies.desk_week(rows)['before']['scored'] == 1


class TestAMonthBack:

    def test_month_is_the_week_four_weeks_earlier(self):
        rows = [_row('2026-02-09'), _row('2026-02-16'), _row('2026-02-23'),
                _row('2026-03-02'), _row('2026-03-09'), _row('2026-03-09')]
        assert anomalies.desk_week(rows)['month']['scored'] == 1

    def test_no_week_four_weeks_back_gives_none(self):
        rows = [_row('2026-03-02'), _row('2026-03-09')]
        assert anomalies.desk_week(rows)['month'] is None


class TestTheRealRun:

    def test_every_figure_is_there_for_the_real_rows(self, anomaly_rows):
        week = anomalies.desk_week(anomaly_rows)
        assert set(week['now']) == {'scored', 'flagged', 'money',
                                    'confirmed', 'waiting'}

    def test_the_flagged_never_outnumber_the_scored(self, anomaly_rows):
        now = anomalies.desk_week(anomaly_rows)['now']
        assert now['flagged'] <= now['scored']
