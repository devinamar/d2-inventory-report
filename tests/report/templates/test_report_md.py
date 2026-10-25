# Tests for the report's Markdown copy (report/templates/report.md.j2), written
# so an LLM can review the analysis: every section explains itself, and the
# lists match the HTML's.
from sources.bungie import api_mappings
from tests import conftest as c

RPM = next(h for h, key in api_mappings.STAT_KEYS.items() if key == 'rpm')


def vault(conn):
    # Two rifle copies; a set past its cap of 1 with one piece kept for a
    # build; a set with nothing flagged, which only the Markdown lists; a
    # duplicated exotic; and the player's own wishlist.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    c.add_popularity(
        conn,
        'Test Rifle',
        [100],
        players=120,
        hard_copies=60,
        columns=[
            c.popularity_column('barrel', [('Fluted Barrel', 0.6)], n_eff=110.0),
            c.popularity_column('traits', [('Rampage + Outlaw', 0.5)], n_eff=40.0),
            c.popularity_column('trait1', [('Rampage', 0.7)], n_eff=40.0),
        ],
    )
    for instance_id in ('w1', 'w2'):
        c.add_copy(conn, instance_id, 100, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A], gear_tier=5)
        with conn:
            conn.execute("INSERT INTO weapon_result VALUES (?, 0, 0)", (instance_id,))
    c.add_preference(conn, 'Test Set', 'F', rank=1, stats=('health',))
    c.add_armor(conn, 'a1', {'health': 30}, set_name='Test Set', score=90)
    c.add_armor(conn, 'a2', {'health': 25}, set_name='Test Set', tuning=('melee',), score=75)
    c.add_armor(conn, 'a4', {'melee': 20}, set_name='Test Set', tuning=('melee',), score=60)
    c.add_armor(conn, 'k1', {'grenade': 30}, set_name='Kept Set', slot='Gauntlets', score=90)
    c.add_armor(conn, 'e1', {'melee': 30}, exotic=True, name='Test Exotic', score=80)
    c.add_armor(conn, 'e2', {'melee': 20}, exotic=True, name='Test Exotic', score=60)
    with conn:
        conn.execute("INSERT INTO armor_rescue VALUES ('a4', 'health', 'melee', 'grenade', 100)")
        conn.execute(
            "INSERT INTO wishlist_preference VALUES ('mine', 'Mine', 'https://example.com/w/mine.txt')"
        )


def test_every_section_explains_itself(conn, tmp_path):
    # Summary, Data sources, True duplicates, Roll Quality, Popular, Armor
    # sets, Builds, Exotics and Preferences each say what they show, how it
    # was derived and how to read it.
    vault(conn)
    _, md = c.write_report(conn, tmp_path)
    assert md.startswith('# Name#1234: Destiny 2 Inventory Report')
    for heading in ('**What this shows.**', '**How it was derived.**', '**Reading it.**'):
        assert md.count(heading) == 9


def test_popular_lists_every_scored_weapon_with_its_picks_and_pairs(conn, tmp_path):
    # The Test Rifle's weakest column (its traits, 40 votes) makes it medium;
    # 60 of its 120 copies came from hard content, so it is an Endgame pick.
    vault(conn)
    _, md = c.write_report(conn, tmp_path)
    assert '### PvE (1 weapons)' in md
    assert (
        '| 1 | Test Rifle | Auto Rifle | 120 | medium | yes | Barrel Fluted Barrel 60% · '
        'Trait 1 Rampage 70% | Rampage + Outlaw 50% |'
    ) in md


def test_the_lists_cover_copies_purges_sets_and_preferences(conn, tmp_path):
    vault(conn)
    _, md = c.write_report(conn, tmp_path)
    assert (
        '1. `id:w1`: gear tier 5, missing wishlist entries, not locked\n   - Trait: Rampage\n'
    ) in md
    assert 'Purge `id:e2`' in md
    assert '#### Kept Set' in md
    assert '| F | Test Set | health ×3 |' in md
    assert '| Mine | mine | https://example.com/w/mine.txt |' in md


def test_a_family_names_its_rpm_season_and_source_and_each_copys_kills_and_trash(conn, tmp_path):
    with conn:
        conn.execute(
            "INSERT INTO DestinyCollectibleDefinition VALUES (9, ?)",
            ('Source: Exotic Archive at the Tower',),
        )
    c.add_weapon_def(conn, 100, traitIds='["releases.v970.core"]', collectibleHash=9, ammoType=1)
    for instance_id in ('w1', 'w2'):
        c.add_copy(
            conn,
            instance_id,
            100,
            [*c.WEAPON_SOCKETS, c.KILL_TRACKER],
            stats={RPM: 140},
            objectives={c.KILL_TRACKER: [(c.ENEMIES_DEFEATED, 1745)]},
            gear_tier=5,
        )
    with conn:
        conn.executemany("INSERT INTO weapon_result VALUES (?, 0, 1)", [('w1',), ('w2',)])
        conn.execute("INSERT INTO wishlist_source (key, label, url) VALUES ('voltron', 'V', '')")
        conn.execute(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, is_trash) "
            "VALUES (1, 'voltron', 100, 1)"
        )
        conn.execute("INSERT INTO instance_wishlist_match VALUES ('w1', 1)")
    _, md = c.write_report(conn, tmp_path)
    assert (
        'Auto Rifle, primary ammo, Adaptive Frame, Kinetic, 140 RPM, S28 Monument of Triumph, '
        'Source: Exotic Archive at the Tower. DIM: `'
    ) in md
    assert (
        '1. `id:w1`: gear tier 5, wishlist score 0, '
        'trash in Voltron (Pandapaxxy/Mercules +trash), 1,745 PvE kills, not locked'
    ) in md
    assert '2. `id:w2`: gear tier 5, wishlist score 0, 1,745 PvE kills, not locked' in md
