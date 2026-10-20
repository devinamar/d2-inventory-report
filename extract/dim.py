# DIM extract: copies the player's DIM tags and notes into item_dim. Without a
# Bungie login or a DIM API key (DIM_API_KEY in .env) the sync is skipped;
# when DIM fails, the previously stored DIM data stays.
import os

from extract import source_status
from sources.bungie.connect import Session
from sources.dim.client import DIMClient


def save(conn, tags: dict) -> None:
    # Rewrite item_dim. DIM also knows items the inventory doesn't hold
    # (postmaster, dismantled copies), so only instance_ids in
    # DestinyItemComponent are saved; the foreign key would reject the rest.
    known = {r[0] for r in conn.execute("SELECT itemInstanceId FROM DestinyItemComponent")}
    with conn:
        conn.execute("DELETE FROM item_dim")
        for iid, ann in tags.items():
            if iid not in known:
                continue
            conn.execute(
                "INSERT INTO item_dim (instance_id, tag, notes) VALUES (?, ?, ?)",
                (iid, ann.tag, ann.notes),
            )


def has_dim_data(conn) -> bool:
    return conn.execute("SELECT 1 FROM item_dim LIMIT 1").fetchone() is not None


def extract(conn, session: Session) -> None:
    print("\nSyncing with DIM...")
    api_key = os.environ.get("DIM_API_KEY", "")
    if not session.has_oauth or not api_key:
        print(f"  No {'Bungie login' if api_key else 'DIM API key'} — skipping DIM sync")
        source_status.save(conn, 'dim', 'skipped')
        return
    try:
        client = DIMClient(api_key)
        if not client.authenticate(session.oauth.access_token, session.oauth.membership_id):
            print("  DIM auth failed — continuing without DIM sync")
            if has_dim_data(conn):
                status = 'stale'
            else:
                status = 'failed'
            source_status.save(conn, 'dim', status)
            return
        print("  DIM authenticated")

        tags = client.fetch_tags(session.membership_id)
        print(f"  DIM tags loaded: {len(tags)} items annotated")

        save(conn, tags)
        source_status.save(conn, 'dim', 'fresh')
    except Exception as e:
        print(f"  DIM sync failed: {e}")
        if has_dim_data(conn):
            status = 'stale'
        else:
            status = 'failed'
        source_status.save(conn, 'dim', status)
