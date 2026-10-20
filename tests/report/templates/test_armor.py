# Tests for the report's Armor sets page (report/templates/armor.html.j2): each
# set with a piece to purge or kept for a build, its pieces' scores, badges and
# tuning, and the queries and chevrons that act on them.
from tests import conftest as c


def vault(conn):
    # A set past its cap of 1: a2 scores lower, a3 is an exact copy of a1, and
    # a4 is past the cap but kept for a build. A second set has nothing
    # flagged.
    c.add_preference(conn, 'Test Set', 'F', rank=1, stats=('health',))
    c.add_armor(conn, 'a1', {'health': 30}, set_name='Test Set', score=90)
    c.add_armor(conn, 'a2', {'health': 25}, set_name='Test Set', tuning=('melee',), score=75)
    c.add_armor(conn, 'a3', {'health': 30}, set_name='Test Set', score=90)
    c.add_armor(conn, 'a4', {'melee': 20}, set_name='Test Set', tuning=('melee',), score=60)
    c.add_armor(conn, 'k1', {'grenade': 30}, set_name='Kept Set', slot='Gauntlets', score=90)
    with conn:
        conn.execute("UPDATE armor_score SET tuning_gain = 10 WHERE instance_id = 'a1'")
        conn.execute("INSERT INTO armor_rescue VALUES ('a4', 'health', 'melee', 'grenade', 100)")


def armor_page(conn, folder):
    vault(conn)
    html, _ = c.write_report(conn, folder)
    return c.report_page(html, 'armor')


def test_a_sets_pieces_show_their_scores_and_badges(conn, tmp_path):
    # Purge for one past the cap, Dupe for an exact copy, Keep with the build
    # it's kept for; stats show as their icons.
    page = armor_page(conn, tmp_path)
    assert '<span class="score">75</span>\n<span class="chip">Purge</span>' in page
    assert '<span class="score">90</span>\n<span class="chip">Dupe</span>' in page
    assert '<span class="chip keep">Keep:<img src="https://www.bungie.net/img/health.png"' in page
    assert 'alt="health" width="16" height="16">30</span>' in page


def test_the_tuning_stats_are_boxed_and_the_gain_shown(conn, tmp_path):
    # a1 tunes health, boxed; a2 tunes melee, which it lacks: boxed, greyed.
    page = armor_page(conn, tmp_path)
    assert '<span class="tuned" title="health"><img' in page
    assert '<span class="tuned zero" title="melee"><img' in page
    assert '+10 from tuning' in page


def test_sets_and_classes_roll_up_and_each_set_has_its_purge_query(conn, tmp_path):
    # A set card, open at first, closes by its name; a class's sets roll up or
    # down together by the double chevron leading its count.
    page = armor_page(conn, tmp_path)
    assert 'aria-expanded="true" aria-controls="set-a1"' in page and 'id="set-a1">' in page
    assert (
        '<span><button type="button" class="expand" aria-expanded="true" aria-label="Collapse all"'
    ) in page
    assert 'Test Set' in page and 'data-q="id:a3 or id:a2">Copy purge IDs</button>' in page


def test_a_set_with_nothing_flagged_is_left_out(conn, tmp_path):
    # Only the Markdown lists it.
    page = armor_page(conn, tmp_path)
    assert 'Kept Set' not in page and 'alt="grenade" width="16" height="16">30' not in page
