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

## Not yet read

`central/store.py`, the relays, the desktop and Android apps, the editor, and most of `web/js`. The engine (`dsengine/`) has
now been read in full.
