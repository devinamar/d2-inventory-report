# Tests for v_stat_icon (db/schema/views/v_stat_icon.sql): the icon of each
# stat the app names.


def test_a_stat_icon_is_a_full_url(conn):
    rpm = conn.execute("SELECT icon FROM v_stat_icon WHERE key = 'rpm'").fetchone()[0]
    assert rpm == 'https://www.bungie.net/img/rpm.png'
