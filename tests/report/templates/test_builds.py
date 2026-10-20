# Tests for the report's Builds page (report/templates/builds.html.j2): per
# class, the three-stat builds the kept armor covers, the ones it leaves
# short, and the pieces kept past their cap for a build. The live vault shows
# all three: the Warlock covers 16 builds, the Titan and Hunter none, and 2
# pieces are kept for builds.
from tests import conftest as c

SLOTS = ('Helmet', 'Gauntlets', 'Chest Armor', 'Leg Armor', 'Class Armor')


def builds_page(conn, folder):
    html, _ = c.write_report(conn, folder)
    return c.report_page(html, 'builds')


def test_a_class_lists_its_short_builds(conn, tmp_path):
    # 20 in health, melee and grenade in every slot covers that build, at 100
    # each; the other 19 fall short, each card with its three totals.
    for slot in SLOTS:
        stats = {'health': 20, 'melee': 20, 'grenade': 20}
        c.add_armor(conn, slot, stats, set_name='Test Set', slot=slot, score=100)
    page = builds_page(conn, tmp_path)
    assert (
        '<span class="num keep">1</span> of 20 builds covered · '
        '<span class="num purge">19</span> short'
    ) in page
    assert (
        '<h3>health · melee · super_stat</h3><span class="short-by">Short by 100</span>'
    ) in page


def test_a_class_no_build_covers_says_why(conn, tmp_path):
    c.add_armor(conn, 't1', {'health': 30}, armor_class='Titan', score=100)
    page = builds_page(conn, tmp_path)
    assert (
        'No build reaches 100: the Titan has 1 Legendary piece, not enough to add up to 100 '
        'in three stats.'
    ) in page


def test_pieces_kept_for_a_build_are_listed(conn, tmp_path):
    # With the build they're kept for and the lowest of its three totals.
    c.add_preference(conn, 'Test Set', 'F')
    c.add_armor(conn, 'a1', {'health': 30}, set_name='Test Set', score=100)
    with conn:
        conn.execute("INSERT INTO armor_rescue VALUES ('a1', 'health', 'melee', 'grenade', 100)")
    page = builds_page(conn, tmp_path)
    assert '<h2>Kept for builds</h2>' in page
    assert '<h3>health · melee · grenade</h3><span class="num keep">lowest 100</span>' in page
    assert '<li><b>Test Set Helmet</b><span>Helmet · Test Set, grade F</span></li>' in page
