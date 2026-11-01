"""Game data: rarities, mutations, islands, fish, rods, boats, gear, bait, enchantments, quests and pets."""
from .util import D


def T(**k):
    return D(k)


# ---------------- Rarities (base spawn weights add up to 100%) ----------------
# size: how much bigger a fish of this rarity looks than a common one of the same build.
RAR = [
    T(id='common', name='Common', w=54.5, col='#c3ced6', diff=1.0, xp=6),
    T(id='uncommon', name='Uncommon', w=25, col='#62d672', diff=1.25, xp=11),
    T(id='rare', name='Rare', w=12, col='#4aa8ff', diff=1.6, xp=22),
    T(id='epic', name='Epic', w=5, col='#b46bff', diff=2.05, xp=45),
    T(id='legendary', name='Legendary', w=2.5, col='#ffb020', diff=2.6, xp=95),
    T(id='mythic', name='Mythic', w=0.99, col='#ff3d7f', diff=3.2, xp=260),
    T(id='leviathan', name='Boss', w=0.01, col='#00ffd5', diff=4.2, xp=2500),   # the id stays 'leviathan' for old saves
]
RI = {r.id: i for i, r in enumerate(RAR)}

# ---------------- Mutations ----------------
MUTS = [
    T(id='albino', name='Albino', mult=2, chance=0.035, col='#ffffff', aura='soft'),
    T(id='electric', name='Electric', mult=3.5, chance=0.017, col='#62f3ff', aura='spark'),
    T(id='gilded', name='Gilded', mult=6, chance=0.008, col='#ffd23d', aura='glitter'),
    T(id='corrupted', name='Corrupted', mult=10, chance=0.003, col='#b02bff', aura='smoke'),
    T(id='prismatic', name='Prismatic', mult=14, chance=0.0015, col='#ff9ad8', aura='glitter'),
    T(id='tideworn', name='Tideworn', mult=8, chance=0.004, col='#8ce1c4', aura='soft'),
    T(id='stormbound', name='Stormbound', mult=11, chance=0.0025, col='#7cf0ff', aura='spark'),
    T(id='moonlit', name='Moonlit', mult=16, chance=0.001, col='#d6c8ff', aura='soft'),
]
MUT = {m.id: m for m in MUTS}
MUT_UPGRADES = {
    'albino': {'targets': [3, 10, 25], 'bonus': [1.12, 1.22, 1.33], 'desc': 'Albino fish are brighter and slightly more valuable.'},
    'electric': {'targets': [3, 10, 25], 'bonus': [1.08, 1.18, 1.28], 'desc': 'Electric mutations spark more often and lure fish in faster.'},
    'gilded': {'targets': [3, 10, 25], 'bonus': [1.16, 1.26, 1.38], 'desc': 'Gilded fish sell for more and feel luckier to catch.'},
    'corrupted': {'targets': [3, 10, 25], 'bonus': [1.12, 1.22, 1.35], 'desc': 'Corrupted catches have a stronger aura and better odds.'},
    'prismatic': {'targets': [3, 10, 25], 'bonus': [1.08, 1.18, 1.3], 'desc': 'Prismatic catches become more valuable.'},
    'tideworn': {'targets': [3, 10, 25], 'bonus': [1.1, 1.2, 1.32], 'desc': 'Tideworn fish bring better luck and value.'},
    'stormbound': {'targets': [3, 10, 25], 'bonus': [1.1, 1.2, 1.32], 'desc': 'Stormbound catches bring more value and mutation luck.'},
    'moonlit': {'targets': [3, 10, 25], 'bonus': [1.08, 1.18, 1.3], 'desc': 'Moonlit catches become rarer and more valuable.'},
}

# ---------------- Islands ----------------
# boat: boat tier needed. lvl: level needed the first time. quest: the island quest that must be finished first.
# short: the name on tabs. link: the island it is charted from. dark: the depth (m) where the water starts going black.
BIOMES = {
    'shore': T(id='shore', name='Starter Shore', short='Shore', depth=180, boat=0, lvl=1, quest=None, x=0.1, y=0.78, link=None, dark=None,
               sky=['#5fb4ff', '#ffd9a0'], water=['#2a9fd6', '#06223f'], floor='#c9b27a',
               desc='A calm bay with a dock, a bait shop and easy fish.'),
    'reef': T(id='reef', name='Coral Reef', short='Reef', depth=450, boat=1, lvl=4, quest='p_shore', x=0.25, y=0.42, link='shore', dark=None,
              sky=['#3fc5ff', '#c2fbff'], water=['#19c2c9', '#04253a'], floor='#f3d9b0',
              desc='Warm shallows, coral towers, the old enchanting altar and an egg hatchery.'),
    'volcano': T(id='volcano', name='Volcanic Biome', short='Volcano', depth=900, boat=2, lvl=8, quest='p_reef', x=0.39, y=0.8, link='reef', dark=None,
                 sky=['#2a1420', '#ff7a3d'], water=['#3b2a35', '#120607'], floor='#2b2224',
                 desc='Lava vents burn unprotected lines. Rich, angry fish.'),
    'trench': T(id='trench', name='Deep Trench Abyss', short='Trench', depth=2000, boat=3, lvl=14, quest='p_volcano', x=0.53, y=0.4, link='volcano', dark=140,
                sky=['#0b0f2a', '#2c3f73'], water=['#123555', '#000004'], floor='#151824',
                desc='Pitch dark below 200 m. Something colossal lives at the bottom.'),
    'pallid': T(id='pallid', name='Pallid Sea', the=True, short='Pallid', depth=1600, boat=4, lvl=20, quest='p_trench', x=0.67, y=0.13, link='trench', dark=420, darkmax=0.8,
                sky=['#5d6670', '#c9ced2'], water=['#4f6f80', '#02070c'], floor='#5a5a58',
                desc='Cold grey whaling waters, a graveyard of whale bones, and the white whale that sank the Pequod.'),
    'frost': T(id='frost', name='Frostbite Shelf', the=True, short='Frost', depth=1400, boat=5, lvl=26, quest='p_pallid', x=0.89, y=0.3, link='pallid', dark=380, darkmax=0.85,
               sky=['#06101e', '#5a8aa0'], water=['#6ac8e0', '#01060c'], floor='#c8d8e0',
               desc='A polar sea under the northern lights. Icebergs, frozen fish and something ancient on the shelf.'),
    'mariana': T(id='mariana', name='Mariana Deep', the=True, short='Mariana', depth=11000, boat=6, lvl=32, quest='p_frost', x=0.87, y=0.64, link='frost', dark=150, darkmax=0.93,
                 sky=['#0a1a3a', '#e88a5a'], water=['#1a7ab8', '#000002'], floor='#2a2a30',
                 desc='The deepest place in the sea: eleven kilometres straight down, where the strange sound came from. Something older waits beyond it.'),
    'loch': T(id='loch', name='Loch Ness', short='Loch', depth=230, boat=3, lvl=18, quest='p_volcano', x=0.3, y=0.13, link='trench', dark=45, darkmax=0.72,
              darkcol=(14, 9, 2), sky=['#5a6670', '#b8c0bc'], water=['#5a4a2a', '#0a0602'], floor='#2a2016',
              desc='A long, cold Highland loch, black with peat below 40 m. Castle ruins on the shore, and something in the water.'),
    'atlantis': T(id='atlantis', name='Ruins of Atlantis', the=True, short='Atlantis', depth=5200, boat=7, lvl=38, quest='p_mariana', x=0.66, y=0.86, link='mariana', dark=250, darkmax=0.8,
                  sky=['#58734f', '#d2bd75'], water=['#4a9b88', '#061d27'], floor='#d9d0ad',
                  desc='A drowned city of pale marble and green-gold light. The last Keeper is still waiting below.'),
    'redhollow': T(id='redhollow', name='Red Hollow', the=True, short='Hollow', depth=1800, boat=7, lvl=1, quest=None, x=0.08, y=0.12, link=None, dark=90, darkmax=0.9, portal=True,
                   sky=['#210c25', '#b32643'], water=['#732c63', '#10051b'], floor='#321c35',
                   desc='A broken mirror of the bay beneath a blood-red moon. The water remembers a different world.'),
}
BIOME_IDS = ['shore', 'reef', 'volcano', 'trench', 'loch', 'pallid', 'frost', 'mariana', 'atlantis', 'redhollow']

# How hard the fish of each island fight, on top of their rarity, and how much XP they give.
# spd: fish speed on the reel bar, zone: your bar width, gain: divides catch speed, loss: progress lost
# when the fish slips out, ten: line tension. Later islands are tougher, and their rods are stronger.
ISLE = {
    'shore': T(i=0, spd=1.0, zone=1.0, gain=1.0, loss=1.0, ten=1.0, xp=1.0),
    'reef': T(i=1, spd=1.02, zone=0.91, gain=1.15, loss=1.06, ten=1.12, xp=1.8),
    'volcano': T(i=2, spd=1.04, zone=0.87, gain=1.35, loss=1.12, ten=1.25, xp=4.0),
    'trench': T(i=3, spd=1.06, zone=0.82, gain=1.55, loss=1.2, ten=1.4, xp=6.0),
    'pallid': T(i=4, spd=1.07, zone=0.80, gain=1.7, loss=1.24, ten=1.52, xp=8.0),
    'frost': T(i=5, spd=1.08, zone=0.79, gain=1.82, loss=1.28, ten=1.62, xp=10.0),
    'mariana': T(i=7, spd=1.10, zone=0.77, gain=2.0, loss=1.32, ten=1.75, xp=13.0),
    'loch': T(i=8, spd=1.06, zone=0.81, gain=1.6, loss=1.22, ten=1.45, xp=7.0),
    'atlantis': T(i=9, spd=1.11, zone=0.76, gain=2.1, loss=1.36, ten=1.82, xp=16.0),
    'redhollow': T(i=6, spd=1.09, zone=0.77, gain=2.0, loss=1.34, ten=1.75, xp=14.0),
}

# ---------------- Fish ----------------
# shape: fish | koi | lion | eel | ray | jelly | squid | puffer | angler | seahorse | leviathan
# len: on-screen length at average weight (rarer fish are drawn much bigger). w: weight range (kg).
# val: base coins. beh: how it fights on the reel bar (calm, dart, erratic, drift, abyss, boss).
# dz: the depth (m) it likes best. It is common within dr metres (default 50) of that depth, and every
# 50 m further away it is about 35 percentage points less likely to show up, so nothing lives everywhere.
FISH = [
    # ----- Starter Shore (0-180 m) -----
    T(id='blenny', name='Tidepool Blenny', b='shore', r='common', shape='fish', len=20, col='#8c8a52', belly='#d9d3a0', fin='#6e6c3e', pat='spots', patc='#4e4c2a', w=[0.02, 0.15], val=11, beh='calm', dz=8, dr=25, desc='Pokes its head out of rock holes and pulls funny faces at you.'),
    T(id='sardine', name='Sardine', b='shore', r='common', shape='fish', len=22, col='#9fb7c9', belly='#eef4f8', fin='#7c97ab', pat='stripe', w=[0.05, 0.3], val=11, beh='calm', dz=20, desc='Travels in nervous silver crowds near the surface.'),
    T(id='mackerel', name='Mackerel', b='shore', r='common', shape='fish', len=28, col='#3f86ad', belly='#dfeef4', fin='#2d6688', pat='bars', w=[0.3, 1.4], val=14, beh='calm', dz=70, desc='Wavy stripes and zero patience.'),
    T(id='seabass', name='Sea Bass', b='shore', r='uncommon', shape='fish', len=40, col='#7d8f86', belly='#e1e6de', fin='#5f6f68', pat='none', w=[0.8, 5], val=44, beh='dart', dz=40, desc='Lurks near the rocks and bolts when it feels the hook.'),
    T(id='flounder', name='Flounder', b='shore', r='uncommon', shape='fish', len=42, col='#a08262', belly='#d9c4a8', fin='#8a6c4e', pat='spots', w=[0.5, 3], val=40, beh='drift', dz=100, desc='Both eyes on one side, which is weird but works. Hides in the sand.'),
    T(id='cod', name='Whiskered Cod', b='shore', r='uncommon', shape='fish', len=46, col='#9a8a5e', belly='#ece6d2', fin='#7a6c48', pat='spots', patc='#6b5c3a', w=[1, 12], val=46, beh='calm', dz=135, desc='Grumpy, always hungry, and has a chin whisker. The cats approve.'),
    T(id='puffer', name='Pufferfish', b='shore', r='rare', shape='puffer', len=46, col='#e0c35a', belly='#fff3c4', fin='#b89a3a', pat='spots', w=[0.5, 3], val=140, beh='erratic', dz=25, desc='Inflates when annoyed. You will annoy it.'),
    T(id='snapper', name='Red Snapper', b='shore', r='rare', shape='fish', len=56, col='#e2553f', belly='#ffd0c3', fin='#b93a28', pat='none', w=[2, 9], val=160, beh='dart', dz=85, desc='A proper dinner fish with a proper temper.'),
    T(id='wolfeel', name='Wolf Eel', b='shore', r='rare', shape='eel', len=88, col='#7d7a78', belly='#b8b2aa', fin='#6a6662', pat='spots', patc='#4a4644', w=[3, 18], val=160, beh='erratic', dz=150, desc='Huge teeth, grumpy face, total softie. Lives in a cave near the bottom.'),
    T(id='sunfish', name='Ocean Sunfish', b='shore', r='epic', shape='fish', len=96, col='#9aa6ae', belly='#e6eaec', fin='#7d8a93', pat='none', w=[250, 1000], val=540, beh='drift', dz=30, desc="The world's heaviest bony fish. Mostly suns itself and thinks about jellyfish."),
    T(id='moonfish', name='Moonfish', b='shore', r='epic', shape='fish', len=100, col='#c8495f', belly='#ffb4c0', fin='#ff6a3d', pat='spots', w=[10, 60], val=520, beh='calm', dz=120, desc='Round, rosy and warm-blooded, which almost no fish is.'),
    T(id='goldtuna', name='Golden Tuna', b='shore', r='legendary', shape='fish', len=128, col='#f2c14e', belly='#fff2c2', fin='#d6941f', pat='none', w=[40, 220], val=2200, beh='calm', glow='#ffd96a', dz=105, rk=0.9, desc='Sailors swear it leaves a trail of coins. The only legend of the bay.'),
    # ----- Coral Reef (0-450 m) -----
    T(id='clown', name='Clownfish', b='reef', r='common', shape='fish', len=22, col='#ff8a2a', belly='#ffc08a', fin='#1d1d1d', pat='bands', patc='#ffffff', w=[0.1, 0.3], val=32, beh='calm', dz=10, dr=25, desc='Lives in an anemone and is very proud of it.'),
    T(id='tang', name='Blue Tang', b='reef', r='common', shape='fish', len=26, col='#2f6bff', belly='#4f8bff', fin='#ffd23d', pat='stripe', patc='#0d1d4d', w=[0.2, 0.6], val=36, beh='calm', dz=35, desc='Forgets things. Swims anyway.'),
    T(id='anthias', name='Rosy Anthias', b='reef', r='common', shape='fish', len=26, col='#ff7aa8', belly='#ffd0e0', fin='#ffb03a', pat='none', w=[0.05, 0.2], val=34, beh='calm', dz=150, desc='Pink, orange and never alone. Hangs off the reef wall in clouds.'),
    T(id='alfonsino', name='Splendid Alfonsino', b='reef', r='common', shape='fish', len=30, col='#e8483a', belly='#ffc2b0', fin='#ff7a5a', pat='none', w=[0.5, 3], val=42, beh='dart', dz=330, dr=70, desc='Enormous eyes for the dim water at the foot of the reef wall.'),
    T(id='parrot', name='Parrotfish', b='reef', r='uncommon', shape='fish', len=46, col='#2fd0a0', belly='#a8f5d8', fin='#ff70b0', pat='scales', w=[1, 6], val=100, beh='calm', dz=20, desc='Chews coral and poops sand. Beaches owe it everything.'),
    T(id='butterfly', name='Butterflyfish', b='reef', r='uncommon', shape='fish', len=36, col='#ffe14d', belly='#fff5b0', fin='#ff9a3c', pat='eye', w=[0.1, 0.5], val=88, beh='drift', dz=50, desc='Wears a fake eye near its tail to confuse you.'),
    T(id='trigger', name='Clown Triggerfish', b='reef', r='uncommon', shape='fish', len=42, col='#1d2438', belly='#f2f2f2', fin='#ffd23d', pat='spots', patc='#ffffff', w=[0.5, 3], val=100, beh='dart', dz=110, desc='Locks its back spine so nothing can pull it out of its hole.'),
    T(id='moray', name='Green Moray', b='reef', r='uncommon', shape='eel', len=84, col='#4e7a2c', belly='#7aa04a', fin='#3e6a22', pat='none', w=[2, 25], val=120, beh='erratic', dz=200, desc='Opens and closes its mouth all day. It is breathing, not threatening. Mostly.'),
    T(id='seahorse', name='Seahorse', b='reef', r='rare', shape='seahorse', len=44, col='#ff9ec7', belly='#ffd6e8', fin='#ff6aa8', pat='none', w=[0.02, 0.1], val=390, beh='drift', dz=25, desc='The dad carries the eggs. Respect.'),
    T(id='lionfish', name='Lionfish', b='reef', r='rare', shape='lion', len=54, col='#d9562e', belly='#ffe0cc', fin='#f6c3a9', pat='bands', patc='#fff1e6', w=[0.5, 1.5], val=340, beh='erratic', dz=70, desc='Venomous fan of a fish. Handle with mittens.'),
    T(id='reefshark', name='Blacktip Reef Shark', b='reef', r='rare', shape='fish', len=76, col='#8a96a2', belly='#eef1f4', fin='#7a8692', pat='none', w=[20, 80], val=410, beh='dart', dz=170, desc='Black-tipped fins and a no-nonsense attitude.'),
    T(id='manta', name='Manta Ray', b='reef', r='epic', shape='ray', len=140, col='#2c3e66', belly='#f2f5fb', fin='#1d2a47', pat='none', w=[200, 1300], val=1300, beh='calm', dz=60, desc='A wingspan longer than your boat.'),
    T(id='wrasse', name='Humphead Wrasse', b='reef', r='epic', shape='fish', len=114, col='#3f9e8c', belly='#9ed8c4', fin='#2e7e70', pat='wrasse', patc='#1f5a50', w=[30, 190], val=1400, beh='calm', dz=230, desc='Big lips, a big bump on its head and a big appetite for spiky things.'),
    T(id='angelcrown', name='Crowned Angelfish', b='reef', r='legendary', shape='fish', len=118, col='#6a3dff', belly='#b99bff', fin='#ffd23d', pat='bands', patc='#ffd23d', w=[1, 4], val=5700, beh='dart', glow='#c9b0ff', dz=110, desc='Royalty of the reef. Knows it.'),
    T(id='coralwyrm', name='Coral Wyrm', b='reef', r='legendary', shape='eel', len=190, col='#ff4fa3', belly='#ffc2df', fin='#ffd23d', pat='spots', patc='#fff2a8', w=[30, 120], val=7600, beh='abyss', glow='#ff8fcf', dz=360, dr=60, desc='Grows out of the deep reef itself, they say. Then leaves.'),
    # ----- Volcanic Biome (0-900 m) -----
    T(id='ashgoby', name='Ash Goby', b='volcano', r='common', shape='fish', len=22, col='#6b6260', belly='#a69e9a', fin='#4a4240', pat='spots', patc='#3a3230', w=[0.1, 0.4], val=74, beh='calm', dz=40, desc='Coated in soot and somehow cheerful. Never strays far from the shallow vents.'),
    T(id='embersmelt', name='Ember Smelt', b='volcano', r='common', shape='fish', len=24, col='#ff7b3a', belly='#ffd2a8', fin='#ff4d1a', pat='stripe', patc='#ffe08a', w=[0.1, 0.3], val=82, beh='dart', glow='#ff9a4a', dz=180, desc='Warm to the touch. Do not touch.'),
    T(id='pumice', name='Pumice Perch', b='volcano', r='common', shape='fish', len=30, col='#9a8e86', belly='#cfc6be', fin='#7a6e66', pat='pores', patc='#6a5e56', w=[0.3, 2], val=88, beh='calm', dz=420, dr=70, desc='Full of tiny holes, so it floats a little. Embarrassing for a fish.'),
    T(id='eelpout', name='Vent Eelpout', b='volcano', r='common', shape='eel', len=58, col='#e8c8b8', belly='#f6e6dc', fin='#d8a898', pat='none', w=[0.2, 1.5], val=96, beh='drift', dz=760, dr=90, desc='Lives right next to boiling vents at the bottom and looks quite relaxed about it.'),
    T(id='basalt', name='Basalt Grouper', b='volcano', r='uncommon', shape='fish', len=48, col='#4a4646', belly='#6e6868', fin='#2f2c2c', pat='scales', w=[5, 30], val=250, beh='calm', dz=120, desc='Heavy as a rock because it mostly is one.'),
    T(id='cindereel', name='Cinder Eel', b='volcano', r='uncommon', shape='eel', len=82, col='#3a2a28', belly='#5a403a', fin='#ff6a1a', pat='cracks', patc='#ff6a1a', w=[2, 12], val=240, beh='erratic', dz=280, desc='Lava glows through cracks in its skin.'),
    T(id='rockfish', name='Scorchfin Rockfish', b='volcano', r='uncommon', shape='fish', len=44, col='#d4552a', belly='#ffc29a', fin='#ff7a3a', pat='mottle', patc='#8a2a10', w=[1, 6], val=280, beh='erratic', dz=560, dr=70, desc='Venomous spines that glow when it is angry, which is always.'),
    T(id='magmapuff', name='Magma Puffer', b='volcano', r='rare', shape='puffer', len=52, col='#ff5a1f', belly='#ffc38a', fin='#c23a12', pat='cracks', patc='#ffe08a', w=[1, 5], val=780, beh='erratic', glow='#ff7a2a', dz=200, desc='Puffs up with boiling water instead of seawater.'),
    T(id='obsidian', name='Obsidian Snapper', b='volcano', r='rare', shape='fish', len=60, col='#1d1b22', belly='#3a3644', fin='#5a4f6e', pat='shine', w=[3, 12], val=870, beh='dart', dz=380, desc='Glassy black scales sharp enough to cut line.'),
    T(id='barracuda', name='Ironjaw Barracuda', b='volcano', r='rare', shape='fish', len=78, col='#6c7480', belly='#d4d8de', fin='#4a5260', pat='bars', patc='#3a404a', w=[5, 40], val=970, beh='dart', dz=640, dr=70, desc='An underbite full of metal-hard teeth. Do not lend it your fingers.'),
    T(id='lavaray', name='Lava Ray', b='volcano', r='epic', shape='ray', len=136, col='#c23a12', belly='#ffb27a', fin='#7a1e08', pat='cracks', patc='#ffd23d', w=[50, 400], val=3200, beh='calm', glow='#ff6a1a', dz=320, desc='Glides over the vents like a burning kite.'),
    T(id='sturgeon', name='Caldera Sturgeon', b='volcano', r='epic', shape='fish', len=124, col='#5a5048', belly='#b8a890', fin='#4a4038', pat='scutes', patc='#e8d0a0', w=[60, 400], val=3600, beh='calm', dz=700, dr=80, desc='Older than the volcano, armoured like a knight, and very hard to argue with.'),
    T(id='phoenix', name='Phoenix Carp', b='volcano', r='legendary', shape='koi', len=126, col='#ff6a00', belly='#ffd23d', fin='#ffd23d', pat='none', w=[8, 30], val=14000, beh='calm', glow='#ffb03a', dz=150, desc='Dies in the lava and is reborn twice as smug.'),
    T(id='seraph', name='Molten Seraph', b='volcano', r='legendary', shape='eel', len=200, col='#ffd27a', belly='#fffbe0', fin='#ff7a1a', pat='cracks', patc='#ffffff', w=[100, 500], val=18000, beh='abyss', glow='#ffe2a0', dz=480, dr=70, desc='White-hot and winged. Looking at it makes your whiskers curl.'),
    T(id='sailfish', name='Blaze Sailfish', b='volcano', r='legendary', shape='fish', len=146, col='#ff6a2a', belly='#ffe2b8', fin='#ff3d1a', pat='bars', patc='#ffe08a', w=[30, 100], val=17000, beh='dart', glow='#ff9a3a', dz=800, dr=70, desc='The fastest fish in the sea, and it is on fire. Raises its burning sail when it hunts.'),
    # ----- Deep Trench Abyss (0-2000 m) -----
    T(id='lantern', name='Lanternfish', b='trench', r='common', shape='fish', len=22, col='#24324a', belly='#4a5a78', fin='#1a2438', pat='dots', patc='#7ffcff', w=[0.02, 0.1], val=150, beh='calm', glow='#7ffcff', dz=280, dr=120, desc='Its glowing dots are how it says hello. Rises toward the surface at night.'),
    T(id='hatchet', name='Hatchetfish', b='trench', r='common', shape='fish', len=24, col='#9aa7b8', belly='#d6dde8', fin='#6a7688', pat='shine', w=[0.05, 0.2], val=170, beh='drift', dz=650, dr=150, desc='Thin as a coin, silver as a coin, worth more than a coin.'),
    T(id='bristle', name='Bristlemouth', b='trench', r='common', shape='fish', len=22, col='#3a3a44', belly='#5a5a68', fin='#2a2a34', pat='photo', patc='#9ff0ff', w=[0.005, 0.02], val=170, beh='calm', glow='#9ff0ff', dz=1000, dr=150, desc='There are more of these than any other animal with a backbone. Nobody has heard of it.'),
    T(id='rattail', name='Rattail', b='trench', r='common', shape='fish', len=34, col='#8a8478', belly='#b8b2a6', fin='#6a6458', pat='none', w=[0.5, 3], val=190, beh='drift', dz=1450, dr=150, desc='A big head, a long whip of a tail and a nose for anything that sinks.'),
    T(id='snailfish', name='Snailfish', b='trench', r='common', shape='fish', len=28, col='#f4c4c8', belly='#fde4e6', fin='#e8a8b0', pat='none', w=[0.1, 0.5], val=200, beh='drift', dz=1850, dr=120, desc='Soft, pink and see-through. Lives deeper than almost any other fish.'),
    T(id='vampsquid', name='Vampire Squid', b='trench', r='uncommon', shape='squid', len=50, col='#6a1630', belly='#9a2a4a', fin='#3a0818', pat='none', w=[0.3, 2], val=550, beh='drift', glow='#6ab8ff', dz=800, dr=120, desc='Turns itself inside out when scared. Relatable.'),
    T(id='viperfish', name='Viperfish', b='trench', r='uncommon', shape='eel', len=66, col='#1a2a3a', belly='#2e4458', fin='#3a5a7a', pat='dots', patc='#7ff0ff', w=[0.05, 0.3], val=530, beh='dart', glow='#7ff0ff', dz=1100, dr=130, desc='Its fangs are so long they do not fit inside its mouth.'),
    T(id='gulper', name='Gulper Eel', b='trench', r='uncommon', shape='eel', len=92, col='#1a1626', belly='#2e2840', fin='#ff5a8a', pat='none', w=[1, 8], val=500, beh='erratic', glow='#ff5a8a', dz=1350, dr=130, desc='Mostly mouth. The rest is also mouth.'),
    T(id='barreleye', name='Barreleye', b='trench', r='rare', shape='fish', len=48, col='#5a7088', belly='#8aa0b8', fin='#3a4a5e', pat='dome', w=[0.5, 2], val=1900, beh='erratic', dz=700, dr=120, desc='Has a see-through head. You can watch it think.'),
    T(id='angler', name='Anglerfish', b='trench', r='rare', shape='angler', len=64, col='#2b2233', belly='#3d3148', fin='#1d1626', pat='none', w=[2, 40], val=1800, beh='dart', glow='#9ffcff', dz=1200, dr=130, desc='Fishes with its own lamp. A colleague, really.'),
    T(id='fangtooth', name='Fangtooth', b='trench', r='rare', shape='fish', len=54, col='#3a2a26', belly='#4a3632', fin='#2a1e1a', pat='none', w=[0.05, 0.4], val=2000, beh='erratic', dz=1600, dr=130, desc='The biggest teeth for its size of any fish. It smiles a lot. Please stop smiling.'),
    T(id='giantsquid', name='Giant Squid', b='trench', r='epic', shape='squid', len=170, col='#b03a3a', belly='#e07a6a', fin='#7a1e1e', pat='spots', patc='#7a1e1e', w=[100, 500], val=7600, beh='erratic', dz=950, dr=140, desc='Eyes the size of dinner plates, mood the size of a ship.'),
    T(id='frilledshark', name='Frilled Shark', b='trench', r='epic', shape='eel', len=150, col='#5a4a42', belly='#7a6a60', fin='#4a3c36', pat='none', w=[5, 40], val=8400, beh='erratic', dz=1500, dr=130, desc='A living fossil with 300 trident-shaped teeth and a frilly collar of gills.'),
    T(id='dragonfish', name='Abyssal Dragonfish', b='trench', r='legendary', shape='eel', len=130, col='#120a18', belly='#2a1438', fin='#5ccfff', pat='dots', patc='#5ccfff', w=[2, 10], val=35000, beh='abyss', glow='#5ccfff', dz=1300, dr=130, desc='Lights up in a colour other fish cannot see.'),
    T(id='oarfish', name='Starlight Oarfish', b='trench', r='mythic', shape='eel', len=260, col='#c8d4e4', belly='#eef4fc', fin='#ff3d5a', pat='spots', patc='#9fdcff', w=[100, 270], val=160000, beh='abyss', glow='#bfe4ff', dz=750, dr=130, desc='A silver ribbon as long as a bus, crowned with red fins. Sailors once took it for a sea serpent.'),
    T(id='whiskerkoi', name='Whisker Koi', b='trench', r='mythic', shape='koi', len=150, col='#fff3e6', belly='#ffffff', fin='#ff9a3c', pat='patches', patc='#ff6a1a', w=[5, 22], val=120000, beh='abyss', glow='#ffcf7a', dz=1150, dr=130, desc="The cats' old guardian swam down into the abyss to keep watch. It still has its whiskers."),
    T(id='voidjelly', name='Void Jelly', b='trench', r='mythic', shape='jelly', len=140, col='#8a5cff', belly='#d8c8ff', fin='#ff5ce0', pat='none', w=[1, 5], val=140000, beh='abyss', glow='#b48cff', dz=1650, dr=130, desc='A jellyfish made of the gap between stars.'),
    T(id='leviathan', name='The Leviathan', b='trench', r='leviathan', shape='leviathan', len=680, col='#0c3a46', belly='#1d6a72', fin='#00ffd5', pat='scales', w=[20000, 80000], val=1000000, beh='boss', glow='#00ffd5', dz=1850, dr=150, desc='The colossus at the bottom of everything. Its glow is the last thing most lights see. It has noticed you.'),
    # ----- Pallid Sea (0-1600 m) -----
    T(id='herring', name='Atlantic Herring', b='pallid', r='common', shape='fish', len=26, col='#7f98b0', belly='#eef2f6', fin='#5f7890', pat='none', w=[0.1, 0.7], val=250, beh='calm', dz=40, dr=60, desc='Silver crowds the whalers followed for miles. Where the herring go, the whales go.'),
    T(id='pollock', name='Pollock', b='pallid', r='common', shape='fish', len=34, col='#5e7064', belly='#d8dccc', fin='#4a5a50', pat='none', w=[0.5, 6], val=270, beh='dart', dz=170, dr=90, desc='Greenish, quick and never alone. The athlete of the cod family.'),
    T(id='hake', name='Silver Hake', b='pallid', r='common', shape='fish', len=36, col='#a8b0b8', belly='#eef0f2', fin='#8890a0', pat='none', w=[0.3, 2.5], val=290, beh='calm', dz=450, dr=220, desc='A big mouth full of sharp teeth. Hunts along the slope at night.'),
    T(id='grenadier', name='Roundnose Grenadier', b='pallid', r='common', shape='fish', len=40, col='#7a7468', belly='#a8a094', fin='#5a544a', pat='none', w=[0.5, 2], val=320, beh='drift', dz=1150, dr=450, desc='A rattail of the deep slope. Lives for sixty years and is in no hurry about anything.'),
    T(id='halibut', name='Atlantic Halibut', b='pallid', r='uncommon', shape='fish', len=72, col='#5a5048', belly='#f2efe8', fin='#4a4038', pat='spots', patc='#3a3028', w=[5, 150], val=820, beh='drift', dz=350, dr=200, desc='A flatfish the size of a door. Both eyes are on one side, and both are on your bait.'),
    T(id='redfish', name='Ocean Perch', b='pallid', r='uncommon', shape='fish', len=44, col='#e0402a', belly='#ffb8a0', fin='#c02a18', pat='none', w=[0.5, 3], val=880, beh='calm', dz=750, dr=250, desc='Bright red, huge eyes and in no rush to grow up. Some live for two hundred years.'),
    T(id='ling', name='Blue Ling', b='pallid', r='uncommon', shape='fish', len=80, col='#5a6a74', belly='#c8d0d4', fin='#44525c', pat='mottle', patc='#3a464e', w=[3, 30], val=860, beh='erratic', dz=1150, dr=300, desc='A cod stretched out like taffy. Lurks in wrecks and rock cracks with one whisker out.'),
    T(id='swordfish', name='Swordfish', b='pallid', r='rare', shape='fish', len=124, col='#3e4a66', belly='#c8ccd8', fin='#2e3850', pat='none', w=[50, 300], val=3200, beh='dart', dz=350, dr=250, desc='Slashes through schools with its sword, and warms its own eyes to see in the cold dark.'),
    T(id='sixgill', name='Bluntnose Sixgill', b='pallid', r='rare', shape='fish', len=134, col='#5a5a52', belly='#8a8a80', fin='#4a4a42', pat='none', w=[100, 500], val=3000, beh='calm', dz=1000, dr=300, desc='Six gill slits, glowing green eyes and a family tree older than the dinosaurs.'),
    T(id='chimaera', name='Ghost Shark', b='pallid', r='rare', shape='fish', len=74, col='#b8b0c8', belly='#e4e0ec', fin='#9890a8', pat='spots', patc='#ffffff', w=[1, 5], val=3300, beh='abyss', dz=1350, dr=250, desc='Not a shark, not a ghost. Rabbit teeth, a whip for a tail and eyes that shine green.'),
    T(id='bluefin', name='Atlantic Bluefin', b='pallid', r='epic', shape='fish', len=150, col='#1e3a6a', belly='#dce4ec', fin='#3a5a8a', pat='none', w=[150, 600], val=14000, beh='dart', dz=250, dr=200, desc='A warm-blooded torpedo. Crosses the whole ocean and still has energy for your line.'),
    T(id='greenland', name='Greenland Shark', b='pallid', r='epic', shape='fish', len=184, col='#4e5660', belly='#7e868e', fin='#3e464e', pat='mottle', patc='#3a4048', w=[400, 1000], val=13000, beh='calm', dz=1100, dr=350, desc='Can live for four hundred years. Swims slower than you walk and does not care.'),
    T(id='stormmarlin', name='Storm Marlin', b='pallid', r='legendary', shape='fish', len=172, col='#2a5aa8', belly='#d8e8ff', fin='#62f3ff', pat='bars', patc='#9fe8ff', w=[100, 400], val=58000, beh='dart', glow='#9fe8ff', dz=200, dr=150, desc='Rides lightning down from the storms and stays charged for days. The whalers feared it nearly as much as the whale.'),
    T(id='ghostpike', name='Ghost Pike', b='pallid', r='legendary', shape='fish', len=156, col='#dcdcd0', belly='#f4f4ec', fin='#b8b8a8', pat='ribs', patc='#ffffff', w=[20, 80], val=64000, beh='abyss', glow='#e8f4ff', dz=1300, dr=200, desc='A long, see-through hunter. You can count its ribs, and it can count yours.'),
    T(id='coelacanth', name='Spectral Coelacanth', b='pallid', r='mythic', shape='fish', len=166, col='#2a3e6a', belly='#4a6a9a', fin='#9fdcff', pat='spots', patc='#e8f6ff', w=[30, 90], val=260000, beh='abyss', glow='#bfe4ff', dz=650, dr=150, desc='Older than the dinosaurs and supposed to be extinct. It also glows, which it was definitely not supposed to do.'),
    T(id='krakenling', name='Kraken Spawn', b='pallid', r='mythic', shape='squid', len=196, col='#5a1a3a', belly='#a03060', fin='#2a0818', pat='spots', patc='#ff5ab0', w=[200, 600], val=280000, beh='erratic', glow='#ff5ab0', dz=1400, dr=150, desc='A baby, apparently. Its parent is still out there somewhere, and it is not small.'),
    T(id='pallidwhale', name='The Pallid Whale', b='pallid', r='leviathan', shape='whale', len=720, col='#e8e4da', belly='#f6f2ea', fin='#c8c0b0', pat='scars', w=[40000, 60000], val=1800000, beh='boss', glow='#bfe8ff', rk=1.12, dz=1350, dr=200, desc='A white whale scarred by a hundred harpoons, some still stuck in its hide. Whalers swore it hunted them. Now it is hunting you.'),
    # ----- Frostbite Shelf (0-1400 m) -----
    T(id='capelin', name='Capelin', b='frost', r='common', shape='fish', len=22, col='#7a9a8a', belly='#e8f0ec', fin='#5a7a6a', pat='none', w=[0.02, 0.06], val=550, beh='calm', dz=40, dr=60, desc='Tiny silver fish that feed half the Arctic. Everyone up here eats capelin.'),
    T(id='polarcod', name='Polar Cod', b='frost', r='common', shape='fish', len=28, col='#8a8a70', belly='#ecebdc', fin='#6a6a52', pat='spots', patc='#5a5a44', w=[0.05, 0.4], val=580, beh='dart', dz=170, dr=110, desc='Hides in cracks under the sea ice. Its blood carries its own antifreeze.'),
    T(id='icefish', name='Blackfin Icefish', b='frost', r='common', shape='fish', len=40, col='#c8d8dc', belly='#f0f6f8', fin='#2a2e36', pat='none', w=[0.3, 2], val=620, beh='drift', dz=520, dr=240, desc='Its blood is clear: no red cells at all. It breathes oxygen soaked straight from the freezing water.'),
    T(id='frostpout', name='Polar Eelpout', b='frost', r='common', shape='eel', len=52, col='#b8a898', belly='#e8dcd0', fin='#9a8a7a', pat='none', w=[0.1, 1], val=680, beh='drift', dz=1050, dr=350, desc='A slow, squishy fish that lives in the mud of the deep shelf and does not mind the cold one bit.'),
    T(id='lumpsucker', name='Spiny Lumpsucker', b='frost', r='uncommon', shape='puffer', len=30, col='#4a9a6a', belly='#c8e8b0', fin='#3a7a52', pat='spots', w=[0.01, 0.05], val=1560, beh='erratic', dz=40, dr=50, desc='Sticks to rocks with a suction cup on its belly. Basically a ping-pong ball with fins.'),
    T(id='sculpin', name='Shorthorn Sculpin', b='frost', r='uncommon', shape='fish', len=40, col='#6a5a48', belly='#e8c890', fin='#5a4a38', pat='mottle', patc='#3a2e22', w=[0.3, 2.5], val=1690, beh='calm', dz=150, dr=120, desc='Spiny, warty and grumpy. Puffs up its head to look bigger, which does not work.'),
    T(id='toothfish', name='Antarctic Toothfish', b='frost', r='uncommon', shape='fish', len=92, col='#4a4a52', belly='#a8a8b0', fin='#3a3a42', pat='none', w=[10, 130], val=1820, beh='dart', dz=900, dr=350, desc='The big hunter of the southern ice. Grows bigger than you and lives for fifty years.'),
    T(id='wolffish', name='Atlantic Wolffish', b='frost', r='rare', shape='fish', len=94, col='#6a7480', belly='#b8c0c8', fin='#5a646e', pat='bars', patc='#3e4650', w=[2, 20], val=6240, beh='erratic', dz=250, dr=150, desc='Crushes crabs with tusks like a walrus. Makes its own antifreeze, and its own rules.'),
    T(id='glasssquid', name='Glass Squid', b='frost', r='rare', shape='squid', len=72, col='#c8e8f0', belly='#f0faff', fin='#9fd0e0', pat='none', w=[0.2, 2], val=6500, beh='abyss', glow='#9fe8ff', dz=600, dr=250, desc='See-through and round as a balloon. Floats by filling itself with ammonia, which is weird, but it is proud of it.'),
    T(id='skate', name='Arctic Skate', b='frost', r='rare', shape='ray', len=112, col='#7a6a5a', belly='#e8e0d8', fin='#6a5a4a', pat='spots', patc='#5a4a3a', w=[5, 40], val=5980, beh='calm', dz=900, dr=300, desc='Flat as a carpet and just as easy to step on. Glides along the deep shelf.'),
    T(id='sleepershark', name='Sleeper Shark', b='frost', r='epic', shape='fish', len=192, col='#3a3e46', belly='#5a5e66', fin='#2e3238', pat='none', w=[300, 900], val=26000, beh='calm', dz=1000, dr=300, desc='Slow, silent and huge. Swallows seals whole, and nobody knows how it catches them.'),
    T(id='colossalsquid', name='Colossal Squid', b='frost', r='epic', shape='squid', len=200, col='#8a1a2a', belly='#c84a5a', fin='#5a0a18', pat='spots', patc='#5a0a18', w=[300, 500], val=27300, beh='erratic', dz=1150, dr=200, desc='Heavier than the giant squid, with swivelling hooks on its arms and the biggest eyes of any animal.'),
    T(id='aurorachar', name='Aurora Char', b='frost', r='legendary', shape='fish', len=152, col='#2a6a5a', belly='#ff8a5a', fin='#e8f0f0', pat='spots', patc='#bfffe8', w=[5, 15], val=117000, beh='dart', glow='#7fffd4', dz=60, dr=80, desc='A char painted by the northern lights. On dark nights you can see it glowing from the boat.'),
    T(id='frostmanta', name='Frost Manta', b='frost', r='legendary', shape='ray', len=196, col='#bfe8ff', belly='#ffffff', fin='#7fc8f0', pat='none', w=[400, 1500], val=123500, beh='calm', glow='#bfe8ff', dz=350, dr=200, desc='Its wings are rimmed with frost that never melts. Sailors used to follow it home through the ice.'),
    T(id='glacierkoi', name='Glacier Koi', b='frost', r='mythic', shape='koi', len=172, col='#e8f8ff', belly='#ffffff', fin='#7fd8ff', pat='patches', patc='#5ab0e0', w=[10, 30], val=494000, beh='abyss', glow='#bfefff', dz=500, dr=200, desc='Frozen in a glacier for ten thousand years. Then the ice melted and it swam off as if nothing had happened.'),
    T(id='polarjelly', name='Polaris Jelly', b='frost', r='mythic', shape='jelly', len=160, col='#6ad8ff', belly='#e8f8ff', fin='#bfa0ff', pat='none', w=[2, 8], val=546000, beh='abyss', glow='#9fe8ff', dz=1000, dr=250, desc='Carries a tiny aurora inside its bell, and lights up the dark under the ice wherever it drifts.'),
    T(id='ancientcrab', name='The Ancient Crab', b='frost', r='leviathan', shape='crab', len=640, col='#8a4a3a', belly='#d8b090', fin='#5a2a1e', pat='none', w=[8000, 15000], val=3200000, beh='boss', glow='#9fe8ff', rk=1.08, dz=1250, dr=150, desc='Older than the ice shelf above it. Its shell is crusted with frozen barnacles, and one claw is bigger than your boat.'),
    # ----- Mariana Deep (0-11000 m): the deeper you go, the stranger it gets -----
    T(id='flyingfish', name='Flying Fish', b='mariana', r='common', shape='fish', len=30, col='#2a5aa8', belly='#e8f0ff', fin='#9fc8ff', pat='none', w=[0.1, 0.6], val=820, beh='dart', dz=20, dr=40, desc='Glides over the waves on wings made of fins. Down here it is the only fish that ever sees the sky.'),
    T(id='bigscale', name='Bigscale Fish', b='mariana', r='common', shape='fish', len=26, col='#5a3a2e', belly='#8a6a5a', fin='#3a2a22', pat='none', w=[0.01, 0.06], val=860, beh='calm', dz=900, dr=800, desc='A small, sleepy deep fish with scales a few sizes too big for it.'),
    T(id='tripodfish', name='Tripod Fish', b='mariana', r='common', shape='fish', len=40, col='#4a4a52', belly='#7a7a82', fin='#6a6a72', pat='none', w=[0.1, 0.6], val=900, beh='drift', dz=3200, dr=1500, desc='Stands on the seabed on three long fin rays, like a camera on a tripod, and waits for food to drift by.'),
    T(id='cuskeel', name='Abyssal Cusk-Eel', b='mariana', r='common', shape='eel', len=60, col='#c8b8a8', belly='#e8dcd0', fin='#b0a090', pat='none', w=[0.2, 2], val=960, beh='drift', dz=6200, dr=1500, desc='One of the deepest fish ever caught. Pale, slow and very far from home, wherever that is.'),
    T(id='hadalsnail', name='Mariana Snailfish', b='mariana', r='common', shape='fish', len=34, col='#f0d8dc', belly='#fff0f2', fin='#e8c0c8', pat='none', w=[0.05, 0.4], val=1040, beh='drift', dz=9200, dr=1700, desc='The deepest fish ever filmed. Soft, see-through and somehow fine with a thousand times the air pressure.'),
    T(id='cookiecutter', name='Cookiecutter Shark', b='mariana', r='uncommon', shape='fish', len=44, col='#6a5a4a', belly='#b8a890', fin='#5a4a3a', pat='none', w=[0.3, 0.8], val=2600, beh='dart', dz=600, dr=500, desc='A tiny shark that bites perfect round cookies out of whales, and then swims off very pleased.'),
    T(id='swallower', name='Black Swallower', b='mariana', r='uncommon', shape='fish', len=40, col='#1a1a22', belly='#3a3040', fin='#2a2a32', pat='none', w=[0.02, 0.2], val=2600, beh='dart', dz=1700, dr=900, desc='Swallows fish twice its size. Sometimes one so big that it bursts. Not great at decisions.'),
    T(id='dumbo', name='Dumbo Octopus', b='mariana', r='uncommon', shape='squid', len=50, col='#ff9a7a', belly='#ffd0c0', fin='#ff7a5a', pat='none', w=[0.5, 6], val=2800, beh='drift', dz=3500, dr=2000, desc='Flaps two ear-like fins to fly through the deep. By far the cutest thing down here.'),
    T(id='tonguefish', name='Deep Tonguefish', b='mariana', r='uncommon', shape='fish', len=36, col='#8a7a6a', belly='#c8b8a8', fin='#7a6a5a', pat='spots', patc='#6a5a4a', w=[0.05, 0.4], val=2700, beh='drift', dz=7000, dr=3000, desc='A flatfish shaped like a tongue that lies on the deepest mud and licks up whatever falls on it.'),
    T(id='stareater', name='Stareater', b='mariana', r='rare', shape='eel', len=72, col='#0a0a14', belly='#1a1a2a', fin='#4a8aff', pat='dots', patc='#7fbfff', w=[0.1, 1], val=9000, beh='erratic', glow='#7fbfff', dz=1500, dr=1000, desc='Black as the dark around it, with a glowing lure on its chin and teeth you only see once.'),
    T(id='lizardfish', name='Deep-sea Lizardfish', b='mariana', r='rare', shape='fish', len=62, col='#9a9068', belly='#c8c0a0', fin='#7a7050', pat='none', w=[0.5, 4], val=8800, beh='dart', dz=2800, dr=1200, desc='Lies on the bottom with its mouth open, waiting. It has been waiting a very long time.'),
    T(id='faceless', name='Faceless Cusk', b='mariana', r='rare', shape='fish', len=52, col='#c8b8b0', belly='#e8dcd8', fin='#b0a098', pat='none', w=[0.3, 2], val=9400, beh='abyss', dz=7000, dr=3000, desc='No eyes you can see and a mouth hidden underneath. Lost to science for 140 years, then found again.'),
    T(id='megamouth', name='Megamouth Shark', b='mariana', r='epic', shape='fish', len=200, col='#4a4a52', belly='#8a8a90', fin='#3a3a42', pat='none', w=[500, 1200], val=40000, beh='calm', dz=500, dr=400, desc='A huge, gentle shark with a mouth like a cave. Nobody had ever seen one until 1976.'),
    T(id='goblinshark', name='Goblin Shark', b='mariana', r='epic', shape='fish', len=190, col='#d8a8a0', belly='#f0d0c8', fin='#c09088', pat='none', w=[100, 210], val=42000, beh='dart', dz=1100, dr=500, desc='A pink shark with a long flat nose and jaws that shoot out of its face. It is a real fish. Really.'),
    T(id='midnightmanta', name='Midnight Manta', b='mariana', r='legendary', shape='ray', len=200, col='#14142a', belly='#3a3a6a', fin='#5a5aff', pat='dots', patc='#bfbfff', w=[500, 2000], val=180000, beh='calm', glow='#7f7fff', dz=5500, dr=1500, desc='A manta made of night, with stars along the edges of its wings. It flies where nothing else can.'),
    T(id='challenger', name='Challenger Dragonfish', b='mariana', r='legendary', shape='eel', len=170, col='#0a0618', belly='#2a1438', fin='#ff5ab0', pat='dots', patc='#ff5ab0', w=[2, 12], val=170000, beh='abyss', glow='#ff5ab0', dz=9300, dr=1200, desc='Named after the deepest spot on Earth. It lights its way with a red lamp nothing else can see.'),
    T(id='siphonophore', name='Deepstar Siphonophore', b='mariana', r='mythic', shape='eel', len=280, col='#ff9ad8', belly='#ffe0f0', fin='#7fffd4', pat='dots', patc='#ffffff', w=[5, 20], val=720000, beh='abyss', glow='#ff9ad8', dz=2800, dr=1500, desc='Not one animal but thousands, linked in a glowing string longer than a whale. It hunts with a curtain of stinging lights.'),
    T(id='abyssangel', name='Abyssal Angel', b='mariana', r='mythic', shape='fish', len=180, col='#f0e8ff', belly='#ffffff', fin='#ffd8f8', pat='none', w=[5, 15], val=780000, beh='abyss', glow='#ffffff', dz=10000, dr=800, desc='A pale, glowing fish seen only at the very bottom of the world. The divers who saw it say it was looking back.'),
    T(id='bloop', name='The Bloop', b='mariana', r='leviathan', shape='bloop', len=760, col='#4f7a70', belly='#a8c4b4', fin='#3a5a52', pat='none', w=[100000, 300000], val=6000000, beh='boss', glow='#9fffe8', rk=1.15, dz=10300, dr=600, desc="In 1997 the ocean's microphones heard a sound louder than any whale, from somewhere very deep. Scientists said it was ice. The cats know better."),
    # Loch Ness (fresh water, peat-dark below 40 m)
    T(id='stickleback', name='Three-spined Stickleback', b='loch', r='common', shape='fish', len=16, col='#6a7a4a', belly='#e0c8a0', fin='#4a5a32', pat='bars', patc='#4a5a32', w=[0.002, 0.008], val=220, beh='dart', dz=12, dr=14, desc='Tiny and fearless, with three spikes on its back. The males turn bright red in spring.'),
    T(id='minnow', name='Highland Minnow', b='loch', r='common', shape='fish', len=14, col='#8a9a7a', belly='#f0e0c0', fin='#6a7a5a', pat='spots', patc='#4a5a3a', w=[0.003, 0.01], val=230, beh='dart', dz=22, dr=22, desc='Swims in nervous little clouds near the shore. Everything in the loch eats them.'),
    T(id='browntrout', name='Brown Trout', b='loch', r='common', shape='fish', len=44, col='#8a6a3a', belly='#ecd090', fin='#6a5030', pat='spots', patc='#3a2010', w=[0.3, 2.5], val=280, beh='dart', dz=55, dr=45, desc='Gold-brown with dark and red spots. The fish every Highland angler grew up on.'),
    T(id='arcticcharr', name='Arctic Charr', b='loch', r='common', shape='fish', len=40, col='#4a5a6a', belly='#ff7a4a', fin='#ff9a6a', pat='dots', patc='#ffd0b0', w=[0.3, 2], val=300, beh='calm', dz=160, dr=55, desc='Left behind in the loch when the ice age ended. Lives deep and cold, with a sunset-orange belly.'),
    T(id='euroeel', name='European Eel', b='loch', r='uncommon', shape='eel', len=80, col='#4a4a2a', belly='#c8b878', fin='#3a3a20', pat='none', w=[0.5, 3], val=680, beh='drift', dz=120, dr=90, desc='Swam here all the way from the Sargasso Sea. Some people think Nessie is just a very, very big one.'),
    T(id='seatrout', name='Sea Trout', b='loch', r='uncommon', shape='fish', len=60, col='#a8b0b8', belly='#f4f4f4', fin='#7a8288', pat='spots', patc='#2a2a30', w=[1, 6], val=650, beh='dart', dz=40, dr=36, desc='A brown trout that went to sea, turned silver, and came home big.'),
    T(id='lamprey', name='Sea Lamprey', b='loch', r='uncommon', shape='eel', len=70, col='#6a6a50', belly='#a8a888', fin='#5a5a40', pat='mottle', patc='#3a3a2a', w=[0.5, 2.5], val=720, beh='erratic', dz=150, dr=70, desc='No jaws, just a round sucker mouth full of teeth. It does not want to be your friend.'),
    T(id='salmon', name='Atlantic Salmon', b='loch', r='rare', shape='fish', len=90, col='#8a98a8', belly='#f4f0ea', fin='#6a7888', pat='dots', patc='#2a3040', w=[3, 15], val=2400, beh='dart', dz=50, dr=45, desc='The king of Scottish rivers, home from the sea to the waters it was born in.'),
    T(id='pike', name='Northern Pike', b='loch', r='rare', shape='fish', len=110, col='#5a6a3a', belly='#e0e0b0', fin='#7a6a3a', pat='spots', patc='#d8d890', w=[4, 18], val=2300, beh='dart', dz=30, dr=28, desc='A long green ambush hunter with a duck-bill jaw full of needles. Waits in the weeds, then strikes.'),
    T(id='ferox', name='Ferox Trout', b='loch', r='rare', shape='fish', len=95, col='#5a4a2a', belly='#d8b880', fin='#4a3a20', pat='spots', patc='#1a1208', w=[5, 14], val=2600, beh='erratic', dz=190, dr=38, desc='A huge, old, cannibal trout from the black depths of the loch. Eats charr for breakfast.'),
    T(id='locheel', name='Giant Loch Eel', b='loch', r='epic', shape='eel', len=220, col='#3a3a2a', belly='#7a7a5a', fin='#2a2a1a', pat='none', w=[20, 60], val=9500, beh='erratic', dz=200, dr=28, desc='Divers swore they saw eels as thick as a man\'s leg at the bottom. It turns out they were right.'),
    T(id='wels', name='Wels Catfish', b='loch', r='epic', shape='fish', len=200, col='#4a4a3a', belly='#c8c0a0', fin='#3a3a2a', pat='mottle', patc='#2a2a1e', w=[60, 140], val=9000, beh='calm', dz=175, dr=50, desc='A whiskered giant with a mouth like a bin lid. Nobody knows who let it into the loch.'),
    T(id='salmonking', name='The Salmon King', b='loch', r='legendary', shape='fish', len=140, col='#d8b860', belly='#fff4d0', fin='#ffd23d', pat='scales', patc='#fff0a0', w=[20, 40], val=42000, beh='dart', glow='#ffd23d', dz=120, dr=100, desc='A golden salmon as old as the castle. Highland stories say it wears a crown of river gold.'),
    T(id='wispjelly', name="Will-o'-the-Wisp", b='loch', r='mythic', shape='jelly', len=90, col='#bfffd0', belly='#ffffff', fin='#7fffb0', pat='none', w=[0.1, 0.6], val=175000, beh='abyss', glow='#bfffd0', dz=90, dr=80, desc='A freshwater jellyfish that glows like the lights that lead travellers into the bog. Do not follow it.'),
    T(id='kelpie', name='The Kelpie', b='loch', r='mythic', shape='seahorse', len=160, col='#2a4a3a', belly='#7fb89a', fin='#9fffc8', pat='none', w=[200, 500], val=190000, beh='abyss', glow='#9fffc8', dz=150, dr=70, desc='A water horse from Scottish legend, with a mane of weed. It offers rides. Never, ever get on.'),
    T(id='nessie', name='Nessie', b='loch', r='leviathan', shape='nessie', len=700, col='#3d5a3a', belly='#8a9a6a', fin='#2a4028', pat='none', w=[3000, 9000], val=1200000, beh='boss', glow='#c8ff9a', rk=0.95, dz=200, dr=25, desc='The Loch Ness Monster. Seen in 1933, photographed (blurrily) in 1934, denied by scientists ever since. She is real, she is huge, and she has been waiting for a cat with a good enough rod.'),
    # ----- Ruins of Atlantis (0-5200 m): the drowned city, district by district -----
    T(id='mosaicwrasse', name='Mosaic Wrasse', b='atlantis', r='common', shape='fish', len=32, col='#397f75', belly='#e4d7a0', fin='#e7ae54', pat='scales', patc='#d8be62', w=[0.1, 0.8], val=1200, beh='calm', dz=220, dr=180, desc='Scales like tiny tiles, and it knows it is art.'),
    T(id='colonnadesardine', name='Colonnade Sardine', b='atlantis', r='common', shape='fish', len=24, col='#b2b69a', belly='#f3e7c8', fin='#6d9c8a', pat='stripe', patc='#e9dda8', w=[0.05, 0.35], val=1350, beh='dart', dz=480, dr=260, desc='Swims between the columns in a perfectly straight line. More discipline than your crew.'),
    T(id='lapisgoby', name='Lapis Goby', b='atlantis', r='common', shape='fish', len=22, col='#397e9a', belly='#d5d9bb', fin='#e4b85c', pat='spots', patc='#f2d783', w=[0.02, 0.18], val=1480, beh='calm', dz=900, dr=420, desc='Lives in a cracked amphora and charges rent in crumbs.'),
    T(id='pearlsprat', name='Pearl Sprat', b='atlantis', r='common', shape='fish', len=20, col='#c5bb9c', belly='#fff4d0', fin='#a8d7c6', pat='dots', patc='#fff8dc', w=[0.02, 0.12], val=1550, beh='drift', dz=1400, dr=500, desc='Swallows sand, makes pearls, and has never once paid the city tax.'),
    T(id='marblegrouper', name='Marble Grouper', b='atlantis', r='uncommon', shape='fish', len=88, col='#737f6a', belly='#d9d0ad', fin='#b7a56f', pat='mottle', patc='#d8ca9a', w=[12, 90], val=4400, beh='calm', dz=780, dr=430, desc='Heavy as a statue, mostly because it might be one.'),
    T(id='siltpuffer', name='Silt Puffer', b='atlantis', r='uncommon', shape='puffer', len=42, col='#a98855', belly='#e8d5a8', fin='#577f70', pat='spots', patc='#594c39', w=[0.3, 4], val=5100, beh='erratic', dz=1650, dr=550, desc='Puffs up when startled. The silt cloud is a very effective exit strategy.'),
    T(id='philosophercarp', name='Philosopher Carp', b='atlantis', r='rare', shape='koi', len=104, col='#cc9b4e', belly='#f1e7c4', fin='#a94d47', pat='patches', patc='#f5df9a', w=[4, 24], val=18800, beh='drift', dz=2050, dr=700, desc='Has opinions about your bait, and one about whether the bait exists.'),
    T(id='tridentbarracuda', name='Trident Barracuda', b='atlantis', r='rare', shape='fish', len=116, col='#497f76', belly='#d8d0a6', fin='#d5ad60', pat='bars', patc='#d9be74', w=[8, 60], val=21400, beh='dart', dz=2950, dr=650, desc='Three points on the tail and no sense of humour.'),
    T(id='amphoraclowfish', name='Amphora Clownfish', b='atlantis', r='rare', shape='fish', len=46, col='#d86743', belly='#f3e0bb', fin='#f5c46b', pat='stripe', patc='#fff1d2', w=[0.4, 3], val=23100, beh='erratic', dz=1450, dr=520, desc='Made a home in a vase. It gets defensive when you compliment the pottery.'),
    T(id='oracleeel', name='Oracle Eel', b='atlantis', r='epic', shape='eel', len=172, col='#4b9b84', belly='#d9d6a8', fin='#a77bd1', pat='dots', patc='#f4dd8a', w=[6, 48], val=68000, beh='abyss', glow='#9fffd4', dz=1780, dr=680, desc='Tells you what you will catch next. Right about half the time. It starts to whisper when it sees you.'),
    T(id='lamplighterjelly', name='Lamplighter Jelly', b='atlantis', r='epic', shape='jelly', len=124, col='#e3c56d', belly='#fff1b8', fin='#68d4bf', pat='none', w=[1, 16], val=73500, beh='drift', glow='#ffe08a', dz=3100, dr=850, desc='Lit the city streets once. Nobody told it to stop.'),
    T(id='vaultoctopus', name='Vault Octopus', b='atlantis', r='epic', shape='squid', len=156, col='#8e5e9f', belly='#d8b8d5', fin='#56bba7', pat='none', w=[20, 120], val=79200, beh='erratic', glow='#c88cff', dz=3900, dr=900, desc='Keeps shiny things in a vault. The vault is its head.'),
    T(id='gorgonray', name='Gorgon Ray', b='atlantis', r='legendary', shape='ray', len=236, col='#887a56', belly='#e9dfbc', fin='#9cbd8d', pat='spots', patc='#f4d77d', w=[900, 4200], val=320000, beh='abyss', glow='#e8d987', dz=2750, dr=850, desc='Looking at it is fine. Being looked at is the problem.'),
    T(id='hippocampus', name='Hippocampus', b='atlantis', r='legendary', shape='seahorse', len=182, col='#4c9f8c', belly='#dce4bb', fin='#e4ba65', pat='scales', patc='#f3dd8a', w=[80, 460], val=345000, beh='erratic', glow='#9fffd4', dz=3400, dr=900, desc='The seahorse’s very large, very smug ancestor.'),
    T(id='orichalcumkoi', name='Orichalcum Koi', b='atlantis', r='mythic', shape='koi', len=240, col='#d9a83b', belly='#fff3c0', fin='#e66d58', pat='scales', patc='#fff0a0', w=[90, 360], val=1250000, beh='abyss', glow='#ffe08a', dz=4050, dr=850, desc='Cast from the lost metal. It hits the water like a bell.'),
    T(id='nereidjelly', name='Nereid Jelly', b='atlantis', r='mythic', shape='jelly', len=205, col='#9455c6', belly='#f2ddff', fin='#5ce0d0', pat='none', w=[20, 180], val=1380000, beh='abyss', glow='#d78bff', dz=4650, dr=500, desc='Drifts through the temple as if it is looking for someone.'),
    T(id='kraken', name='The Kraken', b='atlantis', r='leviathan', shape='kraken', len=1040, col='#713a78', belly='#c080bd', fin='#3a8279', pat='suckers', w=[180000, 520000], val=12000000, beh='boss', glow='#ff5ab0', rk=1.2, dz=4800, dr=350, desc='Its arms have been wrapped around the broken gate for eleven thousand years. It is not letting go.'),
    T(id='firstlight', name='Firstlight Koi', b='atlantis', r='mythic', shape='koi', len=310, col='#ffe08a', belly='#fff4c2', fin='#ff6a8a', pat='scales', patc='#fff8d8', w=[180, 640], val=2400000, beh='abyss', glow='#fff0a0', dz=4950, dr=180, desc='A limited-edition koi: only three can be caught on each server. Its scales hold the first light of the drowned city.', limited=3),
    T(id='vaultguardian', name='Vault Guardian', b='atlantis', r='epic', shape='angler', len=128, col='#547c70', belly='#d7cf9f', fin='#d5ad60', pat='spots', w=[12, 90], val=88000, beh='erratic', glow='#9fffe8', dz=3300, dr=230, cave=True, desc='A keeper fish that guards the archive beneath the western colonnade.'),
    # ----- Red Hollow (the cracked mirror beyond Atlantis) -----
    T(id='redfinfragment', name='Redfin Fragment', b='redhollow', r='common', shape='fish', len=28, col='#d94b55', belly='#ffe0b0', fin='#ff8d8d', pat='stripe', patc='#6a1235', w=[0.05, 0.4], val=1800, beh='dart', dz=90, dr=140, desc='A small red fish with a piece of the world caught in its scales.'),
    T(id='glassminnow', name='Glass Minnow', b='redhollow', r='uncommon', shape='fish', len=38, col='#d4a0d8', belly='#fff0ff', fin='#8b72cc', pat='dots', patc='#ff5ab0', w=[0.1, 1.2], val=6600, beh='drift', glow='#ff7eb8', dz=620, dr=220, desc='Its reflection swims a fraction of a second behind it.'),
    T(id='moonshardray', name='Moonshard Ray', b='redhollow', r='rare', shape='ray', len=112, col='#a4438a', belly='#f2b5dc', fin='#ff547c', pat='none', w=[8, 80], val=23800, beh='abyss', glow='#ff547c', dz=1250, dr=320, desc='A slice of the blood moon, if you believe the fish. It does.'),
    T(id='watcherbelow', name='The Watcher Below', b='redhollow', r='leviathan', shape='watcher', len=820, col='#38284f', belly='#9b4a81', fin='#d62e55', pat='none', w=[60000, 140000], val=7800000, beh='boss', glow='#ff294f', rk=1.18, dz=1680, dr=110, desc='It watched the gate long after the last Keeper vanished. Now it has noticed you.'),
    T(id='chasmphantom', name='Chasm Phantom', b='mariana', r='epic', shape='jelly', len=146, col='#6471bd', belly='#d9ddff', fin='#9fffe8', pat='none', w=[3, 32], val=112000, beh='abyss', glow='#9fffe8', dz=6400, dr=240, cave=True, desc='A lightless jelly that glides through a cavern where the Bloop’s signal echoes.'),
    T(id='lanternlurker', name='Lantern Lurker', b='trench', r='rare', shape='angler', len=110, col='#355467', belly='#91b6b0', fin='#55d8dc', pat='spots', w=[4, 38], val=31000, beh='erratic', glow='#5acfff', dz=850, dr=170, cave=True, desc='It keeps to a narrow cavern in the trench wall and follows every light it sees.'),
]
for _f in FISH:
    _f.dr = _f.dr or 50
FI = {f.id: f for f in FISH}
CAVES = {
    'trench': T(name='Lantern Grotto', x=(0.12, 0.34), d=(680, 1060), fish=['lanternlurker']),
    'mariana': T(name='Signal Vault', x=(0.58, 0.84), d=(5650, 7550), fish=['chasmphantom']),
    'atlantis': T(name='Keeper’s Archive', x=(0.08, 0.31), d=(2780, 3800), fish=['vaultguardian']),
}

# ---------------- Rods ----------------
# depth (m), luck (rarity multiplier), control (reel bar width), reel (catch speed), str (resists tension), lure (bites)
# at: the island whose shop sells it (or whose quest earns it). Quest rods are never sold.
RODS = [
    # Starter Shore
    T(id='starter', name='Starter Rod', price=0, at='shore', depth=60, luck=1.0, control=0.26, reel=1.0, str=1.0, lure=1.0, col='#8a5a2b', desc='A stick, some string, a lot of hope.'),
    T(id='bamboo', name='Bamboo Rod', price=400, at='shore', depth=110, luck=1.06, control=0.27, reel=1.08, str=1.08, lure=1.08, col='#c8a24a', desc='Light and springy. Reaches the middle of the bay.'),
    T(id='fiber', name='Fiberglass Rod', price=1800, at='shore', depth=180, luck=1.12, control=0.285, reel=1.15, str=1.15, lure=1.15, col='#e8eef4', desc='A real rod. Reaches the bottom of the bay.'),
    T(id='driftwood', name='Driftwood Rod', price=0, at='shore', quest='q_driftwood', depth=180, luck=1.15, control=0.29, reel=1.18, str=1.15, lure=1.3, col='#b08a5a', desc='Washed up on Starter Shore. Smells like adventure.'),
    T(id='whisker', name="Cat's Whisker Rod", price=0, at='shore', quest='q_whisker', depth=180, luck=1.18, control=0.31, reel=1.2, str=1.2, lure=1.15, col='#ffd9a0', tip='#ffffff', desc='Strung with a real whisker. The fish can feel it twitch.'),
    # Coral Reef
    T(id='carbon', name='Carbon Rod', price=3500, at='reef', depth=320, luck=1.22, control=0.3, reel=1.28, str=1.3, lure=1.2, col='#3a3f48', desc='Light, stiff and jet black. The pros swear by it.'),
    T(id='kelp', name='Kelp Rod', price=6500, at='reef', depth=400, luck=1.26, control=0.31, reel=1.32, str=1.35, lure=1.25, col='#5a8a3a', tip='#bfffb0', desc='Woven from giant kelp. Cold to the touch, and it chills whatever bites.'),
    T(id='coral', name='Coral Rod', price=9500, at='reef', depth=450, luck=1.32, control=0.315, reel=1.38, str=1.42, lure=1.3, col='#ff6fa8', desc='Grown, not carved. Reaches the foot of the reef wall.'),
    T(id='warden', name="Reef Warden's Rod", price=0, at='reef', quest='q_warden', depth=450, luck=1.36, control=0.33, reel=1.4, str=1.45, lure=1.3, col='#2fd0a0', tip='#9dffb0', desc='The reef trusts whoever carries it.'),
    T(id='storm', name='Storm Rod', price=0, at='reef', quest='q_storm', depth=450, luck=1.36, control=0.32, reel=1.45, str=1.5, lure=1.3, col='#3a6aa0', tip='#62f3ff', desc='Hums before a storm. Crackles during one.'),
    # Volcanic Biome
    T(id='magma', name='Magma Rod', price=26000, at='volcano', depth=650, luck=1.45, control=0.32, reel=1.5, str=1.7, lure=1.35, heat=True, col='#ff5a1f', tip='#ffb03a', desc="Forged in a vent. Lava can't burn its line."),
    T(id='obsidian', name='Obsidian Rod', price=52000, at='volcano', depth=900, luck=1.55, control=0.33, reel=1.6, str=1.85, lure=1.4, heat=True, col='#2a1f3a', tip='#b48cff', desc='Volcanic glass, honed razor sharp. Reaches the vents at the very bottom.'),
    T(id='phoenixrod', name='Phoenix Rod', price=0, at='volcano', quest='q_phoenix', depth=900, luck=1.6, control=0.335, reel=1.65, str=1.9, lure=1.45, heat=True, col='#ff7a1a', tip='#ffd23d', desc='Feathered with phoenix plumes. It refuses to lose.'),
    T(id='midas', name='Midas Rod', price=0, at='volcano', quest='q_gold', depth=900, luck=1.62, control=0.33, reel=1.62, str=1.85, lure=1.4, col='#ffd23d', tip='#fff2a8', desc='Solid gold. Very heavy. Not heat-proof, but completely worth it.'),
    # Deep Trench Abyss
    T(id='abyssal', name='Abyssal Rod', price=80000, at='trench', depth=1300, luck=1.7, control=0.34, reel=1.72, str=2.05, lure=1.5, light=1, col='#5ccfff', desc='Glows faintly in the dark. Reaches the middle of the trench.'),
    T(id='maelstrom', name='Maelstrom Rod', price=130000, at='trench', depth=1550, luck=1.8, control=0.345, reel=1.8, str=2.2, lure=1.55, light=1, col='#2a5a8a', tip='#9fe8ff', desc='Spins the water around the hook into a little whirlpool.'),
    T(id='glow', name='Glow Rod', price=180000, at='trench', depth=1800, luck=1.9, control=0.35, reel=1.88, str=2.35, lure=1.6, light=1, col='#7ffcff', tip='#7ffcff', desc='Grown from deep-sea coral that shines in the dark. Reaches the Leviathan.'),
    T(id='deepwatch', name='Deepwatch Rod', price=0, at='trench', quest='q_deepwatch', depth=2000, luck=1.9, control=0.355, reel=1.9, str=2.35, lure=1.6, light=1, col='#3a4a7a', tip='#7fffd4', desc='Fitted with a tiny sonar. Nothing in the dark surprises it.'),
    T(id='starfall', name='Starfall Rod', price=0, at='trench', quest='q_mythic', depth=2000, luck=2.0, control=0.36, reel=1.95, str=2.45, lure=1.7, heat=True, light=1, col='#8a5cff', tip='#e0c8ff', desc='Forged from a falling star. Mythic fish come to it.'),
    T(id='leviathan', name='Leviathan Rod', price=450000, at='trench', need='scale', depth=2000, luck=2.1, control=0.36, reel=1.96, str=2.55, lure=1.75, heat=True, light=1, col='#00ffd5', tip='#00ffd5', desc='Made with a Leviathan Scale. The bottom of the sea is yours.'),
    # Pallid Sea
    T(id='whaler', name="Whaler's Rod", price=240000, at='pallid', depth=1300, luck=2.15, control=0.362, reel=2.02, str=2.62, lure=1.78, light=1, col='#5a3a24', tip='#c8c8c0', desc='Tarred line and an iron barb.'),
    T(id='tiderunner', name='Tiderunner Rod', price=380000, at='pallid', depth=1600, luck=2.25, control=0.366, reel=2.1, str=2.75, lure=1.82, light=1, col='#3a6a8a', tip='#bfe8ff', desc='Flexes like a wave, and the fish goes with it.'),
    T(id='scrimshaw', name='Scrimshaw Rod', price=0, at='pallid', quest='q_scrimshaw', depth=1600, luck=2.3, control=0.37, reel=2.12, str=2.75, lure=1.85, light=1, col='#efe6d0', tip='#2a2a2a', desc='Carved from old whalebone. Every inch tells a story.'),
    T(id='ahab', name="Ahab's Harpoon", price=0, at='pallid', quest='q_ahab', depth=1600, luck=2.35, control=0.372, reel=2.18, str=2.85, lure=1.9, light=1, col='#2a2a30', tip='#c84a3a', desc='It belonged to a captain who never let go.'),
    T(id='whitewhale', name='White Whale Rod', price=900000, at='pallid', need='ambergris', depth=1600, luck=2.45, control=0.375, reel=2.25, str=2.95, lure=1.95, heat=True, light=1, col='#f2eee4', tip='#bfe8ff', desc="Made with the white whale's ambergris."),
    # Frostbite Shelf
    T(id='icicle', name='Icicle Rod', price=650000, at='frost', depth=1100, luck=2.5, control=0.376, reel=2.3, str=3.0, lure=1.98, light=1, col='#9fe8ff', tip='#ffffff', desc='Blue ice that never melts. It slows whatever it touches.'),
    T(id='aurora', name='Aurora Rod', price=1050000, at='frost', depth=1400, luck=2.62, control=0.38, reel=2.4, str=3.12, lure=2.04, light=1, col='#2a6a5a', tip='#7fffd4', desc='Strung with a thread of the northern lights.'),
    T(id='tusk', name='Narwhal Tusk Rod', price=0, at='frost', quest='q_tusk', depth=1400, luck=2.66, control=0.384, reel=2.42, str=3.15, lure=2.08, light=1, col='#efe6d0', tip='#bfe8ff', desc='A spiral tusk found frozen in the ice.'),
    T(id='pincer', name='Pincer Rod', price=0, at='frost', quest='q_shell', depth=1400, luck=2.7, control=0.386, reel=2.48, str=3.2, lure=2.1, light=1, col='#c86a4a', tip='#ffd0b0', desc='Snapped off the Ancient Crab. It still pinches.'),
    T(id='shellguard', name='Shellguard Rod', price=2400000, at='frost', need='carapace', depth=1400, luck=2.8, control=0.39, reel=2.55, str=3.35, lure=2.15, heat=True, light=1, col='#8a4a3a', tip='#9fe8ff', desc="Plated with the Ancient Crab's shell."),
    # Loch Ness
    T(id='heather', name='Heather Rod', price=150000, at='loch', depth=230, luck=1.86, control=0.35, reel=1.84, str=2.28, lure=1.62, light=1, col='#8a5aa0', tip='#e0b0ff', desc='Bound with Highland heather. Reaches the bottom of the loch.'),
    T(id='tartan', name='Tartan Rod', price=0, at='loch', quest='q_tartan', depth=230, luck=1.96, control=0.356, reel=1.9, str=2.36, lure=1.68, light=1, col='#c8323a', tip='#2a6a3a', desc='Wrapped in the clan tartan. Fish find it very fetching.'),
    T(id='monsterrod', name='Monster Hunter Rod', price=650000, at='loch', need='photo', depth=230, luck=2.16, control=0.364, reel=2.04, str=2.62, lure=1.82, heat=True, light=1, col='#3d5a3a', tip='#c8ff9a', desc='Built around the only real photo of Nessie. Proof, at last.'),
    # Mariana Deep
    T(id='pressure', name='Pressure Rod', price=1800000, at='mariana', depth=4000, luck=2.85, control=0.39, reel=2.58, str=3.4, lure=2.18, light=1, col='#3a4a5a', tip='#ffb43a', desc='Built like a submarine hull. Reaches 4,000 m.'),
    T(id='hadal', name='Hadal Rod', price=3200000, at='mariana', depth=8000, luck=2.98, control=0.394, reel=2.68, str=3.55, lure=2.24, light=1, col='#1a2a4a', tip='#7fbfff', desc='Tested at the bottom of the trench. Reaches 8,000 m.'),
    T(id='challengerrod', name='Challenger Rod', price=0, at='mariana', quest='q_deep', depth=11000, luck=3.05, control=0.396, reel=2.74, str=3.62, lure=2.28, light=1, col='#e8e8f0', tip='#ff5ab0', desc='Reaches the very bottom of the world.'),
    T(id='sounding', name='Sounding Rod', price=0, at='mariana', quest='q_bloop', depth=11000, luck=3.1, control=0.398, reel=2.8, str=3.7, lure=2.3, light=1, col='#6a9ab8', tip='#9fffe8', desc='It hums the Bloop\'s note. Fish come to listen.'),
    T(id='pearlrod', name='Echo Pearl Rod', price=6000000, at='mariana', need='pearl', depth=11000, luck=3.2, control=0.4, reel=2.88, str=3.85, lure=2.36, heat=True, light=1, col='#bfe0f0', tip='#9fffe8', desc='Set with the Bloop\'s Echo Pearl.'),
    # Atlantis
    T(id='marblerod', name='Marble Rod', price=0, at='atlantis', quest='q_marble', depth=3000, luck=3.25, control=0.402, reel=2.92, str=3.92, lure=2.4, light=1, col='#d9d0ad', tip='#ffe08a', desc='Carved from a fallen column. It remembers where the fish used to be.'),
    T(id='inkwellrod', name='Inkwell Rod', price=0, at='atlantis', quest='q_kraken', depth=4200, luck=3.3, control=0.405, reel=2.96, str=4.0, lure=2.42, light=1, col='#4d375e', tip='#ff5ab0', desc='A Kraken arm, turned into a rod. The ink never quite dries.'),
    T(id='krakenrod', name='Kraken Rod', price=12000000, at='atlantis', need='beak', depth=5200, luck=3.5, control=0.41, reel=3.05, str=4.2, lure=2.5, heat=True, light=1, col='#713a78', tip='#ff5ab0', desc='Bound with a Kraken Beak. The line holds like a tentacle.'),
    T(id='eclipse', name='Eclipse Rod', price=0, at='redhollow', quest='q_hollow', depth=1800, luck=3.55, control=0.412, reel=3.1, str=4.25, lure=2.55, heat=True, light=1, col='#571b3b', tip='#ff3a5e', desc='A sliver of the broken moon. Blood Moon answers its call.'),
]
ROD = {r.id: r for r in RODS}

# ---------------- Boats (hold size, and which islands they can reach) ----------------
BOATS = [
    T(id='dinghy', name='Dinghy', price=0, tier=0, hold=15, col='#c86b3c', desc='Leaks a little. Fits one cat.'),
    T(id='skiff', name='Reef Skiff', price=1500, tier=1, hold=30, col='#2f8fd6', desc='Sturdy enough to reach the Coral Reef.'),
    T(id='ironhull', name='Ironhull Trawler', price=12000, tier=2, hold=55, col='#5a6470', desc="Armoured hull for the Volcanic Biome's boiling water."),
    T(id='bathy', name='Bathyscaphe', price=45000, tier=3, hold=90, col='#f2c14e', desc='Pressure-proof. Carries you to the Deep Trench.'),
    T(id='schooner', name='Whaling Schooner', price=150000, tier=4, hold=120, col='#4a3424', desc='Two masts and a hold that smells of oil.'),
    T(id='icebreaker', name='Icebreaker', price=420000, tier=5, hold=150, col='#c8322a', desc='A steel bow that splits the pack ice.'),
    T(id='hadalsub', name='Hadal Sub', price=1200000, tier=6, hold=190, col='#ffb43a', desc='Takes you over the deepest place in the sea.'),
    T(id='orichalcumargo', name='Orichalcum Argo', price=3600000, tier=7, hold=230, col='#b69a59', desc='An Atlantean hull, sealed against pressure and older than the harbour.'),
]
BOAT = {b.id: b for b in BOATS}

# ---------------- Gear (one-time) and bait (stacks) ----------------
GEAR = [
    T(id='sonar1', name='Sonar Mk I', price=900, icon='sonar', desc='Fish glow in their rarity colour.'),
    T(id='sonar2', name='Sonar Mk II', price=6000, need='sonar1', icon='sonar', desc='Adds names and shows mutations from afar.'),
    T(id='sonar3', name='Sonar Mk III', price=30000, need='sonar2', icon='radar', desc='A sonar screen tracks Legendary and better fish around you, and shows how far away each one is.'),
    T(id='shield', name='Heat Shield', price=9000, icon='shield', desc='Lava vents no longer burn your line, and heat stops adding tension.'),
    T(id='lamp', name='Deep Lamp', price=18000, icon='lamp', desc='Lights a much wider circle in the trench.'),
    T(id='reel', name='Gold Reel', price=4000, icon='reel', desc='Catch progress fills 12% faster on every rod.'),
    T(id='charm', name='Ability Charm', price=12000, icon='charm', desc='Your rod ability charges 35% faster.'),
    T(id='catcollar', name='Coral Cat Collar', price=2500, at='reef', icon='charm', accessory=True, desc='A bright reef-made collar. Fish bite 6% sooner.'),
    T(id='shellbracelet', name='Tidal Shell Bracelet', price=180000, at='pallid', icon='charm', accessory=True, desc='An accessory that steadies the line: tension builds 5% slower.'),
    T(id='moonbell', name='Moonbell Anklet', price=520000, at='frost', icon='charm', accessory=True, desc='A tiny bell from the ice shelf. Line tension builds 7% slower.'),
    T(id='orichalcumcompass', name='Orichalcum Compass', price=1400000, at='mariana', icon='radar', accessory=True, desc='An accessory that points toward rare fish and adds 5% luck.'),
    T(id='pearlcharm', name='Keeper’s Pearl Charm', price=2600000, at='atlantis', icon='charm', accessory=True, desc='A pearl from the old city: +6% luck and +5% mutation chance.'),
]
GEARI = {g.id: g for g in GEAR}
BAITS = [
    T(id='worm', name='Worm', price=10, per=10, dot='#e88a8a', bite=1.35, luck=1, desc='Fish notice your hook 35% sooner.'),
    T(id='shrimp', name='Shrimp', price=45, per=10, dot='#ff9a6a', bite=1.1, luck=1.25, desc='+25% luck for rarer fish.'),
    T(id='golden', name='Golden Fly', price=120, per=5, dot='#ffd23d', bite=1, luck=1.1, mut=2, desc='Doubles mutation chances.'),
    T(id='grub', name='Magma Grub', price=220, per=5, dot='#ff5a1f', bite=1.2, luck=1.35, heat=True, at='volcano', desc='Volcano only: +35% luck, and your line ignores the heat.'),
    T(id='glow', name='Glowworm', price=320, per=5, dot='#c8ff6a', bite=1.2, luck=1.45, light=1, at='trench', desc='Trench: +45% luck and a brighter hook.'),
    T(id='levlure', name='Leviathan Lure', price=15000, per=1, dot='#00ffd5', bite=1, luck=1, boss=120, at='trench', desc='Trench: the Leviathan is 120x more likely to come for the hook.'),
    T(id='squidlure', name='Giant Squid Lure', price=30000, per=1, dot='#e8e4da', bite=1, luck=1, boss=120, at='pallid', desc='Pallid Sea: the Pallid Whale is 120x more likely to come for the hook. Sperm whales cannot resist squid.'),
    T(id='crabpot', name='Crab Pot Lure', price=60000, per=1, dot='#c86a4a', bite=1, luck=1, boss=120, at='frost', desc='Frostbite Shelf: the Ancient Crab is 120x more likely to come for the hook. Rotten fish heads, its favourite.'),
    T(id='haggis', name='Haggis Lure', price=30000, per=1, dot='#8a5a3a', bite=1, luck=1, boss=120, at='loch', desc='Loch Ness: nobody else will eat it. Nessie is 120x more likely to come for the hook.'),
    T(id='siren', name='Deep Siren Lure', price=120000, per=1, dot='#9fffe8', bite=1, luck=1, boss=120, at='mariana', desc='Mariana Deep: plays a note only one thing down there answers. The Bloop is 120x more likely to come for the hook.'),
    T(id='whalefall', name='Whale Fall Lure', price=240000, per=1, dot='#ff5ab0', bite=1, luck=1, boss=120, at='atlantis', desc='Atlantis: bears the last Keeper’s mark. The Kraken is 120x more likely to answer.'),
    T(id='fracturelure', name='Fracture Lure', price=360000, per=1, dot='#ff3a5e', bite=1, luck=1, boss=120, at='redhollow', desc='Red Hollow: bait for the thing watching through the crack.'),
]
BAIT = {b.id: b for b in BAITS}
RELIC_PRICE = 1200

# ---------------- Enchantments (rolled at the Altar on the Coral Reef) ----------------
ENCHANTS = [
    T(id='magnet', name='Magnet', w=20, col='#ff6a6a', desc='Fish notice your hook from 50% further away and race to it 25% faster.'),
    T(id='swift', name='Swift', w=18, col='#7cf0ff', desc='Catch progress fills 25% faster.'),
    T(id='steady', name='Steady', w=18, col='#9dffb0', desc='Your reel bar is 18% wider.'),
    T(id='resilient', name='Resilient', w=16, col='#ffd27a', desc='Line tension builds 40% slower.'),
    T(id='lucky', name='Lucky', w=13, col='#7dff5a', desc='+30% luck.'),
    T(id='fortune', name='Fortune', w=9, col='#ffd23d', desc='Mutations 1.8x as likely, and fish sell for 15% more.'),
    T(id='diver', name='Deep Diver', w=8, col='#5aa9ff', desc='+25% max depth.'),
    T(id='blazing', name='Blazing', w=5, col='#ff7a2a', desc="Lava vents and heat can't touch your line."),
    T(id='mythical', name='Mythical', w=1.5, col='#ff3d7f', desc='+50% luck, +10% catch speed, +10% bar width.'),
    T(id='tidecaller', name='Tidecaller', w=1, col='#8ce1c4', desc='Atlantis enchantment: +20% luck and +8% catch speed.'),
]
ENCH = {e.id: e for e in ENCHANTS}

PATCH_NOTES = [
    '1.7.0: Rarer fish move more deliberately, and later islands have fairer reel bars, tension and catch pacing.',
    'Mythic and boss fights now draw varied tricks from larger move pools, with separate cooldowns so one trick cannot repeat back-to-back.',
    'Admins can summon a random island Mythic or boss. Limited-fish spawns use the server inventory and remain shared with the island.',
    'Meet two new mutations: Stormbound and Moonlit. Both can be upgraded as you catch more of them.',
    'New cat accessories add bite speed, steadier lines, or extra luck. Their shop cards show when they unlock and what they do.',
    'Patch notes now open automatically once after an update and remain available in Settings → What’s New.',
    'Surge now uses F by default; Fishpedia moves to G. Existing custom keybinds are kept.',
    'UI polish: clearer equipped/accessory tags, improved gear unlock labels and a more readable update-notes screen.',
    '1.6.0: Explore Atlantis and Red Hollow, discover new fish and gear, and challenge the Kraken and Watcher Below.',
    'Shared Mythic fish now appear consistently to everyone on the same island. The first angler to hook one claims it.',
    'Poseidon’s statue now opens the hidden portal after you recover the Broken Trident. The Red Hollow quest has two endings.',
    'Cavern-only fish now hide in deep-island caves, and Keeper’s Logs reveal ruins crafting blueprints.',
    'The Firstlight Koi is limited to three catches per server; its remaining supply persists across server restarts.',
    'The Kraken’s Rebirth is a final fake-out: keep the line steady when it surges back at 55%.',
    '1.5.2: Release polish pass: clearer bait management, versioned multiplayer messaging, and stronger in-game guidance for the new systems.',
    'Saved fish bait is now easier to track in the bag panel, and the control reminder explains the V key for clearing it.',
    '1.5.1: Patch notes are now in-game, with better altar rolling, fish-bait support, mutation upgrades, and pet balance tweaks.',
    'The altar can now roll until a chosen enchantment appears, while preserving the existing one-relic spin flow.',
    'Common fish are stored as a second bait bonus alongside your food bait, stacking their bonuses together.',
    'Biscuit and Mittens are tuned to make late-game fishing feel more deliberate and less random.',
    'Mutation upgrades now increase the value of specially caught fish and reward repeated mutated catches.',
]

KEEPER_LOGS = [
    T(id='shore', title='A line to hold', text='Hold the line. The note was written on a scrap of sail and tucked into a bait tin. No one remembers who left it.'),
    T(id='reef', title='The old altar', text='The reef keepers call the altar old. They mean older than the reef, older than the harbour, older than the names we give the sea.'),
    T(id='volcano', title='A summons', text='A lure-maker’s mark appears on the boss lures: a small hooked line inside a circle. These are summons, not bait.'),
    T(id='trench', title='The lantern', text='The Leviathan’s glow is a lantern left burning for something that never came back.'),
    T(id='loch', title='The one who ran', text='Nessie left the salt sea. Of the Wardens, she alone tried to leave the work behind.'),
    T(id='pallid', title='Ahab', text='Ahab held the Line so hard it cut him. The Line was meant to be held, not clung to.'),
    T(id='frost', title='A witness in ice', text='The Glacier Koi was frozen for ten thousand years. When the ice opened, it swam away as if nothing had happened.'),
    T(id='mariana', title='The signal', text='The Bloop was the call that told the others to hold. Every cat hears it in dreams.'),
    T(id='atlantis', title='The last Keeper', text='The city was built around a gate. The last Keeper made the lures and waited for someone who could hear the signal.'),
    T(id='kraken', title='The gate', text='The Kraken has not guarded the gate from us. It has guarded us from what is on the other side.'),
]

# The first six coats are free starting choices; the last is earned from the portal ending.
FURS = ['#f4a53c', '#8a8f99', '#2b2b30', '#f2ede4', '#c8763a', '#e6c79c', '#d84c73']
FUR_BONUSES = {
    '#f4a53c': D(bite=1.05), '#8a8f99': D(hookV=1.05), '#2b2b30': D(luck=1.04),
    '#f2ede4': D(mut=1.05), '#c8763a': D(reel=1.05), '#e6c79c': D(control=1.04),
    '#d84c73': D(luck=1.05, mut=1.05),
}
FUR_REWARD = '#d84c73'

# ---------------- Controls ----------------
# Key names are pygame key names (pygame.key.name).
DEFAULT_KEYS = {
    'left': ['left', 'a'], 'right': ['right', 'd'], 'up': ['up', 'w'], 'down': ['down', 's'],
    'act': ['space', 'return'], 'ability': ['q'], 'skill': ['f'], 'recall': ['r'], 'bait': ['v'], 'bag': ['b'], 'shop': ['e'], 'map': ['m'],
    'dex': ['g'], 'quests': ['j'], 'chat': ['t'], 'players': ['tab'],
}
ACTION_NAMES = {
    'left': 'Sail / steer left', 'right': 'Sail / steer right', 'up': 'Reel the hook up',
    'down': 'Dive faster', 'act': 'Cast / reel', 'ability': 'Use rod ability', 'skill': 'Use rod skill (Surge)',
    'recall': 'Pull the line in', 'bait': 'Clear saved fish bait / active bait bonus',
    'bag': 'Open bag and pets', 'shop': 'Open shop', 'map': 'Open sea chart', 'dex': 'Open Fishpedia', 'quests': 'Open quests',
    'chat': 'Chat (online)', 'players': 'Players & leaderboard',
}
EMOTES = [
    T(id='wave', text='Hi!', col='#ffd98a'),
    T(id='heart', text='<3', col='#ff8fb0'),
    T(id='laugh', text='haha', col='#9dffb0'),
    T(id='wow', text='WOW', col='#7cf0ff'),
    T(id='cheer', text='GO GO GO!', col='#00ffd5'),
]

# ---------------- Reel difficulty by rarity ----------------
# speed: how fast the fish moves on the reel bar (bar widths per second)
# zone: multiplies your rod's bar width   gain / loss: catch progress per second inside / outside
# ten: line tension per second while the fish is outside your bar
# Each island's ISLE numbers are applied on top, and your rod's stats push back.
REEL = [
    T(speed=0.13, zone=1.30, gain=0.25, loss=0.065, ten=0.10, label='Easy'),
    T(speed=0.21, zone=1.10, gain=0.19, loss=0.09, ten=0.12, label='Medium'),
    T(speed=0.28, zone=0.90, gain=0.15, loss=0.10, ten=0.15, label='Hard'),
    T(speed=0.34, zone=0.82, gain=0.13, loss=0.11, ten=0.18, label='Very hard'),
    T(speed=0.40, zone=0.80, gain=0.125, loss=0.12, ten=0.21, label='Expert'),
    T(speed=0.40, zone=0.80, gain=0.115, loss=0.105, ten=0.24, label='Insane'),
    T(speed=0.34, zone=0.82, gain=0.11, loss=0.09, ten=0.22, label='BOSS'),
]

# ---------------- Fish gimmicks (tricks they pull on the reel bar) ----------------
# kind: 'passive' tricks are always on; the rest trigger every few seconds, with a warning first.
GIMMICKS = {
    'dash': T(name='Dash', col='#7cf0ff', dur=0.6, cool=6.0, desc='Bolts across the bar without warning.'),
    'puff': T(name='Puff', col='#ffd23d', dur=2.2, cool=8.0, desc='Puffs up and squeezes your bar smaller.'),
    'ink': T(name='Ink', col='#8a6cff', dur=2.4, cool=8.0, desc='Squirts ink that hides the fish.'),
    'zap': T(name='Zap', col='#62f3ff', dur=0.7, cool=7.0, desc='Shocks the line: tension jumps and your bar jitters.'),
    'camo': T(name='Camouflage', col='#9fd3a8', dur=2.6, cool=8.0, desc='Turns almost invisible for a few seconds.'),
    'decoy': T(name='Decoy', col='#ff9a3c', dur=3.0, cool=9.0, desc='Shows a fake fish. Only the real one counts.'),
    'split': T(name='Split', col='#ffcf7a', dur=2.8, cool=9.0, desc='Splits into three. Only one of them is real.'),
    'flash': T(name='Flash', col='#ffffff', dur=0.8, cool=7.0, desc='A blinding flash hides everything for a moment.'),
    'regen': T(name='Regenerate', col='#ff8fcf', dur=2.0, cool=9.0, desc='Heals itself, draining your progress for a moment.'),
    'warp': T(name='Warp', col='#c26bff', dur=2.0, cool=8.0, desc='Bends reality: holding moves your bar the wrong way.'),
    'glitch': T(name='Glitch', col='#ff5ab0', dur=1.2, cool=8.0, desc='The fractured water jumps your bar to a new position.'),
    'burn': T(name='Scorch', col='#ff6a1a', dur=2.0, cool=9.0, desc='Scorches the line so tension rises even inside your bar. Heat protection blocks it.'),
    'stun': T(name='Venom', col='#e05a3a', dur=1.0, cool=8.0, desc='Venom locks your bar in place for a second.'),
    'sharp': T(name='Razor Teeth', col='#d6c8ff', dur=0.5, cool=7.0, desc='Slashes at your line for a sudden tension spike.'),
    'heavy': T(name='Heavy', col='#a8b4c0', kind='passive', desc='So heavy that your bar sinks back faster.'),
    'slippery': T(name='Slippery', col='#5aff8a', kind='passive', desc='Your progress drops much faster when it slips out.'),
    'thrash': T(name='Thrash', col='#ff6a6a', kind='passive', desc='Goes wild once it is more than half caught.'),
    'rebirth': T(name='Rebirth', col='#ffb03a', kind='passive', desc='The first time you land it, it bursts back to life at 55%.'),
}
FISH_GIMS = {
    # shore
    'seabass': ['dash'], 'flounder': ['camo'], 'puffer': ['puff'], 'snapper': ['thrash'], 'wolfeel': ['thrash'],
    'sunfish': ['heavy'], 'moonfish': ['heavy', 'dash'], 'goldtuna': ['thrash'],
    # reef
    'butterfly': ['decoy'], 'trigger': ['sharp'], 'moray': ['slippery'], 'lionfish': ['stun'], 'seahorse': ['camo'],
    'reefshark': ['dash', 'thrash'], 'manta': ['heavy'], 'wrasse': ['heavy', 'thrash'],
    'angelcrown': ['decoy', 'dash'], 'coralwyrm': ['decoy'],
    # volcano
    'embersmelt': ['dash'], 'eelpout': ['slippery'], 'cindereel': ['slippery'], 'basalt': ['heavy'], 'rockfish': ['stun'],
    'magmapuff': ['puff', 'burn'], 'obsidian': ['sharp'], 'barracuda': ['dash', 'sharp'], 'lavaray': ['burn', 'heavy'],
    'sturgeon': ['heavy', 'thrash'], 'phoenix': ['rebirth', 'dash'], 'seraph': ['rebirth', 'burn'],
    'sailfish': ['dash', 'burn', 'thrash'],
    # trench
    'snailfish': ['slippery'], 'vampsquid': ['ink'], 'viperfish': ['flash'], 'gulper': ['slippery'], 'angler': ['decoy'],
    'barreleye': ['camo'], 'fangtooth': ['sharp'], 'giantsquid': ['ink', 'heavy'], 'frilledshark': ['slippery', 'thrash'],
    'dragonfish': ['flash'], 'oarfish': ['camo', 'split'], 'whiskerkoi': ['split', 'regen'],
    'voidjelly': ['warp', 'regen'], 'leviathan': ['heavy'],
    # pallid
    'pollock': ['dash'], 'halibut': ['camo', 'heavy'], 'ling': ['slippery'], 'swordfish': ['dash', 'sharp'],
    'sixgill': ['heavy', 'sharp'], 'chimaera': ['camo'], 'bluefin': ['dash', 'thrash'], 'greenland': ['heavy', 'regen'],
    'stormmarlin': ['zap', 'dash', 'thrash'], 'ghostpike': ['camo', 'flash'], 'coelacanth': ['camo', 'split', 'regen'],
    'krakenling': ['ink', 'heavy', 'split'], 'pallidwhale': ['heavy'],
    # frost
    'polarcod': ['dash'], 'icefish': ['camo'], 'frostpout': ['slippery'], 'lumpsucker': ['puff'], 'sculpin': ['stun', 'puff'],
    'toothfish': ['heavy', 'dash'], 'wolffish': ['sharp', 'thrash'], 'glasssquid': ['camo', 'ink'], 'skate': ['heavy', 'camo'],
    'sleepershark': ['heavy', 'regen'], 'colossalsquid': ['ink', 'heavy', 'sharp'], 'aurorachar': ['dash', 'flash'],
    'frostmanta': ['heavy', 'camo', 'stun'], 'glacierkoi': ['split', 'regen', 'camo'], 'polarjelly': ['warp', 'flash', 'regen'],
    'ancientcrab': ['heavy'],
    # mariana
    'flyingfish': ['dash'], 'tripodfish': ['camo'], 'cuskeel': ['slippery'], 'hadalsnail': ['slippery'], 'cookiecutter': ['sharp', 'dash'],
    'swallower': ['heavy', 'sharp'], 'dumbo': ['camo', 'ink'], 'tonguefish': ['camo'], 'stareater': ['flash', 'decoy'],
    'lizardfish': ['dash', 'sharp'], 'faceless': ['camo', 'slippery'], 'megamouth': ['heavy', 'regen'], 'goblinshark': ['dash', 'sharp'],
    'midnightmanta': ['heavy', 'camo', 'flash'], 'challenger': ['flash', 'warp', 'dash'], 'siphonophore': ['zap', 'split', 'regen'],
    'abyssangel': ['warp', 'flash', 'split', 'regen'], 'bloop': ['heavy'],
    # loch ness
    'stickleback': ['dash'], 'minnow': ['decoy'], 'arcticcharr': ['camo'], 'euroeel': ['slippery'], 'seatrout': ['dash'],
    'lamprey': ['sharp', 'slippery'], 'salmon': ['dash', 'thrash'], 'pike': ['dash', 'sharp'], 'ferox': ['thrash', 'heavy'],
    'locheel': ['slippery', 'heavy', 'thrash'], 'wels': ['heavy', 'regen'], 'salmonking': ['dash', 'flash', 'split'],
    'wispjelly': ['warp', 'flash', 'regen'], 'kelpie': ['camo', 'warp', 'dash'], 'nessie': ['heavy'],
    # Atlantis
    'marblegrouper': ['heavy'], 'siltpuffer': ['puff'], 'philosophercarp': ['decoy'], 'tridentbarracuda': ['dash', 'sharp'],
    'amphoraclowfish': ['camo'], 'oracleeel': ['camo', 'decoy'], 'lamplighterjelly': ['flash', 'regen'],
    'vaultoctopus': ['ink', 'split'], 'gorgonray': ['stun', 'heavy'],
    'hippocampus': ['dash', 'thrash', 'camo'], 'orichalcumkoi': ['split', 'rebirth', 'regen'],
    'nereidjelly': ['warp', 'flash', 'regen', 'split'], 'kraken': ['heavy'],
    # Red Hollow
    'redfinfragment': ['dash'], 'glassminnow': ['camo'], 'moonshardray': ['warp', 'flash'],
    'watcherbelow': ['heavy'],
}
for _f in FISH:
    _f.gim = FISH_GIMS.get(_f.id, [])
MUT_GIMS = {'electric': ['zap'], 'corrupted': ['warp'], 'gilded': ['slippery'],
            'prismatic': ['flash'],             'tideworn': ['regen'], 'stormbound': ['zap'], 'moonlit': ['flash']}
MYTHIC_GIM_POOL = ['dash', 'puff', 'ink', 'zap', 'camo', 'decoy', 'split', 'flash', 'regen', 'warp',
                   'glitch', 'burn', 'stun', 'sharp']
BOSS_STAGE_GIMS = {
            1: ['heavy', 'dash', 'ink', 'puff', 'camo', 'zap', 'sharp'],
            2: ['heavy', 'ink', 'zap', 'dash', 'sharp', 'decoy', 'split', 'burn', 'stun'],
            3: ['heavy', 'warp', 'flash', 'dash', 'regen', 'glitch', 'burn', 'stun', 'sharp', 'zap'],
}

# ---------------- Bosses (one per island from the Deep Trench on) ----------------
# fish: the boss. lure: the bait that calls it. mat: what it drops (for that island's best rod).
# behs/gims: how it fights in each of its 3 stages. eyes: the colour of the lights that watch you when it is near.
MATS = {
    'scale': T(name='Leviathan Scale', col='#00ffd5', drop='a Leviathan Scale'),
    'ambergris': T(name='Ambergris', col='#e8d8a8', drop='a lump of Ambergris'),
    'carapace': T(name='Ancient Carapace', col='#c86a4a', drop='a piece of Ancient Carapace'),
    'pearl': T(name='Echo Pearl', col='#9fffe8', drop='an Echo Pearl'),
    'photo': T(name='Blurry Nessie Photo', col='#c8ff9a', drop='a Blurry Nessie Photo (the only real one)'),
    'beak': T(name='Kraken Beak', col='#ff5ab0', drop='a Kraken Beak'),
    'trident': T(name='Broken Trident', col='#8ce1c4', drop='the Broken Trident'),
    'shard': T(name='Moon Shard', col='#ff3a5e', drop='a Moon Shard'),
}
BOSSES = {
    'trench': T(fish='leviathan', lure='levlure', mat='scale', behs=['calm', 'dart', 'abyss'], gims=BOSS_STAGE_GIMS, eyes='#00ffd5',
                dread='Something colossal is moving in the dark below you...', short='THE LEVIATHAN!',
                stage='The Leviathan breaks free of the depths. Keep reeling!'),
    'pallid': T(fish='pallidwhale', lure='squidlure', mat='ambergris', behs=['calm', 'dart', 'drift'],
                gims={1: ['heavy', 'dash'], 2: ['heavy', 'dash', 'camo', 'sharp'], 3: ['heavy', 'dash', 'flash', 'regen']}, eyes='#dfe8f0',
                dread='A pale shape the size of a ship is gliding beneath you...', short='THE WHITE WHALE!',
                stage='The Pallid Whale sounds and dives. Keep reeling!'),
    'frost': T(fish='ancientcrab', lure='crabpot', mat='carapace', behs=['calm', 'erratic', 'calm'],
               gims={1: ['heavy', 'stun'], 2: ['heavy', 'puff', 'sharp'], 3: ['heavy', 'stun', 'dash', 'regen']},
               eyes='#9fe8ff', dread='The seabed below you... moves.', short='THE ANCIENT CRAB!',
               stage='The Ancient Crab tears itself out of the ice. Keep reeling!'),
    'mariana': T(fish='bloop', lure='siren', mat='pearl', behs=['drift', 'abyss', 'calm'],
                 gims={1: ['heavy', 'camo'], 2: ['heavy', 'warp', 'zap'], 3: ['heavy', 'warp', 'flash', 'regen']},
                 eyes='#9fffe8', dread='A deep sound rolls up from below. Something enormous is singing.', short='THE BLOOP!',
                 stage='The Bloop answers from the deep. Keep reeling!'),
    'loch': T(fish='nessie', lure='haggis', mat='photo', behs=['calm', 'dart', 'calm'],
              gims={1: ['heavy'], 2: ['heavy', 'ink', 'dash'], 3: ['heavy', 'dash', 'regen']},
              eyes='#c8ff9a', dread='The loch goes flat and still... a long neck rises out of the peat-dark water.', short='NESSIE!',
              stage='Nessie dives into the dark peat. Keep reeling!'),
    'atlantis': T(fish='kraken', lure='whalefall', mat='beak', behs=['calm', 'erratic', 'abyss'],
                  gims={1: ['heavy', 'ink', 'camo', 'decoy'], 2: ['heavy', 'split', 'stun', 'sharp', 'flash'],
                        3: ['heavy', 'thrash', 'rebirth', 'dash', 'zap', 'warp', 'regen']},
                  eyes='#ff5ab0', dread='Every wreck on the seabed turns slowly to face you...', short='THE KRAKEN!',
                  stage='The Kraken’s arms close around the ruins. Keep reeling!'),
    'redhollow': T(fish='watcherbelow', lure='fracturelure', mat='shard', behs=['drift', 'erratic', 'abyss'],
                   gims={1: ['heavy', 'camo'], 2: ['heavy', 'glitch', 'warp'], 3: ['heavy', 'glitch', 'warp', 'rebirth', 'flash']},
                   eyes='#ff294f', dread='The red moon flickers. Something beneath the mirror has opened its eye.', short='THE WATCHER BELOW!',
                   stage='The Watcher slips through the crack in the world. Keep reeling!'),
}

# Every island boss can use every trick found on that island's Legendary or Mythic fish.
for _bid, _boss in BOSSES.items():
    _known = {g for _sp in FISH if _sp.b == _bid and _sp.r in ('legendary', 'mythic') for g in _sp.gim}
    _available = {g for _stage in _boss.gims.values() for g in _stage}
    for _g in sorted(_known - _available):
        _boss.gims[3].append(_g)

# ---------------- Rod abilities (charge by keeping the fish in your bar, then press Q) ----------------
# The first rods have simple abilities; fancier ones come with the rods of later islands.
ABILITIES = {
    'tug': T(name='Tug', col='#e8c27a', charge=3.5, desc='Yank the line: +10% catch progress.'),
    'quick': T(name='Quick Reel', col='#7cf0ff', charge=5.0, dur=4.0, desc='Catch progress fills twice as fast for 4 seconds.'),
    'anchor': T(name='Anchor', col='#c8d8e8', charge=4.5, dur=5.0, desc='For 5 seconds your bar stops sliding back: it stays wherever you leave it.'),
    'purr': T(name='Purrfect', col='#ffd9a0', charge=4.0, desc='Snaps your bar right onto the fish and adds 6% progress. Cat power.'),
    'magnet': T(name='Lure Magnet', col='#ff6a8a', charge=6.0, dur=3.0, desc='Your bar follows the fish all by itself for 3 seconds.'),
    'net': T(name='Big Net', col='#9dffb0', charge=5.5, dur=4.0, desc='Your bar grows 60% wider for 4 seconds.'),
    'freeze': T(name='Freeze', col='#bfefff', charge=6.0, dur=3.0, desc='Freezes the fish solid for 3 seconds: it can not move or use tricks.'),
    'slice': T(name='Slice', col='#ff6fa8', charge=6.0, desc='Slash the fish for +30% progress instantly (3% less for each rarity above Common).'),
    'shield': T(name='Coral Shield', col='#2fd0a0', charge=6.0, dur=4.0, desc='For 4 seconds your progress cannot drop and line tension cannot rise.'),
    'storm': T(name='Lightning', col='#62f3ff', charge=6.0, desc='+15% progress, stuns the fish for 1.5 seconds and wipes out its tricks.'),
    'inferno': T(name='Inferno', col='#ff7a2a', charge=6.0, dur=4.0, desc='Burns away all line tension for 4 seconds, and progress fills 50% faster.'),
    'harpoon': T(name='Harpoon', col='#c8d2dc', charge=6.0, desc='+22% progress at once, whatever the rarity, but +15% line tension.'),
    'phoenix': T(name='Rebirth Flame', col='#ff7a1a', charge=7.0, dur=6.0, desc='For 6 seconds, a fish that would escape or snap your line is saved at 30%.'),
    'gold': T(name='Golden Touch', col='#ffd23d', charge=6.5, dur=3.0, desc='Progress fills 2.5x faster for 3 seconds, and the catch sells for 25% more.'),
    'gravity': T(name='Gravity Well', col='#5ccfff', charge=6.0, dur=3.5, desc='Pulls the fish into the middle of your bar for 3.5 seconds.'),
    'whirl': T(name='Whirlpool', col='#6ad8ff', charge=6.5, dur=4.0, desc='Drags the fish toward your bar and adds 4% progress every second, for 4 seconds.'),
    'slowmo': T(name='Time Warp', col='#7ffcff', charge=6.5, dur=5.0, desc='The fish moves at 40% speed for 5 seconds.'),
    'echo': T(name='Sonar Ping', col='#7fffd4', charge=5.5, dur=6.0, desc='+8% progress, and for 6 seconds a marker shows where the fish is heading and tricks are spotted early.'),
    'stars': T(name='Star Shower', col='#b48cff', charge=7.0, dur=3.0, desc='Falling stars add 30% progress over 3 seconds, whatever the rarity.'),
    'tidal': T(name='Tidal Slash', col='#00ffd5', charge=7.0, dur=2.0, desc='Slice and Freeze at once: +25% progress (3% less per rarity) and a 2-second freeze.'),
    # new in 1.4
    'barb': T(name='Barbed Hook', col='#c8c0b0', charge=5.0, desc='+5% now, and for the rest of the fight slipping out loses 40% less progress.'),
    'riptide': T(name='Riptide', col='#5ab8e8', charge=6.0, dur=3.5, desc='For 3.5 seconds the fish is swept along with your bar.'),
    'breach': T(name='Breach', col='#bfe8ff', charge=6.0, dur=3.0, desc='+12% progress, and your bar is twice as wide for 3 seconds.'),
    'frenzy': T(name='Frenzy', col='#ff5a4a', charge=6.5, dur=3.0, desc='Progress fills 3x as fast for 3 s, but the fish swims 40% faster.'),
    'mirror': T(name='Mirror Bar', col='#e8f4ff', charge=6.5, dur=4.0, desc='A mirrored second bar for 4 s. The fish counts in either one.'),
    'permafrost': T(name='Permafrost', col='#9fe8ff', charge=6.5, dur=2.0, desc='Freezes the fish for 2 s. It stays 25% slower for the rest of the fight.'),
    'siphon': T(name='Siphon', col='#7fe8c8', charge=5.5, desc='Turns half your line tension into progress, then resets the tension.'),
    'song': T(name='Deep Song', col='#9fffe8', charge=7.0, dur=2.0, desc='+20% progress, and the fish is stunned for 2 seconds and stops its tricks.'),
    'carapace': T(name='Carapace Guard', col='#c86a4a', charge=6.5, dur=5.0, desc='For 5 seconds your progress cannot drop and line tension cannot rise.'),
    'bloodmoon': T(name='Blood Moon', col='#ff3a3a', charge=6.5, dur=4.0, desc='Progress fills 2.2x as fast for 4 s, but the line strains even in your bar.'),
    'grip': T(name='Tentacle Grip', col='#ff5ab0', charge=7.0, dur=3.0, desc='For 3 seconds, the fish cannot use tricks and your bar follows it.'),
}
ROD_AB = {'starter': 'tug', 'bamboo': 'quick', 'fiber': 'anchor', 'driftwood': 'purr', 'whisker': 'magnet',
          'carbon': 'net', 'kelp': 'freeze', 'coral': 'slice', 'warden': 'shield', 'storm': 'storm',
          'magma': 'inferno', 'obsidian': 'harpoon', 'phoenixrod': 'phoenix', 'midas': 'gold',
          'abyssal': 'gravity', 'maelstrom': 'whirl', 'glow': 'slowmo', 'deepwatch': 'echo', 'starfall': 'stars',
          'leviathan': 'tidal',
          'whaler': 'barb', 'tiderunner': 'riptide', 'scrimshaw': 'breach', 'ahab': 'frenzy', 'whitewhale': 'mirror',
          'icicle': 'permafrost', 'aurora': 'stars', 'tusk': 'breach', 'pincer': 'tidal', 'shellguard': 'carapace',
          'heather': 'quick', 'tartan': 'magnet', 'monsterrod': 'breach',
          'pressure': 'siphon', 'hadal': 'gravity', 'challengerrod': 'riptide', 'sounding': 'echo', 'pearlrod': 'song',
          'marblerod': 'gravity', 'inkwellrod': 'echo', 'krakenrod': 'grip', 'eclipse': 'bloodmoon'}
for _r in RODS:
    _r.ab = ROD_AB.get(_r.id, 'tug')

SKILLS = {
    'survey': T(name='Sonar Pulse', col='#ffe08a', desc='Mark every nearby Rare-or-better fish for 3 seconds.'),
    'undertow': T(name='Ink Veil', col='#9fffe8', desc='Repel Common–Rare fish and move your hook 40% faster for 3 seconds.'),
    'anchorline': T(name='Anchorline', col='#ff5ab0', desc='Cut line tension by 30% and stun a hooked fish for 1.5 seconds.'),
    'bloodtide': T(name='Bloodtide', col='#ff3a5e', desc='Gain 10% progress and clear the current trick warning.'),
}
ROD_SKILL = {'marblerod': 'survey', 'inkwellrod': 'undertow', 'krakenrod': 'anchorline', 'eclipse': 'bloodtide'}


# ---------------- Quests ----------------
# Every island has one island quest (finish it to be allowed to sail on to the next island) and two
# rod quests, whose rods are made for that island. Progress only counts from when the island is open.
# Goals: catch (n fish, optionally from an island, of a tier or better, of a species), species (n
# different species from an island), perfect (n perfect catches), mut (n fish with a mutation),
# earn (coins from selling), boss (beat a boss: sp names which one, otherwise any).
def Goal(kind, n=1, **k):
    return D(kind=kind, n=n, **k)


QUESTS = [
    # Starter Shore
    T(id='p_shore', isle='shore', island=True, name='Shore Apprentice', unlock='reef', coins=400,
      desc='Prove yourself in the bay and the harbour master will let you sail to the Coral Reef.',
      goals=[Goal('catch', 20, isle='shore'), Goal('species', 6, isle='shore'), Goal('catch', 1, isle='shore', tier=2)]),
    T(id='q_driftwood', isle='shore', name='Hooked on Fishing', rod='driftwood', coins=500,
      desc='Catch 40 fish on Starter Shore.', goals=[Goal('catch', 40, isle='shore')]),
    T(id='q_whisker', isle='shore', name='Purr-fection', rod='whisker', coins=600,
      desc='Land 10 Perfect catches (the fish never slips out of your bar).', goals=[Goal('perfect', 10)]),
    # Coral Reef
    T(id='p_reef', isle='reef', island=True, name='Reef Ranger', unlock='volcano', coins=3000,
      desc='Show the reef keepers you know their waters, and they will chart you a course to the Volcanic Biome.',
      goals=[Goal('catch', 35, isle='reef'), Goal('species', 8, isle='reef'), Goal('catch', 2, isle='reef', tier=3)]),
    T(id='q_warden', isle='reef', name='Reef Explorer', rod='warden', coins=3500,
      desc='Catch 12 different Coral Reef species.', goals=[Goal('species', 12, isle='reef')]),
    T(id='q_storm', isle='reef', name='Storm Chaser', rod='storm', coins=3500,
      desc='Catch 2 Electric fish (on any island).', goals=[Goal('mut', 2, mut='electric')]),
    # Volcanic Biome
    T(id='p_volcano', isle='volcano', island=True, name='Trial by Fire', unlock='trench', coins=15000,
      desc='Only anglers who tame the volcano are trusted with a dive into the Deep Trench.',
      goals=[Goal('catch', 50, isle='volcano'), Goal('species', 9, isle='volcano'), Goal('catch', 1, isle='volcano', tier=4)]),
    T(id='q_phoenix', isle='volcano', name='Rising From the Ashes', rod='phoenixrod', coins=12000,
      desc='Catch a Phoenix Carp.', goals=[Goal('catch', 1, sp='phoenix')]),
    T(id='q_gold', isle='volcano', name='Gold Rush', rod='midas', coins=12000,
      desc='Earn 60,000 coins by selling fish.', goals=[Goal('earn', 60000)]),
    # Deep Trench Abyss
    T(id='p_trench', isle='trench', island=True, name='Abyss Conqueror', unlock='pallid', coins=100000,
      desc='Catch a Mythic and defeat the Leviathan, and the whalers will take you north to the Pallid Sea.',
      goals=[Goal('catch', 1, isle='trench', tier=5), Goal('boss', 1, sp='leviathan')]),
    T(id='q_deepwatch', isle='trench', name='Lights in the Deep', rod='deepwatch', coins=40000,
      desc='Catch 12 different Deep Trench species.', goals=[Goal('species', 12, isle='trench')]),
    T(id='q_mythic', isle='trench', name='Mythic Hunter', rod='starfall', coins=60000,
      desc='Catch 3 Mythic fish.', goals=[Goal('catch', 3, tier=5)]),
    # Pallid Sea
    T(id='p_pallid', isle='pallid', island=True, name='Call Me Angler', unlock='frost', coins=250000,
      desc='Earn the respect of the old whalers. They say there is ice, and worse, further north.',
      goals=[Goal('catch', 60, isle='pallid'), Goal('species', 11, isle='pallid'), Goal('catch', 1, isle='pallid', tier=4)]),
    T(id='q_scrimshaw', isle='pallid', name='Scrimshander', rod='scrimshaw', coins=120000,
      desc='Catch 14 different Pallid Sea species.', goals=[Goal('species', 14, isle='pallid')]),
    T(id='q_ahab', isle='pallid', name='The Chase', rod='ahab', coins=200000,
      desc='Defeat the Pallid Whale.', goals=[Goal('boss', 1, sp='pallidwhale')]),
    # Frostbite Shelf
    T(id='p_frost', isle='frost', island=True, name='Polar Expedition', unlock='mariana', coins=600000,
      desc='Survive the ice and its fish, and the expedition will chart the deepest place in the sea for you.',
      goals=[Goal('catch', 70, isle='frost'), Goal('species', 12, isle='frost'), Goal('catch', 2, isle='frost', tier=4)]),
    T(id='q_tusk', isle='frost', name='Ice Explorer', rod='tusk', coins=300000,
      desc='Catch 14 different Frostbite Shelf species.', goals=[Goal('species', 14, isle='frost')]),
    T(id='q_shell', isle='frost', name='Shell Shock', rod='pincer', coins=500000,
      desc='Defeat the Ancient Crab.', goals=[Goal('boss', 1, sp='ancientcrab')]),
    # Loch Ness (a side trip from the Deep Trench)
    T(id='p_loch', isle='loch', island=True, name='Monster Hunter', unlock=None, coins=180000,
      desc='Prove the legend is real: fish the loch end to end, then face the monster herself.',
      goals=[Goal('catch', 45, isle='loch'), Goal('species', 10, isle='loch'), Goal('boss', 1, sp='nessie')]),
    T(id='q_tartan', isle='loch', name='Ceilidh', rod='tartan', coins=90000,
      desc='Catch 12 different Loch Ness species.', goals=[Goal('species', 12, isle='loch')]),
    # Mariana Deep
    T(id='p_mariana', isle='mariana', island=True, name='The Deepest Place', unlock='atlantis', coins=2000000,
      desc='Fish the whole eleven kilometres and become a legend of the bay.',
      goals=[Goal('catch', 80, isle='mariana'), Goal('species', 14, isle='mariana'), Goal('catch', 1, isle='mariana', tier=5)]),
    T(id='q_deep', isle='mariana', name='Pressure Point', rod='challengerrod', coins=800000,
      desc='Catch 16 different Mariana Deep species.', goals=[Goal('species', 16, isle='mariana')]),
    T(id='q_bloop', isle='mariana', name='Heard It Too', rod='sounding', coins=1200000,
      desc='Defeat the Bloop.', goals=[Goal('boss', 1, sp='bloop')]),
    # Atlantis
    T(id='p_atlantis', isle='atlantis', island=True, name='The Last Keeper', unlock=None, coins=4000000,
      desc='Catch 90 fish in the drowned city, find 16 species, and land one Mythic.',
      goals=[Goal('catch', 90, isle='atlantis'), Goal('species', 16, isle='atlantis'), Goal('catch', 1, isle='atlantis', tier=5)]),
    T(id='q_marble', isle='atlantis', name='Cartographer of the Drowned City', rod='marblerod', coins=1600000,
      desc='Chart 18 different species in Atlantis.', goals=[Goal('species', 18, isle='atlantis')]),
    T(id='q_kraken', isle='atlantis', name='Squid Pro Quo', rod='inkwellrod', coins=2400000,
      desc='Defeat the Kraken.', goals=[Goal('boss', 1, sp='kraken')]),
    T(id='q_trident', isle='atlantis', name='The Broken Trident', hidden=True, coins=0, rewardMat='trident',
      desc='Find three lost shards: the Coral Wyrm, Salmon King, and Glacier Koi.',
      goals=[Goal('catch', 1, sp='coralwyrm'), Goal('catch', 1, sp='salmonking'), Goal('catch', 1, sp='glacierkoi')]),
    # Red Hollow, reached through Poseidon's statue rather than the sea chart
    T(id='p_hollow', isle='redhollow', island=True, hidden=True, name='The Fractured Bay', unlock=None, coins=1200000,
      desc='Catch the three fragments and defeat the Watcher Below.',
      goals=[Goal('catch', 1, sp='redfinfragment'), Goal('catch', 1, sp='glassminnow'), Goal('catch', 1, sp='moonshardray'),
             Goal('boss', 1, sp='watcherbelow')]),
    T(id='q_hollow', isle='redhollow', hidden=True, name='A Rod for the End', rod='eclipse', coins=0,
      desc='Discover every fish in the fractured bay.', goals=[Goal('species', 4, isle='redhollow')]),
]
QI = {q.id: q for q in QUESTS}
ISLAND_QUEST = {q.isle: q for q in QUESTS if q.island}
QUEST_VERSION = 2

# ---------------- Pets and eggs (the hatchery opens once you reach the Coral Reef) ----------------
# Pets ride in a little boat behind yours and grow (levels 1-10) while you play with them aboard.
PETS = [
    T(id='gull', name='Gully', kind='Seagull', r='common', col='#f2f4f6',
      desc='Circles over your line and squawks at fish. They notice your hook sooner.'),
    T(id='otter', name='Pebble', kind='Sea Otter', r='uncommon', col='#8a5a3a',
      desc='Holds the line with its little paws. Line tension builds slower.'),
    T(id='parrot', name='Captain Polly', kind='Parrot', r='rare', col='#2fbf4a',
      desc='Spots rare fish from the mast and yells about it. More luck.'),
    T(id='pup', name='Biscuit', kind='Puppy', r='epic', col='#d9a25a',
      desc='Helps pull the line: your hook moves faster. Fully grown, rare fish love your bait and small fry stay away.'),
    T(id='kitten', name='Mittens', kind='Kitten', r='legendary', col='#f2ede4',
      desc='Fishes with a tiny rod of her own. Small fish at first; fully grown she lands Rare, Epic and even Legendary fish.'),
]
PET = {p.id: p for p in PETS}
# minutes of play with the pet aboard to reach each level (level 1 at 0 minutes)
PET_LEVEL_MIN = [0, 6, 15, 27, 43, 63, 88, 118, 154, 196]
PET_MAX = len(PET_LEVEL_MIN)
# the kitten: (seconds between catches, {rarity tier: chance}) for each level
KITTEN = [
    (30, {0: 70, 1: 30}), (30, {0: 60, 1: 40}), (33, {0: 45, 1: 45, 2: 10}), (36, {0: 30, 1: 50, 2: 20}),
    (40, {1: 60, 2: 40}), (44, {1: 40, 2: 50, 3: 10}), (48, {2: 70, 3: 30}), (52, {2: 65, 3: 33, 4: 2}),
    (56, {2: 62, 3: 32, 4: 6}), (60, {2: 60, 3: 30, 4: 10}),
]
EGGS = [
    T(id='reef_egg', name='Reef Egg', price=5000, at='reef', col='#7fe0d0', spot='#ff9ec7',
      odds={'gull': 52, 'otter': 30, 'parrot': 12, 'pup': 5, 'kitten': 1}, desc='Warm and wobbly. Usually something small.'),
    T(id='ember_egg', name='Ember Egg', price=40000, at='volcano', col='#ff8a3a', spot='#ffd23d',
      odds={'gull': 20, 'otter': 30, 'parrot': 30, 'pup': 15, 'kitten': 5}, desc='Hot to the touch. Better pets inside.'),
    T(id='abyss_egg', name='Abyss Egg', price=160000, at='trench', col='#3a4aa0', spot='#7ffcff',
      odds={'otter': 15, 'parrot': 35, 'pup': 32, 'kitten': 18}, desc='Glows in the dark. The best pets hatch from these.'),
]
EGG = {e.id: e for e in EGGS}
PET_DUPE_MIN = 20       # a duplicate pet becomes this many minutes of growth for the one you have


def slice_amount(tier, base=0.30):
    """Slice: +30% at Common, 3% less for each rarity tier above it."""
    return max(0.05, base - 0.03 * tier)
