"""The invoice pipeline's two CSV files, read into bills to pay.

The pipeline writes what arrived. This reads what is owed. They are not the
same list: a superseded document was replaced, and an unreadable one is not
a bill at all until a person looks at it.
"""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


class Line:
    """One line item of one invoice."""

    def __init__(self, description, quantity, net):
        self.description = description
        self.quantity = quantity
        self.net = net


class Invoice:
    """One document the pipeline read, with its own lines attached."""

    def __init__(self, number, status, revises, issuer, issued, due,
                 subtotal, discount, total, order_number, shipment_id,
                 line_count, sha256, problems, source=''):
        self.number = number
        self.status = status
        self.revises = revises
        self.supplier = issuer
        self.issued = issued
        self.due = due
        self.subtotal = subtotal
        self.discount = discount
        self.total = total
        self.order_number = order_number
        self.shipment_id = shipment_id
        self.line_count = line_count
        self.sha256 = sha256
        self.problems = problems
        #: The file the pipeline read it out of, so a reader can open
        #: the page any figure came from.
        self.source = source
        self.lines = []

    @property
    def is_credit(self):
        """A credit note lowers the balance instead of raising it."""
        return '-CN-' in self.number or self.total < 0


def _money(text):
    try:
        return Decimal(text) if text else Decimal('0.00')
    except InvalidOperation:
        return Decimal('0.00')


def _day(text):
    return date.fromisoformat(text) if text else None


def load(folder):
    """Read both files from one folder. Nothing is dropped here."""
    folder = Path(folder)
    rows = []
    with open(folder / 'invoices.csv', encoding='utf-8') as text:
        for record in csv.DictReader(text):
            rows.append(Invoice(
                number=record['invoice_number'],
                status=record['status'],
                revises=record['revises'],
                issuer=record['issuer'],
                issued=_day(record['issue_date']),
                due=_day(record['due_date']),
                subtotal=_money(record['subtotal']),
                discount=_money(record['discount']),
                total=_money(record['grand_total']),
                order_number=record['order_number'],
                shipment_id=record['shipment_id'],
                line_count=int(record['line_count'] or 0),
                sha256=record['sha256'],
                problems=record['problems'],
                source=record.get('source', ''),
            ))
    lines_by_hash = {}
    with open(folder / 'invoice_lines.csv', encoding='utf-8') as text:
        for record in csv.DictReader(text):
            lines_by_hash.setdefault(record['sha256'], []).append(Line(
                description=record['description'],
                quantity=int(record['quantity']),
                net=_money(record['net']),
            ))
    for row in rows:
        row.lines = lines_by_hash.get(row.sha256, [])
    return rows


def by_number(rows, number):
    """The one row with this document number."""
    for row in rows:
        if row.number == number:
            return row
    raise KeyError(number)


def payable(rows):
    """What is actually owed. Superseded and unreadable stay out."""
    return [row for row in rows
            if row.status not in ('superseded', 'unreadable')]


def needs_a_person(rows):
    """The documents a person must read before they become bills."""
    return [row for row in rows if row.status == 'unreadable']
