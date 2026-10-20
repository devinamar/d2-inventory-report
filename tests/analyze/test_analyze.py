# Tests for the analysis steps (analyze/analyze.py): which sets and exotics a
# run checks for a preference before scoring. The editor, which asks about
# those without one, is a stand-in that records what it was given.
from analyze import analyze
from tests import conftest as c


def piece(instance_id, name, gear_tier, set_name='', exotic=False):
    # An armor copy; no gear tier means legacy, from before Armor 3.0.
    armor = c.make_armor(name=name, set_name=set_name, is_exotic=exotic)
    return c.make_armor_inst(armor, instance_id, gear_tier=gear_tier)


def test_every_armor_3_0_set_and_exotic_is_checked_for_a_preference(conn, monkeypatch):
    # An Armor 3.0 piece of any gear tier brings in its set or exotic, and so
    # do two copies of an exotic of any tier, grouped ignoring case. A legacy
    # piece brings in nothing.
    pieces = [
        piece('a1', 'Shrewd Survivor Cloak', 2, set_name='Shrewd Survivor'),
        piece('a2', 'Bushido Helm', 5, set_name='Bushido'),
        piece('a3', 'Frumious Vest', None, set_name='Frumious'),
        piece('x1', 'Solipsism', 5, exotic=True),
        piece('x2', 'Cenotaph Mask', None, exotic=True),
        piece('x3', 'CENOTAPH MASK', None, exotic=True),
        piece('x4', 'Apotheosis Veil', None, exotic=True),
    ]
    checked = []

    def ensure_preferences(sets_needed, exotics_needed, armor_instances, prefs, aegis):
        checked.append((sorted(sets_needed), sorted(exotics_needed)))
        assert (armor_instances, aegis) == (pieces, {})  # every piece; no Aegis rankings stored
        return prefs, False

    monkeypatch.setattr(analyze.editor, 'ensure_preferences', ensure_preferences)
    analyze.ensure_preferences(conn, pieces)
    assert checked == [(['Bushido', 'Shrewd Survivor'], ['Cenotaph Mask', 'Solipsism'])]
