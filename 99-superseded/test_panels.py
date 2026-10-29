"""The fixed menu of panels, and what each one draws.

In the video a question opens panels over the dashboard. The model picks
which ones. It picks from this menu and nothing else, so it cannot ask for
a panel that was never built, and it cannot ask for a figure that was
never defined.

A panel is data, not a picture. It says what to draw. Drawing is the page's
job, and the page is tested in `test_web.py`.
"""

from decimal import Decimal

import panels


class TestTheMenu:
    def test_the_menu_is_closed(self):
        assert set(panels.MENU) == {
            'balance', 'overdue', 'by_band', 'by_supplier',
            'by_month', 'by_item', 'by_order',
        }

    def test_every_panel_says_what_kind_of_chart_it_is(self):
        kinds = {panel.kind for panel in panels.MENU.values()}

        assert kinds <= {'cards', 'bar', 'line', 'table'}

    def test_every_panel_has_a_title_a_person_can_read(self):
        for name, panel in panels.MENU.items():
            assert panel.title
            assert panel.title[0].isupper(), name

    def test_every_panel_only_asks_for_figures_that_exist(self):
        """This is the whole safety of the design. A panel that asks for
        a figure nobody wrote would be a hole for an invented number to
        come through."""
        import metrics

        for name, panel in panels.MENU.items():
            for figure in panel.figures:
                assert figure in metrics.FIGURES, f'{name} wants {figure}'


class TestBuildingOne:
    def test_a_panel_comes_back_filled(self, owed, today):
        built = panels.build('by_supplier', owed, today=today)

        assert built.name == 'by_supplier'
        assert built.kind == 'bar'
        assert built.title == 'Owed by supplier'

    def test_its_rows_are_label_and_value(self, owed, today):
        built = panels.build('by_supplier', owed, today=today)

        assert built.rows[0] == ('Guangzhou Verrelia Glassworks Co., Ltd.',
                                 Decimal('25500.00'))

    def test_the_cards_panel_carries_several_figures(self, owed, today):
        built = panels.build('balance', owed, today=today)

        assert dict(built.rows) == {
            'Total owed': Decimal('67450.00'),
            'Documents': 10,
            'Average document': Decimal('6745.00'),
        }

    def test_the_overdue_panel_carries_the_headline(self, owed, today):
        built = panels.build('overdue', owed, today=today)

        assert dict(built.rows) == {
            'Overdue': Decimal('31750.00'),
            'Documents overdue': 4,
            'Share overdue': Decimal('40.0'),
            'Average days late': Decimal('31.5'),
        }

    def test_a_panel_built_twice_is_the_same_panel(self, owed, today):
        """Nothing here may be random. A demo that shows a different
        number on the second click is not a demo."""
        first = panels.build('by_month', owed, today=today)
        second = panels.build('by_month', owed, today=today)

        assert first.rows == second.rows


class TestItRespectsTheFilters:
    def test_a_panel_only_sees_the_rows_it_was_given(self, owed, today):
        import filtering
        marsk = filtering.apply(owed, supplier='Marsk Line Agencies B.V.')

        built = panels.build('balance', owed=marsk, today=today)

        assert dict(built.rows)['Total owed'] == Decimal('5500.00')

    def test_a_panel_over_nothing_is_empty_not_absent(self, today):
        """An empty panel tells the reader the filter found nothing. A
        missing panel tells them nothing at all."""
        built = panels.build('by_supplier', [], today=today)

        assert built.rows == []
        assert built.empty


class TestAskingForTheWrongThing:
    def test_a_panel_that_is_not_on_the_menu_is_refused(self, owed, today):
        try:
            panels.build('by_cost_centre', owed, today=today)
        except panels.NoSuchPanel:
            return
        raise AssertionError('it built a panel that was never defined')

    def test_the_refusal_names_what_is_available(self, owed, today):
        """The message is read by the next person to add a panel, so it
        has to say what the menu holds."""
        try:
            panels.build('by_cost_centre', owed, today=today)
        except panels.NoSuchPanel as refused:
            assert 'by_supplier' in str(refused)
