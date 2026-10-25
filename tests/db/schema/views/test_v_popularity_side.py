# Tests for v_popularity_side (db/schema/views/v_popularity_side.sql): the
# two sides, each with its Endgame badge's icon and its hard content.
from tests import conftest as c


def test_each_side_has_its_activity_modes_icon_and_its_hard_content(conn):
    # Raid (mode 4) badges PvE and Trials of Osiris (84) PvP; the hard
    # categories keep the published order, the others are left out.
    with conn:
        conn.executemany(
            "INSERT INTO DestinyActivityModeDefinition VALUES (?, ?, ?, ?)",
            [(1, 4, 'Raid', '/raid.png'), (2, 84, 'Trials of Osiris', '/trials.png')],
        )
    c.add_popularity_file(
        conn,
        [
            ('raid_master', 'Master raid', 'pve', True),
            ('raid', 'Raid', 'pve', False),
            ('gm', 'Grandmaster Vanguard Alert', 'pve', True),
            ('trials', 'Trials of Osiris', 'pvp', True),
        ],
    )
    rows = conn.execute("SELECT side, label, icon, hard FROM v_popularity_side").fetchall()
    assert [tuple(r) for r in rows] == [
        (
            'pve',
            'PvE',
            'https://www.bungie.net/raid.png',
            'Master raid, Grandmaster Vanguard Alert',
        ),
        ('pvp', 'PvP', 'https://www.bungie.net/trials.png', 'Trials of Osiris'),
    ]
