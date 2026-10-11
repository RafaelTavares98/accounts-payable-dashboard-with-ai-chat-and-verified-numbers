"""Reading the invoice pipeline's two CSV files into bills to pay.

The pipeline writes what arrived. This reads what is owed. They are not the
same list: a superseded document was replaced, and an unreadable one is not
a bill at all until a person looks at it.
"""

from datetime import date
from decimal import Decimal

import payables


class TestLoading:
    def test_every_row_of_the_file_is_loaded(self, rows):
        """Nothing is dropped on the way in. Dropping happens later, on
        purpose, where a test can see it."""
        assert len(rows) == 12

    def test_a_row_knows_its_number(self, rows):
        found = payables.by_number(rows, 'NCL-2026-3001')

        assert found.number == 'NCL-2026-3001'

    def test_dates_arrive_as_dates_not_text(self, rows):
        found = payables.by_number(rows, 'NCL-2026-3001')

        assert found.issued == date(2026, 3, 2)
        assert found.due == date(2026, 4, 11)

    def test_money_arrives_as_decimal_not_float(self, rows):
        """A float cannot hold 0.10 exactly, and a payables total that is
        wrong in the fourth decimal is still wrong."""
        found = payables.by_number(rows, 'NCL-2026-3001')

        assert found.total == Decimal('10000.00')
        assert isinstance(found.total, Decimal)

    def test_it_remembers_which_file_it_came_from(self, rows):
        """The figure and the page it was read off belong together.
        Without the filename there is no way back to the document."""
        found = payables.by_number(rows, 'NCL-2026-3001')

        assert found.source == 'NCL-2026-3001.pdf'

    def test_the_supplier_is_the_name_on_the_page(self, rows):
        found = payables.by_number(rows, 'KNG-2026-3007')

        assert found.supplier == 'Keuhne & Nager Logistics AG'

    def test_an_empty_cell_is_empty_not_zero(self, rows):
        """Marsk bills against a bill of lading, not a purchase order. An
        absent order number is absent, not `PO-0`."""
        found = payables.by_number(rows, 'MRK-2026-3005')

        assert found.order_number == ''
        assert found.shipment_id == 'B/L MRK7000101'


class TestTheLines:
    def test_an_invoice_carries_its_own_lines(self, rows):
        found = payables.by_number(rows, 'NCL-2026-3001')

        assert len(found.lines) == 2

    def test_the_lines_say_what_was_bought(self, rows):
        found = payables.by_number(rows, 'NCL-2026-3001')

        assert found.lines[0].description.startswith('Lotion pump')
        assert found.lines[0].quantity == 30000
        assert found.lines[0].net == Decimal('6000.00')

    def test_the_lines_add_up_to_the_subtotal(self, rows):
        """If they do not, something was read wrong, and no figure built on
        top of them can be trusted."""
        for row in rows:
            if row.status == 'unreadable':
                continue

            assert sum(line.net for line in row.lines) == row.subtotal

    def test_lines_are_joined_on_the_hash_not_the_number(self, rows):
        """A revision shares its number with the document it replaces.
        Joining on the number gives one of them the other's lines."""
        original = payables.by_number(rows, 'GZV-2026-3004')
        revision = payables.by_number(rows, 'GZV-2026-3004-R1')

        assert original.lines[0].quantity == 10000
        assert revision.lines[0].quantity == 9000

    def test_an_unreadable_row_has_no_lines(self, rows):
        unreadable = [row for row in rows if row.status == 'unreadable'][0]

        assert unreadable.lines == []


class TestWhatIsActuallyOwed:
    def test_ten_of_the_twelve_are_owed(self, owed):
        assert len(owed) == 10

    def test_a_superseded_document_is_not_owed(self, owed):
        numbers = {row.number for row in owed}

        assert 'GZV-2026-3004' not in numbers

    def test_the_revision_that_replaced_it_is_owed(self, owed):
        numbers = {row.number for row in owed}

        assert 'GZV-2026-3004-R1' in numbers

    def test_an_unreadable_document_is_not_owed(self, owed):
        assert all(row.status != 'unreadable' for row in owed)

    def test_an_unreadable_document_is_still_counted_somewhere(self, rows):
        """It must not vanish. A bill nobody can read is a bill somebody
        has to chase, and a dashboard that hides it is lying by omission."""
        waiting = payables.needs_a_person(rows)

        assert len(waiting) == 1
        assert waiting[0].problems == 'no text layer'


class TestACreditNote:
    def test_a_credit_note_is_negative(self, rows):
        found = payables.by_number(rows, 'GZV-CN-2026-3009')

        assert found.total == Decimal('-2000.00')

    def test_a_credit_note_is_owed_like_any_other_document(self, owed):
        """It is owed in reverse: it lowers the balance. Leaving it out
        overstates what the company has to pay."""
        numbers = {row.number for row in owed}

        assert 'GZV-CN-2026-3009' in numbers

    def test_a_credit_note_knows_it_is_one(self, rows):
        found = payables.by_number(rows, 'GZV-CN-2026-3009')

        assert found.is_credit


class TestTheRealPipelineOutput:
    def test_the_columns_match_what_the_pipeline_writes(self, fixtures):
        """These fixtures are a hand written copy of another project's
        output. When that project adds a column, this test is where the
        two drift apart first."""
        header = (fixtures / 'invoices.csv').read_text(
            encoding='utf-8').splitlines()[0]

        assert header.split(',') == [
            'invoice_number', 'status', 'revises', 'issuer', 'issue_date',
            'due_date', 'subtotal', 'discount', 'grand_total',
            'order_number', 'shipment_id', 'line_count', 'decimal_mark',
            'date_order', 'source', 'sha256', 'first_seen', 'problems',
        ]

    def test_the_line_columns_match_too(self, fixtures):
        header = (fixtures / 'invoice_lines.csv').read_text(
            encoding='utf-8').splitlines()[0]

        assert header.split(',') == [
            'invoice_number', 'sha256', 'row', 'description', 'quantity',
            'unit_price', 'net',
        ]

    def test_the_count_column_agrees_with_the_lines_loaded(self, rows):
        for row in rows:
            assert row.line_count == len(row.lines)
