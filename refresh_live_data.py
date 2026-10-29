"""Bring the panel's data up to date with projects 01 and 02.

The panel reads data-live/. Nothing wrote that folder: the files were
copied by hand once. This script does the copy, and rebuilds project
01's cost report first, because that report is read from the invoices
and goes stale every time project 01 runs again.

    python refresh_live_data.py

Nothing is written unless every source file is present.
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANUAL = HERE.parent
PIPELINE = MANUAL / '01-invoice-pipeline'
LIVE = PIPELINE / 'Invoices' / 'live'
ANOMALIES = MANUAL / '02-invoice-anomalies'
TARGET = HERE / 'data-live'

#: Source file, then where the panel expects it, under data-live/.
COPIES = [
    (LIVE / 'data' / 'invoices.csv', 'invoices.csv'),
    (LIVE / 'data' / 'invoice_lines.csv', 'invoice_lines.csv'),
    (LIVE / 'labels.csv', 'labels.csv'),
    (ANOMALIES / 'data' / 'anomalies.csv', 'anomalies.csv'),
    (LIVE / 'cost' / 'landed_cost.csv', 'cost/landed_cost.csv'),
    (LIVE / 'cost' / 'operations.csv', 'cost/operations.csv'),
    (LIVE / 'cost' / 'exceptions.csv', 'cost/exceptions.csv'),
    (LIVE / 'cost' / 'kpis.json', 'cost/kpis.json'),
    # The menu names come from the ERP, not from the cost report.
    (LIVE / 'erp' / 'items.csv', 'cost/items.csv'),
    (LIVE / 'erp' / 'vendors.csv', 'cost/vendors.csv'),
]


def rebuild_cost():
    """Run project 01's cost report over its current invoices."""
    done = subprocess.run([sys.executable, 'run.py', 'cost'],
                          cwd=PIPELINE, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit('project 01 cost report failed:\n'
                         + (done.stderr or done.stdout))
    return (done.stdout or '').strip()


def missing(copies=None):
    """The source files that are not there, in the order listed."""
    copies = COPIES if copies is None else copies
    return [source for source, _ in copies if not source.exists()]


def copy(copies=None, target=None):
    """Copy every source into target. Returns the names written."""
    copies = COPIES if copies is None else copies
    target = TARGET if target is None else target
    written = []
    for source, name in copies:
        where = Path(target) / name
        where.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, where)
        written.append(name)
    return written


def main():
    said = rebuild_cost()
    if said:
        print(said)
    gone = missing()
    if gone:
        raise SystemExit('not there, nothing copied:\n'
                         + '\n'.join(str(p) for p in gone))
    written = copy()
    print(f'{len(written)} files copied into {TARGET.name}/')


if __name__ == '__main__':
    main()
