# Tests for the report's Exotics page (report/templates/exotics.html.j2): each
# exotic with copies to purge.
from tests import conftest as c


def test_exotic_tiles_show_no_tuning(conn, tmp_path):
    # A Tier 5 exotic can tune any stat, so tuning doesn't tell its copies
    # apart.
    c.add_armor(conn, 'e1', {'melee': 30}, exotic=True, name='Test Exotic', score=80)
    c.add_armor(conn, 'e2', {'melee': 20}, exotic=True, name='Test Exotic', score=60)
    html, _ = c.write_report(conn, tmp_path)
    page = c.report_page(html, 'exotics')
    assert 'Test Exotic' in page
    assert 'class="tuned' not in page
