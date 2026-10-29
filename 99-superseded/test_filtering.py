"""The filters on top of the dashboard.

Every number on the page is computed over whatever the filters left. That
is the whole contract: "cálculo direto sobre os dados filtrados". So the
filters have to be boring, predictable, and able to stack.
"""

from datetime import date
from decimal import Decimal

import filtering


class TestOneFilterAtATime:
    def test_no_filter_leaves_everything(self, owed):
        assert len(filtering.apply(owed)) == 10

    def test_by_supplier(self, owed):
        kept = filtering.apply(owed, supplier='Marsk Line Agencies B.V.')

        assert {row.number for row in kept} == {'MRK-2026-3005',
                                                'MRK-2026-3006'}

    def test_by_period(self, owed):
        kept = filtering.apply(owed, since=date(2026, 5, 1),
                               until=date(2026, 5, 31))

        assert {row.number for row in kept} == {'MRK-2026-3005',
                                                'KNG-2026-3007',
                                                'GZV-CN-2026-3009',
                                                'NCL-2026-3010'}

    def test_the_period_is_the_issue_date(self, owed):
        """Not the due date. A bill belongs to the month it was issued in,
        which is the month the cost was incurred."""
        kept = filtering.apply(owed, since=date(2026, 3, 1),
                               until=date(2026, 3, 31))

        assert {row.number for row in kept} == {'NCL-2026-3001',
                                                'MRK-2026-3006'}

    def test_the_period_includes_both_ends(self, owed):
        """A filter of one day must find the bill issued on that day."""
        kept = filtering.apply(owed, since=date(2026, 5, 2),
                               until=date(2026, 5, 2))

        assert [row.number for row in kept] == ['MRK-2026-3005']

    def test_by_order(self, owed):
        """A purchase order is answered by more than one document: the
        goods, the freight, and sometimes a credit."""
        kept = filtering.apply(owed, order='PO-41003')

        assert {row.number for row in kept} == {'GZV-2026-3003',
                                                'GZV-CN-2026-3009'}

    def test_by_shipment(self, owed):
        """One container carries more than one order, so one bill of
        lading has more than one carrier billing against it."""
        kept = filtering.apply(owed, shipment='B/L MRK7000101')

        assert {row.number for row in kept} == {'MRK-2026-3005',
                                                'KNG-2026-3007'}


class TestTheState:
    def test_overdue_means_the_due_date_has_passed(self, owed, today):
        kept = filtering.apply(owed, state='overdue', today=today)

        assert {row.number for row in kept} == {'NCL-2026-3001',
                                                'NCL-2026-3002',
                                                'MRK-2026-3006',
                                                'HCV-2026-3008'}

    def test_due_today_is_not_overdue_yet(self, owed, today):
        """Marsk is due on the first of June and today is the first of
        June. Nobody is late on the day itself."""
        kept = filtering.apply(owed, state='overdue', today=today)

        assert 'MRK-2026-3005' not in {row.number for row in kept}

    def test_open_is_everything_not_yet_due(self, owed, today):
        kept = filtering.apply(owed, state='open', today=today)

        assert {row.number for row in kept} == {'GZV-2026-3003',
                                                'GZV-2026-3004-R1',
                                                'MRK-2026-3005',
                                                'KNG-2026-3007',
                                                'NCL-2026-3010'}

    def test_a_credit_note_is_in_neither(self, owed, today):
        """A credit is money coming back. Calling it overdue would say the
        company is late paying itself."""
        overdue = filtering.apply(owed, state='overdue', today=today)
        still_open = filtering.apply(owed, state='open', today=today)
        numbers = {row.number for row in overdue + still_open}

        assert 'GZV-CN-2026-3009' not in numbers

    def test_a_credit_note_has_its_own_state(self, owed, today):
        kept = filtering.apply(owed, state='credit', today=today)

        assert [row.number for row in kept] == ['GZV-CN-2026-3009']

    def test_paid_is_not_a_state(self, owed, today):
        """Nothing in an invoice says it was paid. Offering a `paid`
        filter would be offering a number this data cannot produce."""
        assert 'paid' not in filtering.STATES

    def test_overdue_needs_a_date(self, owed):
        """Without one the answer would change every morning, silently."""
        try:
            filtering.apply(owed, state='overdue')
        except filtering.NeedsADate:
            return
        raise AssertionError('it filtered by overdue with no date given')


class TestClickingAChart:
    """Every bar on the page is a filter nobody has pressed yet.

    A reader who sees Hanil at the top of the supplier chart wants the
    rest of the page to answer "and what about Hanil?". That is one
    click, not a trip to the dropdown.
    """

    def test_by_item_keeps_the_invoices_carrying_that_line(self, owed):
        kept = filtering.apply(owed, item='Glass bottle, 50 ml, flint')

        assert {row.number for row in kept} == {'GZV-2026-3003',
                                                'GZV-2026-3004-R1'}

    def test_an_item_nobody_bought_leaves_nothing(self, owed):
        assert filtering.apply(owed, item='Rocket fuel') == []

    def test_by_band_keeps_the_invoices_that_late(self, owed, today):
        """Clicking the 31 to 60 days slice should leave the two
        invoices in it, not every overdue invoice."""
        kept = filtering.apply(owed, band='31 to 60 days', today=today)

        assert {row.number for row in kept} == {'NCL-2026-3001',
                                                'MRK-2026-3006'}

    def test_the_bands_are_the_ones_the_chart_draws(self, owed, today):
        import metrics
        drawn = {label for label, _count, _value
                 in metrics.overdue_buckets(owed, today)}

        assert drawn <= set(filtering.BANDS)

    def test_a_band_needs_a_date_like_overdue_does(self, owed):
        try:
            filtering.apply(owed, band='31 to 60 days')
        except filtering.NeedsADate:
            return
        raise AssertionError('it filtered by band with no date given')

    def test_a_band_that_is_not_on_the_chart_is_refused(self, owed, today):
        try:
            filtering.apply(owed, band='101 to 200 days', today=today)
        except ValueError:
            return
        raise AssertionError('it accepted a band the chart never draws')


class TestFiltersStack:
    def test_two_filters_both_apply(self, owed, today):
        kept = filtering.apply(owed,
                               supplier='Ningbo Caplink Industrial Co., Ltd.',
                               state='overdue', today=today)

        assert {row.number for row in kept} == {'NCL-2026-3001',
                                                'NCL-2026-3002'}

    def test_filters_that_cross_leave_nothing(self, owed, today):
        kept = filtering.apply(owed,
                               supplier='Keuhne & Nager Logistics AG',
                               state='overdue', today=today)

        assert kept == []

    def test_the_original_list_is_never_changed(self, owed):
        """Every panel filters the same list. A filter that edits it would
        make the second panel depend on the first."""
        before = len(owed)
        filtering.apply(owed, supplier='Marsk Line Agencies B.V.')

        assert len(owed) == before


class TestWhatCanBeFilteredOn:
    def test_the_dashboard_can_list_its_own_suppliers(self, owed):
        assert filtering.suppliers(owed) == [
            'Guangzhou Verrelia Glassworks Co., Ltd.',
            'Hanil Cosmetic Vessels Co., Ltd.',
            'Keuhne & Nager Logistics AG',
            'Marsk Line Agencies B.V.',
            'Ningbo Caplink Industrial Co., Ltd.',
        ]

    def test_the_dashboard_can_say_what_period_it_holds(self, owed):
        assert filtering.period(owed) == (date(2026, 3, 2), date(2026, 5, 25))

    def test_an_unknown_filter_is_refused_not_ignored(self, owed):
        """Silently ignoring `cost_centre` would show the unfiltered
        number under a filtered heading, which is the worst kind of
        wrong: it looks right."""
        try:
            filtering.apply(owed, cost_centre='Logistica')
        except TypeError:
            return
        raise AssertionError('it accepted a column this data does not have')
