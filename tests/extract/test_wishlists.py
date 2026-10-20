# Tests for the wishlist step (extract/wishlists.py): adding a source, what
# save writes to wishlist_roll, and downloading each source every run but
# parsing only a changed file. The download is a stand-in.
import pytest
import requests

import models
from extract import wishlists as wl_extract
from sources import wishlists as wl_source
from tests import conftest

PLUGS = [
    (1, 'Arrowhead Brake', 'barrels', ''),
    (2, 'Smallbore', 'barrels', ''),
    (3, 'Appended Mag', 'magazines', ''),
    (4, 'Rampage', 'frames', ''),
    (5, 'Kill Clip', 'frames', ''),
    (6, 'Outlaw', 'frames', ''),
]


@pytest.fixture
def conn(conn):
    # The shared test db plus these plugs and two weapons.
    with conn:
        conn.executemany(
            'INSERT INTO DestinyInventoryItemDefinition (hash, name, plugCategoryIdentifier, icon) '
            'VALUES (?, ?, ?, ?)',
            PLUGS,
        )
    conftest.add_weapon_def(conn, 100, 'Fatebringer')
    conftest.add_weapon_def(conn, 200, 'Palindrome')
    return conn


def ingest(conn, text):
    wl_extract.save(
        conn, 'src', 'Source Label', 'http://x', wl_source.parse_wishlist_text(text), 'test-hash'
    )


def test_add_source_saves_a_wishlist_keyed_by_its_label(conn):
    assert wl_extract.add_source(conn, 'My List!', 'https://example.com/list.txt')
    assert tuple(conn.execute(wl_extract.SOURCES).fetchall()[-1]) == (
        'my_list',
        'My List!',
        'https://example.com/list.txt',
    )


def test_add_source_refuses_a_bad_url_label_or_a_taken_one(conn):
    # The defaults hold the key voltron and its URL.
    url = conn.execute("SELECT url FROM wishlist_preference WHERE key = 'voltron'").fetchone()[0]
    count = conn.execute('SELECT COUNT(*) FROM wishlist_preference').fetchone()[0]
    assert not wl_extract.add_source(conn, 'Other', 'ftp://example.com/list.txt')
    assert not wl_extract.add_source(conn, '!!!', 'https://example.com/a.txt')
    assert not wl_extract.add_source(conn, 'Voltron', 'https://example.com/b.txt')
    assert not wl_extract.add_source(conn, 'Copy', url)
    assert conn.execute('SELECT COUNT(*) FROM wishlist_preference').fetchone()[0] == count


def test_each_file_line_persists_as_one_row(conn):
    ingest(conn, 'dimwishlist:item=100&perks=1,3,4\ndimwishlist:item=100&perks=2,3,5')
    rows = conn.execute(
        "SELECT item_hash, perk1, perk2, perk3, is_trash FROM wishlist_roll ORDER BY roll_id"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (100, 1, 3, 4, 0),
        (100, 2, 3, 5, 0),
    ]


def test_unknown_perk_hash_becomes_null_in_place(conn):
    # Perk 99 isn't a stored plug: its column, perk2, is NULL, and perk3
    # still holds 5.
    ingest(conn, 'dimwishlist:item=100&perks=1,99,5')
    (row,) = conn.execute("SELECT perk1, perk2, perk3 FROM wishlist_roll").fetchall()
    assert tuple(row) == (1, None, 5)


def test_a_roll_for_an_unknown_weapon_is_dropped(conn):
    # 999 isn't a stored weapon or the wildcard.
    ingest(conn, 'dimwishlist:item=100&perks=1\ndimwishlist:item=999&perks=1')
    rows = conn.execute("SELECT item_hash FROM wishlist_roll").fetchall()
    assert [r['item_hash'] for r in rows] == [100]


def test_a_wildcard_roll_is_kept(conn):
    ingest(conn, f'dimwishlist:item={models.WILDCARD_ITEM_HASH}&perks=4,5')
    (row,) = conn.execute("SELECT item_hash, perk1, perk2 FROM wishlist_roll").fetchall()
    assert tuple(row) == (models.WILDCARD_ITEM_HASH, 4, 5)


def test_a_trash_roll_is_stored_as_trash(conn):
    ingest(conn, 'dimtrashlist:item=100&perks=5')
    (row,) = conn.execute("SELECT is_trash FROM wishlist_roll").fetchall()
    assert row['is_trash'] == 1


def test_notes_and_tags_are_stored(conn):
    ingest(
        conn,
        'dimwishlist:item=100&perks=1,4,5#notes:raid roll |tags:pve,god-pve',
    )
    (row,) = conn.execute(
        "SELECT wn.text AS note, r.tags "
        "FROM wishlist_roll r LEFT JOIN wishlist_note wn ON wn.note_id = r.note_id"
    ).fetchall()
    assert row['note'] == 'raid roll'
    assert set(row['tags'].split(',')) == {'pve', 'god-pve'}


def test_a_new_download_replaces_the_sources_rolls(conn):
    ingest(conn, 'dimwishlist:item=100&perks=1')
    ingest(conn, 'dimwishlist:item=200&perks=1')
    rows = conn.execute("SELECT item_hash FROM wishlist_roll").fetchall()
    assert [r['item_hash'] for r in rows] == [200]


def test_a_note_is_stored_once_for_every_roll_sharing_it(conn):
    # The live lists' 279,316 rolls with notes share 5,481 notes.
    ingest(
        conn,
        '//notes:raid roll\n'
        'dimwishlist:item=100&perks=1\n'
        'dimwishlist:item=100&perks=2\n'
        'dimwishlist:item=200&perks=3',
    )
    notes = conn.execute('SELECT COUNT(*) FROM wishlist_note').fetchone()[0]
    note_ids = {r['note_id'] for r in conn.execute('SELECT note_id FROM wishlist_roll')}
    assert (notes, len(note_ids)) == (1, 1)


# Downloading: every run downloads each source and parses only a changed file.

URL = 'https://example.com/list.txt'


def only_source(conn):
    # wishlist_preference holding one source, src, in place of the defaults.
    with conn:
        conn.execute('DELETE FROM wishlist_preference')
        conn.execute("INSERT INTO wishlist_preference VALUES ('src', 'Source Label', ?)", (URL,))


def serve(monkeypatch, body):
    # Swap the download for one answering body, or raising it when it's an
    # exception; returns the URLs it was asked for.
    asked = []

    def fetch_text(url):
        asked.append(url)
        if isinstance(body, Exception):
            raise body
        return body

    monkeypatch.setattr(wl_extract.source, 'fetch_text', fetch_text)
    return asked


def status(conn):
    row = conn.execute("SELECT status FROM source_status WHERE source = 'wishlist:src'")
    return row.fetchone()[0]


def test_an_unchanged_file_keeps_its_rolls_without_parsing_them_again(conn, monkeypatch):
    # The body's SHA-256 matches the stored one, so the rolls stay as they are.
    only_source(conn)
    asked = serve(monkeypatch, 'dimwishlist:item=100&perks=1,4')
    parse = wl_source.parse_wishlist_text
    parsed = []

    def parse_and_count(text):
        parsed.append(text)
        return parse(text)

    monkeypatch.setattr(wl_extract.source, 'parse_wishlist_text', parse_and_count)
    wl_extract.extract(conn)
    wl_extract.extract(conn)
    assert (asked, len(parsed), status(conn)) == ([URL, URL], 1, 'cached')
    rolls = conn.execute('SELECT item_hash, perk1, perk2 FROM wishlist_roll')
    assert [tuple(r) for r in rolls] == [(100, 1, 4)]


@pytest.mark.parametrize(
    'rolls_stored, expected',
    [(True, (1, 'stale')), (False, (0, 'failed'))],
    ids=['rolls stored', 'nothing stored'],
)
def test_a_failed_download_is_stale_with_rolls_stored_else_failed(
    conn, monkeypatch, rolls_stored, expected
):
    only_source(conn)
    if rolls_stored:
        ingest(conn, 'dimwishlist:item=100&perks=1')
    serve(monkeypatch, requests.ConnectionError('raw.githubusercontent.com unreachable'))
    wl_extract.extract(conn)
    rolls = conn.execute('SELECT COUNT(*) FROM wishlist_roll').fetchone()[0]
    assert (rolls, status(conn)) == expected
