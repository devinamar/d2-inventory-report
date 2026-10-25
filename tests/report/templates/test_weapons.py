# Tests for the report's Weapons page (report/templates/weapons.html.j2): Roll
# Quality's sections, its cards (one per scored weapon, else per family) with
# their headers, switches and pickers, and each copy's entry: its places and
# scores per side, wishlists, trash, RPM, season, drop source and kills.
from sources.bungie import api_mappings
from tests import conftest as c

RPM = next(h for h, key in api_mappings.STAT_KEYS.items() if key == 'rpm')


def rifle_copies(conn, perks=(c.TRAIT_PERK_A, c.TRAIT_PERK_A), match_count=0):
    # Copies of the Test Rifle (100), w1, w2, ..., one per trait perk, with
    # their weapon_result rows.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    for n, perk in enumerate(perks, 1):
        c.add_copy(conn, f'w{n}', 100, [c.INTRINSIC_ADAPTIVE, perk], gear_tier=5)
        with conn:
            conn.execute(
                "INSERT INTO weapon_result VALUES (?, ?, ?)", (f'w{n}', match_count, match_count)
            )


def score_rifle(conn, **kwargs):
    # d2-perk-popularity scores the Test Rifle on PvE: Kill Clip on 70% of its
    # trait column's votes, Rampage on 30% (medium confidence).
    c.add_popularity(
        conn,
        'Test Rifle',
        [100],
        columns=[c.popularity_column('trait1', [('Kill Clip', 0.7), ('Rampage', 0.3)])],
        **kwargs,
    )


def add_my_list(conn, url='https://example.com/w/mine.txt'):
    # The player's own wishlist, the fourth after the three defaults.
    with conn:
        conn.execute("INSERT INTO wishlist_preference VALUES ('mine', 'Mine', ?)", (url,))


def add_roll(conn, roll_id, source_key, perk, is_trash=0):
    # A roll of source_key's for the Test Rifle naming perk (none for a roll
    # naming no perks), its source stored first.
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO wishlist_source (key, label, url) VALUES (?, ?, '')",
            (source_key, source_key),
        )
        conn.execute(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1, is_trash) "
            "VALUES (?, ?, 100, ?, ?)",
            (roll_id, source_key, perk, is_trash),
        )


def weapons_page(conn, folder):
    html, _ = c.write_report(conn, folder)
    return c.report_page(html, 'weapons')


def entry(page, k):
    # Copy k's picker entry.
    return page.split(f'<div class="pr" data-k="{k}"')[1].split('</button>\n<button')[0]


def test_roll_quality_groups_the_cards_by_slot_and_weapon_type(conn, tmp_path):
    # Each section counts its cards and opens them all by the double chevron
    # leading it; a card, closed at first, opens by its name on its picker and
    # the grid it clones (data-g). The Popularity switch leads the page's.
    rifle_copies(conn)
    page = weapons_page(conn, tmp_path)
    assert '<h3>Kinetic <span class="num count">1</span></h3></summary>' in page
    assert '<summary><button type="button" class="expand" aria-expanded="false"' in page
    assert 'aria-controls="fam-100"' in page and 'id="fam-100" hidden' in page
    assert '<div class="picker" role="radiogroup" aria-label="Test Rifle copies">' in page
    assert '<div class="rp-main" data-g="100"></div>' in page
    assert '<span class="copy-count">2 copies</span>' in page
    assert 'href="https://www.light.gg/db/items/100/"' in page
    assert '<div class="switch side" role="group" aria-label="Popularity">' in page


def test_a_family_whose_versions_roll_different_pools_is_a_card_per_pool(conn, tmp_path):
    # Gun (Pantheon) is the scored weapon for version 100; version 101, which
    # no scored weapon lists, makes a card of the family. Each card's title is
    # the family's, the pool on its own line.
    c.add_weapon_def(conn, 100, name='Gun')
    c.add_weapon_def(conn, 101, name='Gun')
    c.add_popularity(conn, 'Gun (Pantheon)', [100], family='Gun')
    for instance_id, item_hash in (('a', 100), ('b', 101)):
        c.add_copy(conn, instance_id, item_hash)
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    page = weapons_page(conn, tmp_path)
    assert 'aria-label="Gun (Pantheon)">' in page and 'aria-label="Gun">' in page
    assert '<span class="fam-title">Gun</span><span class="fam-pool">(Pantheon)</span>' in page
    assert page.count('<span class="copy-count">1 copy</span>') == 2


def test_a_cards_header_gives_each_sides_rank_confidence_and_endgame(conn, tmp_path):
    # Scored on PvE only: its rank on the PvE button, a dash on PvP's; the
    # PvE chip in medium's heat, PvP's saying it has no scores; the Endgame
    # badge (60 of its 100 copies from hard content) under its name.
    rifle_copies(conn)
    score_rifle(conn, rank=3, hard_copies=60)
    page = weapons_page(conn, tmp_path)
    assert (
        '<button type="button" class="side-pve" data-value="pve" aria-pressed="true">'
        'PvE <span class="num">#3</span></button>'
    ) in page
    assert 'aria-pressed="false">PvP <span class="num">—</span></button>' in page
    assert (
        '<span class="pop-chip heat-mid on-pve" tabindex="0" data-tip="c-pve-100">'
        'Medium confidence</span>'
    ) in page
    assert '<span class="pop-chip on-pvp">No PvP scores</span>' in page
    assert '</h5>\n<span class="endgame"><span class="cert pve" tabindex="0"' in page


def test_the_picker_gives_each_copy_its_place_and_score_on_each_side(conn, tmp_path):
    # w2's Kill Clip is the trait column's favourite (100%, full heat), w1's
    # Rampage 30% against its 70% (43%): w2 leads PvE. PvP has no scores, so
    # no percentage, and the copies keep their instance order there.
    rifle_copies(conn, perks=(c.TRAIT_PERK_A, c.TRAIT_PERK_B))
    score_rifle(conn)
    page = weapons_page(conn, tmp_path)
    assert page.index('<div class="pr" data-k="2" data-r="1 2">') < page.index(
        '<div class="pr" data-k="1" data-r="2 1">'
    )
    assert (
        '<span class="copy-n on-pve keep">#1</span><span class="pr-pop on-pve c10">100%</span>'
        '<span class="copy-n on-pvp">#2</span><span class="pr-id">w2</span>'
    ) in entry(page, 2)
    assert (
        '<span class="copy-n on-pve">#2</span><span class="pr-pop on-pve c4">43%</span>'
        '<span class="copy-n on-pvp keep">#1</span><span class="pr-id">w1</span>'
    ) in entry(page, 1)
    assert '<button type="button" class="copy-btn" data-q="w1" title="Copy id w1"' in page


def test_a_copys_entry_names_the_lists_it_matches_as_the_wishlist_switch_shows(conn, tmp_path):
    # Voltron (the first list) has a Rampage roll, which w1 completes; Mine has
    # a Kill Clip roll, which no copy does. Each line answers the lists it
    # holds for: w1's Voltron under All lists and Voltron, its No wishlist
    # match under Mine, and Missing wishlist entries under the Aegis lists.
    rifle_copies(conn, perks=(c.TRAIT_PERK_A, c.TRAIT_PERK_C), match_count=1)
    add_my_list(conn)
    add_roll(conn, 1, 'voltron', c.TRAIT_PERK_A)
    add_roll(conn, 2, 'mine', c.TRAIT_PERK_B)
    with conn:
        conn.execute("INSERT INTO instance_wishlist_match VALUES ('w1', 1)")
    page = weapons_page(conn, tmp_path)
    w1, w2 = entry(page, 1), entry(page, 2)
    assert (
        '<span data-wl="* voltron"><i class="wl-dot l1" aria-hidden="true"></i>'
        'Voltron (Pandapaxxy/Mercules +trash)</span>'
    ) in w1
    assert '<span class="none" data-wl="mine" hidden>No wishlist match</span>' in w1
    assert '<span class="none" data-wl="* voltron mine">No wishlist match</span>' in w2
    assert (
        '<span class="none" data-wl="aegis_endgame aegis_shopping" hidden>'
        'Missing wishlist entries</span>'
    ) in w1
    assert (
        '<article class="card fam" data-side="pve" data-wpn="all dupes listed-* listed-voltron '
        'listed-mine">'
    ) in page
    assert '<i class="wl-dot l4" aria-hidden="true"></i>Mine</button>' in page


def test_a_weapon_no_list_covers_says_so(conn, tmp_path):
    # Dupes shows the rifle, Has wishlist doesn't; each copy is missing
    # entries in every view.
    rifle_copies(conn)
    page = weapons_page(conn, tmp_path)
    assert '<article class="card fam" data-side="pve" data-wpn="all dupes">' in page
    assert (
        '<span class="none" data-wl="* voltron aegis_endgame aegis_shopping">'
        'Missing wishlist entries</span>'
    ) in entry(page, 1)


def test_a_copy_a_list_trashes_says_so(conn, tmp_path):
    # Like Voltron's 50 lines trashing a whole weapon (item=-<hash>), which
    # fit every copy; none names a weapon in the live vault today. All lists
    # names every list trashing it, the list's own view just it.
    rifle_copies(conn)
    add_roll(conn, 1, 'voltron', None, is_trash=1)
    with conn:
        conn.executemany("INSERT INTO instance_wishlist_match VALUES (?, 1)", [('w1',), ('w2',)])
    page = weapons_page(conn, tmp_path)
    label = 'Voltron (Pandapaxxy/Mercules +trash)'
    assert page.count(f'<span class="trash" data-wl="*">Trash in {label}</span>') == 2
    assert page.count(f'<span class="trash" data-wl="voltron" hidden>Trash in {label}</span>') == 2


def test_a_card_shows_its_rpm_season_and_source_or_each_copys_when_they_differ(conn, tmp_path):
    # The Test Rifle's copies are Monument of Triumph drops (v970.core, as 151
    # of the live vault's copies are) from the Exotic Archive, at 140 RPM, so
    # its card names them once: the season and source under its name, the RPM
    # under its element and frame. A Sudden Death's copies are an Episode:
    # Heresy drop and a Lawless reissue (its own item hash), here at different
    # RPM too, as Hawthorne's Field-Forged Shotgun's are (80 and 95): each
    # copy names its own.
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
        '<span class="rpm">RPM: 80</span>',
        'S26 Episode: Heresy',
    ):
        assert page.count(text) == 1


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


def test_a_card_names_its_ammo_by_its_name_and_its_element_then_frame(conn, tmp_path):
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


def test_copies_that_differ_in_element_each_name_theirs(conn, tmp_path):
    # Ergo Sum's copies roll different elements: the header leaves it out and
    # each copy's entry names its own.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    for instance_id, element in (('w1', 3), ('w2', 2)):
        c.add_copy(
            conn, instance_id, 100, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A], damage_type=element
        )
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    page = weapons_page(conn, tmp_path)
    assert '<span class="fam-stats">\n<span class="frame">' in page
    assert '>Solar</span>' in entry(page, 1) and '>Arc</span>' in entry(page, 2)
