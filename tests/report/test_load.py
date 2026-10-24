# Tests for the report's queries (report/load.py): each test writes copies and
# saved results with the conftest factories, then checks the rows a page
# shows and their order.
from report import load
from tests import conftest as c

ROLL = {'health': 30, 'melee': 25, 'grenade': 20}


def rows(conn, sql, *columns):
    # The query's rows as tuples of the named columns.
    return [tuple(r[col] for col in columns) for r in conn.execute(sql)]


def add_rifle_copy(
    conn, instance_id, traits, gear_tier, match_count, has_wishlist=1, damage_type=None
):
    # A copy of the Test Rifle (definition 100) whose trait socket can switch
    # to traits, and its weapon_result row.
    c.add_copy(
        conn,
        instance_id,
        100,
        [c.INTRINSIC_ADAPTIVE, traits[0]],
        {1: traits},
        gear_tier=gear_tier,
        damage_type=damage_type,
    )
    with conn:
        conn.execute(
            "INSERT INTO weapon_result VALUES (?, ?, ?)", (instance_id, match_count, has_wishlist)
        )


def add_rifle(conn):
    # The Test Rifle, whose trait socket rolls Kill Clip, Rampage and Outlaw in
    # that order, and Subsistence no longer. Its intrinsic socket rolls too, but
    # no copy can switch it.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    c.add_plug_set(
        conn,
        100,
        1,
        900,
        [(c.TRAIT_PERK_B, 1), (c.TRAIT_PERK_A, 1), (c.TRAIT_PERK_C, 1), (c.TRAIT_PERK_D, 0)],
    )
    c.add_plug_set(conn, 100, 0, 901, [(c.INTRINSIC_ADAPTIVE, 1)], key='reusablePlugSetHash')


def add_lists(conn, rolls, matches):
    # Wishlists One and Two, after the defaults, with rolls for the Test Rifle
    # [(roll_id, list key, perk1, perk2, is_trash)] and the copies' matches
    # [(instance_id, roll_id)].
    with conn:
        for table in ('wishlist_preference', 'wishlist_source'):
            conn.executemany(
                f"INSERT INTO {table} (key, label, url) VALUES (?, ?, '')",
                [('one', 'One'), ('two', 'Two')],
            )
        conn.executemany(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1, perk2, is_trash) "
            "VALUES (?, ?, 100, ?, ?, ?)",
            rolls,
        )
        conn.executemany("INSERT INTO instance_wishlist_match VALUES (?, ?)", matches)


def table(rows, scope):
    # The rows of the scope's table: {n: [(perk, state)]}, slot by slot, a
    # blank as (None, None).
    out = {}
    for r in rows:
        if r['scope'] == scope:
            out.setdefault(r['n'], []).append((r['perk'], r['state']))
    return out


def test_roll_quality_ranks_copies_and_splits_their_scores(conn):
    # Every family with a copy left, by name: the Solo Rifle's one copy, then
    # the Test Rifle's, which rank by wishlist score, so c (Tier 4, score 3)
    # comes first, then by gear tier: a (Tier 5) before b (Tier 4), both
    # scoring 1. A pruned copy is left out. a's matched trash roll doesn't
    # count in its split by list. Only the Test Rifle is to review.
    add_rifle(conn)
    c.add_weapon_def(conn, 200, name='Solo Rifle', sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    add_rifle_copy(conn, 'b', [c.TRAIT_PERK_A, c.TRAIT_PERK_C], 4, 1)
    add_rifle_copy(conn, 'a', [c.TRAIT_PERK_B, c.TRAIT_PERK_D], 5, 1)
    add_rifle_copy(conn, 'c', [c.TRAIT_PERK_A], 4, 3)
    add_rifle_copy(conn, 'pruned', [c.TRAIT_PERK_A], 4, 0)
    c.add_copy(conn, 'solo', 200, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A], {1: [c.TRAIT_PERK_A]})
    with conn:
        conn.execute("INSERT INTO weapon_result VALUES ('solo', 0, 0)")
        conn.execute("INSERT INTO weapon_pruning VALUES ('pruned', 'exact_duplicate', 'c')")
    add_lists(
        conn,
        [(1, 'one', c.TRAIT_PERK_B, None, 0), (2, 'two', c.TRAIT_PERK_D, None, 1)],
        [('a', 1), ('a', 2)],
    )

    assert rows(
        conn, load.ROLL_QUALITY, 'instance_id', 'n', 'copies', 'elements', 'archetypes', 'split'
    ) == [
        ('solo', 1, 1, 1, 1, None),
        ('c', 1, 3, 1, 1, None),
        ('a', 2, 3, 1, 1, '1 One'),
        ('b', 3, 3, 1, 1, None),
    ]
    totals = conn.execute(load.TOTALS).fetchone()
    assert totals['families'] == 1
    assert (totals['matched'], totals['uncovered']) == (3, 1)


def test_roll_cells_line_each_copy_up_under_the_wishlist_picks(conn):
    # One names Kill Clip and Rampage, Two Rampage and Outlaw with Firefly,
    # which the rifle can't roll, so Firefly is no pick; One's Subsistence
    # roll is trash. c and b complete the Rampage rolls, a One's Kill Clip
    # roll; b has Outlaw but not Firefly, so Outlaw is only named for it.
    add_rifle(conn)
    add_rifle_copy(conn, 'c', [c.TRAIT_PERK_A], 5, 2)
    add_rifle_copy(conn, 'b', [c.TRAIT_PERK_A, c.TRAIT_PERK_C], 4, 2)
    add_rifle_copy(conn, 'a', [c.TRAIT_PERK_B, c.TRAIT_PERK_D], 4, 1)
    add_lists(
        conn,
        [
            (1, 'one', c.TRAIT_PERK_B, None, 0),
            (2, 'one', c.TRAIT_PERK_A, None, 0),
            (3, 'two', c.TRAIT_PERK_A, None, 0),
            (4, 'one', c.TRAIT_PERK_D, None, 1),
            (5, 'two', c.TRAIT_PERK_C, c.TRAIT_PERK_E, 0),
        ],
        [('c', 2), ('c', 3), ('b', 2), ('b', 3), ('a', 1), ('a', 4)],
    )
    cells = conn.execute(load.ROLL_CELLS).fetchall()
    blank = (None, None)

    # Both lists have rolls for it: a table for All lists, then one for each.
    assert list(dict.fromkeys((r['scope'], r['shows']) for r in cells)) == [
        ('*', '*'),
        ('one', 'one'),
        ('two', 'two'),
    ]
    # All lists: Rampage, which both name, first; then Kill Clip and Outlaw,
    # one roll each, by name. Each copy's perks sit under the picks they
    # match, its others after them.
    assert table(cells, '*') == {
        0: [('Rampage', 'pick'), ('Kill Clip', 'pick'), ('Outlaw', 'pick')],
        1: [('Rampage', 'hit'), blank, blank],
        2: [('Rampage', 'hit'), blank, ('Outlaw', 'named')],
        3: [blank, ('Kill Clip', 'hit'), blank, ('Subsistence', '')],
    }
    # One list alone: its own picks; a perk only Two names is no pick here.
    assert table(cells, 'one')[2] == [blank, ('Rampage', 'hit'), ('Outlaw', '')]
    assert table(cells, 'two')[3] == [blank, blank, ('Kill Clip', ''), ('Subsistence', '')]
    assert [(r['scope'], r['n'], r['perk']) for r in cells if r['faded']] == [
        ('*', 2, 'Rampage'),
        ('one', 2, 'Rampage'),
        ('two', 2, 'Rampage'),
    ]
    assert [(r['scope'], r['n'], r['perk']) for r in cells if r['gap']] == [
        ('*', 3, 'Subsistence'),
        ('one', 2, 'Outlaw'),
        ('one', 3, 'Subsistence'),
        ('two', 3, 'Kill Clip'),
    ]
    assert {(r['scope'], r['n']): r['score'] for r in cells if r['n']} == {
        ('*', 1): 2,
        ('*', 2): 2,
        ('*', 3): 1,
        ('one', 1): 1,
        ('one', 2): 1,
        ('one', 3): 1,
        ('two', 1): 1,
        ('two', 2): 1,
        ('two', 3): 0,
    }
    picks = [(r['scope'], r['perk'], r['lists']) for r in cells if r['n'] == 0]
    assert ('*', 'Rampage', 'One, Two') in picks
    # A ring's colours are its lists', by their places after the three
    # default lists: One 4, Two 5. A hit shows the lists of the rolls the copy
    # completes, a named perk or a pick the lists naming it.
    assert {(r['n'], r['perk']): r['rings'] for r in cells if r['scope'] == '*' and r['perk']} == {
        (0, 'Rampage'): '4-5',
        (0, 'Kill Clip'): '4',
        (0, 'Outlaw'): '5',
        (1, 'Rampage'): '4-5',
        (2, 'Rampage'): '4-5',
        (2, 'Outlaw'): '5',
        (3, 'Kill Clip'): '4',
        (3, 'Subsistence'): None,
    }


def test_roll_tables_lead_with_the_elements_when_copies_differ(conn):
    # The Arc and Void copies get an Element column before the perk sockets;
    # the second Void copy's is faded, as copy #1 is Void too. With one list,
    # the All lists table answers that list too.
    add_rifle(conn)
    add_rifle_copy(conn, 'void', [c.TRAIT_PERK_A], None, 1, damage_type=4)
    add_rifle_copy(conn, 'arc', [c.TRAIT_PERK_A], None, 0, damage_type=2)
    add_rifle_copy(conn, 'void2', [c.TRAIT_PERK_A], None, 0, damage_type=4)
    add_lists(conn, [(1, 'one', c.TRAIT_PERK_A, None, 0)], [('void', 1)])
    assert rows(conn, load.ROLL_COLUMNS, 'socket_idx', 'label') == [(-1, 'Element'), (1, 'Trait')]
    cells = conn.execute(load.ROLL_CELLS).fetchall()
    assert {r['shows'] for r in cells} == {'* one'}
    assert [(r['n'], r['perk'], r['faded']) for r in cells if r['socket_idx'] == -1] == [
        (1, 'Void', 0),
        (2, 'Arc', 0),
        (3, 'Void', 1),
    ]


def test_set_bonuses_carry_their_aegis_ranking(conn):
    # The sheet names the set without " Set" and ranks only its 2-piece bonus.
    c.add_armor(conn, 'a1', ROLL, set_name='Test Set', score=100)
    set_hash = conn.execute(
        "SELECT hash FROM DestinyEquipableItemSetDefinition WHERE name = 'Test Set'"
    ).fetchone()[0]
    with conn:
        conn.executemany(
            "INSERT INTO DestinySandboxPerkDefinition VALUES (?, ?, ?, ?)",
            [(1, 'Two', 'Two pieces.', '/two.png'), (2, 'Four', 'Four pieces.', '')],
        )
        conn.execute(
            "INSERT INTO aegis_bonus (set_name, pieces, bonus_name, rank, grade) "
            "VALUES ('Test', 2, 'Two', 5, 'B')"
        )
    c.add_set_perks(conn, set_hash, [(4, 2), (2, 1)])
    bonuses = load.load_set_bonuses(conn)['Test Set']
    assert [(b['pieces'], b['name'], b['icon']) for b in bonuses] == [
        (2, 'Two', 'https://www.bungie.net/two.png'),
        (4, 'Four', ''),
    ]
    assert (bonuses[0]['aegis'].grade, bonuses[0]['aegis'].rank) == ('B', 5)
    assert bonuses[1]['aegis'] is None


def test_set_pieces_by_class_grade_slot_and_score(conn):
    # The Warlock (more pieces) comes first; grade S before A; helmets before
    # gauntlets; a slot's copies best score first. Grade A keeps two per slot:
    # the third helmet is past the cap but rescued, so it stays.
    c.add_preference(conn, 'Set S', 'S', rank=1, stats=('health', 'melee'))
    c.add_preference(conn, 'Set A', 'A', rank=1)
    for instance_id, set_name, slot, score in (
        ('a1', 'Set A', 'Helmet', 100),
        ('a2', 'Set A', 'Helmet', 90),
        ('a3', 'Set A', 'Helmet', 80),
        ('s3', 'Set S', 'Gauntlets', 95),
        ('s1', 'Set S', 'Helmet', 90),
        ('s2', 'Set S', 'Helmet', 100),
    ):
        c.add_armor(conn, instance_id, {'health': score}, set_name=set_name, slot=slot, score=score)
    c.add_armor(conn, 't1', ROLL, set_name='Set S', armor_class='Titan', score=50)
    with conn:
        conn.execute("INSERT INTO armor_rescue VALUES ('a3', 'health', 'melee', 'grenade', 100)")

    # flagged counts each set's pieces to purge or kept for a build.
    assert rows(conn, load.SET_PIECES, 'armor_class', 'set_name', 'instance_id', 'flagged') == [
        ('Warlock', 'Set S', 's2', 0),
        ('Warlock', 'Set S', 's1', 0),
        ('Warlock', 'Set S', 's3', 0),
        ('Warlock', 'Set A', 'a1', 1),
        ('Warlock', 'Set A', 'a2', 1),
        ('Warlock', 'Set A', 'a3', 1),
        ('Titan', 'Set S', 't1', 0),
    ]
    a3 = conn.execute(load.SET_PIECES).fetchall()[5]
    assert (a3['reason'], a3['rescued'], a3['builds'], a3['purge']) == (
        'cap_tier',
        1,
        'health,melee,grenade',
        0,
    )
    totals = conn.execute(load.TOTALS).fetchone()
    assert (totals['armor_to_purge'], totals['rescued']) == (0, 1)


def test_legacy_pieces_are_listed_apart(conn):
    # The Tier 4 piece is scored with its set, beside the Tier 5 one.
    c.add_armor(conn, 'old', ROLL, tuning=(), gear_tier=None)
    c.add_armor(conn, 'low', ROLL, slot='Gauntlets', tuning=(), gear_tier=4, score=90)
    c.add_armor(conn, 'tuned', ROLL, score=100)
    assert rows(conn, load.LEGACY, 'instance_id') == [('old',)]
    assert rows(conn, load.SET_PIECES, 'instance_id', 'gear_tier') == [('tuned', 5), ('low', 4)]


def test_exotic_dupes_group_under_the_copy_kept(conn):
    # Equal scores: the older copy stays and the other is marked a tie. An
    # exotic with one copy isn't listed.
    c.add_armor(conn, 'e1', ROLL, exotic=True, name='Test Exotic', score=100)
    c.add_armor(conn, 'e2', ROLL, exotic=True, name='TEST EXOTIC', score=100)
    c.add_armor(conn, 'e3', ROLL, exotic=True, name='Other Exotic', score=50)
    assert rows(conn, load.EXOTIC_DUPES, 'instance_id', 'keeper_id', 'reason', 'tie') == [
        ('e1', 'e1', None, 0),
        ('e2', 'e1', 'exotic_dupe', 1),
    ]


def test_builds_count_the_covered_and_list_the_short(conn):
    # One piece in each slot, 30 in health, melee and grenade: that build
    # reaches 150 in each; every build with another stat is short.
    for slot in ('Helmet', 'Gauntlets', 'Chest Armor', 'Leg Armor', 'Class Armor'):
        c.add_armor(conn, slot, dict.fromkeys(ROLL, 30), slot=slot, score=100)
    warlock = conn.execute(load.CLASSES).fetchone()
    assert (warlock['armor_class'], warlock['legendary'], warlock['covered']) == ('Warlock', 5, 1)
    short = conn.execute(load.SHORT_BUILDS).fetchall()
    assert len(short) == 19
    assert [r['low'] for r in short] == sorted(r['low'] for r in short)


def test_preferences_list_sets_by_grade_and_exotics_by_class(conn):
    # The shipped defaults are stored too; only the test's own entries are
    # checked. An exotic the manifest lacks has no class and comes last.
    c.add_preference(conn, 'Zeta Set', '', stats=('health',))
    c.add_preference(conn, 'Beta Set', 'A', rank=2)
    c.add_preference(conn, 'Alpha Set', 'A', rank=1)
    c.add_preference(conn, 'Top Set', 'S', rank=9)
    c.add_armor_def(conn, 900, name='Test Exotic Helm', set_name='', tier=6, armor_class='Hunter')
    with conn:
        conn.executemany(
            "INSERT INTO armor_preference (name, is_exotic, stat_1) VALUES (?, 1, 'melee')",
            [('Unknown Exotic',), ('test exotic helm',)],
        )
    ours = {'Zeta Set', 'Beta Set', 'Alpha Set', 'Top Set', 'Unknown Exotic', 'test exotic helm'}
    sets = rows(conn, load.SET_PREFERENCES, 'name', 'grade')
    assert [r for r in sets if r[0] in ours] == [
        ('Top Set', 'S'),
        ('Alpha Set', 'A'),
        ('Beta Set', 'A'),
        ('Zeta Set', ''),
    ]
    exotics = rows(conn, load.EXOTIC_PREFERENCES, 'name', 'armor_class')
    assert [r for r in exotics if r[0] in ours] == [
        ('test exotic helm', 'Hunter'),
        ('Unknown Exotic', None),
    ]


def test_preference_badges_come_from_the_manifest(conn):
    # A set has a badge per class, its helmet's icon (the Hunter's lacks a
    # helmet: its vest); an exotic's is its own, with the first named plug in
    # an intrinsic socket as its perk.
    c.add_preference(conn, 'Iconic Set', 'B', rank=1)
    c.add_armor_def(conn, 902, name='Iconic Helm', set_name='Iconic Set')
    c.add_armor_def(conn, 903, name='Iconic Vest', set_name='Iconic Set', slot='Chest Armor')
    c.add_armor_def(
        conn,
        905,
        name='Hunter Vest',
        set_name='Iconic Set',
        slot='Chest Armor',
        armor_class='Hunter',
    )
    with conn:
        conn.execute(
            "INSERT INTO DestinyInventoryItemDefinition "
            "(hash, name, description, plugCategoryIdentifier) VALUES (70901, 'Perky', 'Does it.', "
            "'intrinsics')"
        )
    c.add_armor_def(conn, 904, name='Perk Exotic', set_name='', tier=6, sockets=[None, 70901])
    with conn:
        conn.executemany(
            "UPDATE DestinyInventoryItemDefinition SET icon = ? WHERE hash = ?",
            [('/helm.png', 902), ('/vest.png', 903), ('/exotic.png', 904), ('/hunter.png', 905)],
        )
        conn.execute(
            "INSERT INTO armor_preference (name, is_exotic, stat_1) "
            "VALUES ('Perk Exotic', 1, 'melee')"
        )
    (set_hash,) = [
        r[1] for r in rows(conn, load.SET_PREFERENCES, 'name', 'set_hash') if r[0] == 'Iconic Set'
    ]
    badges = [
        r[1:]
        for r in rows(conn, load.SET_BADGES, 'set_hash', 'armor_class', 'icon')
        if r[0] == set_hash
    ]
    assert badges == [
        ('Hunter', 'https://www.bungie.net/hunter.png'),
        ('Titan', 'https://www.bungie.net/helm.png'),
    ]
    exotics = rows(conn, load.EXOTIC_PREFERENCES, 'name', 'item_hash', 'icon', 'perk', 'perk_text')
    assert ('Perk Exotic', 904, 'https://www.bungie.net/exotic.png', 'Perky', 'Does it.') in exotics


def test_wishlists_list_the_defaults_then_the_added(conn):
    defaults = rows(conn, load.WISHLISTS, 'key')
    with conn:
        conn.execute("INSERT INTO wishlist_preference VALUES ('mine', 'Mine', 'u')")
    assert rows(conn, load.WISHLISTS, 'key') == [*defaults, ('mine',)]


def test_sources_say_how_each_fared(conn):
    with conn:
        conn.execute("INSERT INTO wishlist_source (key, label, url) VALUES ('src', 'Src', 'u')")
        conn.executemany(
            "INSERT INTO source_status (source, status, checked_at) VALUES (?, ?, '2026-10-18')",
            [('manifest', 'fresh'), ('dim', 'skipped'), ('wishlist:src', 'stale')],
        )
    assert rows(conn, load.SOURCES, 'name', 'ok', 'status') == [
        ('Bungie manifest', 1, 'Up to date'),
        ('Bungie profile', 0, 'Not checked'),
        ('DIM', 0, 'Skipped'),
        ('Clarity', 0, 'Not checked'),
        ('Src', 0, 'Download failed: the last good copy is used'),
        ('The Aegis', 0, 'Not checked'),
    ]
