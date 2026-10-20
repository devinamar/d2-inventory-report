# Tests for the report's Weapons page (report/templates/weapons.html.j2): Roll
# Quality's sections, family cards and switches, the wishlists' colours, the
# perks' icons, and each weapon's RPM, season, drop source, kills and trash.
from sources.bungie import api_mappings
from tests import conftest as c

RPM = next(h for h, key in api_mappings.STAT_KEYS.items() if key == 'rpm')


def rifle_copies(conn, reusable=None, has_wishlist=0):
    # Two copies of the Test Rifle (100), with their weapon_result rows.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    for instance_id in ('w1', 'w2'):
        c.add_copy(
            conn,
            instance_id,
            100,
            [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A],
            reusable,
            gear_tier=5,
        )
        with conn:
            conn.execute(
                "INSERT INTO weapon_result VALUES (?, ?, ?)",
                (instance_id, has_wishlist, has_wishlist),
            )


def add_my_list(conn, url='https://example.com/w/mine.txt'):
    # The player's own wishlist, the fourth after the three defaults.
    with conn:
        conn.execute("INSERT INTO wishlist_preference VALUES ('mine', 'Mine', ?)", (url,))


def weapons_page(conn, folder):
    html, _ = c.write_report(conn, folder)
    return c.report_page(html, 'weapons')


def test_roll_quality_groups_the_families_by_slot_and_weapon_type(conn, tmp_path):
    # Each section counts its families and opens them all by the double
    # chevron leading it; a family card, closed at first, opens by its name.
    rifle_copies(conn)
    page = weapons_page(conn, tmp_path)
    assert '<h3>Kinetic <span class="num count">1</span></h3></summary>' in page
    assert '<summary><button type="button" class="expand" aria-expanded="false"' in page
    assert 'aria-controls="fam-w1"' in page and 'id="fam-w1" hidden' in page
    assert 'Test Rifle' in page and '<span class="copy-count">2 copies</span>' in page
    assert 'href="https://www.light.gg/db/items/100/"' in page
    assert 'data-q="w1" title="Copy id w1">w1</button>' in page


def test_a_weapon_no_list_covers_says_so(conn, tmp_path):
    # Dupes shows the rifle, Has wishlist doesn't; its All lists table says
    # it's missing entries, and each list's button shows the note in its place.
    rifle_copies(conn)
    add_my_list(conn)
    page = weapons_page(conn, tmp_path)
    assert '<article class="card fam" data-wpn="all dupes">' in page
    assert (
        '<button type="button" data-value="listed" aria-pressed="false">Has wishlist</button>'
    ) in page
    assert '<button type="button" data-value="*" aria-pressed="true">All lists</button>' in page
    assert '<td colspan="3">Missing wishlist entries.</td>' in page
    assert 'data-wl="voltron aegis_endgame aegis_shopping mine" hidden>' in page


def test_each_list_wears_its_colour(conn, tmp_path):
    # The fourth list's button and rings take the fourth colour.
    rifle_copies(conn)
    add_my_list(conn)
    page = weapons_page(conn, tmp_path)
    assert '<i class="wl-dot l4" aria-hidden="true"></i>Mine</button>' in page
    assert '.l4 { --tint: var(--wl4);' in page


def test_a_perk_shows_its_icon_named_in_its_alt_text_and_tooltip(conn, tmp_path):
    rifle_copies(conn)
    page = weapons_page(conn, tmp_path)
    assert 'alt="Rampage"' in page and '<b>Rampage</b>' in page


def test_roll_quality_cards_name_the_lists_with_rolls_for_them(conn, tmp_path):
    # A rifle the player's own list has a roll for: Has wishlist shows its card
    # under All lists and under that list, not under the default lists.
    rifle_copies(conn, reusable={1: [c.TRAIT_PERK_A]}, has_wishlist=1)
    add_my_list(conn, url='')
    with conn:
        conn.execute("INSERT INTO wishlist_source (key, label, url) VALUES ('mine', 'Mine', '')")
        conn.execute(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1) "
            "VALUES (1, 'mine', 100, ?)",
            (c.TRAIT_PERK_A,),
        )
    page = weapons_page(conn, tmp_path)
    assert '<article class="card fam" data-wpn="all dupes listed-* listed-mine">' in page


def test_a_family_shows_its_rpm_season_and_source_or_each_copys_when_they_differ(conn, tmp_path):
    # The Test Rifle's copies are Monument of Triumph drops (v970.core, as 151
    # of the live vault's copies are) from the Exotic Archive, at 140 RPM, so
    # its card names them once: the season and source under its name, the RPM
    # under its element and frame. A Sudden Death's
    # copies are an Episode: Heresy drop and a Lawless reissue (its own item
    # hash), here at different RPM too, as Hawthorne's Field-Forged Shotgun's
    # are (80 and 95): each copy names its own.
    with conn:
        conn.execute(
            "INSERT INTO DestinyCollectibleDefinition VALUES (9, ?)",
            ('Source: Exotic Archive at the Tower',),
        )
    c.add_weapon_def(conn, 100, traitIds='["releases.v970.core"]', collectibleHash=9)
    c.add_weapon_def(conn, 200, 'A Sudden Death', traitIds='["releases.v820.season"]')
    c.add_weapon_def(conn, 201, 'A Sudden Death', traitIds='["releases.v950.core"]')
    copies = (('w1', 100, 140), ('w2', 100, 140), ('s1', 200, 80), ('s2', 201, 95))
    for instance_id, item_hash, rpm in copies:
        c.add_copy(conn, instance_id, item_hash, c.WEAPON_SOCKETS, stats={RPM: rpm})
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    page = weapons_page(conn, tmp_path)
    assert (
        '<span class="fam-name"><span class="fam-title">Test Rifle</span><span class="origin">'
        '<span title="Released 2025-12-02">S28 Monument of Triumph</span>'
        '<span>Source: Exotic Archive at the Tower</span></span></span>'
    ) in page
    assert '<span class="rpm">RPM: 140</span>\n</span>' in page
    for text in (
        'RPM: 140',
        'S28 Monument of Triumph',
        '<span>RPM: 80</span>',
        'S26 Episode: Heresy',
    ):
        assert page.count(text) == 1


def test_a_copy_a_list_trashes_says_so(conn, tmp_path):
    # Like Voltron's 50 lines trashing a whole weapon (item=-<hash>), which
    # fit every copy; none names a weapon in the live vault today.
    rifle_copies(conn)
    with conn:
        conn.execute("INSERT INTO wishlist_source (key, label, url) VALUES ('voltron', 'V', '')")
        conn.execute(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, is_trash) "
            "VALUES (1, 'voltron', 100, 1)"
        )
        conn.executemany("INSERT INTO instance_wishlist_match VALUES (?, 1)", [('w1',), ('w2',)])
    page = weapons_page(conn, tmp_path)
    label = 'Voltron (Pandapaxxy/Mercules +trash)'
    assert page.count(f'<span class="trash">Trash in {label}</span>') == 2


def test_each_copy_shows_its_plugged_trackers_kills_as_dim_does(conn, tmp_path):
    # The count of the tracker plugged into the tracker socket, behind the
    # badge of what it counts. w1's Kill Tracker is plugged, so its Crucible
    # Tracker's 28 doesn't show; w2's Crucible Tracker is plugged, as on one of
    # the live vault's exotics.
    c.add_weapon_def(conn, 100)
    objectives = {
        c.KILL_TRACKER: [(c.ENEMIES_DEFEATED, 1745)],
        c.CRUCIBLE_TRACKER: [(c.OPPONENTS_DEFEATED, 28)],
    }
    for instance_id, plugged in (('w1', c.KILL_TRACKER), ('w2', c.CRUCIBLE_TRACKER)):
        c.add_copy(conn, instance_id, 100, [*c.WEAPON_SOCKETS, plugged], objectives=objectives)
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    page = weapons_page(conn, tmp_path)
    badges = 'https://www.bungie.net/common/destiny2_content/icons/'
    assert (
        '<span class="kill" title="PvE kills (Kill Tracker)">'
        f'<img src="{badges}31c848643d47d317a9b971214a988d22.png" alt="PvE" loading="lazy">1,745'
        '</span>'
    ) in page
    assert (
        '<span class="kill" title="PvP kills (Crucible Tracker)">'
        f'<img src="{badges}66317c523dd68205dcc753c7563d5068.png" alt="PvP" loading="lazy">28'
        '</span>'
    ) in page
    assert page.count('<span class="kill"') == 2


def test_a_family_names_its_ammo_by_its_name_and_its_element_then_frame(conn, tmp_path):
    # Luna's Howl's header: its primary ammo badge right after its name; Solar,
    # then Precision Frame with its icon, stacked beside it.
    c.add_weapon_def(conn, 100, ammoType=1, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    for instance_id in ('w1', 'w2'):
        c.add_copy(conn, instance_id, 100, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A], damage_type=3)
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    page = weapons_page(conn, tmp_path)
    assert (
        'Test Rifle<img class="ammo" '
        'src="https://www.bungie.net/img/destiny_content/ammo_types/primary.png" '
        'alt="Primary ammo" title="Primary ammo" loading="lazy"></span>'
    ) in page
    assert '<span class="fam-stats">\n<span class="element">' in page
    assert (
        '<span class="frame"><img src="https://www.bungie.net/img/adaptive.png" alt="" '
        'loading="lazy">Adaptive Frame</span>'
    ) in page


def test_a_familys_table_sorts_by_score_and_element(conn, tmp_path):
    # Score is the active sort at first; Element, a column only when copies
    # differ in element, as Ergo Sum's do, sorts too. Each copy row carries
    # what report.js sorts it by.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    for instance_id, element in (('w1', 3), ('w2', 2)):
        c.add_copy(
            conn, instance_id, 100, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A], damage_type=element
        )
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    page = weapons_page(conn, tmp_path)
    assert (
        '<th scope="col" aria-sort="descending"><button type="button" class="sort on" '
        'data-sort="score" title="Sort by score">Score<svg'
    ) in page
    assert (
        '<th scope="col" aria-sort="none"><button type="button" class="sort" '
        'data-sort="element" title="Sort by element">Element<svg'
    ) in page
    assert '<tr data-n="1" data-id="w1" data-element="Solar" data-score="-1">' in page
    assert '<tr data-n="2" data-id="w2" data-element="Arc" data-score="-1">' in page
