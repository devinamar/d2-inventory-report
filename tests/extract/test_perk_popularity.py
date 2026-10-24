# Tests for the perk popularity step (extract/perk_popularity.py): the scores
# file lands in perk_popularity_weapon and perk_popularity_file, a new file
# replaces the stored one, and a failed download keeps the stored copy and its
# note. The sample is trimmed from the scores of 2026-10-23: Found Verdict's PvP
# magazine, the origin column of Reckless Endangerment, which no hard-content
# copy voted in, and The Jade Rabbit, a fixed roll with no columns.
import json

import pytest
import requests

from extract import perk_popularity, source_status

GENERATED_AT = '2026-10-23T23:51:33Z'
FOUND_VERDICT = {
    'name': 'Found Verdict',
    'type': 'Shotgun',
    'item_hash': 694500607,
    'rank': 45,
    'players': 189,
    'active_players': 189,
    'hard': True,
    'hard_weight': 0.699,
    'groups': {'hard': {'copies': 53, 'n_eff': 52.5}, 'normal': {'copies': 140, 'n_eff': 136.8}},
    'last_seen': '2026-10-23T22:13:09Z',
    'stale': False,
    'columns': [
        {
            'kind': 'magazine',
            'n_eff': 100.2,
            'credibility': 0.77,
            'confidence': 'high',
            'hard': {'n_eff': 52.5, 'credibility': 0.64},
            'normal': {'n_eff': 136.8, 'credibility': 0.82},
            'perks': [
                {
                    'perk': 'Accurized Rounds',
                    'share': 0.762,
                    'low': 0.67,
                    'high': 0.835,
                    'hard': 0.798,
                    'normal': 0.678,
                },
                {
                    'perk': 'Assault Mag',
                    'share': 0.094,
                    'low': 0.051,
                    'high': 0.167,
                    'hard': 0.077,
                    'normal': 0.135,
                },
            ],
        }
    ],
}
RECKLESS_ENDANGERMENT = {
    'name': 'Reckless Endangerment',
    'type': 'Shotgun',
    'item_hash': 3085559077,
    'rank': 361,
    'players': 38,
    'active_players': 38,
    'hard': False,
    'hard_weight': 0.224,
    'groups': {'hard': {'copies': 2, 'n_eff': 1.5}, 'normal': {'copies': 36, 'n_eff': 28.4}},
    'last_seen': '2026-10-23T21:43:30Z',
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
        ('pve', 'Reckless Endangerment', 361, 0, 0, 2, 1),
        ('pvp', 'The Jade Rabbit', 7, 1, 0, 188, 0),
        ('pvp', 'Found Verdict', 45, 1, 0, 53, 1),
    ]
    found_verdict = conn.execute(
        "SELECT columns FROM perk_popularity_weapon WHERE name = 'Found Verdict'"
    ).fetchone()[0]
    assert json.loads(found_verdict) == FOUND_VERDICT['columns']
    assert rows(
        conn,
        "SELECT columns ->> '$[0].kind', columns ->> '$[0].hard', "
        "columns ->> '$[0].perks[0].perk', columns ->> '$[0].perks[0].hard' "
        "FROM perk_popularity_weapon WHERE name = 'Reckless Endangerment'",
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
