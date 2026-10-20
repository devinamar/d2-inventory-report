# Tests for the report's Preferences page (report/templates/preferences.html.j2):
# everything the app stores from the player, in collapsible sections.
from tests import conftest as c


def test_each_set_shows_with_its_badge_and_the_wishlists_are_listed(conn, tmp_path):
    # A set's badge is its helmet; its tooltip lists the set's bonuses.
    c.add_preference(conn, 'Test Set', 'F', rank=1, stats=('health',))
    c.add_armor(conn, 'a1', {'health': 30}, set_name='Test Set', score=90)
    set_hash = conn.execute(
        "SELECT hash FROM DestinyEquipableItemSetDefinition WHERE name = 'Test Set'"
    ).fetchone()[0]
    with conn:
        conn.execute(
            "UPDATE DestinyInventoryItemDefinition SET icon = '/helm.png' "
            "WHERE equipableItemSetHash = ?",
            (set_hash,),
        )
        conn.execute("INSERT INTO DestinySandboxPerkDefinition VALUES (1, 'Two Up', 'Helps.', '')")
        conn.execute("INSERT INTO DestinyItemSetPerkDefinition VALUES (?, 0, 2, 1)", (set_hash,))
        conn.execute(
            "INSERT INTO wishlist_preference VALUES ('mine', 'Mine', 'https://example.com/w/mine.txt')"
        )
    html, _ = c.write_report(conn, tmp_path)
    page = c.report_page(html, 'preferences')
    assert 'Test Set</span></th>' in page and '<details class="fold">' in page
    assert f'data-tip="set-{set_hash}"><img src="https://www.bungie.net/helm.png"' in page
    assert f'<div id="tip-set-{set_hash}"><b>2-piece: Two Up</b><p>Helps.</p></div>' in page
    assert (
        'href="https://example.com/w/mine.txt" title="https://example.com/w/mine.txt">mine.txt</a>'
    ) in page
