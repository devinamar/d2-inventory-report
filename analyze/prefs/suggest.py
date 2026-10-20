# Best-guess stat priorities from set-bonus and exotic-effect text, by
# keyword. Advisory only: shown while picking stats, never applied
# automatically.
import re

import models

# Keywords per stat (Armor 3.0 stat names). A stat scores one point per
# keyword occurrence.
SUGGEST_KEYWORDS = {
    'health': [
        r'heal',
        r'\bcure',
        r'restorat',
        r'recover',
        r'shield',
        r'overshield',
        r'resist',
        r'resilien',
        r'flinch',
        r'surviv',
        r'frost armor',
        r'woven mail',
        r'devour',
        r'damage reduction',
    ],
    'melee': [r'melee'],
    'grenade': [r'grenade(?!\s+launcher)'],
    'super_stat': [r'\bsuper', r'orb of power', r'orbs of power'],
    'class_stat': [
        r'class abilit',
        r'\brift',
        r'barricade',
        r'\bdodge',
        r'thruster',
        r'phoenix dive',
    ],
    'weapons': [
        r'weapon',
        r'reload',
        r'handling',
        r'stabilit',
        r'\brange',
        r'\baim',
        r'\bammo',
        r'precision',
        r'\bdraw',
        r'\bstow',
        r'\bswap',
        r'\bbow\b',
        r'shotgun',
        r'sword',
        r'hand cannon',
        r'auto rifle',
        r'scout',
        r'pulse',
        r'sidearm',
        r'fusion',
        r'rocket',
        r'machine gun',
        r'submachine',
        r'glaive',
        r'sniper',
        r'kinetic',
        r'primary ammo',
        r'special ammo',
    ],
}


SUGGEST_PATTERNS = {stat: [re.compile(p) for p in pats] for stat, pats in SUGGEST_KEYWORDS.items()}


def suggest_stats(*texts) -> list:
    # Up to three stats, best first, scored by keyword hits across texts; []
    # when nothing matches. A 2-piece that heals and a 4-piece about melee
    # suggest ['health', 'melee'].
    blob = ' '.join(t for t in texts if t).lower()
    if not blob:
        return []
    scored = []
    for idx, stat in enumerate(models.ARMOR_STAT_NAMES):
        score = sum(len(p.findall(blob)) for p in SUGGEST_PATTERNS[stat])
        if score:
            scored.append((score, idx, stat))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [stat for _, _, stat in scored[:3]]
