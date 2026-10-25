# Tests for v_plug (db/schema/views/v_plug.sql): each stored plug as the app
# shows it, the kind of weapon perk socket its category fills, and what the
# weapon calls that socket.
import pytest


def test_plug_text_as_written_and_its_icon_as_a_url(conn):
    # Bungie's inline tokens stay in the text.
    text = '[Light Attack]  : [Stagger] Powered [Arc] melee\n\nheal you.'
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition "
            "(hash, name, description, icon, plugCategoryIdentifier) VALUES (?, ?, ?, ?, ?)",
            (9001, 'Test', text, '/t.png', 'frames'),
        )
    row = conn.execute("SELECT icon, description FROM v_plug WHERE hash = 9001").fetchone()
    assert tuple(row) == ('https://www.bungie.net/t.png', text)


@pytest.mark.parametrize(
    'category, kind, label',
    [
        # The first perk column, under each name a weapon type gives it.
        ('barrels', 'barrel', 'Barrel'),
        ('scopes', 'barrel', 'Scope'),
        ('tubes', 'barrel', 'Tube'),
        ('bowstrings', 'barrel', 'String'),
        ('blades', 'barrel', 'Blade'),
        ('hafts', 'barrel', 'Haft'),
        # The second perk column, likewise.
        ('magazines', 'magazine', 'Magazine'),
        ('batteries', 'magazine', 'Battery'),
        ('arrows', 'magazine', 'Arrow'),
        ('guards', 'magazine', 'Guard'),
        ('magazines_gl', 'magazine', 'Magazine'),
        ('stocks', 'stock', 'Stock'),
        ('grips', 'grip', 'Grip'),
        ('frames', 'trait', 'Trait'),
        ('origins', 'origin', 'Origin'),
        ('intrinsics', 'intrinsic', 'Frame'),
        # Plugs that aren't weapon perks.
        ('v400.plugs.weapons.masterworks.trackers', None, None),
        ('shader', None, None),
    ],
)
def test_plug_kind_and_label_come_from_its_category(conn, category, kind, label):
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition (hash, name, plugCategoryIdentifier) "
            "VALUES (9101, 'Plug', ?)",
            (category,),
        )
    row = conn.execute("SELECT kind, label FROM v_plug WHERE hash = 9101").fetchone()
    assert tuple(row) == (kind, label)
