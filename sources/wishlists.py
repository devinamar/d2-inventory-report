# DIM wishlists: community lists of recommended (and "trash") weapon rolls in
# DIM's text format. Downloads a wishlist file and parses every roll line into
# a ParsedRoll; extract/wishlists.py picks the sources (the
# wishlist_preference table) and saves the rolls to the db.
#
# File format, one entry per line:
#   dimwishlist:item=<hash>&perks=<p1>,<p2>,...#notes:<text>  a recommended roll
#   dimtrashlist:...                                           a trash roll
#   item=<hash>          with no perks (or perks=,): any roll of the weapon
#   item=-<hash>         DIM shorthand for "trash this whole weapon"
#   item=-69420          wildcard: the roll applies to any weapon
#   //notes:<text>       a note inherited by the rolls that follow it
#   title:<text>         starts a section (not stored) and clears the note
#   description:<text>   section description (not stored)
#   ...|tags:<a,b c>     tags at the end of any note, split on comma or space
import dataclasses
import re

import requests

import models

# Matches dimwishlist and dimtrashlist lines. Uses match, not fullmatch, so
# stray text after the notes doesn't drop the whole line.
ROLL_RE = re.compile(
    r'^dim(?P<kind>wish|trash)list:'
    r'item=(?P<item>-?\d+)'
    r'(?:&perks=(?P<perks>[\d,]*))?'
    r'(?:#notes:(?P<notes>.*))?'
)


@dataclasses.dataclass
class ParsedRoll:
    # One roll line. Perk hashes stay in file order: by DIM convention barrel,
    # magazine, trait 1, trait 2, plus up to two extras on some weapon types
    # (glaives, swords, grenade launchers). The scorer looks up each perk's
    # category in the plug table.
    item_hash: int
    perks: tuple[int, ...]
    notes: str = ''
    tags: set[str] = dataclasses.field(default_factory=set)
    is_trash: bool = False


def fetch_text(url: str) -> str:
    # Raw file body. Raises on network / HTTP failure.
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def split_tags(inline_notes: str | None, block_notes: str) -> tuple:
    # (notes, tags) for one roll. The roll's own #notes: text wins over the
    # inherited block note; a trailing |tags:a,b c part becomes a lowercase
    # tag set.
    if inline_notes and inline_notes.strip():
        source = inline_notes.strip()
    else:
        source = block_notes
    if '|tags:' not in source:
        return source, set()
    notes, _, tag_text = source.rpartition('|tags:')
    tags = {t.lower() for t in re.split(r'[,\s]+', tag_text) if t}
    return notes.strip(), tags


def parse_wishlist_text(text: str) -> list:
    # [ParsedRoll] in file order. A //notes: line sets the note inherited by
    # the rolls after it; any other non-roll line clears it.
    rolls = []
    block_notes = ''

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith('//notes:'):
            block_notes = line[8:]
        elif match := ROLL_RE.match(line):
            item_hash = int(match.group('item'))
            is_trash = match.group('kind') == 'trash'
            # DIM shorthand: negative item hash means "trash this whole
            # weapon" — except the wildcard sentinel, which stays as-is.
            if item_hash < 0 and item_hash != models.WILDCARD_ITEM_HASH:
                item_hash, is_trash = -item_hash, True
            perks = tuple(int(h) for h in (match.group('perks') or '').split(',') if h.isdigit())
            notes, tags = split_tags(match.group('notes'), block_notes)
            rolls.append(
                ParsedRoll(
                    item_hash=item_hash,
                    perks=perks,
                    notes=notes,
                    tags=tags,
                    is_trash=is_trash,
                )
            )
        else:
            block_notes = ''  # any other line, a title: included, clears the note

    return rolls
