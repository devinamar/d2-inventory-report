# The app's own names for the Bungie stats it reads.

# Stat hash -> the app's name for it: the six armor stats and a weapon's
# rounds per minute. Edge of Fate renamed the six armor stats but kept their
# hashes; the old names are noted for reference. Written to stat_key each run
# for the views.
STAT_KEYS = {
    392767087: 'health',  # was Resilience
    4244567218: 'melee',  # was Strength
    1735777505: 'grenade',  # was Discipline
    144602215: 'super_stat',  # was Intellect
    1943323491: 'class_stat',  # was Recovery
    2996146975: 'weapons',  # was Mobility
    4284893193: 'rpm',
}
