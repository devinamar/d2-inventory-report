# Tests for writing the report's files (report/report.py).
from report import report
from tests import conftest as c


def test_the_report_is_written_in_both_formats_named_after_the_player(conn, tmp_path):
    # The file names leave out the Bungie Name's #code.
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100, c.WEAPON_SOCKETS)
    report.write(conn, tmp_path, 'Name#1234')
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        'd2_report_Name.html',
        'd2_report_Name.md',
    ]


def test_write_skips_a_db_without_inventory(conn, tmp_path):
    report.write(conn, tmp_path, 'Name#1234')
    assert list(tmp_path.iterdir()) == []
