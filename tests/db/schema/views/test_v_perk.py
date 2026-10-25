# Tests for v_perk (db/schema/views/v_perk.sql): one row per weapon perk name,
# with the plug that stands for the name, its icon and its text.


def test_a_perk_name_is_one_row_standing_on_its_noted_plug(conn):
    # Rampage's enhanced plug shares the name and has Clarity's note, so it
    # stands for the name; Kill Clip has no note, so its lowest hash does, with
    # Bungie's text. The masterwork isn't a perk.
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition "
            "(hash, name, description, icon, plugCategoryIdentifier) "
            "VALUES (9002, 'Rampage', 'Enhanced.', '/e.png', 'frames')"
        )
        conn.execute("INSERT INTO clarity_note VALUES (9002, 'Stacks three times.')")
    rows = conn.execute(
        "SELECT perk, plug_hash, icon, text FROM v_perk "
        "WHERE perk IN ('Rampage', 'Kill Clip', 'Masterwork') ORDER BY perk"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (
            'Kill Clip',
            1002,
            'https://www.bungie.net/img/killclip.png',
            'Reloading after a kill grants bonus damage.',
        ),
        ('Rampage', 9002, 'https://www.bungie.net/e.png', 'Stacks three times.'),
    ]
