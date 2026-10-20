# Tests for the report's page shell (report/templates/page.html.j2): a tab and a
# section for each page.
from tests import conftest as c

PAGES = ('summary', 'weapons', 'armor', 'builds', 'exotics', 'preferences')


def test_every_page_has_its_tab_and_its_section(conn, tmp_path):
    c.add_weapon_def(conn, 100)
    c.add_copy(conn, 'w1', 100, c.WEAPON_SOCKETS)
    html, _ = c.write_report(conn, tmp_path)
    for page in PAGES:
        assert f'id="page-{page}"' in html
        assert f'href="#{page}"' in html
