# Tests for the perk popularity step (extract/perk_popularity.py): the scores
# file lands in perk_popularity_weapon and perk_popularity_file, a new file
# replaces the stored one, and a failed download keeps the stored copy and its
# note. The sample is trimmed from the scores of 2026-10-25: the PvP magazine of
# Found Verdict (Episode: Heresy), one of two weapons its trait pools split it
# into; the origin column of Reckless Endangerment (Witch Queen), which no
# hard-content copy voted in; and The Jade Rabbit, a fixed roll with no columns.
import json

import pytest
import requests

from extract import perk_popularity, source_status

GENERATED_AT = '2026-10-25T15:18:40Z'
FOUND_VERDICT = {
    'name': 'Found Verdict (Episode: Heresy)',
    'type': 'Shotgun',
    'item_hash': 694500607,
    'rank': 48,
    'players': 157,
    'active_players': 157,
    'family': 'Found Verdict',
    'item_hashes': [694500607, 851296754],
    'hard': True,
    'hard_weight': 0.699,
    'groups': {'hard': {'copies': 47, 'n_eff': 46.5}, 'normal': {'copies': 113, 'n_eff': 109.9}},
    'last_seen': '2026-10-23T22:13:09Z',
    'stale': False,
    'columns': [
        {
            'kind': 'magazine',
            'n_eff': 88.3,
            'credibility': 0.75,
            'confidence': 'medium',
            'hard': {'n_eff': 46.5, 'credibility': 0.61},
            'normal': {'n_eff': 109.9, 'credibility': 0.79},
            'perks': [
                {
                    'perk': 'Accurized Rounds',
                    'share': 0.786,
                    'low': 0.69,
                    'high': 0.859,
                    'hard': 0.815,
                    'normal': 0.718,
                },
                {
                    'perk': 'Assault Mag',
                    'share': 0.082,
                    'low': 0.041,
                    'high': 0.159,
                    'hard': 0.065,
                    'normal': 0.122,
                },
            ],
        }
    ],
}
RECKLESS_ENDANGERMENT = {
    'name': 'Reckless Endangerment (Witch Queen)',
    'type': 'Shotgun',
    'item_hash': 3216652511,
    'rank': 737,
    'players': 6,
    'active_players': 6,
    'family': 'Reckless Endangerment',
    'item_hashes': [3216652511],
    'hard': False,
    'hard_weight': 0.0,
    'groups': {'hard': {'copies': 0, 'n_eff': 0.0}, 'normal': {'copies': 6, 'n_eff': 4.8}},
    'last_seen': '2026-10-23T20:22:26Z',
    'stale': False,
    'columns': [
        {
            'kind': 'origin',
            'n_eff': 4.8,
            'credibility': 0.14,
            'confidence': 'very low',
            'hard': None,
            'normal': {'n_eff': 4.8, 'credibility': 0.14},
            'perks': [
                {
                    'perk': "Vanguard's Vindication",
                    'share': 0.75,
                    'low': 0.33,
                    'high': 0.948,
                    'hard': None,
                    'normal': 0.75,
                }
            ],
        }
    ],
}
JADE_RABBIT = {
    'name': 'The Jade Rabbit',
    'type': 'Scout Rifle',
    'item_hash': 3844694310,
    'rank': 7,
    'players': 1188,
    'active_players': 1188,
    'family': 'The Jade Rabbit',
    'item_hashes': [3844694310],
    'hard': True,
    'hard_weight': 0.727,
    'groups': {
        'hard': {'copies': 188, 'n_eff': 187.5},
        'normal': {'copies': 1023, 'n_eff': 1017.5},
    },
    'last_seen': '2026-10-23T22:13:43Z',
    'stale': False,
    'columns': [],
}
SCORES = {
    'generated_at': GENERATED_AT,
    'settings': {
        'window_days': 30,
        'rescue_copies': 10,
        'raw_days': 14,
        'hard_weight': 0.75,
        'credibility_k': 30,
    },
    'categories': [
        {'key': 'raid_master', 'label': 'Master raid', 'side': 'pve', 'weight': 32, 'hard': True},
        {'key': 'trials', 'label': 'Trials of Osiris', 'side': 'pvp', 'weight': 8, 'hard': True},
    ],
    'pve': [RECKLESS_ENDANGERMENT],
    'pvp': [JADE_RABBIT, FOUND_VERDICT],
}
NOTE = f'temporary pull: {GENERATED_AT}'


def rows(conn, sql):
    return [tuple(r) for r in conn.execute(sql)]


def status(conn):
    row = conn.execute("SELECT status, detail FROM source_status WHERE source = 'perk_popularity'")
    return tuple(row.fetchone())


def download(monkeypatch, scores):
    # Swap the source's fetch for one answering scores.
    monkeypatch.setattr(perk_popularity.source, 'fetch_scores', lambda: scores)


def test_a_downloaded_file_lands_in_the_tables(conn, monkeypatch):
    # Each weapon's own values as columns, its groups and columns as published;
    # the file's settings and categories in its one row.
    download(monkeypatch, SCORES)
    perk_popularity.extract(conn)
    assert rows(
        conn,
        "SELECT side, name, rank, hard, stale, groups ->> '$.hard.copies', "
        "json_array_length(columns) FROM perk_popularity_weapon ORDER BY side, rank",
    ) == [
        ('pve', 'Reckless Endangerment (Witch Queen)', 737, 0, 0, 0, 1),
        ('pvp', 'The Jade Rabbit', 7, 1, 0, 188, 0),
        ('pvp', 'Found Verdict (Episode: Heresy)', 48, 1, 0, 47, 1),
    ]
    family, item_hashes, columns = conn.execute(
        "SELECT family, item_hashes, columns FROM perk_popularity_weapon "
        "WHERE name = 'Found Verdict (Episode: Heresy)'"
    ).fetchone()
    assert (family, json.loads(item_hashes)) == ('Found Verdict', [694500607, 851296754])
    assert json.loads(columns) == FOUND_VERDICT['columns']
    assert rows(
        conn,
        "SELECT columns ->> '$[0].kind', columns ->> '$[0].hard', "
        "columns ->> '$[0].perks[0].perk', columns ->> '$[0].perks[0].hard' "
        "FROM perk_popularity_weapon WHERE family = 'Reckless Endangerment'",
    ) == [('origin', None, "Vanguard's Vindication", None)]
    file = conn.execute("SELECT * FROM perk_popularity_file").fetchall()
    assert [(r[0], json.loads(r[1]), json.loads(r[2])) for r in file] == [
        (GENERATED_AT, SCORES['settings'], SCORES['categories'])
    ]
    assert status(conn) == ('fresh', GENERATED_AT)


def test_a_new_file_replaces_the_stored_one(conn, monkeypatch):
    perk_popularity.save(conn, SCORES)
    newer = {**SCORES, 'generated_at': '2026-10-26T08:31:00Z', 'pve': [], 'pvp': [JADE_RABBIT]}
    download(monkeypatch, newer)
    perk_popularity.extract(conn)
    assert rows(conn, "SELECT name FROM perk_popularity_weapon") == [('The Jade Rabbit',)]
    assert rows(conn, "SELECT generated_at FROM perk_popularity_file") == [
        ('2026-10-26T08:31:00Z',)
    ]
    assert status(conn) == ('fresh', '2026-10-26T08:31:00Z')


@pytest.mark.parametrize('scores, expected, weapons', [(SCORES, 'stale', 3), (None, 'failed', 0)])
def test_a_failed_download_keeps_the_stored_copy_and_its_note(
    conn, monkeypatch, scores, expected, weapons
):
    # What every run does while the repo is private: the copy pulled by hand
    # stays, noted as such.
    def fetch_scores():
        raise requests.HTTPError('404 Client Error: Not Found')

    if scores:
        perk_popularity.save(conn, scores)
    source_status.save(conn, 'perk_popularity', 'stale', NOTE)
    monkeypatch.setattr(perk_popularity.source, 'fetch_scores', fetch_scores)
    perk_popularity.extract(conn)
    assert status(conn) == (expected, NOTE)
    assert len(rows(conn, "SELECT * FROM perk_popularity_weapon")) == weapons
