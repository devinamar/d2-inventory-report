# Tests for The Aegis's set-bonus rankings (analyze/aegis_rankings.py), read
# from what extract/aegis.py stored. Set names match after normalizing: 4 of
# the live vault's 52 sets are named "... Set", which the sheet leaves off.
import models
from analyze import aegis_rankings
from extract import aegis

BONUSES = [
    models.AegisBonus(
        'Ferropotent', 2, 'Rapid Repair', tags=('survivability',), rank=26, grade='B'
    ),
    models.AegisBonus('Ferropotent', 4, 'Built From Scratch', trigger='a\nb', rank=61, grade='C'),
    models.AegisBonus('Iron Panoply', 4, 'Panoply', source='Iron Banner', rank=19, grade='B'),
]


def test_set_takes_its_best_ranked_bonus(conn):
    aegis.save(conn, BONUSES)

    aegis_data = aegis_rankings.load(conn)
    ranking = aegis_rankings.get_aegis_ranking(aegis_data, 'Ferropotent')
    assert (ranking.grade, ranking.rank, ranking.pieces) == ('B', 26, 2)
    assert aegis_rankings.get_aegis_ranking(aegis_data, 'Iron Panoply Set').rank == 19
    assert aegis_rankings.get_aegis_ranking(aegis_data, 'Unknown') is None
    assert [b.pieces for b in aegis_rankings.get_aegis_bonuses(aegis_data, 'ferropotent')] == [2, 4]
