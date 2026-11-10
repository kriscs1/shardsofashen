# Code issues found by review

Issues found by reading the code (2026-11-10), not yet fixed. Tick a box when its fix is committed, with a test.
"Reproduced" means it was run against the real engine; the rest come from reading the code.

## Worth fixing

- [ ] **1. A tile can be used from up to three screens away, through walls.** (Reproduced.) A verb on a far tile is
  queued while the player walks, and the walk's target is wherever the cursor last was. A second `verb` message with
  no target moves the cursor onto the player and returns before the queued verb is cleared
  (`dsengine/player_actions.py` `handle`, the `verb` branch; `dsengine/session.py` `update_player_walk`). "Climb
  Down" on a hatch 397 px away ran at once; "Mine" was refused only because its script checks distance itself. The
  `cast` branch sets the cursor with no bounds check at all. Fix: keep the click with the queued verb, not the live
  cursor.
- [ ] **2. A time pass can become the full game for good on one server.** At a ticket login `full:<account>` is
  stored as "1" while a pass is running (`server/game.py` `full_of`). A reload comes in by the linked device with no
  ticket: it reads that "1", has no `pass_until` and no grant, and `passes_ran_out` never asks again. Separately, if
  the central server doesn't answer `owns_now` once, `pass_until` stays 0 and the pass never ends that session. Only
  matters once `DS_DEMO=1`.
- [ ] **3. One bad NPC can freeze the whole server.** Each player's work is guarded, but `update_npcs`, the carts,
  the action queue, farms, waves and the rest of `World.tick` are not. An exception there aborts the tick, and
  `send_updates` is in the same `try` (`server/game.py` `run`), so nobody is sent anything; if the error persists it
  repeats and logs 20 times a second. `update_npcs` also leaves `self.dt` altered when `update_npc` raises. Player
  code runs in that unguarded part too: a missile landing (`world.py` `missile_arrive`: the spell's hit, the kill,
  its Kill script), the tavern's dice roll, the wonders and a wave's end (`waves.py` `finish`: the rewards and
  `On.Win.Script`). A missile also ignores levels: it follows a target that has climbed a ladder.
- [ ] **4. A mute ends when the player reloads.** `muted_until` lives only on the Session; leaving discards it and
  coming back makes a new one. `/letter` isn't counted as talking either, so a muted player can still send letters.
- [ ] **5. A trade can be switched at the last moment.** Changing an offer resets both accepts, but an "accept"
  already on its way counts for the new offer (`dsengine/together.py` `trade_msg`). Fix: the accept carries the
  offer's version, or a short lock after any change (the market already checks the price seen).
- [ ] **6. A failed save is treated as done.** `save_all` logs the exception, then clears `save_soon` and every
  `save_requested` and resets the timer. A trade's save waits up to a minute for the next try; a player who was
  leaving is never saved again.
- [ ] **13. Any friendly NPC in sight can be killed with a bolt spell.** (Reproduced: a Villager and a Cat on 1,1,0
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
- [ ] **14. A monster's respawn is lost when a same-named one stands on its spot.** (Reproduced: Cave Horror on
  -1,10,0; the queue entry finished with 1 of 2 alive.) `do_queue_entry` (`dsengine/world.py`) drops the `ADD` when
  `find_entity_at` finds a same-named entity within 24 px of the spawn point, by where it is now or where it began,
  and the entry isn't tried again: only a restart brings the monster back. 481 of the 1,784 hostile map NPCs have a
  same-named neighbour within 200 px. Fix: put the entry off a few seconds, or match by the original spot only.
- [ ] **19. A homestead's rugs are lost at every server restart.** (Reproduced: a cell `{"under": "Rug001"}` came
  back from `Homes.load` as `{}`.) `load` (`dsengine/homes.py`) keeps only a cell's `tile`, `decor` and `roof`, while
  `build` stores a rug as `under` and `make_map` draws it from there. The rug and what it cost are gone. Fix: add
  `"under"` to that tuple.
- [ ] **23. A melee monster can be killed from outside its chase area at no risk.** (Reproduced: a Hobgoblin, a
  Skeleton and three Bears died to Fire Bolt cast from 196 to 237 px, none coming any nearer.) Hit, it starts a
  fight, finds its foe outside its chase area on its next think and gives up (`dsengine/npcs.py` `update_npc`, the
  chase branch, then `npc_give_up`): it walks back, doesn't heal and is hit again. Fire Bolt reaches 256 px and a
  written spell up to 320; a default chase area ends about 7 tiles from the spawn point. Monsters that shoot do
  shoot back (their reach is tested before the area). Fix: one hurt from where it can't follow comes anyway for a
  while (a wider chase area while hurt), or backs off out of sight and heals.
- [ ] **25. A made-up Play purchase token can give the full game free.** (The address was checked with yarl, not
  against Google.) `play` (`central/bought.py`) puts the token into the address unescaped, and aiohttp folds `..`:
  a token of `../../../voidedpurchases?maxResults=3` asks
  `.../applications/<package>/purchases/voidedpurchases?maxResults=3`. Any answer of 200 with JSON that has no
  `purchaseState` counts as bought (it defaults to 0, and `acknowledgementState` to 1), and each variation is a new
  `purchases.ref`, so any number of accounts could claim it. Only matters once Play is set up and the demo is on. Fix:
  refuse a token with anything but `[A-Za-z0-9._-]` in it, and require `purchaseState` to be there (and `kind` to be
  `androidpublisher#productPurchase`).
- [ ] **26. The desktop app's bridge answers any page in its window.** `Bridge` (`desktop/app.py`) never asks
  whether the start screen is what's showing (the Android one does, with `home()`), so a remote server's page, or a
  friend's relayed game, can call `pywebview.api.state()` and read `steam_ticket`, and call `hostAs`, `stopHosting`,
  `play`, `openLink` and `set`. A hostile server could send the Steam ticket to `/api/buy` for an account of its own:
  the purchase is claimed by Steam id, so the real owner is then told it's another account's. Fix: each method checks
  the window's address is the start screen's (as Android's does), `goHome` and the carried character aside.
  `set` from a game's page can also change `central` (the start screen then signs in to someone else's central
  server: a place to take the password) and `token`. And mending 28 by just adding `Prefs.get` would let any game's
  page read the sign-in `token`, the `hostKey` and the device keys: see 33.
- [ ] **27. One friend's dropped connection can close a host's whole game to friends.** `from_host`
  (`central/relay.py`) sends the host's `m` to a friend's connection with no guard; if that connection has just
  dropped (not yet `closed`), the error leaves the host's read loop in `host`, the tunnel closes and every friend is
  put out. Fix: catch the send's errors there (ConnectionError, RuntimeError) and drop just that connection.
- [ ] **32. A game that gives another game's id is handed your device key for it, and that key is your account
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
- [ ] **33. "Copy to device" keeps nothing in either app, and says it did.** `exported` (`web/js/main.js`) calls
  `DSApp.set("carried", ...)` from the game's page and tells the player "A copy of X is on this device". On Android
  `set` and `get` answer only the start screen (`MainActivity` `home()`), so the copy is dropped, and `get` gives ""
  in your own game too. On the desktop `set` keeps it but `get` raises (item 28), so it's never offered. Fix with 26
  and 28: both bridges let a game's page `get` and `set` the `carried` key, and only that one.

## Smaller

- [ ] **7. Reset code burned on a short password.** `central/app.py` `reset` drops the emailed code before checking
  the new password's length.
- [ ] **8. No daily cap on "forgot" emails.** After six tries the wait allows one a minute for ever (about 1,440 a
  day to one mailbox), and each new code cancels the last. The per-mailbox count is keyed on the raw text, so "Bob"
  and "Bob!" count separately. (Confirmation emails are capped at 5 a day.)
- [ ] **9. Account names leak at login.** "has been deleted" and "signs in with Google" are said for a name before
  any password is checked.
- [ ] **10. God mode is shared.** It's written to `data/Config.ini` and read by every admin on entering, so one
  admin's switch is everyone's, and it changes a checked-in data file.
- [ ] **11. Stale market index.** A box index is resolved against the list as last re-sent, so a click made just as
  the board refreshes can land on a different listing; the price check catches it unless the prices match.
- [ ] **12. An odd header gives a 500.** `hmac.compare_digest` on a non-ASCII `joined` token or `X-DS-Relay` header
  raises TypeError (it only hurts the sender).
- [ ] **15. Hiring a sellsword while one is with you takes the 25 gold and gives nothing.** The gold goes before
  `companion_call` (`dsengine/together.py`), which returns silently if one is already along (or if the NPC can't be
  added), and the script says it worked.
- [ ] **16. Dragon Dice: a winner who left during the 20 seconds isn't paid.** `Tavern.roll`
  (`dsengine/tavern.py`) pays only winners whose session is there; the rest of the pot vanishes.
- [ ] **17. The bounty's day is the server's local day**, not UTC (`together.py` `today`).
- [ ] **18. Wear and the stolen mark are lost** when a stack is dropped, and in `check_saved_equipment`. After a
  restart, things lying on the ground are put back from the queue's `REMOVE` entries by name and quantity only
  (`world.py` `apply_saved_queue`), so a stolen one comes back unmarked and a worn one as new.
- [ ] **20. Coming back into the Shifting Deep after it shifted puts you inside rock.** (Reproduced: placed on a
  `Black001` tile, the player stays in it and can walk 207 px through rock to open floor.) The floors are remade
  with a new seed at each shift and at every server start (`dsengine/deep.py` `make`), and a player who left inside
  comes back at the old spot on the new floor. Fix: entering a Deep map whose seed isn't the one they left, put them
  at floor 1's stairs or the entrance. The spring thaw does the same on a smaller scale: `Seasons.tick` turns the
  ice back to water whether or not someone is standing on it (the action queue's tile changes wait for a player
  to step off; this one doesn't).
- [ ] **21. Free Homesteading XP.** `Grass001`, `Dirt001` and `Soil001` need nothing and cost no Shards, and `build`
  (`dsengine/homes.py`) gives 0.02 Homesteading for each: laid over each other in turn they level the skill for
  nothing.
- [ ] **22. A cart can be held for ever by hailing it.** `Carts.hail` holds a cart with no timetable 20 seconds at a
  time, as often as asked, by anyone, whether or not riders who've paid are aboard.
- [ ] **24. A Fire Bolt Scroll on the ground keeps off the cold.** (Reproduced: on snow at 11,22,0, not warm; one
  dropped beside the player, warm.) `warm` (`dsengine/cold.py`) takes any entity whose name starts with `Fire`,
  `Forge`, `Range`... as a fire: so are a dropped Fire Bolt or Fire Storm Scroll or Fire Ward Charm, a Ranger, the
  Forgemaster, the Forgemother and a Ranger's Cot. Fix: an Entities.ini key (`Warmth=1`) or the exact names.
- [ ] **28. The desktop app can't give back what a game page kept.** `Bridge.get` (`desktop/app.py`) calls
  `self._prefs.get(key)`, and `Prefs` has only `set`: the page's `DSApp.get` (the character carried between servers,
  `web/js/main.js`) raises AttributeError there. `Host.start` also sets `mode` to "solo" whatever it's given.
- [ ] **29. A refunded purchase keeps the full game.** `central/bought.py` asks the store once, when it's claimed;
  nothing asks again (Play's voided purchases, Steam, itch). The Android app does take it back on the device
  (`Billing.restore`), but the account keeps `full`. An admin can take it back by hand.
- [ ] **30. A game open to friends can be pestered by anyone with its id.** `/play/<id>/...` (`central/relay.py`)
  needs no sign-in. Twelve connections that never sign in fill `CONNS_MOST` and the game is "busy" to real friends
  (the game's own end has a 5-second heartbeat but no time limit for signing in: `server/game.py` `serve_ws`). And
  what's kept is keyed on the address with its query, so `js/main.js?1`, `?2`... each ask the host again and each is
  kept, up to the 200 MB. Fix: a time limit to sign in, and keep by path alone (or only the `?v=` the page uses).
- [ ] **31. A changed password leaves game servers' grants good.** `set_password` (`central/store.py`) drops the
  sign-in tokens but not the grants, and `grant_name` renews a grant at each use: a server that holds one can go on
  asking for that account as long as it likes. (A ban and a deleted account are checked at each use.)
- [ ] **34. The editor writes over a file changed on disk since it loaded it.** The Maps and Scripts pages' saves
  (`dsedit/pages/maps.py`, `pages/scripts.py`) never look at the file's stamp: only showing the page reloads, and
  only what isn't changed in the editor. The ini pages' Save does merge (`changed_on_disk`, reload, reapply), but
  their New, Rename and Delete (`pages/iniform.py` `new_item`, `rename_item`, `delete_item`, the like in `racks.py`,
  `terrains.py`, `crops.py`, `decor.py`, `quests.py`, and `project.py` `rename_place_uses`) call `ini.save()` on the
  lines in memory. A builder run, or the other synced PC's edit, made while the editor is open is lost whole. Fix:
  check the stamp before every save, and reload and merge, or ask.
- [ ] **35. The editor's writing of files** (`dsedit/project.py`). `write_text_lines` writes straight into the file,
  so a crash (or Drive syncing) mid-write leaves it cut short: write a temp file and `os.replace`. Text is encoded
  with `errors="replace"`: a character outside cp1252 is saved as "?" without a word, and a UTF-8 file with a BOM is
  read as cp1252 and saved back garbled. `ScriptDoc.load` takes a line with no tabs as an empty command (its text is
  gone on save), and `Entity.parse` makes a coordinate that isn't a number 0. (`ashen/ini.py` `write` writes in place
  too.)

## Checked and sound

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

## Not yet read

Read in full: `dsengine/`, `server/`, `central/` (the relays with it), `desktop/app.py`, the Android app's Java and
`ds_host.py`, the start screen, `web/js` `main.js`, `input.js`, `state.js` and `net.js`, `ashen/ini.py`, `ashen/lb.py`
and `tools/admin.py`.

Checked only in part: the rest of `web/js` (`render`, `ground`, `sky`, `ui`, `journal`, `games`, `audio`, `look`,
`build`, `verbs`, `mobile`, `voice` and the small ones) was searched for what it puts into HTML and for caches that
grow, not read for wrong behaviour. Of the editor, `project.py` and each page's saving were read; `pages/maps.py`'s
drawing and tools, `widgets.py`, `decor.py`, `world.py`, `mapops.py` and the other pages weren't.

Not read: `tools/` (but `admin.py`), `ashen/places.py` and `areas.py`, `desktop/build_desktop.py`, the builders in
`dev/migrate/`, and the tests.
