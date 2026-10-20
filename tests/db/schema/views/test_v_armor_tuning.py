# Tests for v_armor_tuning (db/schema/views/v_armor_tuning.sql): the stats each
# armor copy's tuning socket can raise.
from tests import conftest as c


def test_tuning_lists_the_stats_the_tuning_socket_can_raise(conn):
    # One row per stat a +5 tuning mod raises; Balanced Tuning (+1s) adds none,
    # and a copy without tuning plugs has no rows.
    c.add_armor_def(conn, 200, sockets=[c.TUNING_BALANCED])
    options = {
        'legendary': [c.TUNING_BALANCED, c.TUNING_HEALTH],
        'exotic': [c.TUNING_BALANCED, c.TUNING_HEALTH, c.TUNING_MELEE],
    }
    for instance_id, plugs in options.items():
        c.add_copy(conn, instance_id, 200, [c.TUNING_BALANCED], {0: plugs})
    c.add_copy(conn, 'untuned', 200, [c.TUNING_BALANCED])
    rows = conn.execute(
        "SELECT instance_id, stat FROM v_armor_tuning ORDER BY instance_id, stat"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ('exotic', 'health'),
        ('exotic', 'melee'),
        ('legendary', 'health'),
    ]
