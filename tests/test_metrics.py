"""Every figure the dashboard can show, and nothing else.

One function per figure. The model is never allowed to produce a number,
so every number in every answer has to come out of one of these. If a
sentence quotes a figure that no function here returns, the figure was
invented, and the project has failed at the only thing it promised.

The expected values were worked out by hand from the twelve rows in
`fixtures/`. They are small on purpose: a reader can check them.
"""

from datetime import date
from decimal import Decimal

import metrics


class TestTheBalance:
    def test_the_total_owed(self, owed):
        """Ten documents, the credit note subtracting rather than
        adding."""
        assert metrics.total_owed(owed) == Decimal('67450.00')

    def test_the_credit_note_lowers_it(self, owed):
        without = [row for row in owed if not row.is_credit]

        assert metrics.total_owed(without) == Decimal('69450.00')

    def test_how_many_documents_it_covers(self, owed):
        assert metrics.count(owed) == 10

    def test_the_average_document(self, owed):
        assert metrics.ticket_average(owed) == Decimal('6745.00')

    def test_the_average_is_two_decimal_places(self, owed):
        average = metrics.ticket_average(owed)

        assert average == average.quantize(Decimal('0.01'))

    def test_an_empty_list_owes_nothing(self):
        """A filter that leaves no rows must give zero, not an error and
        not the unfiltered total."""
        assert metrics.total_owed([]) == Decimal('0.00')

    def test_an_empty_list_has_no_average(self):
        """Dividing by no documents is not zero. It is nothing."""
        assert metrics.ticket_average([]) is None


class TestWhatIsLate:
    def test_how_much_is_overdue(self, owed, today):
        assert metrics.overdue_total(owed, today) == Decimal('31750.00')

    def test_how_many_are_overdue(self, owed, today):
        assert metrics.overdue_count(owed, today) == 4

    def test_the_share_that_is_overdue(self, owed, today):
        """Four of the ten documents. Counted by document, not by value,
        because that is what a payables desk chases."""
        assert metrics.overdue_rate(owed, today) == Decimal('40.0')

    def test_the_average_days_late(self, owed, today):
        """51, 16, 48 and 11 days. The average is 31.5, and rounding it
        to 31 would hide half a day across four invoices."""
        assert metrics.average_days_overdue(owed, today) == Decimal('31.5')

    def test_the_average_days_late_is_one_decimal_place(self, owed, today):
        """20.4722222222222222222 reached the page once. A Decimal
        division keeps every place it can, and nobody is late by a
        billionth of a day.

        Nine of the ten divide to a repeating decimal. The whole ten
        divide evenly, which is why this went unnoticed.
        """
        nine = [row for row in owed if row.number != 'HCV-2026-3008']

        average = metrics.average_days_overdue(nine, today)

        assert average == average.quantize(Decimal('0.1'))

    def test_the_share_overdue_is_one_decimal_place(self, owed, today):
        nine = [row for row in owed if row.number != 'HCV-2026-3008']

        share = metrics.overdue_rate(nine, today)

        assert share == share.quantize(Decimal('0.1'))

    def test_the_average_document_is_two_decimal_places(self, owed):
        nine = [row for row in owed if row.number != 'HCV-2026-3008']

        average = metrics.ticket_average(nine)

        assert average == average.quantize(Decimal('0.01'))

    def test_the_oldest_one(self, owed, today):
        worst = metrics.oldest_overdue(owed, today)

        assert worst.number == 'NCL-2026-3001'

    def test_nothing_late_means_no_average(self, owed, today):
        early = date(2026, 3, 1)

        assert metrics.average_days_overdue(owed, early) is None


class TestTheBuckets:
    def test_overdue_falls_into_bands(self, owed, today):
        """The video shows this as a bar per band. Two invoices are less
        than a month late, two are between one and two months."""
        bands = metrics.overdue_buckets(owed, today)

        assert bands == [
            ('1 to 30 days', 2, Decimal('19250.00')),
            ('31 to 60 days', 2, Decimal('12500.00')),
            ('61 to 90 days', 0, Decimal('0.00')),
            ('over 90 days', 0, Decimal('0.00')),
        ]

    def test_the_bands_add_up_to_the_overdue_total(self, owed, today):
        bands = metrics.overdue_buckets(owed, today)
        counted = sum(value for _, _, value in bands)

        assert counted == metrics.overdue_total(owed, today)

    def test_every_band_is_shown_even_when_empty(self, owed, today):
        """A missing bar reads as a missing band, not an empty one."""
        bands = metrics.overdue_buckets(owed, today)

        assert len(bands) == 4


class TestBySupplier:
    def test_what_each_supplier_is_owed(self, owed):
        assert metrics.by_supplier(owed) == [
            ('Guangzhou Verrelia Glassworks Co., Ltd.', Decimal('25500.00')),
            ('Ningbo Caplink Industrial Co., Ltd.', Decimal('21000.00')),
            ('Hanil Cosmetic Vessels Co., Ltd.', Decimal('14250.00')),
            ('Marsk Line Agencies B.V.', Decimal('5500.00')),
            ('Keuhne & Nager Logistics AG', Decimal('1200.00')),
        ]

    def test_the_biggest_comes_first(self, owed):
        """A ranking that is not sorted is a list."""
        values = [value for _, value in metrics.by_supplier(owed)]

        assert values == sorted(values, reverse=True)

    def test_the_suppliers_add_up_to_the_total(self, owed):
        counted = sum(value for _, value in metrics.by_supplier(owed))

        assert counted == metrics.total_owed(owed)

    def test_the_credit_lands_on_the_supplier_who_issued_it(self, owed):
        """Guangzhou billed 20,000 and 7,500 and credited 2,000."""
        by_name = dict(metrics.by_supplier(owed))

        assert by_name['Guangzhou Verrelia Glassworks Co., Ltd.'] == \
            Decimal('25500.00')


class TestByMonth:
    def test_what_each_month_brought_in(self, owed):
        assert metrics.by_month(owed) == [
            ('2026-03', Decimal('12500.00')),
            ('2026-04', Decimal('46750.00')),
            ('2026-05', Decimal('8200.00')),
        ]

    def test_the_months_are_in_order(self, owed):
        """Oldest first. A time series sorted by size is not a time
        series."""
        labels = [label for label, _ in metrics.by_month(owed)]

        assert labels == sorted(labels)

    def test_the_months_add_up_to_the_total(self, owed):
        counted = sum(value for _, value in metrics.by_month(owed))

        assert counted == metrics.total_owed(owed)

    def test_a_month_with_nothing_in_it_is_still_a_month(self, owed):
        """Between March and May there is April. Were April empty, the
        line would have to dip, not skip."""
        labels = [label for label, _ in metrics.by_month(owed)]

        assert labels == ['2026-03', '2026-04', '2026-05']


class TestTheWeeksAhead:
    def test_it_groups_by_the_week_money_is_due(self, owed):
        """Two months of issue dates make a two point line, which is a
        straight diagonal and says nothing. What a payables desk wants
        is the week each bill falls due."""
        weeks = metrics.by_due_week(owed)

        assert len(weeks) >= 8

    def test_each_label_is_the_monday_of_that_week(self, owed):
        labels = [label for label, _ in metrics.by_due_week(owed)]

        assert labels[0] == '2026-04-06'

    def test_the_weeks_run_without_a_gap(self, owed):
        """A week nothing falls due in is a zero, not a missing week."""
        from datetime import date, timedelta
        labels = [label for label, _ in metrics.by_due_week(owed)]
        days = [date.fromisoformat(label) for label in labels]

        for before, after in zip(days, days[1:]):
            assert after - before == timedelta(days=7)

    def test_the_weeks_add_up_to_the_total(self, owed):
        counted = sum(value for _, value in metrics.by_due_week(owed))

        assert counted == metrics.total_owed(owed)


class TestWhatArrivedEachWeek:
    def test_it_groups_by_the_week_the_bill_arrived(self, owed):
        """What falls due is only half the picture. Beside it belongs
        what came in, because a week that bills heavily is the week
        that will fall due later."""
        weeks = metrics.by_issue_week(owed)

        assert weeks
        assert weeks[0][0] == '2026-03-02'

    def test_it_adds_up_to_the_total(self, owed):
        counted = sum(value for _, value in metrics.by_issue_week(owed))

        assert counted == metrics.total_owed(owed)

    def test_it_can_be_read_on_the_same_weeks_as_the_due_series(self, owed):
        """Two lines on one axis have to share their x values, or the
        reader is comparing two different scales by eye."""
        weeks = ['2026-04-06', '2026-04-13', '2026-04-20']

        lined = metrics.by_issue_week(owed, weeks=weeks)

        assert [label for label, _ in lined] == weeks


class TestWhatTheMoneyWasSpentOn:
    """An invoice carries no category column, so the category is read
    off the words on the line. That is a guess, and it has to be an
    honest one: anything the words do not place lands in Other rather
    than being pushed into whichever bucket looks best."""

    def test_glass_is_bottles_and_jars(self, owed):
        spent = dict(metrics.by_category(owed))

        assert spent['Bottles and jars'] == Decimal('33500.00')

    def test_pumps_and_caps_are_closures(self, owed):
        spent = dict(metrics.by_category(owed))

        assert spent['Closures and pumps'] == Decimal('30000.00')

    def test_carriage_is_freight(self, owed):
        spent = dict(metrics.by_category(owed))

        assert spent['Freight'] == Decimal('5600.00')

    def test_a_fee_is_not_freight(self, owed):
        """A documentation fee rides on a freight invoice and is not
        carriage. Folding it in overstates the cost of moving goods."""
        spent = dict(metrics.by_category(owed))

        assert spent['Surcharges and fees'] == Decimal('1100.00')

    def test_what_the_words_do_not_place_is_other(self, owed):
        spent = dict(metrics.by_category(owed))

        assert spent['Other'] == Decimal('-2000.00')

    def test_it_adds_up_to_every_line(self, owed):
        counted = sum(value for _, value in metrics.by_category(owed))
        lines = sum(value for _, value in metrics.by_item(owed))

        assert counted == lines

    def test_the_biggest_comes_first(self, owed):
        values = [value for _, value in metrics.by_category(owed)]

        assert values == sorted(values, reverse=True)

    def test_a_donut_can_hold_them(self, owed):
        """Past six or so slices a ring stops being readable."""
        assert len(metrics.CATEGORIES) <= 7


class TestWhatChanged:
    """"Why did arrivals drop after the second of May?" is a question
    about a change, and nothing on the menu measured one. The model
    cannot explain a fall nobody computed."""

    def test_it_reads_the_moves_in_a_series(self, owed):
        weeks = metrics.by_issue_week(owed)

        moves = metrics.changes(weeks)

        assert len(moves) == len(weeks) - 1

    def test_a_move_says_from_where_to_where(self, owed):
        weeks = metrics.by_issue_week(owed)

        label, before, after, delta = metrics.changes(weeks)[0]

        assert label == weeks[1][0]
        assert before == weeks[0][1]
        assert after == weeks[1][1]
        assert delta == after - before

    def test_the_sharpest_fall_is_findable(self, owed):
        weeks = metrics.by_issue_week(owed)

        worst = metrics.sharpest(weeks, rising=False)

        assert worst[3] < 0
        assert worst[3] == min(m[3] for m in metrics.changes(weeks))

    def test_the_sharpest_rise_is_findable(self, owed):
        weeks = metrics.by_issue_week(owed)

        best = metrics.sharpest(weeks, rising=True)

        assert best[3] == max(m[3] for m in metrics.changes(weeks))

    def test_a_series_of_one_has_no_moves(self, owed):
        assert metrics.changes([('2026-04-06', Decimal('1.00'))]) == []

    def test_a_series_of_one_has_no_sharpest(self, owed):
        assert metrics.sharpest([('2026-04-06', Decimal('1.00'))]) is None


class TestByOrder:
    def test_what_one_purchase_order_cost(self, owed):
        """Twenty thousand of glass, two thousand credited back."""
        by_order = dict(metrics.by_order(owed))

        assert by_order['PO-41003'] == Decimal('18000.00')

    def test_freight_has_no_order_number(self, owed):
        """A carrier bills against a bill of lading. Grouping those under
        an empty order would invent an order called nothing."""
        by_order = dict(metrics.by_order(owed))

        assert '' not in by_order


class TestWhatIsOnTheLines:
    def test_the_most_bought_items(self, owed):
        """Grouped by the words on the line, because the invoice carries
        no part catalogue and this project does not invent one."""
        top = metrics.by_item(owed)

        assert top[0][0] == 'Glass bottle, 50 ml, flint'
        assert top[0][1] == Decimal('16500.00')

    def test_the_items_add_up_to_the_subtotals(self, owed):
        counted = sum(value for _, value in metrics.by_item(owed))
        subtotals = sum(row.subtotal for row in owed)

        assert counted == subtotals


class TestEveryFigureIsNamed:
    def test_the_menu_of_figures_is_closed(self):
        """A panel asks for a figure by name. A name that is not on this
        list cannot be computed, which is how an invented figure is
        stopped before it reaches a sentence."""
        assert set(metrics.FIGURES) == {
            'total_owed', 'count', 'ticket_average',
            'overdue_total', 'overdue_count', 'overdue_rate',
            'average_days_overdue', 'oldest_overdue',
            'overdue_buckets', 'by_supplier', 'by_month',
            'by_order', 'by_item', 'by_due_week', 'by_issue_week',
            'by_category',
        }

    def test_every_name_on_the_menu_is_a_real_function(self):
        for name in metrics.FIGURES:
            assert callable(getattr(metrics, name))

    def test_asking_for_a_figure_by_name_works(self, owed, today):
        got = metrics.compute('overdue_count', owed, today=today)

        assert got == 4

    def test_asking_for_a_figure_that_does_not_exist_is_refused(self, owed):
        try:
            metrics.compute('profit_margin', owed)
        except metrics.NoSuchFigure:
            return
        raise AssertionError('it computed a figure that was never defined')
