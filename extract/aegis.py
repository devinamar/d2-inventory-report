# Aegis extract: saves The Aegis's armor set-bonus rankings to the
# aegis_bonus table. A failed download or an empty parse keeps the last good
# copy.
from extract import source_status
from sources import aegis as source


def has_bonuses(conn) -> bool:
    return conn.execute("SELECT 1 FROM aegis_bonus LIMIT 1").fetchone() is not None


def save(conn, bonuses: list) -> None:
    # Replace the stored rankings with bonuses ([AegisBonus]).
    with conn:
        conn.execute("DELETE FROM aegis_bonus")
        conn.executemany(
            "INSERT OR REPLACE INTO aegis_bonus VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    b.set_name,
                    b.pieces,
                    b.bonus_name,
                    b.source,
                    b.season,
                    '\n'.join(b.tags),
                    b.trigger,
                    b.effect,
                    b.analysis,
                    b.rank,
                    b.grade,
                )
                for b in bonuses
            ],
        )


def extract(conn) -> None:
    try:
        bonuses = source.parse_csv(source.fetch_csv())
        if not bonuses:
            raise ValueError("the sheet parsed empty")
    except Exception as e:
        print(f"  Warning: Aegis set-bonus sheet unavailable, using the stored copy: {e}")
        if has_bonuses(conn):
            status = 'stale'
        else:
            status = 'failed'
        source_status.save(conn, 'aegis', status)
        return
    save(conn, bonuses)
    source_status.save(conn, 'aegis', 'fresh')
    sets = len({b.set_name for b in bonuses})
    print(f"  Aegis: {len(bonuses)} set bonuses ranked across {sets} sets.")
