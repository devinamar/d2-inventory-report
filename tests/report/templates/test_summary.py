# Tests for the report's Summary page (report/templates/summary.html.j2): the
# player, the headline counts, the armor to purge by reason and the data
# sources panel.
import re

import pytest

from extract import source_status
from tests import conftest as c


def vault(conn):
    # A rifle in three copies, two with a wishlist match and one no list
    # covers; a set past its cap of 1 in a slot; and two copies of an exotic.
    c.add_weapon_def(conn, 100, sockets=[c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A])
    for instance_id, matches, covered in (('w1', 1, 1), ('w2', 1, 1), ('w3', 0, 0)):
        c.add_copy(conn, instance_id, 100, [c.INTRINSIC_ADAPTIVE, c.TRAIT_PERK_A], gear_tier=5)
        with conn:
            conn.execute(
                "INSERT INTO weapon_result VALUES (?, ?, ?)", (instance_id, matches, covered)
            )
    c.add_preference(conn, 'Test Set', 'F', rank=1, stats=('health',))
    c.add_armor(conn, 'a1', {'health': 30}, set_name='Test Set', score=90)
    c.add_armor(conn, 'a2', {'health': 25}, set_name='Test Set', score=75)
    c.add_armor(conn, 'e1', {'melee': 30}, exotic=True, name='Test Exotic', score=80)
    c.add_armor(conn, 'e2', {'melee': 20}, exotic=True, name='Test Exotic', score=60)


def summary_page(conn, folder):
    html, _ = c.write_report(conn, folder)
    return c.report_page(html, 'summary')


def test_the_header_names_the_player_and_its_button_copies_every_purge(conn, tmp_path):
    vault(conn)
    page = summary_page(conn, tmp_path)
    assert 'Name<span>#1234</span>' in page
    assert 'class="dim purge" data-q="id:a2 or id:e2">Copy purge IDs</button>' in page


def test_the_headline_counts(conn, tmp_path):
    # The live vault's are 615 weapons, 499 armor pieces, 79 to review, 224
    # copies with matches, 155 missing entries and 86 to purge.
    vault(conn)
    page = summary_page(conn, tmp_path)
    assert '<b class="num">3</b> weapons</span><span><b class="num">4</b> armor pieces' in page
    assert '<span class="num">1</span> to review' in page
    for count, fact in (
        (0, 'true duplicates'),
        (2, 'copies with wishlist matches'),
        (1, 'copies missing wishlist entries'),
    ):
        assert f'<dt class="num">{count}</dt><dd>{fact}</dd>' in page
    assert '<span class="num purge">2</span> to purge' in page


def test_the_purge_split_by_reason(conn, tmp_path):
    # Most first; here one each: a piece past its set's cap, an extra exotic
    # copy and a legacy piece.
    vault(conn)
    c.add_armor(conn, 'old', {'health': 10}, set_name='Old Set', tuning=(), gear_tier=None)
    page = summary_page(conn, tmp_path)
    reasons = re.findall(r'<span class="num">(\d+)</span><span>([^<]+)</span></li>', page)
    assert reasons == [
        ('1', 'Low score'),
        ('1', 'Extra exotic copies'),
        ('1', 'Legacy, before Armor 3.0'),
    ]


@pytest.mark.parametrize(
    'aegis, state, cell',
    [
        ('fresh', 'All 6 up to date', '<span class="status">Up to date</span>'),
        (
            'stale',
            '1 source has a problem',
            '<span class="status bad">Download failed: the last good copy is used</span>',
        ),
    ],
    ids=['all up to date', 'one stale'],
)
def test_the_data_sources_panel_says_whether_every_source_is_up_to_date(
    conn, tmp_path, aegis, state, cell
):
    vault(conn)
    for source in ('manifest', 'profile', 'dim', 'clarity', 'perk_popularity'):
        source_status.save(conn, source, 'fresh')
    source_status.save(conn, 'aegis', aegis)
    page = summary_page(conn, tmp_path)
    assert state in page
    assert cell in page
