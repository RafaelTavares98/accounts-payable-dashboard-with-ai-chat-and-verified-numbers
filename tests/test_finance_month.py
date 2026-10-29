"""The finance view's monthly figures, the ones its five tiles show.

The cost desk closes a month, not a week, so this view compares the
latest month with the one before it and with the quarter behind it.
"""

from decimal import Decimal

import cost


def _line(month, landed='100.00', status='final', credits='0.00'):
    return cost.Line(
        shipment='S1', order='PO-1', code='C1', product='Part',
        quantity=Decimal('1'), parts=Decimal(landed),
        credits=Decimal(credits), landed=Decimal(landed), status=status,
        carrier='DHI', mode='LCL', month=month)


class TestNoLines:

    def test_no_lines_give_no_month(self):
        assert cost.finance_month([]) is None


class TestTheLatestMonth:

    def test_the_month_is_the_latest_one_costed(self):
        got = cost.finance_month([_line('2026-01'), _line('2026-02')])
        assert got['month'] == '2026-02'

    def test_landed_adds_every_line_that_month(self):
        lines = [_line('2026-02', '10.00'), _line('2026-02', '5.00'),
                 _line('2026-01', '900.00')]
        assert cost.finance_month(lines)['now']['landed'] == Decimal('15.00')

    def test_final_leaves_the_provisional_out(self):
        lines = [_line('2026-02', '10.00'),
                 _line('2026-02', '5.00', status='provisional')]
        assert cost.finance_month(lines)['now']['final'] == Decimal('10.00')

    def test_provisional_is_what_is_not_final(self):
        lines = [_line('2026-02', '10.00'),
                 _line('2026-02', '5.00', status='provisional')]
        now = cost.finance_month(lines)['now']
        assert now['provisional'] == Decimal('5.00')

    def test_the_share_is_the_provisional_part_of_the_whole(self):
        lines = [_line('2026-02', '75.00'),
                 _line('2026-02', '25.00', status='provisional')]
        assert cost.finance_month(lines)['now']['share'] == Decimal('25.0')

    def test_a_month_with_no_money_has_no_share(self):
        assert cost.finance_month([_line('2026-02', '0.00')]
                                  )['now']['share'] is None

    def test_credits_are_added_on_their_own(self):
        lines = [_line('2026-02', '100.00', credits='9.00')]
        assert cost.finance_month(lines)['now']['credits'] == Decimal('9.00')


class TestWhatItComparesWith:

    def test_before_is_the_month_costed_before_it(self):
        lines = [_line('2026-01', '7.00'), _line('2026-02')]
        assert cost.finance_month(lines)['before']['landed'] == Decimal('7.00')

    def test_one_month_alone_has_nothing_before_it(self):
        assert cost.finance_month([_line('2026-02')])['before'] is None

    def test_the_quarter_back_is_three_months_earlier(self):
        lines = [_line('2026-01', '7.00'), _line('2026-02'),
                 _line('2026-03'), _line('2026-04')]
        assert cost.finance_month(lines)['quarter']['landed'] == Decimal('7.00')

    def test_too_few_months_give_no_quarter(self):
        lines = [_line('2026-01'), _line('2026-02')]
        assert cost.finance_month(lines)['quarter'] is None


class TestTheRealRun:

    def test_every_figure_is_there(self, real_lines):
        now = cost.finance_month(real_lines)['now']
        assert set(now) == {'landed', 'final', 'provisional', 'share',
                            'credits'}

    def test_final_and_provisional_add_up_to_landed(self, real_lines):
        now = cost.finance_month(real_lines)['now']
        assert now['final'] + now['provisional'] == now['landed']
