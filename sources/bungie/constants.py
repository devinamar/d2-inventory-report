# The profile API components the app requests for each run:
#   102 = ProfileInventories (vault)
#   201 = CharacterInventories
#   205 = CharacterEquipment
#   300 = ItemInstances
#   304 = ItemStats
#   305 = ItemSockets (the plug in each socket)
#   309 = ItemPlugObjectives (kill trackers and other plug progress)
#   310 = ItemReusablePlugs (the plugs each socket can switch to)
PROFILE_COMPONENTS = [102, 201, 205, 300, 304, 305, 309, 310]
