# Clarity extract: saves Clarity's community perk descriptions to the
# clarity_note table. dim.json is downloaded only when Clarity's version
# differs from the stored copy's (kept in source_status); if nothing can be
# fetched, the stored copy stays.
from extract import source_status
from sources import clarity as source


def has_notes(conn) -> bool:
    return conn.execute("SELECT 1 FROM clarity_note LIMIT 1").fetchone() is not None


def save(conn, notes: dict) -> None:
    # Replace the stored descriptions with notes ({plug_hash: text}).
    with conn:
        conn.execute("DELETE FROM clarity_note")
        conn.executemany("INSERT INTO clarity_note VALUES (?, ?)", notes.items())


def extract(conn) -> None:
    # Download, parse and save dim.json when Clarity has a new version.
    stored_version = source_status.detail(conn, 'clarity')
    try:
        version = source.fetch_version()
        if version == stored_version and has_notes(conn):
            source_status.save(conn, 'clarity', 'cached', version)
            return
        print("  Downloading Clarity database...")
        notes = source.parse_clarity_json(source.fetch_descriptions())
        if not notes:
            raise ValueError("dim.json holds no descriptions")
    except Exception as e:
        print(f"  Warning: Clarity database unavailable: {e}")
        if has_notes(conn):
            status = 'stale'
        else:
            status = 'failed'
        source_status.save(conn, 'clarity', status, stored_version)
        return
    save(conn, notes)
    source_status.save(conn, 'clarity', 'fresh', version)
