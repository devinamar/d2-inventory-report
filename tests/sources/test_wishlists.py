# Tests for parsing DIM wishlist files (sources/wishlists.py): each roll line
# becomes one ParsedRoll, in file order, with the notes and tags that apply to
# it.
import pytest

import models
from sources import wishlists


def rolls(text):
    return wishlists.parse_wishlist_text(text)


# Roll lines


def test_a_wishlist_line_becomes_a_roll():
    assert rolls('dimwishlist:item=100&perks=1,2,3,4') == [
        wishlists.ParsedRoll(item_hash=100, perks=(1, 2, 3, 4))
    ]


def test_a_trash_line_is_flagged_trash():
    (roll,) = rolls('dimtrashlist:item=100&perks=5')
    assert (roll.item_hash, roll.perks, roll.is_trash) == (100, (5,), True)


def test_a_negative_item_hash_trashes_the_whole_weapon():
    # DIM's shorthand: item=-<hash>, with no perks.
    assert rolls('dimwishlist:item=-100') == [
        wishlists.ParsedRoll(item_hash=100, perks=(), is_trash=True)
    ]


def test_the_wildcard_hash_stays_and_is_not_trash():
    # item=-69420 applies the roll to every weapon.
    (roll,) = rolls(f'dimwishlist:item={models.WILDCARD_ITEM_HASH}&perks=9,10')
    assert (roll.item_hash, roll.perks, roll.is_trash) == (
        models.WILDCARD_ITEM_HASH,
        (9, 10),
        False,
    )


def test_each_line_is_its_own_roll_in_file_order():
    # A curator's two barrels by two traits, written out one line per pair.
    text = '\n'.join(f'dimwishlist:item=100&perks={b},{t}' for b in (1, 2) for t in (3, 4))
    assert [r.perks for r in rolls(text)] == [(1, 3), (1, 4), (2, 3), (2, 4)]


# Notes


def test_inline_notes_belong_to_their_roll():
    text = 'dimwishlist:item=100&perks=1#notes:god roll\ndimwishlist:item=100&perks=2'
    assert [r.notes for r in rolls(text)] == ['god roll', '']


def test_a_block_note_is_inherited_by_the_rolls_after_it():
    text = '//notes:Great for raids\ndimwishlist:item=100&perks=1\ndimwishlist:item=100&perks=2'
    assert [r.notes for r in rolls(text)] == ['Great for raids', 'Great for raids']


def test_inline_notes_win_over_the_block_note():
    text = '//notes:block\ndimwishlist:item=100&perks=1#notes:inline\ndimwishlist:item=100&perks=2'
    assert [r.notes for r in rolls(text)] == ['inline', 'block']


def test_blank_inline_notes_fall_back_to_the_block_note():
    text = '//notes:block\ndimwishlist:item=100&perks=1#notes:   '
    assert [r.notes for r in rolls(text)] == ['block']


def test_a_blank_line_keeps_the_block_note():
    text = '//notes:keep me\n\ndimwishlist:item=100&perks=1'
    assert [r.notes for r in rolls(text)] == ['keep me']


@pytest.mark.parametrize(
    'line',
    ['title:Second curator', 'description:For raids', '// a comment', 'dimwishlist:item=abc'],
)
def test_any_other_line_clears_the_block_note(line):
    # A section marker, a comment, or a roll line the parser can't read.
    text = f'//notes:first\n{line}\ndimwishlist:item=100&perks=1'
    assert [r.notes for r in rolls(text)] == ['']


# Lines it can't read


@pytest.mark.parametrize(
    'line',
    ['dimwishlist:item=abc&perks=1', 'dimwishlist:perks=1,2', 'wishlist:item=100&perks=1'],
)
def test_a_roll_line_it_cannot_read_is_dropped(line):
    assert rolls(line) == []


def test_text_after_a_roll_that_is_not_notes_is_ignored():
    # #notes without its colon isn't a notes marker; the roll still counts.
    (roll,) = rolls('dimwishlist:item=100&perks=1,2#notes')
    assert (roll.perks, roll.notes) == ((1, 2), '')


def test_empty_perk_entries_are_skipped():
    (roll,) = rolls('dimwishlist:item=100&perks=1,,2,')
    assert roll.perks == (1, 2)


# Tags


def test_tags_split_on_commas_and_spaces_in_lowercase():
    (roll,) = rolls('dimwishlist:item=100&perks=1#notes:good |tags:PvE pve-minor,m+kb')
    assert (roll.notes, roll.tags) == ('good', {'pve', 'pve-minor', 'm+kb'})


def test_tags_come_from_the_block_note_too():
    (roll,) = rolls('//notes:raid roll |tags:pve,god-pve\ndimwishlist:item=100&perks=1')
    assert (roll.notes, roll.tags) == ('raid roll', {'pve', 'god-pve'})


# Line endings


def test_crlf_endings_and_indented_lines_parse():
    # No note keeps the \r.
    text = (
        '//notes:raid roll\r\n'
        '  dimwishlist:item=100&perks=1\r\n'
        '\tdimwishlist:item=200&perks=2#notes:god roll\r\n'
    )
    assert [(r.item_hash, r.notes) for r in rolls(text)] == [(100, 'raid roll'), (200, 'god roll')]
