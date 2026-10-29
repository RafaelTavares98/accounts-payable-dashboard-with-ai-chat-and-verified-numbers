"""The fixed menu of panels on the cost view, and what each one draws.

The model picks from this menu and nothing else, so it cannot ask for a
panel that was never built, and it cannot ask for a figure that was never
defined. A panel is data, not a picture.
"""

from decimal import Decimal

import pytest

import cost
import cost_panels

D = Decimal


class TestTheMenu:
    def test_the_menu_is_closed(self):
        assert set(cost_panels.MENU) == {
            'landed', 'by_component', 'by_carrier', 'by_mode',
            'by_product', 'unit_cost', 'by_month', 'by_shipment',
        }

    def test_every_panel_says_what_kind_of_chart_it_is(self):
        kinds = {spec.kind for spec in cost_panels.MENU.values()}

        assert kinds <= {'cards', 'bar', 'line', 'table'}

    def test_every_panel_has_a_title_a_person_can_read(self):
        for name, spec in cost_panels.MENU.items():
            assert spec.title[0].isupper(), name

    def test_every_panel_only_asks_for_figures_that_exist(self):
        """A panel that asks for a figure nobody wrote would be a hole
        for an invented number to come through."""
        for name, spec in cost_panels.MENU.items():
            for figure in spec.figures:
                assert callable(getattr(cost, figure, None)), \
                    f'{name} wants {figure}'

    def test_every_panel_is_described_for_the_model(self):
        assert set(cost_panels.LOOKS_LIKE) == set(cost_panels.MENU)

    def test_the_fill_order_only_names_panels_on_the_menu(self):
        assert set(cost_panels.FILL_ORDER) <= set(cost_panels.MENU)

    def test_no_payment_figure_is_left_on_the_menu(self):
        """The department does not pay invoices. Overdue and days late
        left the page with the payables view."""
        words = ' '.join(spec.title.lower()
                         for spec in cost_panels.MENU.values())

        for gone in ('overdue', 'owed', 'late', 'paid'):
            assert gone not in words


class TestBuildingOne:
    def test_the_landed_panel_carries_the_headline(self, lines):
        built = cost_panels.build('landed', lines)

        assert dict(built.rows) == {
            'Landed cost': D('24659.00'),
            'Final': D('23559.00'),
            'Provisional': D('1100.00'),
            'Share provisional': D('4.5'),
            'Recoverable taxes, apart': D('3147.50'),
        }

    def test_a_ranking_is_label_and_value(self, lines):
        built = cost_panels.build('by_carrier', lines)

        assert built.kind == 'bar'
        assert built.rows[0] == ('Marsk Line Agencies B.V.', D('16484.50'))

    def test_the_month_panel_adds_final_and_provisional(self, lines):
        built = cost_panels.build('by_month', lines)

        assert built.rows == [('2026-04', D('16484.50')),
                              ('2026-05', D('8174.50'))]

    def test_the_shipment_panel_names_the_dearest(self, lines):
        built = cost_panels.build('by_shipment', lines)

        assert built.rows[0] == ('B/L MRK7000001', D('16484.50'))

    def test_a_panel_built_twice_is_the_same_panel(self, lines):
        """Nothing here may be random."""
        assert cost_panels.build('by_product', lines).rows == \
            cost_panels.build('by_product', lines).rows


class TestItRespectsTheFilters:
    def test_a_panel_only_sees_the_lines_it_was_given(self, lines):
        air = cost.only(lines, mode='air')

        built = cost_panels.build('landed', air)

        assert dict(built.rows)['Landed cost'] == D('7074.50')

    def test_a_panel_over_nothing_is_empty_not_absent(self):
        built = cost_panels.build('by_carrier', [])

        assert built.rows == []
        assert built.empty


class TestAskingForTheWrongThing:
    def test_a_panel_that_is_not_on_the_menu_is_refused(self, lines):
        with pytest.raises(cost_panels.NoSuchPanel):
            cost_panels.build('by_cost_centre', lines)

    def test_the_refusal_names_what_is_available(self, lines):
        with pytest.raises(cost_panels.NoSuchPanel, match='by_carrier'):
            cost_panels.build('by_cost_centre', lines)
