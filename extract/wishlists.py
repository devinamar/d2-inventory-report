# Wishlist extract: downloads each source in wishlist_preference every run and
# compares the body's SHA-256 with the stored content_hash. Unchanged files
# keep their stored rolls ('cached'); changed ones are parsed and their rolls
# rewritten ('fresh'). A failed download keeps the stored rolls ('stale'), or
# leaves none when there were none ('failed'). Each source's status goes to
# source_status as 'wishlist:<key>'.
import hashlib
import re

import models
from extract import source_status
from sources import wishlists as source

# Sources: the wishlists to download, the defaults first, then those the
# player added in that order.
SOURCES = "SELECT key, label, url FROM wishlist_preference ORDER BY rowid"


def add_source(conn, label: str, url: str) -> bool:
    # --add-wishlist: save a wishlist source of the player's to
    # wishlist_preference, its key made from label, and say so. Returns False,
    # saving nothing, for a URL that isn't http(s), a label without a letter or
    # digit, or a key or URL another source has.
    key = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
    clash = conn.execute(
        "SELECT label FROM wishlist_preference WHERE key = ? OR url = ?", (key, url)
    ).fetchone()
    problem = ''
    if not url.startswith(('https://', 'http://')):
        problem = 'the URL must start with https:// or http://'
    elif not key:
        problem = 'the label needs a letter or digit'
    elif clash:
        problem = f'{clash[0]} already has that name or URL'
    if problem:
        print(f"Wishlist not added: {problem}.")
        return False
    with conn:
        conn.execute(
            "INSERT INTO wishlist_preference (key, label, url) VALUES (?, ?, ?)", (key, label, url)
        )
    print(f"Added wishlist {label} (key {key}); the next run downloads it.")
    return True


# Fetch phase: download each source and decide whether its rolls change.


def content_hash(conn, source_key: str) -> str:
    # SHA-256 of the source's last downloaded body; '' if it was never fetched.
    row = conn.execute(
        "SELECT content_hash FROM wishlist_source WHERE key = ?",
        (source_key,),
    ).fetchone()
    if row:
        return row['content_hash']
    return ''


def has_wishlist(conn, source_key: str) -> bool:
    # True when the source has rolls from an earlier download.
    return (
        conn.execute(
            "SELECT 1 FROM wishlist_roll WHERE source_key = ? LIMIT 1",
            (source_key,),
        ).fetchone()
        is not None
    )


def mark_cached(conn, key: str, label: str, url: str) -> None:
    # Keep the stored rolls of a source whose body matched the stored hash,
    # refreshing its label and URL from wishlist_preference.
    with conn:
        conn.execute(
            "INSERT INTO wishlist_source (key, label, url) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET label = excluded.label, url = excluded.url",
            (key, label, url),
        )


def fetch_wishlist(conn, key: str, label: str, url: str) -> tuple:
    # Download one source and compare it with the stored copy. Returns
    # (status, text, body_hash); text and body_hash are set only for 'fresh',
    # which the caller must parse and save. 'cached' means unchanged, 'stale'
    # that the download failed with rolls stored, 'failed' that it failed with
    # none.
    try:
        print(f"  {label}: checking source...")
        text = source.fetch_text(url)
    except Exception as e:
        if has_wishlist(conn, key):
            print(f"    download failed ({e}), using stored copy")
            return 'stale', None, None
        print(f"    download failed ({e}), skipping")
        return 'failed', None, None

    body_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if body_hash == content_hash(conn, key):
        print("    unchanged; keeping stored rolls")
        mark_cached(conn, key, label, url)
        return 'cached', None, None

    return 'fresh', text, body_hash


# Save phase: rewrite a changed source's rolls.


def save_note(conn, text: str) -> int | None:
    # note_id of the note's wishlist_note row, inserting it if new (the text
    # is UNIQUE, so each note is stored once). None for empty text.
    if not text:
        return None
    conn.execute("INSERT OR IGNORE INTO wishlist_note (text) VALUES (?)", (text,))
    row = conn.execute("SELECT note_id FROM wishlist_note WHERE text = ?", (text,)).fetchone()
    return row['note_id']


def save(conn, key: str, label: str, url: str, parsed_rolls: list, body_hash: str) -> None:
    # Replace the source's rolls and store body_hash as its content_hash, so
    # the next run can skip an unchanged file. Rolls for items that aren't
    # manifest weapons are dropped (except wildcards); unknown perk hashes
    # become NULL in place so the other perks keep their positions.
    with conn:
        conn.execute(
            "INSERT INTO wishlist_source (key, label, url, content_hash) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET "
            "  label = excluded.label, "
            "  url = excluded.url, "
            "  content_hash = excluded.content_hash",
            (key, label, url, body_hash),
        )
        conn.execute("DELETE FROM wishlist_roll WHERE source_key = ?", (key,))
        weapons = {
            r[0]
            for r in conn.execute(
                "SELECT hash FROM DestinyInventoryItemDefinition WHERE itemType = 3"
            )
        }
        plugs = {
            r[0]
            for r in conn.execute(
                "SELECT hash FROM DestinyInventoryItemDefinition "
                "WHERE plugCategoryIdentifier IS NOT NULL"
            )
        }
        skipped_rolls = dropped_perks = 0
        for pr in parsed_rolls:
            if pr.item_hash != models.WILDCARD_ITEM_HASH and pr.item_hash not in weapons:
                skipped_rolls += 1
                continue
            slots = [h if h in plugs else None for h in pr.perks]
            dropped_perks += sum(
                1 for orig, slot in zip(pr.perks, slots, strict=True) if orig and slot is None
            )
            slots += [None] * (6 - len(slots))
            conn.execute(
                "INSERT INTO wishlist_roll "
                "(source_key, item_hash, note_id, tags, is_trash, "
                " perk1, perk2, perk3, perk4, perk5, perk6) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    key,
                    pr.item_hash,
                    save_note(conn, pr.notes),
                    ','.join(sorted(pr.tags)),
                    int(pr.is_trash),
                    *slots,
                ),
            )
    if skipped_rolls or dropped_perks:
        print(
            f"    {label}: skipped {skipped_rolls} rolls for items that aren't "
            f"manifest weapons, {dropped_perks} perks the manifest no longer has"
        )


# Summary: what each source has stored, printed after its fetch.


def roll_counts(conn, key: str) -> tuple:
    # (rolls, trash rolls, weapons, wildcard rolls) stored for the source.
    # Wildcard rolls are counted only in the last.
    wildcard = models.WILDCARD_ITEM_HASH
    return tuple(
        conn.execute(
            "SELECT COUNT(CASE WHEN item_hash != ? THEN 1 END), "
            "       COUNT(CASE WHEN item_hash != ? AND is_trash THEN 1 END), "
            "       COUNT(DISTINCT NULLIF(item_hash, ?)), "
            "       COUNT(CASE WHEN item_hash = ? THEN 1 END) "
            "FROM wishlist_roll WHERE source_key = ?",
            (wildcard, wildcard, wildcard, wildcard, key),
        ).fetchone()
    )


def extract(conn) -> None:
    # For each source: fetch it, parse and save it when it changed, then
    # print a summary of its stored rolls.
    print("\nLoading wishlists...")
    for key, label, url in conn.execute(SOURCES).fetchall():
        status, text, body_hash = fetch_wishlist(conn, key, label, url)
        if status == 'fresh':
            save(conn, key, label, url, source.parse_wishlist_text(text), body_hash)
        source_status.save(conn, f'wishlist:{key}', status)
        if status == 'failed':
            print(f"    [FAIL] {label}: failed to download")
            continue
        roll_count, trash, weapons, wildcards = roll_counts(conn, key)
        if trash:
            trash_str = f" ({trash} trash)"
        else:
            trash_str = ''
        if wildcards:
            wildcard_str = f" + {wildcards} wildcard"
        else:
            wildcard_str = ''
        print(
            f"    [OK] {label}: {roll_count} rolls{trash_str} for {weapons} weapons{wildcard_str}"
        )
