# Perk popularity extract: saves d2-perk-popularity's scores as published, one
# row per weapon in perk_popularity_weapon (its scored columns and their perks
# kept as JSON) and the file's settings and categories in perk_popularity_file.
# A failed download keeps the stored copy and its detail (the file's
# generated_at, or a note for a copy pulled by hand).
import json

from extract import source_status
from sources import perk_popularity as source


def has_scores(conn) -> bool:
    return conn.execute("SELECT 1 FROM perk_popularity_weapon LIMIT 1").fetchone() is not None


def save(conn, scores: dict) -> None:
    # Replace the stored scores with scores (perk_scores.json, parsed).
    weapons = [
        (
            side,
            w['name'],
            w['family'],
            w['type'],
            w['item_hash'],
            json.dumps(w['item_hashes']),
            w['rank'],
            w['players'],
            w['active_players'],
            w['hard'],
            w['hard_weight'],
            w['last_seen'],
            w['stale'],
            json.dumps(w['groups']),
            json.dumps(w['columns']),
        )
        for side in ('pve', 'pvp')
        for w in scores[side]
    ]
    with conn:
        conn.execute("DELETE FROM perk_popularity_weapon")
        conn.execute("DELETE FROM perk_popularity_file")
        conn.executemany(
            f"INSERT INTO perk_popularity_weapon VALUES ({', '.join('?' * 15)})",
            weapons,
        )
        conn.execute(
            "INSERT INTO perk_popularity_file VALUES (?, ?, ?)",
            (
                scores['generated_at'],
                json.dumps(scores['settings']),
                json.dumps(scores['categories']),
            ),
        )


def extract(conn) -> None:
    # Download and save the scores; on a failure, keep the stored copy.
    stored_detail = source_status.detail(conn, 'perk_popularity')
    try:
        scores = source.fetch_scores()
        if not scores['pve'] and not scores['pvp']:
            raise ValueError("perk_scores.json lists no weapons")
    except Exception as e:
        print(f"  Warning: perk popularity scores unavailable, using the stored copy: {e}")
        if has_scores(conn):
            status = 'stale'
        else:
            status = 'failed'
        source_status.save(conn, 'perk_popularity', status, stored_detail)
        return
    save(conn, scores)
    source_status.save(conn, 'perk_popularity', 'fresh', scores['generated_at'])
    print(
        f"  Perk popularity: {len(scores['pve'])} PvE and {len(scores['pvp'])} PvP weapons "
        f"scored ({scores['generated_at']})."
    )
