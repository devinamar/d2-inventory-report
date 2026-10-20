# Tests for v_armor_perk (db/schema/views/v_armor_perk.sql): the intrinsic
# perks plugged into each armor copy.
from tests import conftest as c


def test_armor_perks_are_the_plugged_intrinsics(conn):
    # The copy's own plug, not the definition's starting one.
    c.add_armor_def(conn, 300, name='Heart', set_name='', tier=6, sockets=[c.INTRINSIC_ADAPTIVE])
    c.add_copy(conn, 'x1', 300, [c.INTRINSIC_AGGRESSIVE])
    perks = conn.execute("SELECT perk FROM v_armor_perk WHERE instance_id = 'x1'").fetchall()
    assert [r['perk'] for r in perks] == ['Aggressive Frame']
