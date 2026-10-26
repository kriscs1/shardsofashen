# The new mainland: the plan

The owner's brief (rebuild every overworld map but the Isle): cities, towns, villages and hamlets far apart with wild
country between them; each settlement the size it's given, with what that size has; houses all different, spaced
out; the market square near the centre with paved roads off it, roads less regular further out; local materials
for each place's streets; roads joining everything on a landmass; a port for a city on a coast, a dock for anything
smaller; waystones and homestones by every centre. Galaith is a huge city in a gap in a mountain range down the
whole west coast, the dragon before its walls behind the barrier, the walls white but burnt black, a mine behind it.

Built by `dev/migrate/build_estforlan.py` (re-runnable: the same world every time). The quest places it carries
over (`dev/migrate/world_parts/`) were lifted from the old maps once by `dev/migrate/lift_world_parts.py`.

## The grid (maps X,Y,0; 25 x 21 tiles each)

```
     x  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4
y 0     I I I I I ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
y 1     I I I I I ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
y 2     ~ I I I ~ ~ ~ ~ ~ ~ ~ ~ v v ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
y 3     ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ v v ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
y 4     M M g g g g g g g g g g g g g g g g g C C a a a ~
y 5     M M w g g g g g g g g g g g g g g g g C C a a a ~
y 6     M M w w w w g g g g g g g g g g g g g C C a a a ~
y 7     M M w w w w w w w g o o o o o g g g g C C a a a ~
y 8     M M w w w w w w w o o o o o o o e e e C C a a ~ ~
y 9     M M w w w w w w w o o o o o o e e e e e h h u u ~
y10     M M M M M M M M M M o o o o o e e e e e h g g g ~
y11     M G G G G G G F F P o o o o e e e e e e h g g g ~
y12     M G G G G G G F F P h h o o e e e e e e h g g g ~
y13     M G G G G G G F F P h h h h h e e e e u u g g g ~
y14     M G G G G G G F F P h h h h h h u u u u u u u u ~
y15     M M M M M M M M M M h h h h h h u u u u u u u u ~
y16     M d d d d d s s s s h n n n n n u u u u u u u u ~
y17     M d d d d d s s s s s n n n n n u u u u u u u u ~
y18     M d d d d d s s s s s n n n n n u u u u u u u ~ ~
y19     M d d d d d s s s s N N N N N N u u u u u ~ ~ ~ ~
y20     ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ D ~ ~
y21     ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
```

I the Isle (untouched) · ~ sea · M the West Range · C the Cinder Peaks · N the Frostpeak range · G Galaith ·
F the dragon's scorched field · P the pass (the barrier across its gap) · g fields and meadows · w the Wildwood ·
o Greymoor · h the Redrock hills · s the Saltmarsh · d the Sunscar Desert · n the Frostpeak snowfields ·
e the Elderwood · a the Ashwold · u the downs · v Wardhaven's island · D Dragon Island.

## Settlements (maps they take; their streets' material)

| Place | Size | Maps | Streets | Coast |
|---|---|---|---|---|
| Galaith | huge city | 1-6, 11-14 | white marble flags; cobbles out to the walls | (inland: the West Range) |
| Southport | large city | 2-5, 4-6 | red brick | north: a port |
| King Rupert's Keep | medium city, the keep and bailey in its middle | 21-23, 10-12 | grey cobbles | east: a port |
| Wizards' Court | medium city, the court and its tower on its edge by the Cinder Peaks | 16-18, 4-6 | blue-grey flags | north: a port |
| Fenwick | medium city | 6-8, 16-17 | timber boardwalks | (the marsh) |
| Ravensgate | medium city | 21-23, 15-16 | dark slate | east: a port |
| Ashford | small city | 9-10, 4-5 | red brick | north: a port |
| Highwatch | town | 12-13, 13-14 | red sandstone | |
| Frosthold | town | 13-14, 17-18 | grey flagstones | |
| Wardhaven | town on its island, its gatehouse over the bridge | 12-13, 2-3 | grey cobbles | north: a dock; the bridge |
| Oakhollow | village | 7-8, 8-9 | gravel | |
| Thornwick | village | 17-18, 10-11 | gravel | |
| Emberwatch | village | 22-23, 5-6 | black basalt | east: a dock |
| Moorcross | hamlet | 12, 8 | dirt | |
| Wildwood | hamlet | 2, 8 | dirt | |
| Dunerest | hamlet | 3, 18 | sandstone | |
| Saltmarsh | hamlet | 9, 19 | boardwalk | south: a dock |

## Quest places carried over (lifted from the old maps, set down at the same tiles of their new map)

| Old map | New map | What |
|---|---|---|
| 1,4,0 | 20,10,0 | the old iron mine's yard and hatch (its levels 1,4,-1 2,4,-1 2,4,-2 2,4,-3 move with it: 20,10,-1 21,10,-1 21,10,-2 21,10,-3) |
| 2,4,0 | 22,11,0 | the keep (its solar 2,4,1 → 22,11,1) |
| 4,4,0 | 18,5,0 | the Wizards' Court's castle (Bert's study 4,4,1 → 18,5,1) |
| 3,5,0, 4,5,0 | 13,4,0, 14,4,0 | the hollow barrel by the lake, the smugglers' cove (the tunnel 3,5,-1 4,5,-1 → 13,4,-1 14,4,-1) |
| 3,3,0 | 11,4,0 | Ashford's farm crossroads and the herbalist's cottage |
| 2,3,0 | 9,4,0 | Ashford's Green Dragon, its beer garden and games, the arena master, the settler's yard |
| 1,3,0 | 4,4,0 | Southport's landing, pier and port guard |
| 1,6,0 | 7,9,0 | old Hob's boarded-up house in Oakhollow |
| 0,5,0 | 4,9,0 | the spider nest |
| 1,9,0 | 3,16,0 | the buried library's mound (1,9,-1 → 3,16,-1) |
| 0,10,0 | 1,18,0 | the caravan wreck |
| 4,9,0 | 12,16,0 | the way down to the Frostpeak caverns (4,9,-1 → 12,16,-1) |
| 5,6,0 | 14,9,0 | the wolf den |
| 5,8,0 | 15,14,0 | the bandit camp |
| 5,9,0 | 11,18,0 | the troll's frozen lake |
| 8,2,0 | 23,4,0 | the Cinder Fort |
| 6,4,0, 7,3,0, 9,4,0 | 21,4,0, 21,7,0, 22,8,0 | the Ashen shrines |
| 8,5,0 | 19,12,0 | the Heartwood |
| 9,7,0 | 18,17,0 | the barrow |
| 9,8,0 | 23,17,0 | Captain Rook's pier |
| 8,10,0 | 22,20,0 | Dragon Island (the whole map) |
| 6,7,0, 7,8,0, 8,7,0, 8,8,0 | 17,14,0, 19,18,0, 22,15,0, 22,16,0 | the downs' graveyards and Ravensgate's |
| 14,6,0 | 0,12,0 | the mine behind Galaith (14,6,-1 → 0,12,-1) |
| 10,6,0 | 9,12,0, 7,12,0 | the barrier in the pass (mirrored: at 19,10-12, you come from the east); the dragon on its field before the gate |

The rest of each settlement's people with a quest (the Speaker, the Mayor, the Steward, the scholar, the witch...)
keep their Ids and are put in the matching new building. Scripts that named an old map name the new one.

The settlements are grown, not drawn: `dev/migrate/build_estforlan.py` (its parts in `dev/migrate/estforlan`) builds it all
from this plan (`estforlan/layout.py`); run it again to build the same world again.
