"""The copy that brings projects 01 and 02 into the panel's folder."""

import json

import pytest

import refresh_live_data as refresh


def _pair(tmp_path, name='invoices.csv', body='a,b\n1,2\n'):
    source = tmp_path / 'from' / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(body, encoding='utf-8')
    return source


def test_missing_names_every_absent_source(tmp_path):
    there = _pair(tmp_path)
    gone = tmp_path / 'from' / 'labels.csv'
    copies = [(there, 'invoices.csv'), (gone, 'labels.csv')]
    assert refresh.missing(copies) == [gone]


def test_missing_is_empty_when_all_are_there(tmp_path):
    there = _pair(tmp_path)
    assert refresh.missing([(there, 'invoices.csv')]) == []


def test_copy_writes_the_file_under_the_expected_name(tmp_path):
    source = _pair(tmp_path, body='number\nABC-1\n')
    target = tmp_path / 'data-live'
    assert refresh.copy([(source, 'invoices.csv')], target) == \
        ['invoices.csv']
    assert (target / 'invoices.csv').read_text(encoding='utf-8') == \
        'number\nABC-1\n'


def test_copy_makes_the_cost_folder(tmp_path):
    source = _pair(tmp_path, name='kpis.json', body=json.dumps({'a': 1}))
    target = tmp_path / 'data-live'
    refresh.copy([(source, 'cost/kpis.json')], target)
    assert (target / 'cost' / 'kpis.json').exists()


def test_copy_replaces_an_older_file(tmp_path):
    source = _pair(tmp_path, body='new\n')
    target = tmp_path / 'data-live'
    (target).mkdir()
    (target / 'invoices.csv').write_text('old\n', encoding='utf-8')
    refresh.copy([(source, 'invoices.csv')], target)
    assert (target / 'invoices.csv').read_text(encoding='utf-8') == 'new\n'


def test_the_panel_needs_every_name_the_list_carries():
    """These are the names the panel's own loaders open."""
    names = {name for _, name in refresh.COPIES}
    assert names == {
        'invoices.csv', 'invoice_lines.csv', 'labels.csv', 'anomalies.csv',
        'cost/landed_cost.csv', 'cost/operations.csv', 'cost/exceptions.csv',
        'cost/kpis.json', 'cost/items.csv', 'cost/vendors.csv',
    }


def test_rebuild_cost_stops_when_project_01_fails(monkeypatch):
    class Done:
        returncode = 1
        stdout = ''
        stderr = 'no erp folder'

    monkeypatch.setattr(refresh.subprocess, 'run',
                        lambda *a, **k: Done())
    with pytest.raises(SystemExit) as stopped:
        refresh.rebuild_cost()
    assert 'no erp folder' in str(stopped.value)


def test_rebuild_cost_returns_what_project_01_said(monkeypatch):
    class Done:
        returncode = 0
        stdout = 'cost report: landed_cost.csv\n'
        stderr = ''

    monkeypatch.setattr(refresh.subprocess, 'run',
                        lambda *a, **k: Done())
    assert refresh.rebuild_cost() == 'cost report: landed_cost.csv'


def test_main_copies_nothing_when_a_source_is_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, 'rebuild_cost', lambda: '')
    gone = tmp_path / 'from' / 'invoices.csv'
    monkeypatch.setattr(refresh, 'COPIES', [(gone, 'invoices.csv')])
    target = tmp_path / 'data-live'
    monkeypatch.setattr(refresh, 'TARGET', target)
    with pytest.raises(SystemExit) as stopped:
        refresh.main()
    assert 'nothing copied' in str(stopped.value)
    assert not target.exists()
