# Scorer tests (analyze/wishlists/scorer.py): loading the stored rolls, and
# counting the non-trash wishlist rolls each copy can equip. A roll names its
# perks by hash; their names and kinds come from the test database's plugs
# (v_plug), through the same PlugCatalog a run uses.
import pytest

import models
from analyze.wishlists import scorer
from extract import wishlists as wl_extract
from sources import wishlists as wl_source
from tests import conftest

X, Y = conftest.BARREL_PERK_X, conftest.BARREL_PERK_Y  # Hammer-Forged Rifling, Fluted Barrel
P = conftest.MAG_PERK_P  # Appended Mag
# Rampage, Kill Clip, Outlaw
A, B, C = conftest.TRAIT_PERK_A, conftest.TRAIT_PERK_B, conftest.TRAIT_PERK_C


@pytest.fixture
def plugs(conn):
    return scorer.PlugCatalog(conn)


def make_copy(instance_id, item_hash, barrels, magazines, trait_1, trait_2):
    # A weapon copy whose roll has a barrel and a magazine socket (when given)
    # and two trait sockets, each holding the named perks.
    roll = []
    if barrels:
        roll.append(models.PerkSocket('barrel', barrels))
    if magazines:
        roll.append(models.PerkSocket('magazine', magazines))
    roll.append(models.PerkSocket('trait', trait_1))
    roll.append(models.PerkSocket('trait', trait_2))
    return models.WeaponInstance(instance_id, item_hash, roll)


def roll(*perks, trash=False, item_hash=100):
    return models.WishlistRoll(
        item_hash=item_hash, roll_id=hash(perks + (trash,)) & 0xFFFFFFF, perks=perks, is_trash=trash
    )


def test_roll_perks_are_sorted_by_their_plug_kind(plugs):
    # Barrels, magazines and traits are matched; the origin trait, the tracker
    # and an unknown hash are left out.
    r = roll(X, P, A, B, conftest.ORIGIN_PERK, conftest.KILL_TRACKER, 999999)
    assert scorer.classify_roll(r, plugs) == {
        'barrel': ['Hammer-Forged Rifling'],
        'magazine': ['Appended Mag'],
        'trait': ['Rampage', 'Kill Clip'],
    }


def test_a_roll_with_nothing_to_match_is_dropped(plugs):
    assert scorer.classify_roll(roll(conftest.ORIGIN_PERK, conftest.KILL_TRACKER), plugs) is None


def test_single_matching_roll_scores_one(plugs):
    copy = make_copy(
        'c1', 100, ['Hammer-Forged Rifling'], ['Appended Mag'], ['Rampage'], ['Kill Clip']
    )
    scores = scorer.score_all_instances([copy], {'voltron': {100: [roll(X, P, A, B)]}}, plugs)
    assert scores['c1'].match_count == 1
    assert scores['c1'].has_wishlist is True


def test_every_roll_line_the_copy_can_equip_counts(plugs):
    # Two barrels and two possible second traits: a curator's four lines, four
    # matches.
    copy = make_copy(
        'c1',
        100,
        ['Hammer-Forged Rifling', 'Fluted Barrel'],
        [],
        ['Rampage'],
        ['Kill Clip', 'Outlaw'],
    )
    rolls = [roll(X, A, B), roll(X, A, C), roll(Y, A, B), roll(Y, A, C)]
    scores = scorer.score_all_instances([copy], {'voltron': {100: rolls}}, plugs)
    assert scores['c1'].match_count == 4


def test_trash_rolls_cover_the_weapon_but_dont_score(plugs):
    copy = make_copy('c1', 100, ['Hammer-Forged Rifling'], [], ['Rampage'], ['Kill Clip'])
    scores = scorer.score_all_instances(
        [copy], {'voltron': {100: [roll(X, A, B, trash=True)]}}, plugs
    )
    assert scores['c1'].match_count == 0
    assert scores['c1'].has_wishlist is True


def test_a_roll_naming_no_perks_fits_every_copy(plugs):
    # Like Aegis Shopping's 10 "any roll of this exotic" lines (perks=,),
    # which score, and Voltron's 53 item=-<hash> lines, which trash the whole
    # weapon. A roll naming only perks that aren't matched still fits none.
    copies = [
        make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip']),
        make_copy('c2', 100, [], [], ['Outlaw'], ['Kill Clip']),
    ]
    wish, trash, origin_only = roll(), roll(trash=True), roll(conftest.ORIGIN_PERK)
    rolls = {'aegis_shopping': {100: [wish, origin_only]}, 'voltron': {100: [trash]}}
    scores = scorer.score_all_instances(copies, rolls, plugs)
    for copy in ('c1', 'c2'):
        assert scores[copy].matched_roll_ids == (wish.roll_id, trash.roll_id)
        assert scores[copy].match_count == 1


def test_a_weapon_a_list_mentions_is_covered_though_no_roll_scores(plugs):
    # Like Aegis Shopping's Choir of One line, which names only its catalyst:
    # the list covers the weapon, but nothing in it can be matched.
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    scores = scorer.score_all_instances(
        [copy], {'aegis_shopping': {100: [roll(conftest.ORIGIN_PERK)]}}, plugs
    )
    assert (scores['c1'].match_count, scores['c1'].has_wishlist) == (0, True)


def test_a_perk_the_copy_cant_roll_means_no_match(plugs):
    # Outlaw is in neither trait socket.
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    scores = scorer.score_all_instances([copy], {'voltron': {100: [roll(C, B)]}}, plugs)
    assert scores['c1'].match_count == 0


def test_a_stock_the_copy_cant_switch_to_means_no_match(conn):
    # A Peculiar Charm switches between Hand-Laid and Short-Action Stock;
    # Voltron's rolls naming Fitted Stock don't fit it.
    with conn:
        conn.executemany(
            "INSERT INTO DestinyInventoryItemDefinition (hash, name, plugCategoryIdentifier) "
            "VALUES (?, ?, 'stocks')",
            [(2101, 'Short-Action Stock'), (2102, 'Fitted Stock')],
        )
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    copy.roll.append(models.PerkSocket('stock', ['Hand-Laid Stock', 'Short-Action Stock']))
    short_action, fitted = roll(2101, A, B), roll(2102, A, B)
    scores = scorer.score_all_instances(
        [copy], {'voltron': {100: [short_action, fitted]}}, scorer.PlugCatalog(conn)
    )
    assert scores['c1'].matched_roll_ids == (short_action.roll_id,)


def test_traits_must_sit_in_different_sockets(plugs):
    # Both trait sockets hold only Rampage, so Rampage + Kill Clip can't fit.
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Rampage'])
    scores = scorer.score_all_instances([copy], {'voltron': {100: [roll(A, B)]}}, plugs)
    assert scores['c1'].match_count == 0


def test_a_wildcard_roll_scores_but_doesnt_cover(plugs):
    # A wildcard roll (item -69420) is checked against every copy; it counts
    # toward the score but doesn't mean a source covers the weapon.
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    wildcard = roll(A, B, item_hash=models.WILDCARD_ITEM_HASH)
    scores = scorer.score_all_instances(
        [copy], {'voltron': {models.WILDCARD_ITEM_HASH: [wildcard]}}, plugs
    )
    assert scores['c1'].match_count == 1
    assert scores['c1'].has_wishlist is False


def test_matches_add_up_across_sources_and_duplicate_lines(plugs):
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    sources = {'voltron': {100: [roll(A, B), roll(A, B)]}, 'aegis_endgame': {100: [roll(A, B)]}}
    scores = scorer.score_all_instances([copy], sources, plugs)
    assert scores['c1'].match_count == 3


def test_matched_roll_ids_list_only_the_rolls_that_fit(plugs):
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    fits, misses = roll(A, B), roll(A, C)
    scores = scorer.score_all_instances([copy], {'voltron': {100: [fits, misses]}}, plugs)
    assert scores['c1'].matched_roll_ids == (fits.roll_id,)


def test_no_wishlists_means_no_scores(plugs):
    copy = make_copy('c1', 100, [], [], ['Rampage'], ['Kill Clip'])
    assert scorer.score_all_instances([copy], {}, plugs) == {}


def test_a_weapon_no_source_lists_scores_zero_and_isnt_covered(plugs):
    copy = make_copy('c1', 999, [], [], ['Rampage'], ['Kill Clip'])
    scores = scorer.score_all_instances([copy], {'voltron': {100: [roll(A, B)]}}, plugs)
    assert scores['c1'].match_count == 0
    assert scores['c1'].has_wishlist is False


# Loading the stored rolls

WISHLIST = f"""title:Raid picks
//notes:Great for raids |tags:pve,god-pve
dimwishlist:item=100&perks={X},{A},{B}
dimwishlist:item=100&perks={Y},{A},{B}
dimwishlist:item=200&perks={X}
dimtrashlist:item=100&perks={C}#notes:no
dimwishlist:item=999&perks={A}
title:Trash list
dimwishlist:item=-300
"""


def save_wishlist(conn, text):
    # Store text as source src's rolls, the way a run does.
    wl_extract.save(conn, 'src', 'Source', 'http://x', wl_source.parse_wishlist_text(text), 'h')


def test_stored_rolls_load_per_weapon_in_file_order(conn):
    # One file line is one roll: a trash roll keeps its perks, a whole-weapon
    # trash roll has none, and a roll for a weapon that isn't stored (999) is
    # gone. A new download replaces the source's rolls.
    for item_hash in (100, 200, 300):
        conftest.add_weapon_def(conn, item_hash)
    save_wishlist(conn, WISHLIST)
    loaded = scorer.load_wishlist(conn, 'src')
    assert set(loaded) == {100, 200, 300}
    assert [(r.perks, r.is_trash) for r in loaded[100]] == [
        ((X, A, B), False),
        ((Y, A, B), False),
        ((C,), True),
    ]
    assert [(r.perks, r.is_trash) for r in loaded[300]] == [((), True)]

    save_wishlist(conn, f'dimwishlist:item=300&perks={Y},77')
    loaded = scorer.load_wishlist(conn, 'src')
    assert {item: [r.perks for r in rolls] for item, rolls in loaded.items()} == {300: [(Y,)]}
