# Credits

Almost everything in Shards of Ashen is made for it: the art and most sounds are drawn and synthesised in code by
`dev/migrate/build_*.py`, and the place music is composed by `dev/migrate/build_music.py`.

These come from elsewhere, all under CC0 (public domain: free to use, credit not required, given anyway with thanks):

| File | What it is | Source | Author | Licence |
|---|---|---|---|---|
| `sounds/TownTheme.ogg` | the music outside | [Town Theme RPG](https://opengameart.org/content/town-theme-rpg) | cynicmusic (cynicmusic.com, pixelsphere.org) | CC0 |
| `sounds/Miss.wav` | a blow that misses (`cloth4`) | [RPG Audio](https://kenney.nl/assets/rpg-audio) | Kenney (kenney.nl) | CC0 |
| `sounds/Teleporter.wav` | teleporting | [Teleport Spell](https://opengameart.org/content/teleport-spell) | Ogrebane | CC0 |
| `sounds/Boat.wav` | sailing (`wave_02`, faded out) | [Water Waves](https://opengameart.org/content/water-waves) | transitking (freesound.org) | CC0 |
| `sounds/Pickup.wav` | picking something up (`handleSmallLeather`) | [RPG Audio](https://kenney.nl/assets/rpg-audio) | Kenney (kenney.nl) | CC0 |
| `sounds/EatFood.wav` | eating (crunches 1, 3 and 5) | [7 Eating Crunches](https://opengameart.org/content/7-eating-crunches) | StarNinjas | CC0 |
| `sounds/CookingFood.wav` | cooking (the first 4 s, faded) | [boiling water loops](https://opengameart.org/node/12411) | TinyWorlds | CC0 |
| `sounds/DigHole.wav` | digging | [Digging Underground](https://opengameart.org/node/138434) | Almitory | CC0 (one of its licences) |
| `sounds/FillBucket.wav` | filling a bucket (`loop_water_01`, faded) | [40 CC0 water / splash / slime SFX](https://opengameart.org/content/40-cc0-water-splash-slime-sfx) | rubberduck | CC0 |
| `sounds/EmptyBucket.wav` | emptying a bucket (`splash_01`) | [40 CC0 water / splash / slime SFX](https://opengameart.org/content/40-cc0-water-splash-slime-sfx) | rubberduck | CC0 |
| `sounds/MakeFire.wav` | lighting a fire | [Fire Crackling](https://opengameart.org/content/fire-crackling) | AntumDeluge | CC0 |
| `sounds/PutFireOut.wav` | putting a fire out (`Marker #1`, faded) | [Steam release sounds](https://opengameart.org/content/steam-release-sounds) | bart | CC0 |
| `sounds/StrikeFlint.wav` | striking a flint | [Flare ignition](https://opengameart.org/content/flare-ignition) | qubodup | CC0 |
| `sounds/Voice_Man`, `Voice_Old_Man*.wav` | a man's murmur, and an old man's (syllables) | [15 seconds of "blah blah blah"](https://freesound.org/s/165539/) | unfa (freesound.org) | CC0 |
| `sounds/Voice_Deep*.wav` | a deep voice's murmur | [Indistinct deep male mumble](https://freesound.org/s/536967/) | dynamique (freesound.org) | CC0 |
| `sounds/Voice_Woman`, `Voice_Old_Woman*.wav` | a woman's murmur, and an old woman's | [Female Gibberish](https://freesound.org/s/800349/) | cloyen (freesound.org) | CC0 |
| `sounds/Voice_Gruff*.wav` | a gruff murmur | [Human_Male_Crazy Mumbles_1](https://freesound.org/s/389642/) | SilentStrikeZ (freesound.org) | CC0 |
| `sounds/Voice_Ghost*.wav` | a ghost's whisper (with an echo) | [indistinctwhispering](https://freesound.org/s/377743/) | BlueSiren (freesound.org) | CC0 |
| `sounds/Voice_Croak`, `Voice_Beast*.wav` | the Frog King's croak and the dragon's rumble (slowed) | [Monster or Creature Mutterings and Gibberish](https://freesound.org/s/677407/) | SnowFightStudios (freesound.org) | CC0 |

Each was made mono 22050 Hz and its loudness matched to the game's own sounds. The voices are syllables cut from
the recordings by `dev/migrate/build_voices.py`, which fetches them the first time.

The server and the Android app run on open-source software: Python (PSF licence), aiohttp (Apache 2.0) and
Chaquopy (MIT).
