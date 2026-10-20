# Tests for the stat suggestions the editor shows while picking
# (analyze/prefs/suggest.py), guessed from set-bonus and exotic text.
from analyze.prefs import suggest


def test_healing_and_melee_text_suggests_health_then_melee():
    out = suggest.suggest_stats(
        'Performing a finisher heals you and starts health regeneration.',
        'Your melee hits release a burst.',
    )
    assert out and out[0] == 'health' and 'melee' in out


def test_weapon_text_suggests_weapons():
    out = suggest.suggest_stats('Bow, Shotgun, or Sword final blows; reload and handling bonus.')
    assert out[0] == 'weapons'


def test_a_grenade_launcher_isnt_the_grenade_stat():
    out = suggest.suggest_stats('Final blows with a Rocket Launcher or Grenade Launcher.')
    assert out[0] == 'weapons'
    assert 'grenade' not in out


def test_no_text_suggests_nothing():
    assert suggest.suggest_stats('', None) == []
