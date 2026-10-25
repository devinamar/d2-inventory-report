# Tests for the perk grids (report/templates/grids.html.j2): one template per
# grid with its rows' heat, places, shares, wishlists and copies per side, its
# pair lines with their verdicts and copies, and details lines, then the
# tooltip blocks and the icon and ring rules.
from tests import conftest as c


def add_gun(conn):
    # Gun rolls Rampage or Kill Clip, then Outlaw or Subsistence; it is scored
    # on PvE only, Endgame there (60 of its 100 copies from hard content). Its
    # copy has Firefly, which it can't roll, and Voltron (the first list)
    # names Kill Clip.
    c.add_weapon_def(conn, 100, name='Gun', sockets=[c.INTRINSIC_ADAPTIVE, None, None])
    c.add_plug_set(conn, 100, 1, 901, [(c.TRAIT_PERK_A, 1), (c.TRAIT_PERK_B, 1)])
    c.add_plug_set(conn, 100, 2, 902, [(c.TRAIT_PERK_C, 1), (c.TRAIT_PERK_D, 1)])
    c.add_popularity(
        conn,
        'Gun',
        [100],
        hard_copies=60,
        columns=[
            c.popularity_column('traits', [('Kill Clip + Outlaw', 0.7)], n_eff=120.0),
            c.popularity_column('trait1', [('Kill Clip', 0.7), ('Rampage', 0.3)], n_eff=120.0),
            c.popularity_column('trait2', [('Outlaw', 1.0)], n_eff=120.0),
        ],
    )
    c.add_copy(conn, 'a', 100, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A, c.TRAIT_PERK_E])
    with conn:
        conn.execute(
            "INSERT INTO wishlist_source (key, label, url) VALUES ('voltron', 'Voltron', '')"
        )
        conn.execute(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1, is_trash) "
            "VALUES (1, 'voltron', 100, ?, 0)",
            (c.TRAIT_PERK_B,),
        )


def grids(conn, folder):
    # The part of the report after its pages: the grids and their tooltips.
    html, _ = c.write_report(conn, folder)
    return html.split('</main>')[1]


def gun_grid(conn, folder):
    # Gun's grid template.
    return grids(conn, folder).split('<template id="g100">')[1].split('</template>')[0]


def test_a_grids_rows_carry_both_sides_heat_places_shares_and_lists(conn, tmp_path):
    # PvP has no scores: no heat or share there, the game's order, and its
    # traits recede. The copy (1 on its card) has Rampage, and Firefly, which
    # only it has.
    add_gun(conn)
    template = gun_grid(conn, tmp_path)
    assert '<div class="pc" data-col="trait1">' in template
    assert '<span class="conf on-pvp">no scores</span>' in template
    assert (
        '<li class="pk a10 bn qb" data-tip="p1002" data-r="1 2" data-a="70%" data-l="1">'
        '<span>Kill Clip</span></li>'
    ) in template
    assert (
        '<li class="pk a4 bn qb" data-tip="p1001" data-r="2 1" data-a="30%" data-o="1">'
        '<span>Rampage</span></li>'
    ) in template
    assert (
        'class="pk a0 bn qa qb own" data-tip="p1005" data-r="3 3" data-a="—" data-o="1">'
    ) in template


def test_a_grid_holds_its_pairs_lines_and_each_scored_sides_details(conn, tmp_path):
    # Kill Clip + Outlaw, the top pair, is desired; Rampage + Firefly, which
    # the copy makes and players weren't seen with, is undesirable on PvE,
    # where the pairs' confidence is high. PvP has no pair scores.
    add_gun(conn)
    template = gun_grid(conn, tmp_path)
    assert (
        '<path data-a="p1002" data-b="p1003" data-pve="1 1.0 0.7 1.0 1.0 1 1 g"></path>'
    ) in template
    assert (
        '<path data-a="p1001" data-b="p1005" data-pve="0 0 0 0 0 0 0 b" data-c="1"></path>'
    ) in template
    assert '<p class="pop-meta on-pve"><span><b>Confidence:</b> High in every column' in template
    assert 'on-pvp"><span><b>Confidence' not in template


def test_a_copys_completed_roll_marks_its_perks_and_its_pair(conn, tmp_path):
    # The copy completes Mine's roll naming Rampage and Firefly (Mine is the
    # fourth list): both rows name it as the copy's hit, and the pair line
    # names the list; a trash roll of Voltron's naming them marks it too.
    add_gun(conn)
    with conn:
        conn.execute("INSERT INTO wishlist_preference VALUES ('mine', 'Mine', '')")
        conn.execute("INSERT INTO wishlist_source (key, label, url) VALUES ('mine', 'Mine', '')")
        conn.executemany(
            "INSERT INTO wishlist_roll (roll_id, source_key, item_hash, perk1, perk2, is_trash) "
            "VALUES (?, ?, 100, ?, ?, ?)",
            [
                (2, 'mine', c.TRAIT_PERK_A, c.TRAIT_PERK_E, 0),
                (3, 'voltron', c.TRAIT_PERK_A, c.TRAIT_PERK_E, 1),
            ],
        )
        conn.execute("INSERT INTO instance_wishlist_match VALUES ('a', 2)")
    template = gun_grid(conn, tmp_path)
    assert (
        'data-tip="p1001" data-r="2 1" data-a="30%" data-l="4" data-o="1" data-h="1:4">'
    ) in template
    assert 'data-c="1" data-w="4" data-t="1"></path>' in template


def test_tooltips_cover_the_perks_and_each_scored_weapons_confidence_and_badge(conn, tmp_path):
    add_gun(conn)
    html = grids(conn, tmp_path)
    assert '<div id="tip-p1002"><b>Kill Clip</b>' in html
    assert '<div id="tip-c-pve-100"><b>PvE #1 · High confidence</b>' in html
    assert '120 effective votes in every column' in html
    assert '<div id="tip-e-pve-100"><b>PvE Endgame</b><p>60% of its PvE copies (60 of 100)' in html
    assert 'Shown from 30% and 50 copies.' in html
    assert 'tip-c-pvp-100' not in html


def test_each_perk_has_its_icon_and_every_mix_of_lists_its_ring(conn, tmp_path):
    # Three default lists make seven mixes.
    add_gun(conn)
    html = grids(conn, tmp_path)
    assert '[data-tip="p1002"] { --i: url("https://www.bungie.net/img/killclip.png"); }' in html
    assert html.count('{ --tint: ') == 7
    assert '<span class="wl-name l1">Voltron (Pandapaxxy/Mercules +trash)</span>' in html
