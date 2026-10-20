# Tests for saving the analysis results (analyze/results.py).
from analyze import results
from tests import conftest as c

BUILD = ('health', 'melee', 'grenade')


def test_saving_new_scores_clears_the_old_rescues(conn):
    # The rescue search runs after the scores are saved and reads the kept
    # pieces, so last run's rescues must already be gone.
    c.add_armor(conn, 'a1', {'health': 30}, score=100)
    results.save_armor_rescue(conn, {'a1': [(BUILD, 100)]})
    results.save_armor_scores(conn, {})
    assert conn.execute("SELECT COUNT(*) FROM armor_rescue").fetchone()[0] == 0
