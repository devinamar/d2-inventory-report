# Tests for v_plug (db/schema/views/v_plug.sql): each stored plug as the app
# shows it, and the kind of weapon perk socket its category fills.
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
    'category, kind',
    [
        # The first perk column, under each name a weapon type gives it.
        ('barrels', 'barrel'),
        ('scopes', 'barrel'),
        ('tubes', 'barrel'),
        ('bowstrings', 'barrel'),
        ('blades', 'barrel'),
        ('hafts', 'barrel'),
        # The second perk column, likewise.
        ('magazines', 'magazine'),
        ('batteries', 'magazine'),
        ('arrows', 'magazine'),
        ('guards', 'magazine'),
        ('magazines_gl', 'magazine'),
        ('stocks', 'stock'),
        ('grips', 'grip'),
        ('frames', 'trait'),
        ('origins', 'origin'),
        ('intrinsics', 'intrinsic'),
        # Plugs that aren't weapon perks.
        ('v400.plugs.weapons.masterworks.trackers', None),
        ('shader', None),
    ],
)
def test_plug_kind_comes_from_its_category(conn, category, kind):
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition (hash, name, plugCategoryIdentifier) "
            "VALUES (9101, 'Plug', ?)",
            (category,),
        )
    assert conn.execute("SELECT kind FROM v_plug WHERE hash = 9101").fetchone()[0] == kind
