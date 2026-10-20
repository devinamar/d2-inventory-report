# Tests for the end-of-run console summary (report/summary.py), counted from
# the stored results.
from report import summary
from tests import conftest as c


def test_the_end_of_run_summary_prints_the_runs_counts(conn, capsys):
    # A rifle in two copies, one a wishlist covers; a set past its cap of 1;
    # an exotic, outside any set; a DIM tag and note. No true duplicate, so
    # that line is left out. The live vault's 52 sets were printed as 131,
    # each exotic's name counted as a set.
    c.add_weapon_def(conn, 100)
    for instance_id, covered in (('w1', 1), ('w2', 0)):
        c.add_copy(conn, instance_id, 100, c.WEAPON_SOCKETS)
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, ?)", (instance_id, covered))
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'a1', {'health': 30}, set_name='Test Set', score=90)
    c.add_armor(conn, 'a2', {'health': 25}, set_name='Test Set', score=75)
    c.add_armor(conn, 'e1', {'melee': 30}, set_name='', name='Test Vest', exotic=True)
    with conn:
        conn.execute("INSERT INTO item_dim VALUES ('w1', 'keep', 'god roll')")
    summary.print_summary(conn)
    lines = capsys.readouterr().out.splitlines()
    for line in (
        '  - 1 weapon to review: more than one copy each',
        '  - 1 weapon copy covered by a wishlist',
        '  - 1 armor set in vault',
        '  - 1 armor piece to purge',
        '  - DIM: 1 tagged item, 1 with notes',
    ):
        assert line in lines
    assert not any('true duplicate' in line for line in lines)
