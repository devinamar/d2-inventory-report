# Tests for v_weapon_grid (db/schema/views/v_weapon_grid.sql): each grid's
# rows, what its versions can roll, what players were seen with and what its
# copies have, with their shares, heat and order per side.
from tests import conftest as c


def add_gun(conn, item_hash=100, name='Gun'):
    # Gun: barrels Hammer-Forged Rifling and Fluted Barrel, magazines Appended
    # and Tactical Mag, first traits Rampage and Kill Clip, second traits
    # Outlaw and Subsistence, each in the game's order.
    c.add_weapon_def(conn, item_hash, name=name, sockets=[c.INTRINSIC_ADAPTIVE] + [None] * 4)
    for idx, plugs in enumerate(
        (
            (c.BARREL_PERK_X, c.BARREL_PERK_Y),
            (c.MAG_PERK_P, c.MAG_PERK_Q),
            (c.TRAIT_PERK_A, c.TRAIT_PERK_B),
            (c.TRAIT_PERK_C, c.TRAIT_PERK_D),
        ),
        1,
    ):
        c.add_plug_set(conn, item_hash, idx, item_hash * 10 + idx, [(p, 1) for p in plugs])


def grid(conn, *columns):
    rows = conn.execute(
        f"SELECT {', '.join(columns)} FROM v_weapon_grid ORDER BY grid_id, col_order, pve_pos"
    ).fetchall()
    return [tuple(r) for r in rows]


def test_a_grid_lists_the_pool_the_votes_and_its_copies_perks(conn):
    # Fluted Barrel never drops: the family's 120 barrel votes never saw it.
    # Appended Mag stays, with 50 magazine votes too few to tell. Vanguard's
    # Vindication is voted though the pool has no origin socket, and Firefly
    # is only the copy's. Rampage, at 0.3 of 0.7, isn't quiet; Subsistence and
    # Firefly, unvoted, are.
    add_gun(conn)
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[
            c.popularity_column('barrel', [('Hammer-Forged Rifling', 0.8)], n_eff=120.0),
            c.popularity_column('magazine', [('Tactical Mag', 1.0)]),
            c.popularity_column('traits', [('Kill Clip + Outlaw', 0.7)]),
            c.popularity_column('trait1', [('Kill Clip', 0.7), ('Rampage', 0.3)]),
            c.popularity_column('trait2', [('Outlaw', 1.0)]),
            c.popularity_column('origin', [("Vanguard's Vindication", 1.0)]),
        ],
    )
    sockets = [c.INTRINSIC_ADAPTIVE, c.BARREL_PERK_X, c.MAG_PERK_P, c.TRAIT_PERK_A, c.TRAIT_PERK_E]
    c.add_copy(conn, 'a', 100, sockets)
    # Aegis Endgame (the second list) names Kill Clip and Outlaw, and Voltron
    # (the first) Kill Clip; a trash roll's Rampage isn't named.
    with conn:
        conn.executemany(
            "INSERT INTO wishlist_source (key, label, url) VALUES (?, ?, '')",
            [('voltron', 'Voltron'), ('aegis_endgame', 'Aegis')],
        )
        conn.executemany(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1, perk2, is_trash) "
            "VALUES (?, ?, 100, ?, ?, ?)",
            [
                (1, 'aegis_endgame', c.TRAIT_PERK_B, c.TRAIT_PERK_C, 0),
                (2, 'voltron', c.TRAIT_PERK_B, None, 0),
                (3, 'voltron', c.TRAIT_PERK_A, None, 1),
            ],
        )
    lists = {perk: places for perk, places in grid(conn, 'perk', 'lists')}
    assert (lists['Kill Clip'], lists['Outlaw'], lists['Rampage']) == ('1 2', '2', '')
    assert grid(conn, 'col', 'label', 'perk', 'own', 'pve_heat', 'pve_pos', 'pve_quiet') == [
        ('barrel', 'Barrel', 'Hammer-Forged Rifling', 0, 10, 1, 0),
        ('magazine', 'Magazine', 'Tactical Mag', 0, 10, 1, 0),
        ('magazine', 'Magazine', 'Appended Mag', 0, 0, 2, 0),
        ('trait1', 'Trait 1', 'Kill Clip', 0, 10, 1, 0),
        ('trait1', 'Trait 1', 'Rampage', 0, 4, 2, 0),
        ('trait2', 'Trait 2', 'Outlaw', 0, 10, 1, 0),
        ('trait2', 'Trait 2', 'Subsistence', 0, 0, 2, 1),
        ('trait2', 'Trait 2', 'Firefly', 1, 0, 3, 1),
        ('origin', 'Origin', "Vanguard's Vindication", 0, 10, 1, 0),
    ]


def test_a_side_without_scores_keeps_the_games_order_and_no_heat(conn):
    # Nothing is scored on PvP: the rows keep the game's order, with no share
    # or heat, and every trait recedes.
    add_gun(conn)
    c.add_popularity(
        conn,
        'Gun',
        [100],
        columns=[c.popularity_column('trait1', [('Kill Clip', 0.7), ('Rampage', 0.3)])],
    )
    rows = grid(conn, 'perk', 'pvp_share', 'pvp_heat', 'pvp_pos', 'pvp_quiet')
    assert [r for r in rows if r[0] in ('Rampage', 'Kill Clip', 'Hammer-Forged Rifling')] == [
        ('Hammer-Forged Rifling', None, None, 1, 0),
        ('Kill Clip', None, None, 2, 1),
        ('Rampage', None, None, 1, 1),
    ]


def test_a_perk_another_pool_of_the_family_was_seen_with_stays(conn):
    # Gun (Raid) never voted Fluted Barrel, but Gun (Pantheon) did: it drops
    # somewhere in the family, so it stays on both.
    add_gun(conn, 100, 'Gun')
    add_gun(conn, 101, 'Gun')
    barrel = [('Hammer-Forged Rifling', 0.8)]
    c.add_popularity(
        conn,
        'Gun (Raid)',
        [100],
        family='Gun',
        columns=[c.popularity_column('barrel', barrel, n_eff=120.0)],
    )
    c.add_popularity(
        conn,
        'Gun (Pantheon)',
        [101],
        family='Gun',
        columns=[c.popularity_column('barrel', [('Fluted Barrel', 0.6)], n_eff=20.0)],
    )
    rows = grid(conn, 'grid_id', 'perk')
    assert [
        r for r in rows if r[0] == 100 and r[1] in ('Hammer-Forged Rifling', 'Fluted Barrel')
    ] == [
        (100, 'Hammer-Forged Rifling'),
        (100, 'Fluted Barrel'),
    ]


def test_a_card_no_scored_weapon_lists_gets_a_grid_of_its_own(conn):
    # Rifle isn't scored: its grid is its pool, named after its version, with
    # no scores on either side.
    add_gun(conn, 200, 'Rifle')
    c.add_copy(conn, 'r', 200, [c.INTRINSIC_ADAPTIVE, c.BARREL_PERK_X])
    rows = grid(conn, 'grid_id', 'col', 'perk', 'pve_rel', 'pvp_rel')
    assert rows[:2] == [
        (200, 'barrel', 'Hammer-Forged Rifling', None, None),
        (200, 'barrel', 'Fluted Barrel', None, None),
    ]
    assert len(rows) == 8
