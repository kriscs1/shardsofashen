# Code issues found by review

Issues found by reading the code (2026-11-10). Tick a box when its fix is committed, with a test. All are fixed
(2026-11-12) but 29, in part, and 47, which waits on a choice of the owner's.
"Reproduced" means it was run against the real engine; the rest come from reading the code.

## Worth fixing

- [x] **1. A tile can be used from up to three screens away, through walls.** (Reproduced.) A verb on a far tile is
  queued while the player walks, and the walk's target is wherever the cursor last was. A second `verb` message with
  no target moves the cursor onto the player and returns before the queued verb is cleared
  (`dsengine/player_actions.py` `handle`, the `verb` branch; `dsengine/session.py` `update_player_walk`). "Climb
  Down" on a hatch 397 px away ran at once; "Mine" was refused only because its script checks distance itself. The
  `cast` branch sets the cursor with no bounds check at all. Fix: keep the click with the queued verb, not the live
  cursor.
- [x] **2. A time pass can become the full game for good on one server.** At a ticket login `full:<account>` is
  stored as "1" while a pass is running (`server/game.py` `full_of`). A reload comes in by the linked device with no
  ticket: it reads that "1", has no `pass_until` and no grant, and `passes_ran_out` never asks again. Separately, if
  the central server doesn't answer `owns_now` once, `pass_until` stays 0 and the pass never ends that session. Only
  matters once `DS_DEMO=1`.
- [x] **3. One bad NPC can freeze the whole server.** Each player's work is guarded, but `update_npcs`, the carts,
  the action queue, farms, waves and the rest of `World.tick` are not. An exception there aborts the tick, and
  `send_updates` is in the same `try` (`server/game.py` `run`), so nobody is sent anything; if the error persists it
  repeats and logs 20 times a second. `update_npcs` also leaves `self.dt` altered when `update_npc` raises. Player
  code runs in that unguarded part too: a missile landing (`world.py` `missile_arrive`: the spell's hit, the kill,
  its Kill script), the tavern's dice roll, the wonders and a wave's end (`waves.py` `finish`: the rewards and
  `On.Win.Script`). A missile also ignores levels: it follows a target that has climbed a ladder.
- [x] **4. A mute ends when the player reloads.** `muted_until` lives only on the Session; leaving discards it and
  coming back makes a new one. `/letter` isn't counted as talking either, so a muted player can still send letters.
- [x] **5. A trade can be switched at the last moment.** Changing an offer resets both accepts, but an "accept"
  already on its way counts for the new offer (`dsengine/together.py` `trade_msg`). Fix: the accept carries the
  offer's version, or a short lock after any change (the market already checks the price seen).
- [x] **6. A failed save is treated as done.** `save_all` logs the exception, then clears `save_soon` and every
  `save_requested` and resets the timer. A trade's save waits up to a minute for the next try; a player who was
  leaving is never saved again.
- [x] **13. Any friendly NPC in sight can be killed with a bolt spell.** (Reproduced: a Villager and a Cat on 1,1,0
  died to Fire Bolt, and counted as kills.) No forged message is needed: with no foe in range the spell is held
  ready and the next click is its target (`web/js/input.js`), and `spell_target_ok`
  (`dsengine/player_combat.py`) asks only that an NPC is alive, active and in sight. Melee is closed off (a friendly
  NPC has no "Attack" verb). The NPC is gone for everyone until it respawns: shopkeepers, quest givers, someone's
  hired sellsword. Fix: `spell_target_ok` asks `hostile_for` (or for the Attack verb) of an NPC.
  **The horse carts and the Isle's ferries die the same way, and never come back.** (Reproduced: "You have killed
  the Ferry!"; nothing had respawned two minutes later.) They're NPCs with `source="CART"` (`dsengine/carts.py`
  `spawn`), only `MAP` NPCs respawn, and `Carts.tick` skips a cart that isn't alive: no ferry off the Isle for
  anyone until the server restarts. The travelling salesman and a creature holding a swapped player's body are open
  to it too.
- [x] **14. A monster's respawn is lost when a same-named one stands on its spot.** (Reproduced: Cave Horror on
  -1,10,0; the queue entry finished with 1 of 2 alive.) `do_queue_entry` (`dsengine/world.py`) drops the `ADD` when
  `find_entity_at` finds a same-named entity within 24 px of the spawn point, by where it is now or where it began,
  and the entry isn't tried again: only a restart brings the monster back. 481 of the 1,784 hostile map NPCs have a
  same-named neighbour within 200 px. Fix: put the entry off a few seconds, or match by the original spot only.
- [x] **19. A homestead's rugs are lost at every server restart.** (Reproduced: a cell `{"under": "Rug001"}` came
  back from `Homes.load` as `{}`.) `load` (`dsengine/homes.py`) keeps only a cell's `tile`, `decor` and `roof`, while
  `build` stores a rug as `under` and `make_map` draws it from there. The rug and what it cost are gone. Fix: add
  `"under"` to that tuple.
- [x] **23. A melee monster can be killed from outside its chase area at no risk.** (Reproduced: a Hobgoblin, a
  Skeleton and three Bears died to Fire Bolt cast from 196 to 237 px, none coming any nearer.) Hit, it starts a
  fight, finds its foe outside its chase area on its next think and gives up (`dsengine/npcs.py` `update_npc`, the
  chase branch, then `npc_give_up`): it walks back, doesn't heal and is hit again. Fire Bolt reaches 256 px and a
  written spell up to 320; a default chase area ends about 7 tiles from the spawn point. Monsters that shoot do
  shoot back (their reach is tested before the area). Fix: one hurt from where it can't follow comes anyway for a
  while (a wider chase area while hurt), or backs off out of sight and heals.
- [x] **25. A made-up Play purchase token can give the full game free.** (The address was checked with yarl, not
  against Google.) `play` (`central/bought.py`) puts the token into the address unescaped, and aiohttp folds `..`:
  a token of `../../../voidedpurchases?maxResults=3` asks
  `.../applications/<package>/purchases/voidedpurchases?maxResults=3`. Any answer of 200 with JSON that has no
  `purchaseState` counts as bought (it defaults to 0, and `acknowledgementState` to 1), and each variation is a new
  `purchases.ref`, so any number of accounts could claim it. Only matters once Play is set up and the demo is on. Fix:
  refuse a token with anything but `[A-Za-z0-9._-]` in it, and require `purchaseState` to be there (and `kind` to be
  `androidpublisher#productPurchase`).
- [x] **26. The desktop app's bridge answers any page in its window.** `Bridge` (`desktop/app.py`) never asks
  whether the start screen is what's showing (the Android one does, with `home()`), so a remote server's page, or a
  friend's relayed game, can call `pywebview.api.state()` and read `steam_ticket`, and call `hostAs`, `stopHosting`,
  `play`, `openLink` and `set`. A hostile server could send the Steam ticket to `/api/buy` for an account of its own:
  the purchase is claimed by Steam id, so the real owner is then told it's another account's. Fix: each method checks
  the window's address is the start screen's (as Android's does), `goHome` and the carried character aside.
  `set` from a game's page can also change `central` (the start screen then signs in to someone else's central
  server: a place to take the password) and `token`. And mending 28 by just adding `Prefs.get` would let any game's
  page read the sign-in `token`, the `hostKey` and the device keys: see 33.
- [x] **27. One friend's dropped connection can close a host's whole game to friends.** `from_host`
  (`central/relay.py`) sends the host's `m` to a friend's connection with no guard; if that connection has just
  dropped (not yet `closed`), the error leaves the host's read loop in `host`, the tunnel closes and every friend is
  put out. Fix: catch the send's errors there (ConnectionError, RuntimeError) and drop just that connection.
- [x] **32. A game that gives another game's id is handed your device key for it, and that key is your account
  there.** (Read, not run.) The start screen (`web/home/index.html` `join`) keeps one device key per game id and puts
  it in the address of whatever page it opens for that id. The id is the game's own word: `/api/info` for an address
  typed in, the UDP answer for a game found on the network; and a public server's id is in `/api/servers` for anyone.
  So a game on the network (or at an address someone's handed out) that claims a public server's id is given the key
  you use there. At the real server a device key once used with a ticket is linked for good, and then signs in as
  that account by itself, from any address (`server/game.py` `authenticate`: `if not owner and linked`): its
  characters played, copied, traded away. (Tickets aren't taken this way: a game proves its id to the central
  server.) Fix: keep a key with the address it was first given to (or keep keys for games the central server vouched
  for apart from those found by address or on the network); and a linked device asks for a ticket again when it
  comes from a new address.
- [x] **33. "Copy to device" keeps nothing in either app, and says it did.** `exported` (`web/js/main.js`) calls
  `DSApp.set("carried", ...)` from the game's page and tells the player "A copy of X is on this device". On Android
  `set` and `get` answer only the start screen (`MainActivity` `home()`), so the copy is dropped, and `get` gives ""
  in your own game too. On the desktop `set` keeps it but `get` raises (item 28), so it's never offered. Fix with 26
  and 28: both bridges let a game's page `get` and `set` the `carried` key, and only that one.
  *Fixed with 26 and 28.*

## Smaller

- [x] **7. Reset code burned on a short password.** `central/app.py` `reset` drops the emailed code before checking
  the new password's length.
- [x] **8. No daily cap on "forgot" emails.** After six tries the wait allows one a minute for ever (about 1,440 a
  day to one mailbox), and each new code cancels the last. The per-mailbox count is keyed on the raw text, so "Bob"
  and "Bob!" count separately. (Confirmation emails are capped at 5 a day.)
- [x] **9. Account names leak at login.** "has been deleted" and "signs in with Google" are said for a name before
  any password is checked.
- [x] **10. God mode is shared.** It's written to `data/Config.ini` and read by every admin on entering, so one
  admin's switch is everyone's, and it changes a checked-in data file.
- [x] **11. Stale market index.** A box index is resolved against the list as last re-sent, so a click made just as
  the board refreshes can land on a different listing; the price check catches it unless the prices match.
- [x] **12. An odd header gives a 500.** `hmac.compare_digest` on a non-ASCII `joined` token or `X-DS-Relay` header
  raises TypeError (it only hurts the sender).
- [x] **15. Hiring a sellsword while one is with you takes the 25 gold and gives nothing.** The gold goes before
  `companion_call` (`dsengine/together.py`), which returns silently if one is already along (or if the NPC can't be
  added), and the script says it worked.
- [x] **16. Dragon Dice: a winner who left during the 20 seconds isn't paid.** `Tavern.roll`
  (`dsengine/tavern.py`) pays only winners whose session is there; the rest of the pot vanishes.
- [x] **17. The bounty's day is the server's local day**, not UTC (`together.py` `today`).
- [x] **18. Wear and the stolen mark are lost** when a stack is dropped, and in `check_saved_equipment`. After a
  restart, things lying on the ground are put back from the queue's `REMOVE` entries by name and quantity only
  (`world.py` `apply_saved_queue`), so a stolen one comes back unmarked and a worn one as new.
- [x] **20. Coming back into the Shifting Deep after it shifted puts you inside rock.** (Reproduced: placed on a
  `Black001` tile, the player stays in it and can walk 207 px through rock to open floor.) The floors are remade
  with a new seed at each shift and at every server start (`dsengine/deep.py` `make`), and a player who left inside
  comes back at the old spot on the new floor. Fix: entering a Deep map whose seed isn't the one they left, put them
  at floor 1's stairs or the entrance. The spring thaw does the same on a smaller scale: `Seasons.tick` turns the
  ice back to water whether or not someone is standing on it (the action queue's tile changes wait for a player
  to step off; this one doesn't).
- [x] **21. Free Homesteading XP.** `Grass001`, `Dirt001` and `Soil001` need nothing and cost no Shards, and `build`
  (`dsengine/homes.py`) gives 0.02 Homesteading for each: laid over each other in turn they level the skill for
  nothing.
- [x] **22. A cart can be held for ever by hailing it.** `Carts.hail` holds a cart with no timetable 20 seconds at a
  time, as often as asked, by anyone, whether or not riders who've paid are aboard.
- [x] **24. A Fire Bolt Scroll on the ground keeps off the cold.** (Reproduced: on snow at 11,22,0, not warm; one
  dropped beside the player, warm.) `warm` (`dsengine/cold.py`) takes any entity whose name starts with `Fire`,
  `Forge`, `Range`... as a fire: so are a dropped Fire Bolt or Fire Storm Scroll or Fire Ward Charm, a Ranger, the
  Forgemaster, the Forgemother and a Ranger's Cot. Fix: an Entities.ini key (`Warmth=1`) or the exact names.
- [x] **28. The desktop app can't give back what a game page kept.** `Bridge.get` (`desktop/app.py`) calls
  `self._prefs.get(key)`, and `Prefs` has only `set`: the page's `DSApp.get` (the character carried between servers,
  `web/js/main.js`) raises AttributeError there. `Host.start` also sets `mode` to "solo" whatever it's given.
- [ ] **29. A refunded purchase keeps the full game.** `central/bought.py` asks the store once, when it's claimed;
  nothing asks again (Play's voided purchases, Steam, itch). The Android app does take it back on the device
  (`Billing.restore`), but the account keeps `full`. An admin can take it back by hand.
  *Part fixed:* once a day central asks Google Play what it has voided, and a voided purchase takes `full` back.
  Steam and itch.io aren't asked again: central keeps only a hash of their ids, so there's nothing to ask them with.
- [x] **30. A game open to friends can be pestered by anyone with its id.** `/play/<id>/...` (`central/relay.py`)
  needs no sign-in. Twelve connections that never sign in fill `CONNS_MOST` and the game is "busy" to real friends
  (the game's own end has a 5-second heartbeat but no time limit for signing in: `server/game.py` `serve_ws`). And
  what's kept is keyed on the address with its query, so `js/main.js?1`, `?2`... each ask the host again and each is
  kept, up to the 200 MB. Fix: a time limit to sign in, and keep by path alone (or only the `?v=` the page uses).
- [x] **31. A changed password leaves game servers' grants good.** `set_password` (`central/store.py`) drops the
  sign-in tokens but not the grants, and `grant_name` renews a grant at each use: a server that holds one can go on
  asking for that account as long as it likes. (A ban and a deleted account are checked at each use.)
- [x] **34. The editor writes over a file changed on disk since it loaded it.** The Maps and Scripts pages' saves
  (`dsedit/pages/maps.py`, `pages/scripts.py`) never look at the file's stamp: only showing the page reloads, and
  only what isn't changed in the editor. The ini pages' Save does merge (`changed_on_disk`, reload, reapply), but
  their New, Rename and Delete (`pages/iniform.py` `new_item`, `rename_item`, `delete_item`, the like in `racks.py`,
  `terrains.py`, `crops.py`, `decor.py`, `quests.py`, and `project.py` `rename_place_uses`) call `ini.save()` on the
  lines in memory. A builder run, or the other synced PC's edit, made while the editor is open is lost whole. Fix:
  check the stamp before every save, and reload and merge, or ask.
- [x] **35. The editor's writing of files** (`dsedit/project.py`). `write_text_lines` writes straight into the file,
  so a crash (or Drive syncing) mid-write leaves it cut short: write a temp file and `os.replace`. Text is encoded
  with `errors="replace"`: a character outside cp1252 is saved as "?" without a word, and a UTF-8 file with a BOM is
  read as cp1252 and saved back garbled. `ScriptDoc.load` takes a line with no tabs as an empty command (its text is
  gone on save), and `Entity.parse` makes a coordinate that isn't a number 0. (`ashen/ini.py` `write` writes in place
  too.)
- [x] **36. The editor's Move map leaves saved characters and the engine behind.** (Read, not run.) `move`
  (`dsedit/mapops.py`) renames the file and its arrival script and rewrites the name in the data files and scripts,
  but puts nothing in `RENAMED_MAPS` (`dsengine/renames.py`): a character saved on the map, and whatever a save keeps
  by map name, still names the old one (the dialog says players "will be where the map was"; the rule is that every
  rename goes in `renames.py`). The rewrite also takes the name wherever those three numbers stand in any data file
  or script (`name_re`: not after a digit or `-`, not before a digit), so a colour or a list such as `0,0,0`, or the
  end of `5,1,1,0`, would be changed too (today's files had only real uses for the names tried: a risk, not a fault
  yet). And the file is moved first and the text files rewritten one by one, so a failure partway leaves it half
  done. Fix: add the old name to `RENAMED_MAPS`, rename only in the keys and arguments known to hold a map (as
  `region.py` does for places), and move the file last.
- [x] **37. Carts.ini in the editor** (`dsedit/carts.py`). A comment line inside a route's section is dropped on save
  (the docstring says comments are kept; today's file has none inside a section). The text is split on CRLF only, so
  a file saved with LF ends is read as one line and its routes are lost at the next save. `save` writes in place and
  never looks at the file's stamp (34 and 35 again). `region.py` `update_refs` (moving an area) writes Quests.ini,
  WorldMap.ini and scripts in place too, under whatever the Quests and Scripts pages hold unsaved.
- [x] **38. Tall grass that flowers stands still all through its season.** `seasonal` (`web/js/ground.js`) keeps the
  recoloured picture by season, name and width, and every sway frame comes under the tile's one name: the first frame
  made is drawn for all of them. `Tall_Grass001` (6 sway frames, flowers in Spring) is one. Fix: the frame in the
  key (or a WeakMap on the picture itself).
- [x] **39. A redrawn sprite can go on showing as it was** (`tools/export_web_assets.py`, `server/app.py`). A swaying
  or flaming tile's frames are made again only when `Tiles.ini` or `Config.ini` is newer than they are, not when the
  sprite is (or `ashen/anim.py`): run a builder that redraws the plant and the still tile is new, its sway the old
  drawing. A sprite deleted or renamed leaves its files in `web/assets` for good. And `/assets/` is served with
  `max-age=3600` at an address with no version in it, while the manifest (the sizes) is always fresh: for an hour
  after an update a browser can draw the old picture at the new size. Fix: frames compared with the sprite's stamp
  too; files not in the manifest removed; the manifest's `version` in each asset's address (and then a long
  `max-age`).
- [x] **40. The page gives up for good on two things that fail once.** A picture that fails to load is marked `bad`
  and never asked for again until the page is loaded anew (`web/js/assets.js` `image`): one dropped request on a
  phone and that sprite is missing all session. A tune played as a sound (`web/js/audio.js` `playEffectTune`) holds
  the music off until its `ended`; if it stalls or errors, the music never comes back. Fix: forget a bad picture
  after a while; clear `AU.effect` on `error` too, and after the tune's length at most.
- [x] **41. Smaller things in the editor and the page.** Renaming a script (`dsedit/pages/scripts.py` `rename`) warns
  of the triggers that name it, not of `Goto.Script` lines in other scripts, which go on naming the old one. F5
  (`dsedit/app.py` `play`) saves every changed page without asking. In the page, `cache.blend` (`ground.js`) and
  `greyCache` (`ui.js`) are never emptied (held in check only by how many combinations there are), `hatchPattern`
  (`ui.js`) makes a new canvas and pattern every frame the world map is open, and `drawBoosts` would throw each frame
  on a boost kind it has no words for (the engine's four are all it's sent today).
- [x] **42. The editor's pages, read through.** In `dsedit/pages/maps.py`: a notice's words typed in the inspector
  are saved to its script file 0.7 s after the last key, apart from the Scripts page (so with 34, a script open there
  can go back to the older words); `map_delete` ends with `(others or self.project.maps())[0]`, which throws when the
  last map goes; `_check_refs` runs `refs.fresh()` on a thread while the window reads `self.refs`; `add_trap` replaces
  a trigger already on the tile without saying so; the lock inspector's Pick field replaces all of the lock's other
  options; `rename_everywhere` and `move_to_map` save maps as part of the action, with no undo. Quests:
  `rename_marker` saves without asking, and every script is read again each time a quest is opened. Deleting or
  renaming a quest, spell, crop or buildable doesn't say what still uses it. Racks: `rename_rack` leaves scripts
  opening the old name (it warns only afterwards), and each key typed is an undo step. `iniform`'s save sets the keys
  in memory before `extra_save`, so a save that fails leaves memory changed and the file not; the Crops page writes
  `Crop=` on the new seed without clearing it from the seed it was on. Tiles: a tile with no `Walkable.Data` loads as
  49 ones and saving writes that grid out; after Split, the palette's pictures of the tile aren't made again.
- [x] **43. Tests that can't fail, and tests that lean on each other.** `tests/test_engine.py` shares one world
  across the file, and before about line 9300 most tests put things back only at their end, not in a `finally`:
  players (`leave`), the time of day, the season, NPCs taken out of `world.ents`, `farms.clock`, a tile of 1,1,0, and
  at 7627 `enc.settings["on"]` (a throw there leaves encounters on for every later test). So one failure can set off
  others that have no fault. Some change the shared world for good: 809 never leaves "Wren", 10050 removes every
  Hobgoblin on 2,2,-2, `dark_mage()` (8051) moves a Dark Mage and doesn't move it back; 3263 leans on the test before
  it having killed the dragon. Asserts that can't fail or may not run: 303 (`... is None or True`), 5271 and 5413
  (inside an `if`), and loose `or`s at 350, 2465, 4360, 4642, 4654, 6738, 7786 and 7907;
  `test_a_river_freezes_in_winter_but_never_the_sea` freezes nothing (it checks only which waters count as rivers).
  `tests/test_server.py` defines `chats` twice (171 and 672; the second, waiting 0.6 s, is the one every test gets),
  waits by fixed sleeps in many places (0.3 s for a save, 0.5 s after `/ban`) where a poll would hold on a slow
  disk, and several tests have no `finally` round `runner.cleanup`. `tests/test_central.py`: `assert await post(...)`
  near 1302 asserts a dict (wants `["ok"]`), `assert orig` near 1550 and the `or` near 1886 are loose, the block near
  533 checks nothing, and the friends test sleeps 4 x 1 s. The editor's logic is tested only inside
  `test_engine.py`.
- [x] **44. Bryony Tarrow never says her words about the Wardens.** In `data/Scripts/Talk to Bryony_Tarrow.txt`
  line 12 is `>Conditional $Variable.1>=5 15`: from stage 5 of `ShardfallGate` on she says "It opened, did it?" for
  good, and line 15 (`Goto.Script Bryony and the Wardens`) is reached only before stage 3, by someone Nell hasn't
  sent yet. So that script's line for a player who has the Wardens' truth (`$Attr.WardensTruth=1`) is never said.
  Line 12 should send stage 5 and later to line 15 (and say "It opened" once, or leave it to that script), with the
  stranger's words kept for the stages before 3. Also small: `data/Scripts/21,5,0.txt` shows "The Wizards' Court."
  each time the map is entered, and `ashen/anim.py` `flame_frame` seeds from `hash(tile)`, which Python changes each
  run, so the flames' exported frames differ from one export to the next (never wrong, never the same).
- [x] **45. `Remove.Action.From.Queue` takes one string joined with `[TAB]`, and matches too loosely.** Its one
  argument is the whole queue entry glued with `[TAB]` (`dsengine/scripting.py` turns that into tabs), and
  `remove_action_from_queue` (`dsengine/world.py`) drops an entry if the pattern matches the whole entry, the entry
  less its due time, or just its name: so `Remove.Action.From.Queue Fire` would cancel every queued Fire on every
  map. Only `data/Scripts/Use Bucket_of_Water With Fire.txt` uses it (to cancel the burning out of a fire it puts out
  early), and it's the only use of `[TAB]`. Better: the same fields as `Add.Action.To.Queue` (action, name, type,
  misc, map, X,Y), each matched on its own, `*` for any or at the end of one (`Ripe_*`), and fields left off the end
  counting as `*`; the engine's own cancels (`player_actions.py` for stacks, `forms.py`) can use the same match
  instead of joining their own patterns. Then `[TAB]` goes: its two replacements in `scripting.py`, its line in
  `dev/Script Commands.txt`, and the editor's suggestion that builds it (`dsedit/scriptlang.py` line 172), with the
  bucket script changed and an old lone `[TAB]` argument split into fields when it's read. Also: when
  `Remove.Entity` takes a thing away, a queued REMOVE of that thing on that spot could go with it (there's nothing
  left for it to remove, and it would take a fire lit there later), so the bucket script wouldn't need the line at
  all; a queued ADD (a respawn) stays.

- [x] **46. A script line with any `$` works out every variable, whether it names it or not.** (Timed.)
  `parse_script_variables` (`dsengine/scripting.py`) builds its list of 27 replacements (shardstones active, the
  player's level, the tax due, the free slots...) with each value worked out before it looks at the text, so
  `Hello $Player.Name` takes about 31 us where plain text takes 0.1 us and `$Item.Gold >= 10` 2 us; `stones_active`
  is most of it. Every line of every script run through it once took 232 ms (18 us a line), so it's never felt in a
  tick of 50 ms, but it's waste on a phone hosting. Better: each variable a name and a function, called only when
  its name is in the text, keeping `$Player.Health.Max` before `$Player.Health` and the woman's words
  (`PLAYER_WORDS`) before the other `$Player.` ones; a test that every variable still comes out as before.
- [ ] **47. 367 of the 1,372 scripts are word for word another's.** 82 sets, all written by builders, one script
  per NPC's Id whether it differs or not: 37 of the 39 barmaids say "Sit anywhere you like, love" from
  `dev/migrate/towns.py` (line 603, a `Talk to <Id>` each), and the stalls, smiths, bakers and butchers are the same
  in up to 10 towns (`build_estforlan.py`, never run again). They cost nothing running, only clutter. The engine
  already lets them share: `find_action_script` tries `Talk to <Id>`, then `Talk to <name>` (the map's NPC name,
  `Barmaid`), so `towns.py` could write one `Talk to Barmaid.txt` and leave out the barmaids' own, and a barmaid with
  more to say keeps hers by her Id. Every Barmaid on the maps has an Id script today, so none would start saying it
  who doesn't now. The `build_estforlan.py` sets would need a migration (delete the copies, write the shared one)
  rather than that builder.
  *Not done: it would change who passes on rumours.* `gossips` (`dsengine/rumours.py`) lets a kind with `Gossip=1`
  pass on rumours only when the NPC has no `Talk to <Id>` of its own, and the guards' captain (`standing.py`) and
  talking in an animal's body (`player_actions.py`) ask for that file too. Barmaid, Butcher, Fishmonger,
  Greengrocer, Doctor, Nurse, Tailor, Cobbler, Carter, Barkeep and Old_Woman all have `Gossip=1`, but every one of
  them on the maps has an Id script (most of them these copies), so none of them gossips today. Sharing their words
  by name would have them all pass on rumours before their usual words. If they should (their `Gossip=1` says so),
  the share by name does both at once; if not, the copies can still go if the shared script is found under each Id
  (a list of Ids for one script), with the editor's Id scripts and its renames taught it too.

## Checked and sound

- (Fixing 42 and 43.) The editor's `_check_refs` thread builds its references on its own and swaps them in whole.
  The river test already freezes the river it waits on, and the lair's hobgoblins a test takes come back when
  their map is entered again (`test_the_lairs_hobgoblins_come_back_when_someone_comes_in`), so neither leans on
  another test.

- NaN, infinity and wrong-typed fields in client messages fail inside the per-player guard.
- The page escapes what it puts into HTML.
- The SQL in `server/store.py` and `server/game.py` uses `?` parameters.
- Market buys and gifts re-check stock and room.
- Thieving cooldowns, shop bans, spell cooldowns and the PvP mark survive leaving and coming back.
- Shop, bank and crafting verbs are checked again on the server, and their amounts are bounded.
- The dead can only wake or look. Chests' loot is each player's own.
- Companions and party membership are cleared on leaving.
- The tavern's limit of 10 bets an hour is saved. A body swap is undone on leaving.
- No standing lets a shop be bought from below what it pays. Enchantable gear never stacks.
- Farming and Shard Bloom ownership checks hold. A quest's Shards are paid once.
- Every chest script that gives things has a once-guard. A dropped thing picked up takes its despawn entry with it
  (no copy after a restart).
- A tile doesn't change back under a player standing on it. An open box doesn't shield a player from monsters.
- The market checks the price seen, room and its listing limits. Script file commands can't leave the game folder.
- The central server's SQL (`central/store.py`) is all `?` parameters, its writes are rolled back on an error, and
  tokens, tickets and grants are kept hashed. A ticket works once, for the server and the way in it was asked for.
- A time pass's reward counts once, and only signed by Google (`central/admob.py`). Google sign-in uses state, a
  nonce and PKCE. Passwords are scrypt, compared in constant time.
- What comes through the relay over HTTP is only the page and its files (nothing privileged is served that way).
  The Android bridge keeps everything but `goHome`, `kind` and `adFree` to the start screen. `game.zip` is
  unpacked with its paths checked.
- The start screen escapes what it puts into HTML (`esc`), and so do the game page's panels (`coinHTML`, `esc`,
  `textContent`). The client's caches are bounded (ground chunks by `CHUNKS_KEPT`, `lastImage` cleared past 600).
- On Android a purchase is given back on a new install and taken back on a refund, on the device (`Billing.java`).
- `ashen/lb.py` `safe_eval` only ever runs its own arithmetic (no `eval`), and an overflow comes back as the text.
- `tools/admin.py` makes an admin only through the DB flag.
- The rest of the page: the build panel, the game tables and the journal put text into the page through `esc` or
  `coinHTML`, or draw it on the canvas; the interface (`ui.js`) keeps no truth of its own. The lock's timing is
  clamped by the server, and the cups, dice and tune are the server's. `V.fx` stops at 60, and the look caches are
  cleared past 2,000 and 3,000.
- The editor: the decor split keeps a copy of everything it changes in `dev/Archive` and records it for the builders;
  copying a map or an area leaves off Ids and place names; a map job asks before saving and forgets undo; a page that
  isn't changed reloads a map changed on disk when it's shown; the minimap is built in the background, one build at
  a time.
- `tools/`: nothing runs through a shell, `sync_home.py` copies only what differs, `bot.py` and `browser_check.py`
  only play. `desktop/owning.py` asks Steam through its own library and `build_desktop.py` carries no secrets (data,
  maps, sprites, the page, the server and engine). `ashen/places.py` and `areas.py` read without changing anything.
- The editor's other files (`widgets.py`, `theme.py`, `icons.py`, and the pages' drawing and tools): dialogs are
  modal, the condition builder falls back to plain text for what it can't show, the decor split refuses while Maps or
  Tiles have unsaved changes and backs up first, Buildables, Crops, Spells and Quests check their fields before
  saving, and renumbering a script keeps its jumps right. A craft row in `ItemRacks.ini` that makes 1 is saved
  without its `,1` (it reads the same).
- `tools/midisynth.py`, `make_login_video.py` and `make_login_background.py`, and `ashen/anim.py`, `assets.py`,
  `cursor.py`, `entity.py`, `midi.py` and `script_language.py`: nothing but the flame seed in 44.
- The tests, read in full: most are whole play-throughs with exact numbers (gold, Shards, quest stages), and from
  about line 9300 of `test_engine.py` they put back what they change in a `finally`. `test_desktop.py` polls and
  cleans up. The test that every query keeps its values out of its text walks `central/store.py` and
  `server/store.py`; the one query made elsewhere (`server/game.py`, a fixed text with no values) is sound. They skip
  only where the data has no shop to test (two `pytest.skip`), and nothing is marked to fail.

## Not yet read

Everything the game runs is read in full: `dsengine/`, `server/`, `central/`, `desktop/`, the Android app's Java and
`ds_host.py`, the start screen, `web/js`, `ashen/`, `tools/`, `dsedit/` and `tests/`.

Left out, at the owner's word: the scripts in `dev/` (the builders and migrations of `dev/migrate/`), as no longer
relevant. Nothing about them is logged here.
