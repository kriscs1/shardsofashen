# Roadmap, round 4 (2026-11-05)

The owner's list, grouped by the files it touches so each group is one read of the code, one build, one validate +
pytest run, one commit. Tick a box when done and committed; say beside it what was decided differently.
Carry on from the first unticked box.

**Working rules to save effort**
- Grep for the code once per group, change everything in it, run `validate.py` + `pytest` once, commit once.
- World work goes in ONE builder per zone (`dev/migrate/build_<zone>.py`), run once, then render the maps to check.
  Never hand-edit maps; never re-run `build_estforlan.py` (CLAUDE.md).
- Client groups: one browser check (desktop + phone) per group, not per item.
- New systems are a small data file + one engine module each (the pattern of `encounters.py` / `banter.py`), with a test.
- The level bands for the zones are set once (group 8, a table), so later groups only look them up.
- Don't use sub-agents for building; use them only for the final QA audits (gameplay/multiplayer/security testers).

---

## 1. Start screen, accounts, servers (web/home, server/, central/, android, desktop)
- [x] Back button when a single-player game starts (to the main menu): page + `DSApp` in Android and desktop.
- [x] "Shards account" -> "Hallisium account" wherever text is shown (start screen, game page, emails, admin,
      privacy, README); internal names stay.
- [x] The "Public beta" pill never wraps onto two lines on mobile (`white-space: nowrap`, smaller on narrow).
- [x] Unraid server shows its name, not "a Shards of Ashen server" (check `DS_NAME`, the template variable, the announce).
- [x] Unraid log spam every few seconds: find the repeating line (central poll, ban check, announce), log only on change.
- [x] Public servers: join without typing the address (join from the Public servers list / ticket / friend's link).
      The list has no addresses now: a signed-in player's ticket brings the one they join, and the apps never show it. A browser's address bar still shows the server; only relaying every game through the central server could hide that.
- [x] Public servers: no local route at all, even by a workaround, and no login page of their own; play only
      through the client or the main webpage's ticket (tighten `make_app` index and `authenticate`; tests).
- [x] Character-creation warning: a character is tied to its server and play type; self-hosted can't join public;
      public -> local can't go back; saves are online on public servers, on your device otherwise. Add a
      public -> local **character transfer** (one way: a copy to the app's Single player, or a file; the public original stays).
- [x] Log player progress for single player too: anonymous, a unique id per device, a clear notice (first run,
      Options, privacy page; `server/progress.py`, `central/store.py`, `privacy.html` in the same commit).

## 2. Character creation, UI wording, small client fixes (web/js)
- [x] Creation says "Top" and "Bottom" (not shirt/trousers/skirt) and "Body 1" / "Body 2" (not man/woman).
- [x] Hover descriptions aren't all lowercase (find the lowercasing in the tooltip code).
- [x] Mary's letter: repaginate to fit the pages, no last page of two words.
- [x] Chat box stretches right to the hotbar's edges (desktop layout).
- [x] Gear tab: spread the slots out to fill the bigger Stats/Gear box.
- [x] Stance buttons: a smooth light-up round the edge for all 360 degrees (a conic ring, not steps).
- [x] Quest finished screen for every quest: name + rewards, its own panel apart from the chat (check what exists
      in `ui.js` / `quests.py` first; make it fire for all, with a test).

## 3. Movement, clicking and feel (web/js, dsengine)
- [x] Lag when crossing between map tiles (starter house -> churchyard): profile the map-change / `mapcells` path first.
- [x] Bench: sit cursor differs from the sleep cursor; getting up walks at normal speed; the yellow click ring is
      cleared when you click a bench.
- [x] No shake of the character and screen when a click-move arrives (camera snap / interpolation).
- [x] The player never takes click priority over what's beneath (stairs, items): pick what's under the cursor first.
- [x] Sheep a little smaller (sprite scale in its builder).

## 4. Ground, textures and look (build_terrain, ground.js, dsedit)
- [x] Terrain transitions (path/grass etc, different priorities): a few dotted patches bleeding across
      (`ground.js` paintRounds / a scatter pass keyed on the grid-corner hash).
- [x] Grass, water and sand less repetitive: more or larger seamless textures, or alternates.
- [x] Dense forest texture: no dark bits.
- [x] Lava animated and better looking.
- [x] Second storeys and basements get a south wall; basements: no wood by the walls with stone in the middle
      (new side-wall tiles; `house_tiles`, `build_interiors`); one migration for existing houses.
- [x] Buildings of two or more storeys look it from outside (taller facade, upper windows, a ledge; not churches):
      a builder + migration over every such house.

## 5. Map editor (dsedit)
- [x] First open lands on Northport.
- [x] A 2-tile-wide painter for single tiles.

## 6. Quick world fixes
- [x] Dice games playable in every pub (audit pubs against the dice NPC/script; add where missing).
- [x] Secret basement passage: two houses' basements joined by a black-roof passage so a man locked out of his
      house gets in (a new side quest, in a town with few quests, with its rumour).
- [x] Mangrove trees: new tile and sprites, replacing the sand by the sea in the marshes; a use: Fever Tonic is bog myrtle and
      mangrove bark now (Strip Bark, Alchemy 3), not marigold.

## 7. Galaith rearranged (a builder in the `build_galaith_city.py` style; outer walls unchanged)
- [ ] West to east, roughly as sketched: Royal quarter in the middle on the left with Nobles above and below it;
      fountains, orchard and gardens left of it; then Merchants (the market); then the hovels on the right;
      a tree-lined grand boulevard (white) along the middle.
- [ ] Double walls spaced apart on the east side, ramparts and makeshift defences, lots of guards.
- [ ] The gate put back at the end of the boulevard; royal guards outside the royal gate.
- [ ] Quest coordinates (palace -9,14,0, east gate, mine) follow their buildings; tests; minimaps.

## 8. Level gates and training (data + scripts; one table in `dev/migrate/zones.py`)
- [ ] The table of zones and level bands (gradual progression from the Isle outward).
- [ ] A story reason you can't leave the Isle before level 5 (Bess/Wim; no hint text).
- [ ] The Mire Tunnel and Emberwatch guarded by high-level mobs so you must level to enter.
- [ ] Lots of bad-NPC training areas across the bands (camps, dens, graveyards), by builder.
- [ ] Every hard zone's mobs and ores checked against the table (validate warns on a gap).

## 9. New zones (each its own builder, natural shapes, quests, levelled by the table)
- [ ] The four new zones around 0,-3,10 / -1,18,0 / 21,8,0 / 24,7,0 (read what's there first): high-level mobs,
      higher-level mining rocks moved in, structures to explore, a few quests each; one zone only magic NPCs.
- [ ] A dusty wasteland around 12,7,0 to 16,13,0: a natural (non-rectangular) outline, desert terrain, ruins.
- [ ] A snowy, icy island growing from 18,23,0: yetis and more, a harder band, the cold applies.
- [ ] Fill the open mainland: farms, side quests (each with a rumour), big buildings, mining areas, fishing areas,
      other (ruins, camps, shrines, a lighthouse); roads join them.

## 10. Seasons (`dsengine/seasons.py`, `data/Seasons.ini`)
- [ ] Season from the UTC date; longer days in summer, longer nights in winter.
- [ ] Winter: snow instead of rain, rivers freeze and can be walked, marsh mosquitoes gone, snowy patches about;
      the snowy land is always snow.
- [ ] Autumn trees change colour; in spring tall grass gets flowers (cheap tint/decor, no canvas filters).
- [ ] Crops and fish change by season (gathering scripts read the season).

## 11. The new systems (a module, a data file and a test each)
- [ ] Shard storms (rare weather: remnants rise, Shards on the ground; warn players).
- [ ] Ghost ships (foggy nights at a port; loot and the dead aboard; gone by morning).
- [ ] The Wandering Inn (a different wild spot each day; rumours, dice, a keeper who knows too much).
- [ ] Mimic villagers (a name misspelt, never sleeps, a purple glint; turn on you when caught).
- [ ] A hunter that remembers (a survivor grows stronger and tracks you down; saved per player).
- [ ] The Tax Collector (unkillable, polite, follows anyone carrying too much gold, at walking pace).
- [ ] Your own legend (gossip from stats the game already keeps; added like rumours).
- [ ] Rival heirs (a yearly crown tournament in the arena; the winner's statue in Galaith).
- [ ] Letters by carrier (items and notes to offline friends; a courier appears on their next login).
- [ ] Mary's notes as a hunt (her scattered notes form a map once all found; the Heart of Ashen secret).

## Before each commit
validate 0 errors, pytest green, export assets / minimaps when changed, a browser check for client changes,
CLAUDE.md updated with any lasting rule, commit to main and push (keep the owner's uncommitted work).
