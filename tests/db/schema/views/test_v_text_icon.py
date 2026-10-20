# Tests for v_text_icon (db/schema/views/v_text_icon.sql): the icon for each
# inline token in Bungie's text that names a damage type, a champion breaker
# type or an ability stat.


def test_tokens_with_an_icon_get_its_url(conn):
    # A button prompt such as [Light Attack] has none, and neither does a
    # damage type without an icon.
    with conn:
        conn.execute("UPDATE DestinyDamageTypeDefinition SET icon = '/arc.png' WHERE name = 'Arc'")
        conn.execute(
            "INSERT INTO DestinyBreakerTypeDefinition VALUES (1, 'Shield Piercing', '/sp.png')"
        )
        conn.execute("UPDATE DestinyStatDefinition SET name = 'Grenade' WHERE name = 'grenade'")
    icons = dict(conn.execute("SELECT token, icon FROM v_text_icon").fetchall())
    assert icons['[Arc]'] == 'https://www.bungie.net/arc.png'
    assert icons['[Shield-Piercing]'] == 'https://www.bungie.net/sp.png'
    assert icons['[Grenade]'] == 'https://www.bungie.net/img/grenade.png'
    assert '[Light Attack]' not in icons and '[Void]' not in icons
