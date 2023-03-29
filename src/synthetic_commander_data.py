import pandas as pd
import numpy as np

# create dummy data for commander damage
# these are in order of battle
boss_names = ['Thermite', 'Loud_Mouth', 'Black_Smith', 'Plate', 'Modernia']
usernames = [
    "AuroraBorealis",
    "CrimsonBlade",
    "ShadowWalker",
    "MysticDreamer",
    "SilentAssassin",
    "LunarEclipse",
    "OceanSoul",
    "EmeraldEyes",
    "CelestialSiren",
    "ThunderClap",
    "MysticGoddess",
    "IceQueen",
    "GalacticWarrior",
    "EnigmaGamer",
    "GoldenGoddess",
    "RubyKnight",
    "SilverSamurai",
    "ShadowPhoenix",
    "CelestialWarrior",
    "Dragonborn",
    "PhantomReaper",
    "FrostyNinja",
    "StormyKnight",
    "SkyDragoness",
    "ObsidianKnight",
    "MysticSamurai",
    "ThunderousShadow",
    "FlamePhoenix",
    "EmeraldEnigma",
    "InfernoKnight",
    "ShadowShifter",
    "CrystalGuardian"
]
N_commanders = len(usernames)
N_levels = 10
# create multi-index dataframe on boss and level
index = pd.MultiIndex.from_product([boss_names, range(N_levels)], names=['boss', 'level'])
# create random data
# damage decreases linearly as level increases
# damage also decreases linearly as commander number increases
lb_dmg = 1e6
ub_dmg = 5e8
commander_damage = {}
for l in range(N_levels):
    for boss in boss_names:
        commander_damage[boss, l] = {}
        for i in range(N_commanders):
            commander_damage[boss, l][usernames[i]] = int(np.random.randint(lb_dmg, ub_dmg) * (1 - (i/N_commanders)) * (1 - (l/N_levels)))
# convert to dataframe
commander_damage = pd.DataFrame(commander_damage)
# transpose to get the correct format
commander_damage = commander_damage.T
# convert to csv
commander_damage.to_csv('commander_damage.csv')
