# How each external source fared this run (the source_status table). Every
# extract step records its source; the report's data sources table reads the
# rows back.
import datetime


def save(conn, source: str, status: str, detail: str = '') -> None:
    # Record this run's status for source ('fresh', 'cached', 'stale',
    # 'failed' or 'skipped'; see db/schema/app/source_status.sql),
    # stamped with the current time.
    with conn:
        conn.execute(
            "INSERT INTO source_status VALUES (?, ?, ?, ?) "
            "ON CONFLICT(source) DO UPDATE SET "
            "  status = excluded.status, "
            "  checked_at = excluded.checked_at, "
            "  detail = excluded.detail",
            (source, status, datetime.datetime.now().isoformat(timespec='seconds'), detail),
        )


def detail(conn, source: str) -> str:
    # The detail stored with source's last status; '' when there is none.
    row = conn.execute("SELECT detail FROM source_status WHERE source = ?", (source,)).fetchone()
    if row:
        return row['detail']
    return ''
