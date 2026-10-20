# Tests for v_kill_tracker (db/schema/views/v_kill_tracker.sql): the kill
# trackers on each weapon copy and the count each keeps.
from tests import conftest as c


def test_kill_tracker_counts_each_tracker_and_marks_the_plugged_one(conn):
    # Each tracker with what it counts, as DIM reads its objective, and the
    # objective's badge. The origin perk's objective isn't a tracker's, so it's
    # left out.
    c.add_weapon_def(conn, 100)
    objectives = {
        c.KILL_TRACKER: [(c.ENEMIES_DEFEATED, 46)],
        c.CRUCIBLE_TRACKER: [(c.OPPONENTS_DEFEATED, 12)],
        c.ORIGIN_PERK: [(c.ENEMIES_DEFEATED, 5)],
    }
    c.add_copy(conn, 'w1', 100, [*c.WEAPON_SOCKETS, c.KILL_TRACKER], objectives=objectives)
    rows = conn.execute(
        "SELECT tracker, kind, description, kills, is_plugged, icon FROM v_kill_tracker "
        "WHERE instance_id = 'w1' ORDER BY tracker"
    ).fetchall()
    icons = 'https://www.bungie.net/common/destiny2_content/icons/'
    assert [tuple(r) for r in rows] == [
        (
            'Crucible Tracker',
            'PvP',
            'Crucible Opponents Defeated',
            12,
            0,
            icons + '66317c523dd68205dcc753c7563d5068.png',
        ),
        (
            'Kill Tracker',
            'PvE',
            'Enemies Defeated',
            46,
            1,
            icons + '31c848643d47d317a9b971214a988d22.png',
        ),
    ]
