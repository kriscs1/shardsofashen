# Dragon Sword v2: data formats and conventions

This is the contract shared by the game (the browser game: the server in `server\` and `dsengine\`, the client in
`web\`; see README-Server.md), the editor (the Python package `dsedit\`, started by `Dragon Sword Editor.py`: maps,
scripts, tiles, entities, item racks, spells, quests, buildables, crops and minimaps in one window) and the builders in
`dev\migrate`. If you change a format, update this file. (The game and the editor were Liberty BASIC,
`Dragon Sword.bas` and `Dragon Sword Editor.bas`, until they were ported to Python in October 2026. The desktop
Python game, `Dragon Sword.py`, was retired for the browser game; `dragonsword\` keeps only the helpers they share.)

All paths are relative to `DefaultDir$` (the `New (converted)` folder).

## Language and checking

* The game: Python 3 with aiohttp (the server), and pygame and numpy to make its pictures (tools\export_web_assets.py). The editor: Liberty BASIC 4.04
  (`C:\Program Files (x86)\Liberty BASIC v4.04\liberty.exe`).
  The command line can't syntax-check, so run `python dev\lblint.py <file.bas> --locals`
  after every edit. It reports unbalanced blocks, bad goto/gosub targets, unknown
  subs, wrong argument counts and sub-local variables that are never set.
* Liberty BASIC gotchas: no `else if` (nest instead); there's no include, so each
  program is one file; variables inside a sub/function are local unless declared
  `global`; arrays are always global; a sub can't `goto` a label outside itself;
  `dim` of an existing array clears it; `word$(s$, n, delim$)`; and string
  comparisons are case-sensitive.

## Folder layout

| Folder / file | Purpose |
|---|---|
| `data\Config.ini` | Engine settings (see below) |
| `data\Tiles.ini` | One section per tile sprite name |
| `data\Entities.ini` | One section per entity (item/NPC/object) sprite name |
| `data\ItemRacks.ini` | Shops, crafting lists |
| `data\DayNight.ini` | The sky through the day, night, the times' names, sleeping |
| `data\Weather.ini` | The kinds of weather and where they come |
| `data\Scripts\*.txt` | Scripts (see Scripts) |
| `maps\X,Y,Z.txt` | One file per screen |
| `maps\Test\` | The test maps that were in `maps\` before the old world was converted |
| `saves\<PlayerName>.ini` | Player save games |
| `saves\TEMPLATE.ini` | New-player defaults |
| `sounds\*.wav`, `sounds\*.mid` | Sound effects / music |
| `sprites\Tiles`, `sprites\Entities`, `sprites\Interface` | PNG sprites, one file each: the picture with transparency where it is see-through (the interface panels ChatBar, InfoBox, ResponseBox, SideBarBorder and StatBox, and `sprites\Textures`, are plain pictures). Old Liberty BASIC BMPs (twice as high: the top half the mask, black = drawn, white = see-through, the bottom half the picture) still load if there is no PNG of that name; the BMPs the game used to have are in `dev\Archive\BMP sprites.zip`. The builders in dev\migrate work on that two-half layout in memory (common.py `read_bmp` / `write_sprite`) and write PNGs. |
| `sprites\Effects` | Combat and spell effects, made by `dev\migrate\build_effects.py` and loaded the first time each is needed: `Hit<N>`, `Crit<N>`, `Heal<N>` (N = 1..99) and `Miss` splats; four-frame animations `<Name>1..4` (Puff, Slash, Fire_Burst, Ice_Burst, Spark, Heal_Glow, Stone_Glow, Teleport_Glow); missiles; `Hurt_Top/Bottom/Left/Right` (the hurt flash, as wide/high as the map). The combat sounds in `sounds\` are made by `dev\migrate\build_sounds.py`. |
| `sprites\Worn` | What the player wears, drawn over them: `Worn_<Item><Dir><Frame>.png` (the 12 player frames) for every item with a Slot except rings, made by `dev\migrate\build_worn.py` from the player's body (re-run it after adding equipment; the look comes from the item's name: material + kind). Loaded the first time an item is worn; an item without frames just isn't shown. |
| `sprites\Walk` | NPC walking frames, made from the sprites\Entities sprite by `dev\migrate\build_walk.py` (re-run it after changing an NPC sprite). `<Name><Dir><Frame>.png`: Dir 1 = north, 2 = east, 4 = south, 8 = west; Frame a = standing, b/c = steps. All 12 = the NPC faces all four ways; only 2a-2c and 8a-8c = side-on (animals face east or west). Loaded by the game the first time that NPC is shown; an NPC without frames keeps its single sprite. |
| `dev\` | Tool files: `Log.txt` (game log; NOT `Debug\Log.txt`), `Minimap Colours.txt`, `Open Script.txt`, `Undo List.txt`, `Redo List.txt`, `sprites\` (editor-only sprites), `lblint.py` |

## Names

* Every sprite, tile and entity name uses `_` for spaces (e.g. `Gold_Coin(s)`, `Cooked_Meat`,
  `Pine_Tree001`). The game shows `_` as a space.
* Tile names end in a 3-digit variant number (`Grass001`). Entity names don't.
* Old → new renames: `GoldCoin(s)`→`Gold_Coin(s)`, `TinderBox`→`Tinderbox`, `BucketOfWater`→`Bucket_of_Water`,
  `RawChicken`→`Raw_Chicken`, `CookedMeat`→`Cooked_Meat`, `MeatSandwich`→`Meat_Sandwich`, `PineTree001`→`Pine_Tree001`,
  `TreeStump001`→`Tree_Stump001`, `PlaceHolder`→`Placeholder`, `EmptyVial`→`Empty_Vial`, `KingTyron`→`King_Tyron`, etc.
  The sprites in `sprites\` are the source of truth for names.

## data\Config.ini

```
[Debugging]   Logging.Enabled=1
[Gameplay]    Player.Movement.Speed, Player.Attack.Speed, Player.Visible,
              Hitpoints.Base, Hitpoints.Per.Level (max HP = base + per level x (Strength + Defence levels)),
              HP.Regen.Delay (seconds out of combat before HP comes back, default 6), HP.Regen.Every (seconds per HP, 3),
              Skill.Max.Level (the highest level of every skill, default 50: XP stops there),
              NPC.Respawn.Delay, Item.Respawn.Delay (map items respawn after pickup),
              Item.Despawn.Delay (dropped items vanish, default 180), Maximum.Bank.Slots,
              FogOfWar.Enabled, FogOfWar.Viewable.Distance,
              Start.Map=1,1,0   Start.X=300   Start.Y=300
[Interface]   Map.X.Tiles=25  Map.Y.Tiles=21
              Python game: FogOfWar.Cell.Size=16 (fog cell in pixels; should divide 800 and 672),
              FogOfWar.Smooth=1 (soft fog edges), FogOfWar.Seen.Darkness=130 (0-255),
              Widescreen=1 (the playfield widens to fill a widescreen display; 0 = 1024 x 768),
              Zoom=1 (0.75/1/1.5/2/3, set by the mouse wheel and + / -), Camera.Smooth=8 (0 = no easing), Smooth.Scaling=1 (0 = sharp pixels)
              [Gameplay] Night.Light.Radius=130 (Python game: light round the player at night, 0 = none)
              InventoryItems.Columns=5  InventoryItems.Rows=7  ActionBox.Columns=11  ActionBox.Rows=3
[Skills]      List=Strength,Defence,Hitpoints,Cooking,Smithing,Fishing,Mining,Woodcutting,Firemaking,Herblore,Crafting,Magic
              Icon.<Skill>=<sprite> ; the picture on the skill's tile in the Stats tab, e.g. Icon.Mining=Pickaxe
                                    ; (also shown over the player's head for a moment when the skill gains XP)
              Disabled=Name,Name  ; skills switched off: no Stats tile, no XP (Hitpoints can't be). Set by the Admin panel
              Level.Skills=Strength,Defence,Magic  Level.Best=2 (the player's level: the average of their
              best Level.Best of these; quests' Requires.Level, shown on the Quests tab)
[Admin]       Players=Admin       ; the characters (comma list, any case) with an Admin button on the sidebar: give
                                  ; yourself items, set skill levels, switch skills off. Everyone else: no button
              GodMode=0           ; 1 = nothing can hurt those characters (the panel's God mode tick box sets it)
[Sounds]      Enabled=1  Music=FinalFantasy.mid (the music everywhere outside)  Music.By.Place=0 (1: each map's
              theme from data\Music.ini instead)
              Volume=100  Music.Volume=80  Ambient.Volume=70 (the Options sliders; background sounds play at a quarter
              of Volume x Ambient.Volume)  Music.On=1  Ambient=1
[Animation]   Water.Frames=6  Water.Speed=260  Flame.Frames=4  Flame.Speed=140  Sway.Frames=6  Sway.Speed=230
              (frames and ms a frame of the foam, the flames' flicker and plants' sway: Tiles.ini Water, Flame, Sway)
              Foam.Colour=234 244 250
[Minimap]     Pixel.Size=n        ; pixels per tile in Minimap<Z>.png (written by MiniMap Creator)
              Origin.<Z>=X,Y      ; map X,Y at the top-left of Minimap<Z>.png, e.g. Origin.0=0,0
```
`sprites\Interface\Minimap<Z>.png` is generated by dev\migrate\build_minimaps.py: one per level, see-through where there is no map.
The game must read `Map.X.Tiles`/`Map.Y.Tiles` (the old `Screen.X.Tiles` key name is wrong).

## data\Tiles.ini

```
[TileName]
Walkable.Data=<Res*Res chars of 1/0, row-major from top-left; Res=7 so 49 chars>
Show.Name=0|1          ; show the name on mouseover
Use.Words=Chop,Examine ; comma list of right-click verbs; the first is the default left-click action
Examine.Info=text
Line.of.Sight=0|1      ; 0 blocks line of sight
Walk.Speed=0.8         ; x the normal walking speed on this tile (0.2 to 3): roads 1.2, sand 0.8, rubble 0.7
Blend=6                ; edge blending: grass 6, snow 5, cave floor and walls 4, sand 3, dirt paths 2, open water 1
                       ; (0 or none = never blends)
Blend.Texture=Grass001 ; the picture drawn over a lower neighbour's edge (default: the tile itself)
Unlocked.Tile=City_Gate002 ; Python game: where a map's Lock line is on this tile, drawn instead while the lock is
                       ; open (a gate drawn open); the map's own tile again if it locks
Open.Tile=Door_Open001  ; a door: drawn instead while the player or an NPC is at it (it swings open as they come
                       ; and shuts 1.5 s after they've gone; not while a Lock holds it shut)
Layer=Decor            ; a decor tile: see-through, drawn over a cell's ground tile (+Decor(Name) on the map), so
                       ; one chair, tree or pot of flowers goes on any floor (blank = a ground tile)
Sway=1.6               ; a plant: how many pixels its top sways in the wind (blank = it doesn't)
Sway.Ground=Grass001   ; a swaying GROUND tile: the ground it's drawn on, so the plant's pixels can be told from it
                       ; (default its Blend.Texture). Decor doesn't need it: its plant is what isn't see-through
Flame=1                ; its bright fire-coloured pixels flicker (torches, fireplaces, lanterns)
Water=1                ; water: foam laps wherever land meets it (land beside it, a rock or sand in it)
Anim.Frames=4          ; drawn from its own pictures <Name>1..<Name>4 in sprites\Tiles in turn, each cell a little
Anim.Speed=200         ; out of step with the next; ms a picture (default 200). The pictures aren't tiles of their own
Door=1                 ; a door: townsfolk go home through it at night (Gate: a gateway nobody lives behind);
                       ; either way a doorway, so standing in it under a roof's edge you see inside
Glow.Colour=255 160 70 ; for the editor's "Split props off their floors": drawn with the floor lit this colour round
Glow.Match=4           ; it, kept as see-through light (Match: how near, a few if exact)
Light=72               ; how far (pixels) it lights the dark at night: on a ground tile, a decor or a roof
                       ; (torches 72, lamp posts 96, lit windows 34, upper windows in roofs 30)
Overhead=1             ; drawn over people as well as under them: a gatehouse's arch you walk through
Seat=S                 ; a bench or chair: Sit on it (give it Use.Words=Sit), facing N, E, S or W, till you move
Piece=corner: top left ; which piece of a set it is (a roof's "ridge, west end", a fence's "a T: east, south and
                       ; west"): the editor's Maps palette says it, with the set from data\TileSets.ini
```
Nothing in the game knows a tile by its name: what sways, flickers, foams and lights is these keys. How many frames the
sway, flicker and foam have and how fast they go is data\Config.ini [Animation].
A decor tile's Walkable.Data and Line.of.Sight add to the ground tile's (a spot is walkable only if both let you; either
can block the view); its Walk.Speed, if it has one, is used instead of the ground's. The mouse names the decor, not the
floor under it, so its Use.Words, Examine.Info and `<Verb> <Name>` scripts are the ones used. A decor flickers if its
name is a flame's (Wall_Torch...) and sways if it has Sway. Blend, Blend.Texture and Texture belong to ground tiles.
The editor's Tiles ▸ "Split props off their floors…" (dsedit\decor.py) turns tiles drawn on a floor into decor tiles and
changes the maps to match, keeping the old files in `dev\Archive\Decor split <date time>\`.
It records what each tile became in `dev\migrate\decor_map.json` ({tile: [floor, decor]}): the builders (common.py)
read the old opaque pictures from that archive, never overwrite a decor sprite, and write Floor+Decor(Name) on the
maps they make.
Where two tiles with Blend meet, the higher one's Blend.Texture is drawn a few wavy pixels over the lower one's edge
(and round its corners) through the masks in sprites\Interface\Blend_*.png; it works across map seams too.
dev\migrate\build_content.py sets both keys from the colours round each tile's edge (flowers, boulders, bushes...
on grass count as grass), and dev\migrate\build_tiles.py makes the masks.
Defaults: all walkable, Show.Name=0, Line.of.Sight=1, Walk.Speed=1.
Rugs are decor: `Rug001-009` (a 3 x 3 rug of any size: its corners, edges and middle) and `Rug011-017` (a runner one
tile wide, east-west 011-013 or north-south 014-016, and a mat on its own, 017), and the same 16 pieces of a second,
blue rug, `Woven_Rug`. The rugs once drawn on stone tiles (Rug031-047) are Tile001+Decor(Rug001-017) now.
Potted plants are five different plants, `Potted_Plant001-005` (leafy, fern, flowering bush, lemon tree, aloe);
the builders put one of them wherever they furnish a room with a pot (common.decor_variant). Drawn by
dev\migrate\decor_sets.py; dev\migrate\migrate_rugs_pots.py moved the maps over (once).
On walls, decor too (dev\migrate\migrate_wall_decor.py, once): windows `<Base>_Window001-005` (each wall's own style
of frame and shutters, but any of them goes on any wall), ivy `Ivy001-003` (its hanging signs are gone: shops have
signboards on posts, remove_wall_signs.py); and
`Bookshelf001` (on any floor or against any thin wall: the Bookshelf101/201 and Bookshelf_<Wall>_Thin_... copies are
gone, like the beds against walls), ladders `Ladder001` (up), `002` (a hatch down), `003`, `006` (a hole in the
ground), `008` (up to the loft), `009` (a trapdoor). A bank's column or plaque over a window or sign replaces it
(build_cinder.dress_banks).

### data\TileSets.ini: tiles that go together
```ini
[Wood_Fence]
Title=wood fence       ; what the set is
Columns=4              ; how many tiles across it's laid out
Tiles=Wood_Fence003,Wood_Fence007,Wood_Fence001,Wood_Fence004,...   ; row by row as they fit together; a blank
                       ; between commas is a gap, and a tile can be in it more than once (a fence's middle)
```
Roofs (`<Material>_Roof`, `_Roof_Chimney`, `_Roof_Dormer`), the thin walls round a room (`<Wall>_Thin_<Floor>`, the
floor in the middle), rugs, fences and potted plants. Pointing at a tile in the editor's Maps palette shows its set
laid out with that piece marked, and its Tiles.ini `Piece=`. Only the editor reads it (and validate.py checks every tile
in it has a sprite). Made by dev\migrate\decor_sets.py; your changes are kept.

The ground is painted solid, so a tile with see-through parts (Pine_Tree002) only works as an overlay
(`Grass001+Infront(Pine_Tree002)` or `Plank001+Decor(Chair001)`), never as a cell's own tile: dev\migrate\validate.py
reports it.

## data\Entities.ini

```
[EntityName]
Type=MapItem|StaticObject|NPC      ; what the Map Editor places it as by default
Attitude=Good|Bad         ; NPC only: what a new one is on a map. Good = friendly (Talk to; flees when hit),
                          ; Bad = a foe (Attack; chases and attacks on sight if Aggressive=1). Each map line says
                          ; its own (Attitude= in its Options), and scripts can change it (Set.NPC.Attitude)
Use.Words=Eat,Examine     ; comma list; first is the default left-click action
Examine.Info=text
Stackable=1               ; max quantity per inventory slot (1 = not stackable)
Droppable=1               ; 0 = can't be dropped
Value=5                   ; shop price in Gold_Coin(s)
Food.Value=2              ; hitpoints healed when eaten (0 = not food)
; NPC only:
Hitpoints=10  Attack.Speed=1  Strength=1  Defence=1  Aggro.Range=70
Weapon.Range=0  Movement.Speed=2  Aggressive=1  Respawn=10
Drops=Bones,1-1,100 Gold_Coin(s),1-2,50       ; space-separated Item,min-max,percent
Roam.Radius=3              ; tiles it wanders from its spawn (0 = stands still) unless the map line gives a Zone
Chase.Radius=4             ; tiles beyond its Zone it will follow the player
Walk.Speed=0.5             ; speed when roaming/patrolling/returning, as a fraction of Movement.Speed (chasing = full speed)
Pause=1-4                  ; seconds it stands still between moves when roaming
Solid=0                    ; optional: nothing bumps into it and it bumps into nothing (default 1)
States=Sit                 ; optional: how it may rest when it stops a while (sprites <Name>_Sit2 / _Sit8); a map
                           ; line's State=Sit makes it always rest so
Fidgets=Stretch,Butt       ; optional: now and then, at rest, one of these for a moment (<Name>_Stretch2 / 8...)
Hunts=Rabbit,Sheep         ; optional: NPCs it goes for when it sees one (within its Aggro.Range, or 128, and its
                           ; chase area). They run if they Flee (Flees=1), else fight back; a kill leaves no loot.
                           ; Hunts=Foes (guards): any monster that attacks on sight, even one fighting you
; StaticObject only:
Walkable.Data=111...000    ; optional: its footprint, 0 = can't be walked through, over its sprite at 7 cells to 32
                           ; pixels each way (a 32 x 32 object: 49 cells, like a tile's; 64 x 32: 14 x 7). Blank =
                           ; you walk through it. It goes on the walk grid wherever the object is (pathfinding too)
Anim.Frames=4  Anim.Speed=200   ; it animates where it stands: sprites <Name>1..4, ms a frame
; Anything:
Light=84                   ; optional: how far (pixels) it lights the dark at night (a fire, a range)
Layer=Under|Over           ; optional: Under = drawn under the player (a rabbit you step over);
                           ; Over = it flies (drawn over everyone, the tiles' Walk.Speed doesn't slow it)
; Equipment only:
Slot=Weapon                ; Weapon | Shield | Head | Body | Legs | Feet | Hands | Ring  (8 slots)
Attack=4                   ; bonus to hit chance and damage while worn
Defence=2                  ; bonus to defence while worn
Magic=4                    ; optional (staffs): added to every spell's damage and healing while worn
Requires=Strength 5        ; optional: skill and level needed to equip (space separated pairs, e.g. "Defence 10 Strength 5")
; Spell scrolls only:
Spell=Fire_Bolt            ; the data\Spells.ini section it casts (give it Use.Words=Cast); reading it uses it up
```
Equippable items get the right-click verbs `Wield` (Weapon, Shield) or `Wear` (others) automatically; equipped items
are shown in the Equipment panel and can be removed from there. NPCs use their own Strength/Defence only.

## data\ItemRacks.ini

```
[SHOP-General]            ; a shop; Display.Item.Rack <type> <npc> <rackName>
Type=Shop
Buy.Rate=1.2              ; player pays Value*Buy.Rate
Sell.Rate=0.8             ; player receives Value*Sell.Rate
Item1=Tinderbox,3         ; Name,stock (bought stock comes back after Config [Gameplay] Shop.Restock.Seconds,
                          ; up to 4x longer for dear items; "+" = never runs out)
Item2=Bucket,2
[CRAFT-Cooking]
Type=Craft
Skill=Cooking
Item1=Meat_Sandwich,Cooked_Meat 1 Bread 1,5      ; Product,ingredients (name qty pairs),xp gained
Item2=Arrows,Logs 1 Bronze_Bar 1,0.2,3,25        ; ...,level needed,how many one making gives (default 1)
```
The bank is not a rack: it's stored in the save file.

## maps\X,Y,Z.txt

* X = east (+), Y = south (+), Z = level (0 ground, -1 underground, +1 upstairs).
* The first `Map.Y.Tiles` (21) lines are tile rows, each with `Map.X.Tiles` (25) tile cells separated by `:`.
* A cell is `TileName` optionally followed by overlays, each `+Kind(Arg)`:
  * `+Decor(TileName)`: a see-through decor tile (Tiles.ini Layer=Decor) drawn over the cell's tile, as part of the
    ground (under entities): a chair, a tree, flowers. Written first. Example: `Plank001+Decor(Chair001)`.
    A script's `Change.Tile` with a decor tile changes only the decor (`Tree_Stump001`: the tree goes, the grass
    stays); with a ground tile the cell becomes just that tile (the decor goes); `Grass001+Decor(Oak_Tree001)` sets
    both. Changing back puts back the tile and the decor it had.
  * `+Roof(RoofName.Group)`: a roof tile drawn over the cell. Group is a number. All roofs in the
    same group hide when the player stands under any of them. Example: `Brick001+Roof(Roof001.01)`.
  * `+Infront(TileName)`: a tile drawn over entities (e.g. tree tops).
* After the tile rows, one entity per line, tab-separated:
  * `MapItem<TAB>Name<TAB>X<TAB>Y<TAB>Quantity[<TAB>Options]`: X/Y are pixel coordinates. Options: `Id=<name>` (below).
    `Once=1`: a one-time item: picked up, it never comes back (no respawn; the save remembers it in `[Taken.Once]`
    by its Id, or map@x,y). Entities.ini `Once=1` makes every placed one of that item one-time. You must have room for
    all of it to pick it up.
  * `StaticObject<TAB>Name<TAB>X<TAB>Y[<TAB>Options]`: Options as an NPC's (Key=Value words). Name can be a decor tile
    (Tiles.ini Layer=Decor, with no entity of that name): placed anywhere and drawn in front of or behind the player
    like any object, with its tile's picture, verbs, examine text, footprint (Walkable.Data), Light, sway and flicker.
  * **Ids**: any NPC, MapItem or StaticObject line may have `Id=<name>` in its Options: it names that one thing in
    the world (unique, and not a sprite's name: validate.py checks). Scripts named `<Verb> <Id>` are tried before
    `<Verb> <Name>` (e.g. `Pickup CellarKey.txt`, `Talk to OldHob.txt`, `Kill <Id>.txt`, `Use Key With <Id>.txt`). A
    picked-up item respawns with its Id. Add.Entity's misc can give one too (`3 Id=CellarKey`, `Id=Ferry_To_Southport`).
    Every notice has one, from its title (build_content.notice_ids): its text is `Read <Id>.txt` (e.g. `Read Ashford`).
  * `NPC<TAB>Name<TAB>X<TAB>Y<TAB>Options`: a person or a monster. Options are space-separated `Key=Value` pairs:
    * `Attitude=Good|Bad`: friendly or a foe (every NPC line has it; missing = its Entities.ini Attitude). The game
      treats a Bad NPC as the old BadNPC (Attack is its left click, it chases and attacks on sight if Aggressive, spells
      aim at it) and a Good one as the old GoodNPC (Talk to; it flees when hit).
    * `Id=<name>`: names this one NPC for scripts (unique in the world; validate.py checks). `Set.NPC.Attitude NPC ID |
      Good|Bad` changes one NPC for good: the one with that Id, or CLICKED (the NPC the player clicked to start the
      script: talked to, attacked, used an item on). Only that NPC changes, not others of its name; it stays changed
      when its map is loaded again or it respawns (in the save, [NPC.Attitudes], by its Id or else by map@x,y, its map
      line's place). Edit.Entity ATTITUDE changes one NPC until its map is loaded again. An NPC a script turns Bad
      also becomes Aggressive (it turns on you).
    * The old `GoodNPC` / `BadNPC` lines still load, as an NPC with Attitude=Good / Bad (build_world.py converts them,
      the Map Editor saves them as NPC lines, validate.py warns about them).
    The other Options control how the NPC moves; tile coordinates are 1-based:
    * `Zone=x1,y1,x2,y2`: the rectangle of tiles it roams in. Default: Entities.ini `Roam.Radius` tiles around its spawn tile.
    * `Chase=x1,y1,x2,y2`: the rectangle it may follow the player in. Default: the Zone grown by `Chase.Radius` tiles
      on every side. When the player leaves it (or gets out of sight range), the NPC gives up, walks back and carries on
      with what it was doing (roaming, or its patrol from the waypoint it was heading to).
    * `Patrol=x,y/x,y/x,y`: tile waypoints walked in order, then back to the first (a loop). The NPC patrols instead of
      roaming. `PatrolMode=PingPong` walks the route forwards then backwards instead.
    * `Pause=min-max`: seconds it stands still at each roam point or waypoint (default: Entities.ini `Pause`).
    * `Stand=1`: it stays where it is (shopkeepers, guards on a post); it still turns to face a nearby player.
    Anything that isn't `Key=Value` (old stray fields) is ignored. Tools must keep the field when re-saving.
    Zone, Chase and Patrol tiles may reach past the map's edges onto the maps around it, up to one map's width or height
    (x from -24 to 50, y from -20 to 42 on a 25 x 21 map): 26,5 is tile 1,5 of the map to the east, 0,5 tile 25,5 of the
    map to the west. The NPC still belongs to this map: it loads and unloads with it (the game keeps the 9 maps round the
    player live), and respawns here.
  * `Trigger<TAB>ScriptName<TAB>TileX<TAB>TileY`: TileX/TileY are 1-based **tile** coordinates. The
    script runs when the player walks onto that tile.
  * `Lock<TAB>TileX<TAB>TileY<TAB>Condition<TAB>Message`: the tile (1-based tile coords, usually a door) can't be
    walked onto, by the player or NPCs, and isn't used by pathfinding, until Condition is true. Message is shown when
    the player bumps into it or clicks it (default "It's locked."). An empty Condition means it is always locked.
    Conditions are re-checked whenever an attribute, the inventory, a skill or the equipment changes, and on map load.
    If the tile's Tiles.ini section has `Unlocked.Tile`, that tile is drawn there while the lock is open (on the maps
    round the current one too).
* Blank lines are ignored. Unknown entity types are logged and skipped.

### Conditions (Lock lines, and anywhere else a condition is written in data)

The same syntax as the script `>Conditional` command: `a=b`, `a<>b`, `a<b`, `a>b`, `a<=b`, `a>=b`, joined with
` and ` / ` or ` (numbers compare as numbers, anything else as case-insensitive text). Before evaluating, these are replaced:

| Variable | Value |
|---|---|
| `$Attr.<Name>` | the save attribute `<Name>` (e.g. `$Attr.BeggarQuest>=2`); unset = 0 |
| `$Item.<Name>` | how many `<Name>` the player has, carried plus equipped (e.g. `$Item.Key>=1`) |
| `$Skill.<Name>` | the player's level in that skill (e.g. `$Skill.Mining>=20`) |
| `$Equipped.<Slot>` | the item name in that equipment slot (Weapon, Shield, Head, Body, Legs, Feet, Hands, Ring), or `none` |
| all script variables | `$Player.X`, `$Map.Name`, ... (see Script Commands.txt) |

Example: `Lock	20	7	$Attr.BeggarQuest>=2 or $Item.Key>=1	The door is locked. Maybe the beggar knows where the key is.`

## Scripts (data\Scripts\*.txt)

* One command per line: `NN<TAB>Command<TAB>arg1<TAB>arg2...`, where NN is the 2-digit line number.
  Lines starting with `//` are comments.
* The command set and argument order are defined in `dragonsword/script_language.py` (COMMANDS, HELP, VARIABLES).
  That list is the language: the game, the editor and dev\migrate all read it. The game must implement every command
  in it, and the editor must not rename commands or reorder their arguments.
* Conditions start with `>`; their last argument is the line to jump to if the condition is NOT met.
* Variables in arguments: `$Player.X`, `$Player.Y`, `$Map.Name`, `$Cursor.X`, `$Cursor.Y`,
  `$Tile.under.Cursor.X`, `$Tile.under.Cursor.Y`, `$Entity.under.Cursor.ID`, `$Variable.1`..`$Variable.9`.
  `Variable.n$` (no `$` prefix) as an argument names the variable to store into.
* **Script lookup** when the player does `Verb` on an entity/tile `Name` of type `Type`:
  0. for something with an Id= on its map line: `Verb Id.txt` (e.g. `Read Ashford.txt`, `Pickup CellarKey.txt`)
  1. `Verb Name.txt` (e.g. `Chop Tree001.txt`, then without the digits, `Chop Tree.txt`)
  2. `Verb [Type].txt` (e.g. `Pickup [MapItem].txt`, `Drop [InventoryItem].txt`)
  3. the engine's built-in default for that verb (Pickup, Drop, Examine, Eat, Talk to, Attack, Walk here)
  * Using one item on another: `Use A With B.txt`, then `Use B With A.txt`.
  * Triggers: the script name stored in the map. Read map entity lines with `line input`,
    because script names can contain commas (e.g. map-entry scripts such as `1,1,0`).
  * Using one item on another also tries the names without their 3-digit variant (`Use Axe With Tree001` finds `Use Axe With Tree.txt`).
  * NPC death: `Kill <Name>.txt` (e.g. `Kill Hobgoblin.txt`) runs whenever that NPC is killed.
  * Skills: `<Skill> Skill.txt` (e.g. `Cooking Skill.txt`) runs when that skill is clicked in the stat box.
  * Map entry: `<MapName>.txt` (e.g. `1,1,0.txt`) runs each time that map is loaded, if it exists.
  * Variables are expanded in every argument, including script names in Goto.Script.
  * Item quantities may be a range `min-max` (random within the range).
  * Empty script files count as "not found".

## data\Gathering.ini (read by the in-game Help screen)

One section per kind of thing the player can gather. The actual gathering is done by scripts
(e.g. `Chop Tree.txt`); this file describes it so the Help screen can list it.

```
[Logs from trees]          ; section name = how the entry is titled in the Help screen
Gives=Logs                 ; item(s) received, space separated (sprite names)
Source=Tree001 Tree002     ; tiles or entities to use (sprite names)
Verb=Chop                  ; the right-click verb
Tool=Bronze_Axe/Axe/Steel_Axe/Mithril_Axe   ; item(s) needed in the inventory ("" = none). Space separated = all of them;
                           ; A/B/C = any one of them (weakest first: the Help screen shows the best one held)
Skill=Woodcutting          ; skill used ("" = none)
Level=1                    ; skill level needed (0 = none)
XP=0.25                    ; skill XP per success (shown only)
Where=Forests all over the island      ; a hint about where to find it
```

## data\Spells.ini

One section per spell; a scroll item (Entities.ini `Spell=<section>`, `Use.Words=Cast`) casts it. Left-click (Cast) a
scroll in the inventory to cast it at what you're fighting or the nearest monster in range; or Use it on a monster.
Reading a scroll uses it up, needs the Magic level and trains Magic. 1.5 seconds between spells.

```
[Fire_Bolt]
Scroll=Fire_Bolt_Scroll    ; the item that casts it
Effect=Bolt                ; Bolt (one foe) | Area (every foe within Radius) | Heal | Boost | Teleport (Shield = Boost)
Kind=Scroll                ; Scroll (read: needs the Skill level, 1.5s between them) | Potion (drunk: Use.Words=Drink)
Skill=Magic                ; the skill for Level and XP (potions: Herblore, with XP=0 - they train Herblore when brewed)
Leaves=Empty_Vial          ; optional: an item you get back (the vial)
Level=1                    ; Magic level needed
Damage=2-5                 ; Bolt, Area: min-max, + Magic level / 4 + the staff's Magic + a Magic Potion
Range=256                  ; Bolt: pixels
Radius=128                 ; Area: pixels around the player
Slow=50,8                  ; Bolt (optional): the target moves at 50% speed for 8 seconds
Heal=8-14                  ; Heal: min-max hitpoints, + Magic level / 3 + the staff's Magic (not for potions)
Attack=3  Defence=5  Magic=5 ; Boost: + Attack (to hit and max hit), Defence, Magic (spell damage) ...
Sight=150                  ; Boost: ... and/or + pixels you see through the fog of war (Owl Potion, Farsight) ...
Duration=60                ; ... for this many seconds (a new boost of the same kind replaces the old one)
Map=1,1,0  X=300  Y=300    ; Teleport: where to (Map empty = the start in Config.ini)
Missile=Fire_Bolt_Missile  ; Bolt (optional): a sprites\Effects sprite that flies to the target first
Impact=Fire_Burst          ; sprites\Effects\<Impact>1..4: played on the target (on the player for Heal/Shield/Teleport)
Sound=SpellFire            ; sounds\<Sound>.wav, played when it takes effect (SpellCast plays when the scroll is read)
XP=0.3                     ; Magic XP per cast
```
Generated by dev\migrate\build_content.py (SPELLS); the scrolls are written at the Wizard's (CRAFT-Scrolls, Magic).

## data\Quests.ini (read by the in-game Help screen)

```
[King's Hobgoblin Hunt]     ; quest title
Giver=King_Tyron            ; who gives it
Attribute=HobgoblinQuest    ; the save attribute that tracks progress (scripts set it with Update.Attribute)
Stage0=Speak to King Tyron in his keep south of Ashford.   ; shown when the attribute is 0 / unset ("" = hide the quest until it starts)
Stage1=Slay five hobgoblins in the old mine ($HobgoblinsSlain of 5).   ; $AttributeName is replaced with that attribute's value
Stage2=Return to King Tyron for your reward.
Done=3                      ; the attribute value that means finished (shown as Complete)
Type=Main                   ; part of the main story: first in the journal (a gold "Main story" badge, a diamond on
Chapter=2                   ; the Quests tab), in Chapter order. Blank or Side: a side quest
Requires.Level=12           ; before it can be started: the player's level (Config [Gameplay] Level.Skills, Level.Best:
Requires.Quests=Passage to the Mainland; Bog Lights    ; the average of their best two of Strength, Defence, Magic),
Requires.Skills=Woodcutting 10, Herblore 5             ; quests finished, skill levels
```
A quest that can't be started yet shows in the journal as Locked, with what it needs. Its giver's script asks
`>Quest.Can.Start <quest or attribute> <goto>` before offering it (the chat says what's missing); a script that sets a
quest's attribute from 0 while it still needs something is stopped there. dev\migrateuild_cinder.py (REQUIREMENTS)
sets these for every quest and puts the check in every giver's script.

## saves\<Name>.ini

```
[Player]       Name=Kris  Sprite=Player  Map=1,1,0  X=300  Y=300  Hitpoints=10  Direction=4
[Skills]       Strength=0  Cooking=33.34 ...    ; level units: level = int(value), fraction = progress to next level.
                                                ; Hitpoints= is the Hitpoints LEVEL (0 or missing = 10); the current
                                                ; hitpoints are [Player] Hitpoints
[Inventory]    Slot1=Axe,1  Slot2=Logs,5 ...
[Bank]         Slot1=Gold_Coin(s),1025 ...
[Equipment]    Weapon=Iron_Sword  Shield=Iron_Shield  Feet=Leather_Boots ...   ; empty slots are left out
[Attributes]   Door1Open=0 ...                  ; free-form script variables (Update.Attribute / Get.Value)
[NPC.Attitudes] OldHob=Good  1,4,0@256,448=Bad  ; Set.NPC.Attitude, one NPC each: <its Id, or map@x,y of its map line>=Good|Bad
[Quest.Notes]  Note1=The Withering Wood|0|Find the Heartwood...   ; the journal's quest notes (Quest.Note), in order:
                                                ; <quest title>|<1 = crossed out (Quest.Note.Done), 0 = not>|<text>
[Explored]     Grid=10x8  Maps=1,1,0 2,1,0 ...  ; a map in Maps= with no key of its own is fully revealed;
               3,2,0=1 2 3 ...                  ; otherwise the key lists revealed fog cells (row-major, 80 x 84 cells from the map's top left).
                                                ; No Grid = old 5x5 grid; a save from another grid (11x9 before v2.5) is converted
[Action.Queue] Total=n  Entry1=<queue entry, tabs written as [TAB]>
```

## Engine conventions

* Speeds (Player.Movement.Speed, NPC Movement.Speed) under 10 are tiles per second; 10 or more are pixels per second.
* Max hitpoints = Config [Gameplay] `Hitpoints.Base` (19) + `Hitpoints.Per.Level` (0.5) x (Strength
  level + Defence level); the Hitpoints skill isn't trained or used. In scripts and conditions the skill "Hitpoints"
  means the current HP (Update.Skill Hitpoints +10 heals 10).
* Combat. A blow lands with a 60% chance, +-4% per point of attack over defence (10% to 95%).
  * The player: attack = Strength + the Attack bonus of everything worn, against the NPC's Defence. Damage 1 to
    Player.Max.Hit = 1 + Strength/3 + Attack bonus; 5% + Strength/15% of hits are critical (max hit + up to half again).
    Each hit trains Strength (damage x 0.01); being hit trains Defence.
  * An NPC: attack = its Strength x 3 + 2, against a third of the Defence level + the armour's Defence (+ Stone Skin).
    Damage 1 to 1 + its Strength. A miss (or a blow armour turns) trains Defence 0.03, a hit damage x 0.01.
  * Attacked while standing about, the player fights back. Out of combat, hitpoints come back (HP.Regen.*).
  * Feedback (sprites\Effects): a number over whoever is hit (red, yellow for a critical hit, blue 0 for a miss or a
    blow the armour turned, green when healed), a sword slash on what the player hits, the attacker lunges and the
    target reels back, a red flash round the map when the player is hurt, a puff of smoke when something dies.
    Sounds: Fight1-3, Crit, Miss, Block, Hurt, Death.
* Queue entries are the Add.Action.To.Queue arguments joined by tabs plus a due time. Engine commands are
  ADD, REMOVE, CHANGE.TILE, SET.QUANTITY (what is left of a partly-picked-up map stack), ADD.SHOP.ITEM and REMOVE.SHOP.ITEM. Remove.Action.From.Queue removes every match; a trailing `*` is a wildcard.
* ItemRacks: optional `Specific=1` (the shop only buys listed items); craft rows may have a 4th field, the required level; stock `+` = unlimited.
* Built-in verbs: Walk here, Pickup, Drop, Drop 1, Examine, Eat, Use, Use X with Y, Talk to, Attack, Count, Climb Up (Z+1), Climb Down (Z-1), Bank.
* Optional config: `[Debugging] Debug=1` enables the debug hotkeys; `[Minimap] Blackout=1` hides unexplored maps.
* Clicking a skill in the stat box runs `<Skill> Skill.txt` if it exists.
* INI values can't have inline `;` comments (Windows doesn't strip them); put comments on their own line.
* Ladders: Ladder001/Ladder004/Ladder008 and Stairs001 = Climb Up (Z+1), Ladder002/005/006/007/009 and Stairs002 = Climb
  Down (Z-1), Ladder003 = both. A ladder's other end is at the same tile X,Y on the level above/below, on walkable
  floor. (Scripts: `Climb Up Stairs` / `Climb Down Stairs` for both stairs, `Climb Up Ladder008`, `Climb Down Ladder009`.)
* Crafting stations are StaticObjects whose Use script opens a CRAFT- rack: Range (CRAFT-Cooking), Furnace
  (CRAFT-Smelting: ore to bars), Anvil (CRAFT-Smithing: bars to tools and armour), Alchemy_Table (CRAFT-Herblore),
  Workbench (CRAFT-Crafting). Smelting and smithing both train Smithing. Mining and woodcutting scripts use the best
  pickaxe/axe carried (bronze, iron, steel, mithril): a better tool raises the chance, and mithril rock needs steel or better.
* People and goblins are drawn on the player's body by dev\migrate\build_people.py (the hand-drawn originals are in
  dev\Archive\Original NPC sprites); their walking frames come from it through build_walk.py.
* Scenery, landmarks, wildlife and the landmark chests are made by dev\migrate\build_scenery.py (part of build_content.py):
  the scatter of flowers, rocks, bushes, fallen logs and copses is a hash of map and cell, so it's the same every build;
  on the original Isle maps it's added as patches (recorded in content_patches.txt).
* The Wildlands (maps 0,5,0 to 5,10,0) are generated by dev\migrate\build_regions.py (called by build_content.py before
  the scenery pass) from one continuous world grid of noise-shaped lands, so their seams always match (build_world's
  edge check skips seams between them: SEAMLESS_MAPS). Towns, roads, quest sites, monsters, the Trader/Settler scripts
  (one script per name, a `>On.Map` branch per town) and the six quests are tables at the top of that file. The map
  rows use legend characters above ASCII (the printable ones are all taken).
  Its coast: a rounded outline pushed in and out by noise (land kept round towns and quest sites); sea cells in the
  corner of a step become diagonal shore pieces: Water002-009 on grass, Sand_Water002-009 and Snow_Water002-009 on
  sand and snow (made from the grass ones by dev\migrate
egion_tiles.py, with the same Walkable.Data).
* Quests.ini Marker<N>=<map> <tile x> <tile y>[;<map> <x> <y>...]: while the quest's attribute is N (in progress), a
  yellow cross on the minimap at each place (only for maps on the level you're on). Made by dev\migrate\build_travel.py.
* data\Ambient.ini [Maps] <map>=<name>: the background sound looped on that map, sounds\Ambient_<name>.wav (Forest,
  Waves, Wind, Marsh, Desert, Snow, Cave, Lair, Indoors: 10 s loops made by build_sounds.py). Made by build_travel.py.
* Config.ini settings changed in the game's Options screen (Esc, Options): [Sounds] Enabled, Volume (25-100, %),
  Music.On, Ambient; [Gameplay] DayNight, QuestMarkers, AutoSave.Minutes (0 = off). [Gameplay] Day.Minutes (default 24)
  is how long a whole day and night lasts.
* Villages (build_regions.py, build_eastreach.py, build_walled.py): laid out by `dev\migrate\villages.py`: a ragged
  clearing, a square, winding streets, 5-7 houses of different sizes and materials (walls Brick001, Stone_Wall001,
  Timber001, Plaster001, Sandstone001 with doors Door001/002/004/005/006; roofs `<Thatch|Shingle|Slate|Clay>_Roof001-015`,
  drawn by house_tiles.py). A map line's roof may name its material: `(x1, y1, x2, y2, group, material)` in the builders,
  and build_world writes each cell's piece (eaves, ridge, gable ends) as `+Roof(<Material>_RoofNNN.<group>)`. The roof
  leaves the front wall with the door showing.
  * Doors face out: Door001-006 are drawn with the foot of the door at the bottom (the outside below). Door007-024 are
    the same six doors turned, three each in order (outside to the north, west, east): 007-009 Door001, 010-012
    Door002, ... 022-024 Door006 (house_tiles.DOOR_TURNS). build_content.door_facing swaps them in on every built map:
    the outside is the side of the door with more open ground behind it.
  * Houses facing north (their front wall above the roof) get `<Base>_Window003` either side of the door: Window001
    upside down. Their hearth, in the back (bottom) wall, is Fireplace002 (Fireplace001 turned, the fire upright).
    A hearth cooks like a fire: `Use <Raw_...> With Fireplace` goes to `... With Fire` (build_content.hearths).
* King Tyron's palace (dev\migrate\build_palace.py, tiles palace_tiles.py): the Royal Isle, 4,4,0, over a causeway
  at the east end of the goblin camp's north road (3,4,0 row 3). Throne hall, wizard's tower (study 4,4,1), the
  royal treasury (Lock: HobgoblinQuest>=2), a waystone. Tyron's Keep (2,4,0) is now the King's garrison.
* Fishing only at fishing spots (build_fishing.py): animated StaticObjects on the water by a shore you can walk to.
  Fish_Spot (Raw_Fish, Fishing 1: the sea round the Isle and the Southlands), Trout_Spot (10: Southlands rivers and
  ponds, some in the Wildlands), Salmon_Spot (20: Wildlands and far rivers and lakes), Swordfish_Spot (35: the sea off
  the far south and the Eastreach), Eel_Spot (15: cave pools). A rod and one bait a catch (a miss keeps it); fishing in
  plain water says to find a spot. `python -I dev\migrate\build_fishing.py` draws their sprites.
* Entities.ini Anim.Frames=N (and Anim.Speed, ms a frame, default 200): a StaticObject that animates where it stands,
  cycling sprites <Name>1..<Name>N (the plain <Name> sprite is its first frame, for the editors).
* The interface sprites (sprites\Interface: SideBar, StatBox, ChatBar, InfoBox, ResponseBox, SideBarBorder, AB_*, Heart,
  Mana, the item-count digits InterfaceNumber0-9 and +, the health bars 0-100PCHealth) are repainted by dev\migrate\build_gui.py from the originals in dev\Archive\Interface (same sizes, masks and
  layout; copy those back to undo).
* Rugs (interior_tiles.py): Rug001-017 on planks, Rug031-047 on stone tiles: base + 0-8 the nine pieces of a rug at
  least 2 x 2, + 10-12 a runner one tile high, + 13-15 one tile wide, + 16 a mat (villages.lay_rug). Every house has
  a table (and chairs), a rug, a shelf and a plant: villages.lay_house, and build_content.furnish_old_houses for the
  hand-drawn ones.
* Waystones: only four (build_travel.WAYSTONES): Ashford, Highwatch, Dunerest, Thornwick. None on the Isle.
* Music: outside, Config [Sounds] Music (FinalFantasy.mid) plays everywhere, without a break between maps. Inside a
  building (under a roof) it fades over to Hearth, and back out again it fades back in where it had got to (the
  game plays a copy of the MIDI that starts there: dragonsword\midi.py). Every change fades out (1.1 s) and in
  (1.6 s). data\Music.ini (build_music.py): [Themes] <Theme>=its tracks (sounds\Music_<Theme><n>.mid, original
  pieces composed by build_music.py; run it to remake them), [Maps] <map>=<Theme>: used only with Config [Sounds]
  Music.By.Place=1, when each map plays its own theme (changing 2.5 s after you reach a place with different music;
  the palace and the dragon's lair keep theirs indoors too).
  The theme `Title` plays on the login and loading screens (its pieces taking turns), until the game starts.
  Background sounds (data\Ambient.ini, build_travel.py): none on maps by the sea (over 100 water tiles). Where the
  monsters are the music turns: Danger (urgent: a boss, or aggressive monsters worth 100 hitpoints on the map, the
  goblin camp, the warren) or Dread (eerie: three or more skeletons or giant spiders, the Barrow King).
* The fog of war is painted by the game (world.fog_paint): blue-grey clouds anchored to the ground, a pale rim where
  it thins.
* Item respawns: an item picked up off a map comes back after its Entities.ini Respawn= seconds, else Config
  [Gameplay] Item.Respawn.Delay x (1 + sqrt(Value) / 2), at most 2 hours.
* Shops: what you sell gets Value x the rack's Sell.Rate x Config [Gameplay] Sell.Price.Factor (0.25). In a shop,
  inventory items it won't buy are greyed out and can only be examined; a crafting rack greys out what you haven't
  the level to make, with the level on it.
  * Two storeys: the material may be `villages.roof_spec()`, `<roof>:<wall>:<chimney column>:<dormer columns>`. Then the
    roof's bottom row is the upper storey's front, `<Base>_Upper001` (a window) / `002` (plain), part of the roof so it
    hides with it when you go in (Base = Brick, Stone_Wall, Timber, Plaster, Sandstone), with the eaves' shadow and a
    jettied beam or a stone string course. Roof pieces 016-030 are 001-015 with a chimney stack, 031/032 a dormer
    window on the lower slope / bottom eave. The ground-floor front has `<Base>_Window001` either side of the door.
  * Inside (villages.lay_house): Fireplace001 in the back wall under the chimney, and furniture on the planks, from
    interior_tiles.py: Bed001 over Bed002, Table001 with Chair001-004, Bookshelf001, Potted_Plant001 (beds, tables,
    shelves and plants block; chairs don't). Every floor cell stays reachable from the door, and the people's spots and
    the workshop's benches are kept clear.
  * About half the houses of 5 x 5 or more have an upper floor: map `X,Y,1` over the village's map (Black001 round the
    houses), the same walls up to the upper storey, its windows, beds. Reached by Stairs001 (up) / Stairs002 (down),
    or in some houses Ladder008 / Ladder009, at the same tile on both floors. build_world removes a level-1 map it made
    before and no longer makes (if you haven't edited it).
  * The Southlands' hand-drawn brick houses (Southport, Ashford, the farm) get the same roofs, upper storey and windows
    (build_content.restyle_old_houses); the Keep's stone halls keep Roof001.
* Old Hob's house in Oakhollow (build_regions.locked_house): its door has a Lock (`$Attr.HobsDoorOpen>=1`); one front
  window is `<Base>_Window002` (a loose shutter, verb Climb Through: script `Climb Through <Base>_Window002`), which
  moves you in or out. Climbing in unbolts the door (HobsDoorOpen=1). His chest (HobsChest) is inside.
* Old Hob (dev\migrate\build_hob.py, HobQuest 0-4): his diary (Hobs_Diary, Read) in the locked house starts it; Morwen
  in Fenwick gives a Calming_Draught (a branch at the top of Talk to Witch); Hob is an Attitude=Bad NPC in the western
  woods (0,6,0); `Use Calming_Draught With Hob` runs `Set.NPC.Attitude OldHob Good` (his map line has Id=OldHob). If you had already emptied his chest
  (HobsChest=1) he wants his 150 gold back: give it, or keep it and he turns Bad again (HobAngry=1). A side quest: added
  after build_dragon, so the dragon quest doesn't wait for it. The Map Editor's Good / Bad (G) button flips an NPC's
  Attitude; the Entity Editor has an Attitude box for NPCs.
* Wardhaven (maps 4,2,0 to 5,3,0, dev\migrate\build_walled.py): an island over a bridge from the end of the farm road
  east of Ashford (3,3,0 row 12). A village inside city walls (interior_tiles.py: the east-west walls two tiles tall,
  City_Wall001 over City_Wall004; City_Wall002 north-south; towers City_Wall003 over City_Wall005; the gateway
  City_Gate003 over City_Gate001). Both gate cells have a Lock `$Attr.DragonQuest>=4`, so the town stays shut until
  the Dragon of Ashpeak is done; Tiles.ini Unlocked.Tile draws them open (City_Gate004 over City_Gate002). Inside: bank,
  Trader (SHOP-Wardhaven), smithy, Settler, waystone; outside the gate a Guard (Talk to Guard goes to the Wardhaven
  Guard script on 5,3,0). It isn't a quest, so the dragon quest (offered when every other quest is done) doesn't wait
  for it.
* The wheat field: Field001 (ploughed earth) with StaticObjects Ripe_Wheat001-003 on it (verb Harvest, walk-through).
  Harvesting gives Wheat and leaves a Stubble for 60 seconds (Add.Action.To.Queue), then the plant is back. Entity and
  tile names show without their 3-digit number (Ripe_Wheat002 -> "Ripe Wheat").
* Waystones (StaticObject Waystone, verb Travel): one in each town. Touching one sets attribute Waystone.<Key>=1; the
  travel menu (scripts Travel Waystone and Waystone Menu) only goes to waystones with that set. Made by build_travel.py.
* Entities.ini, bows: Range=<pixels> (shoots from that far when the target can be seen) and Ammo=<item> (one used up
  a shot; with none left the bow is a club). Monsters that shoot: Missile=<sprites\Effects picture>, Missile.Impact=<an
  effect animation where it hits>, Missile.Sound; they shoot from 36 + Weapon.Range pixels and bite close up.
* Entities.ini Kill.Sound=<kind>: the sound a monster makes as it dies, sounds\Kill_<kind>.wav (Beast, Small, Bird,
  Livestock, Humanoid, Troll, Undead, Bug, Dragon; made by build_sounds.py). Set for every Bad NPC by build_content.py
  from its name; Beast when missing.
* Spells.ini Level: the Magic (or Skill=) level needed to read the scroll. A scroll works 60% of the time at that level,
  7% more for each level above it (at most 98%); when it fizzles the scroll is used up for half the experience.
* Spells.ini Cost=<mana> and Cooldown=<seconds> (scrolls); Mana=<amount> on a potion gives mana back. The player's
  mana is 10 + 3 per Magic level and refills in a minute (saved as [Player] Mana in the save).
* Config.ini [Interface] Font: the font for all the game's text (spaces allowed; Options cycles Palatino Linotype,
  Georgia, Book Antiqua, Constantia, Segoe UI and Lucida Sans Unicode).
* Python game: Display.Conversation takes up to 11 response/goto pairs (the editor shows 4), and a response
  ending in `[if <condition>]` (the Conditions syntax) is only listed when the condition is true.
* Scripts are at most 99 lines (two-digit line numbers): a longer one carries on in another with Goto.Script (e.g. Open
  Chest -> Open Chest 2).
* The quest log (the StatBox's Quests tab) shows data\Quests.ini the same way as the journal: status from each quest's
  Attribute and Done, the hover text from the current StageN.
  * Colours: gold = in progress, green and crossed out = complete, grey = not started (sidebar and journal alike).
  * Pointing at a quest (in the Quests tab, or at its card in the journal) shows its checklist: Steps, the StageN
    texts from 0 up to the stage it is at (the ones passed ticked and crossed out, the current one in gold; later
    stages are never shown), then Notes, the lines scripts wrote with `Quest.Note QUEST NAME | NOTE` (once each),
    crossed out by `Quest.Note.Done QUEST NAME | NOTE` (NOTE `*` = all of that quest's notes). QUEST NAME is the
    quest's title or its Attribute. A quest whose Stage0 is empty (hidden until started) shows up once it has a note.
    Writing a note says so in the chat (Journal (quest): text). The notes are saved in the save's [Quest.Notes].
  * The generated quests' notes are one table, dev\migrate\quest_notes.py: notes put in after the script step where a
    quest reaches a stage (or after a given step of a given script), and all crossed out when it is done. A rule that
    no longer matches any script is a build problem.
* Editing and rebuilding: the builders (dev\migrate\build_world.py and the files it runs) remember what they last
  wrote in dev\migrate\generated.json: each ini value (Entities.ini, Tiles.ini...), each whole section of ItemRacks.ini,
  Spells.ini, Quests.ini and Gathering.ini, and each whole map and script file they make. On a rebuild anything you
  have changed (or deleted) since then in an editor or by hand is kept, and listed at the end ("Kept N of your edits");
  everything else is brought up to date. To let a builder take a value back, set it to what the builder makes (or
  delete generated.json, which makes the next build overwrite everything as before).
* Editor tools for these: the Entity Editor (now with a bow's Range and Ammo, and what an NPC shoots: Missile,
  Missile.Impact, Missile.Sound), the Item Rack Editor (shops, recipes with Makes), the Spell Editor (Spells.ini: every
  key, new and delete) and the Quest Editor (Quests.ini: giver, attribute, stages, Done, minimap markers; "Add the Map
  Editor's tile" adds the tile picked in the Map Editor as a marker).
* World content (cave tiles, sprites, map population, gathering, recipes, shops and quests) is generated by
  dev\migrate\build_tiles.py, build_sprites.py and build_content.py (via build_world.py); edit the tables there and re-run.
* Pathfinding: the player (click to walk) and NPCs (chasing, wandering home, scripted Move.Entity) path around
  obstacles on a grid of half tiles, using Tiles.ini Walkable.Data, Lock lines and blocking entities. Config
  `[Gameplay] Pathfinding=1` (0 = walk in straight lines as before).

## The editor (Dragon Sword Editor.py)

`python "Dragon Sword Editor.py"` (the `dsedit` package) is every editor in one window: a rail of sections on the left
(Ctrl+1..8), the section on the right, Ctrl+K to go to anything (maps, scripts, tiles, entities, racks, spells, quests),
Ctrl+S / Ctrl+Z / Ctrl+Y in the section you're in, F5 to play the game. A dot on the rail = unsaved changes there;
you're asked before anything unsaved is lost. Everything links: "Used on" / "Placed on" / "Opened by" lists jump to the
place, a map's trigger opens its script, a script's arguments jump to what they name (↗), a rack's item opens in
Entities, a quest marker comes from the tile picked in Maps.

* **Maps**: layers Ground / Roofs / Tree tops / Things (1-4); Paint, Fill (or Shift+click), Rectangle, Erase, Pick
  (or Ctrl+click); the palette (filters by family / type, and by name); the maps round this one shown dimmed round its
  edges (double-click one to go there; Ctrl+arrows, PgUp/PgDn). The inspector on the right: a tile's sprites, a
  thing's fields, an NPC's attitude, Id, Stand, roam zone and chase area (drawn on the map), patrol (click tiles), a
  trigger's script (Edit makes it if it's new), a lock's condition (the condition builder) and message.
* **Scripts**: the line table (conditions in blue, gotos as →, problems marked) and the line editor: the command, and
  for each argument its own choices, a "…" builder (conditions, a point or tile clicked on a map, quantities, pickers
  with sprites) and ↗ to open what it names; right-click a box for the $ variables. Lines added, removed or moved keep
  every goto pointing at the same line. Problems are listed (and checked as you type).
* **Tiles** (Tiles.ini, and each tile's minimap colour in dev\Minimap Colours.txt), **Entities** (Entities.ini: the
  fields that don't apply to the Type are greyed out; drops and requirements builders; animated preview), **Item
  Racks** (rows built with the row editor, prices shown), **Spells**, **Quests** (stages and minimap markers),
  **Minimaps** (builds Minimap<Z>.png with dev\migrate\build_minimaps.py; the preview is a world map: click a map to
  open it).
* Files are written as the builders write them (ANSI, CRLF), changing only what you edited, so a rebuild with
  dev\migrate\build_world.py keeps your edits (common.py GEN) as before.
* The old Liberty BASIC `Dragon Sword Editor.bas` is no longer used by anything (the script language moved to
  dragonsword/script_language.py).

## Status effects, the gravestone, the hotbar (dragonsword\extras.py), moving tiles (dragonsword\anim.py)
* Entities.ini `On.Hit=<Effect> <chance %>` (Poison, Burn, Bleed, Chill): a monster's landed blow or missile gives
  it you. Poison/Burn/Bleed hurt you every so often for a while; Chill slows your walking and your blows. `Cures=<Effect>
  <Effect>...` on an item (the Antidote) ends them when you Drink it. Dying ends them. `Resists=<Effect>...` on
  something worn (the Fire_Ward_Charm: Burn) stops those effects starting, and blows from a monster whose On.Hit is
  one of them hit a third softer.
* Ranged monsters: `Weapon.Range` (pixels) and `Missile` (a sprites\Effects picture), `Missile.Impact` (an animation):
  Goblin_Archer, Goblin_Shaman, Skeleton_Archer, Frost_Witch and the Dragon (dev\migrate\build_status.py).
* Dying leaves your inventory in a Gravestone where you fell, for Config [Gameplay] `Grave.Minutes` (10) of play: the
  save's `[Grave]` (Map, X, Y, Left = ms, ItemN=name,qty). Search the Gravestone to take it back.
* The hotbar: the save's `[Hotbar]` SlotN=<item> (1-5).
* Foam along every shore and flickering flames are drawn by the game from the tiles (Tiles.ini Water=1, Flame=1).

## Day and night (dragonsword\daynight.py), weather (dragonsword\weather.py)
* The time of day: a fraction of a day (0 midnight, 0.5 noon), a day lasting Config [Gameplay] `Day.Minutes` (24); the
  save's [Player] `Time=`. Config [Gameplay] `DayNight=0`: always day.
* **data\DayNight.ini**: `[Sky]` `<time>=R G B strength` (the colour over the world, eased between the times);
  `[Night]` `From`, `To` (when night falls and ends), `Indoors` (how much of the dark gets under a roof),
  `Glow.Colour` (the warm glow round lights), `Falls`, `Ends` (what's said); `[Periods]` `<time>=<name>` (the name of
  the time of day up to each time); `[Sleep]` (below).
* At night everything with `Light=<radius>` lights the dark round it: Tiles.ini (ground, decor, roofs: torches 72,
  lamp posts 96, lit windows 34) and Entities.ini (fires, ranges, or anything).
* Entities.ini `Schedule=Day` (townsfolk, the meadow's creatures): home through the nearest door (Tiles.ini `Door=1`;
  `Door=Gate` is a gateway nobody lives behind) at night, out again in the morning. `Schedule=Night` (bats, the open
  country's skeletons): only out after dark (in caves always).
* **Sleeping**: the `Sleep` verb (Use.Words on beds, any tile or thing) or the script command `Sleep <until>`
  (Morning, Evening, a time 0-1, or blank: the morning if it's night, else the evening). The screen goes dark, the
  time moves on and the player wakes there, healed. DayNight.ini `[Sleep]`: `Morning`, `Evening`, `Heal` (1 = full
  hitpoints and mana), `Foe.Range` (no sleep with a foe this close), `Fight.Seconds` (nor this soon after a fight),
  `Fade`, `Hold` (ms), and what's shown and said (`Text`, `Wake.Morning`, `Wake.Evening`, `Foes`, `Fighting`,
  `No.Day`). The game saves when you wake.
* **data\Weather.ini** (Config [Gameplay] `Weather=1`): `[Weather]` `First`, `Lasts=min-max` (seconds), `Fade.Out`,
  `Fade.In`, `Shade.Colour`, `Otherwise` (what a weather turns into where neither it nor what it Becomes is),
  `Lightning.Every`, `Thunder.After`, `Thunder.Sound`. `[Kind.<name>]` for each kind: `Shade` (0-255), `Message`,
  `Draw` (rain, snow, fog or blank), `Amount`, `Colour` (rain), `Wind` (snow), `Ambient` (the sound in place of the
  place's own), `Lightning=1`, `Becomes`. `[Climate.<sound>]` (a map's data\Ambient.ini sound; else
  `[Climate.Default]`): `<kind>=<how likely>`. Not in caves; indoors you only hear it.
* Firemaking is no longer a skill: anyone with a tinderbox can light logs (better logs burn longer).

## Durability (dragonsword\durability.py)
* Entities.ini `Durability=<blows>` on weapons and armour (dev\migrate\build_status.py sets it by material: copper 60,
  bronze 100, iron 160, steel 240, mithril 360, the Dragon Sword 600, leather 110...). A weapon wears 1 for each blow it
  lands; each blow you take wears one piece of what you're wearing. Worn out: broken, no bonuses till mended.
* The wear is kept with each item: the save's `[Inventory]` SlotN=<item>,<qty>,<wear>, `[Equipment]` <Slot>=<item>,<wear>,
  `[Bank]` SlotN=<item>,<qty>,<wear;wear;...>, the grave's ItemN=<item>,<qty>,<wear>.
* Mending: the Repair verb on a blacksmith NPC (Use.Words Repair: the smith, the forgemaster, Brokk): everything worn,
  for about 40% of what the wear took off its Value. Or use the item on an Anvil: one bar of its metal (Leather, or
  logs for wood), Smithing 1 (bronze, copper) to 25 (mithril). The Dragon Sword: only a smith.
