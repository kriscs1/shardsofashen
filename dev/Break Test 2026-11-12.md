# Shards of Ashen: break test, 12 November 2026

**Since the test:** every finding is fixed (commit `9b64a1a1`, 13 November) but three, which are left for later on
purpose: PERF-06, PERF-13 and part of SEC-01. They're in `dev/Code Issues.md`, under "Left for later". That commit's
message names only the later fixes; the earlier ones (MP-01, MP-03, GP-01 to GP-07, GP-09) went in with it.

Four specialist testers worked on it (gameplay, multiplayer, security, performance; they're defined in
`.claude/agents/`), at commit `f519397d`, against scratch databases. None of them changed the game. Their scripts and
logs were in that session's scratch folder and aren't kept. The full suite passed (541 tests) before they began, and
560 after the fixes.

**Status words:**
- **Reproduced**: a script showed it.
- **Measured**: numbers were taken.
- **Suspected**: from reading the code only.

---

## A. Every finding

| ID | Area | How bad | What was wrong | Now |
|---|---|---|---|---|
| MP-01 | Logins | Critical | Two tabs logging in as a character at the same moment left a "ghost" connection. It still moved and chatted as them after they'd left, and its `quit` wrote an old save over the newer one, so items could be duplicated. (Reproduced) | Fixed: the connection that's in takes the session before any wait |
| GP-01 | Isle main quest | Critical | Closing Aldous's talk, dying or logging out before his script reached the gift lost the Lair_Key for good: chapter 3 couldn't be finished. (Reproduced) | Fixed: a script that's given or set something is finished, whatever cuts it short |
| GP-02 | Isle main quest | Critical | The same with Edwin: the cellar key and the draughts were lost, and chapter 4 was stuck. (Reproduced) | Fixed, as GP-01 |
| PERF-01 | Server CPU | Critical | Spamming "Walk here" cost 20 to 25 ms of path-finding a click: one player could freeze the world for 10 s and more. (Measured) | Fixed: one walk plan at a time (`WALK_PLAN_GAP`) |
| GP-03 | Bag and quests | High | Quest items given into a full pack went on the ground, where they vanished after 180 s or someone else took them. (Reproduced) | Fixed: the Quest pouch. `Quest=1` items take no pack room and can't be dropped |
| MP-02 / PERF-08 | Saves | High | Every join, leave, trade or gift saved every player, packing all their explored maps again: 0.8 s at 50 players, 23 s when 45 logged in at once. (Measured) | Fixed: packed fog is kept, and an unchanged character isn't written again |
| MP-03 | Ferry | High | A dropped connection mid-crossing left you standing on the water, unable to move. (Reproduced) | Fixed: a rider is saved, and set down, at the stop they're going to |
| PERF-02 | Server CPU | High | Sending "explored" over and over took more than half the tick's 50 ms for everyone. (Measured) | Fixed: a budget of fog checks a player |
| PERF-03 | Logs and disk | High | A wrong Origin header, with no login, wrote 403 MB of log in 20 s. (Measured) | Fixed: logged once an address |
| PERF-04 | Server pauses | High | The garbage collector stopped the server for about 36 ms every few seconds. (Measured) | Fixed: `gc.freeze()` once the world's loaded (0.4 ms) |
| PERF-05 | Server CPU | High | Each player's view worked out chest locks and who may fight again for every viewer, every tick: the main cost at 50 players. (Measured) | Fixed: once a tick, shared |
| GP-04 | Skills | Medium | Most skills stopped at 24: rounding in the XP curve never reached 25. (Reproduced) | Fixed |
| GP-05 | Isle main quest | Medium | Chapter 4's rescue could be skipped: the barrel and the loose floorboard had no `FatherFreed` check. (Reproduced) | Fixed |
| GP-06 | Death | Medium | No grave was laid when you woke on the map you died on. (Reproduced) | Fixed |
| SEC-01 | Lock picking | Medium | The page was sent every pin's timing and the server trusted the page's clock, so a crafted client opened a level-5 lock 25 times out of 25. (Reproduced) | Partly fixed: pins still to come are hidden. See section B |
| SEC-02 | Limits | Medium | A made-up `X-Forwarded-For` got round the new-character and connection limits (9 new characters out of 9). (Reproduced) | Fixed: without a declared proxy, a connection counts as its own address |
| PERF-06 | Server CPU | Medium | Loops over the whole world every tick, and creatures' thinking grows with the maps players are on. (Measured) | Left for later. See section B |
| PERF-07 | Network | Medium | The whole quest list (38 KB) was sent again on any change. (Measured) | Fixed: only what changed |
| PERF-10 | Phone host | Medium | An app's own game took 8 MB messages from every player, not just the host. (Suspected) | Fixed: 8 MB only from the host's own device |
| GP-07 | Cooking | Low | A death or logout mid-cook lost the ingredients (the Herbalist the same, suspected). (Reproduced) | Fixed, as GP-01: what's on the fire is cooked |
| GP-08 | Talks | Low | Examining an item in the bag mid-talk let the NPC walk off. (Reproduced) | Fixed |
| GP-09 | Rewards | Low | Frank's and Morrow's rewards could be lost the same way as GP-01. (Suspected) | Fixed, as GP-01 |
| MP-04 | Gifts | Low | A gift was taken with one free slot and the rest went on the ground (10 swords, 1 slot: 9 on the ground). (Reproduced) | Fixed: you take what fits, the giver keeps the rest |
| SEC-03 | Messages | Low | NaN, infinities and `null` in clicks, the hotbar and building failed with a full traceback in the log. (Reproduced) | Fixed: `page_xy`, and `lb.val` gives 0 for them |
| SEC-04 | Messages | Low | A deeply nested message (30,000 brackets) dropped the connection with a traceback. (Reproduced) | Fixed: `auth.read_message` |
| PERF-09 | Send log | Low | Asking for the Send log over and over sent huge amounts. (Measured) | Fixed: once every 5 s a page |
| PERF-11 | Memory | Low | `encounters.next_for`, `banter.next_for` and `world.failed` kept an entry for every character that ever joined. (Measured) | Fixed: cleared on leaving |
| PERF-12 | Memory | Low | Map region lists used more memory than they need (about 10 MB over 400 maps). (Measured) | Fixed: arrays |
| PERF-13 | Network / CPU | Low | Compressing the messages (permessage-deflate) costs CPU: 49% against 38% at 50 players. Worth keeping: it takes 17.9 KB/s a player down to 3.5. (Measured) | Left as it is |
| PERF-14 | Ping | Low | The ping shown included up to a tick of waiting (47 ms on this machine). (Measured) | Fixed: answered at once |

Smaller things the testers suspected from the code, all fixed with the rest:
- `quest_giver_at` could point a quest marker at another player's own NPC.
- Party sync skipped a member busy in a script, who then stayed at the old stage. They're synced when it ends.
- A 21st queued script was dropped silently. It's logged now.
- `pickup_map_item` didn't check again that a `Once=` item was still there for you. It does now.

## B. Left for later

**PERF-06: finding things by map.** The server keeps every creature and object (about 3,750) in one list. Each tick
it goes through the whole list to sort things by map: `npcs.py` (`by_map`), `view.py` (`ents_by_map`), and
`world.py` `update_object_blocks`, once for each map where something that blocks changed. That's about 1.7 ms a tick
on this PC (0.87 + 0.80), whether 1 player is on or 5.
- **What does grow with players:** creatures think only on maps near a player. Five players on five maps wake five
  neighbourhoods. With 50 on separate maps, a tick took 12.1 ms and creatures' thinking was 45% of it, mostly
  `entity_can_stand` and `npc_walk_to`. A map index doesn't change that part.
- **The fix:** keep things indexed by map as they move. It's left because every way something changes map has to keep
  the index right: stairs, doors, ferries, respawns, spawns, deaths, summons, teleports. A missed one makes a
  creature invisible, or impossible to hit, on its new map.
- **When to do it:** if a phone host's ticks start running late (a phone was estimated to run out of budget at
  10 to 15 players), or the world grows a lot. Do cheaper creature path-finding at the same time.

**SEC-01: lock picking can't be made bot-proof.** The pin being picked has to be drawn, so the page knows its timing.
Since the fix, the pins still to come are sent only as `{}`, the pins already set only as their band, and the server's
own clock judges each tap (within `TAP_LAG`, 400 ms). A bot can still time the one pin it sees. The lock's level, and
the Stealth it needs to begin, still apply.

**A lower rate for clicks** (suggested with PERF-01) wasn't done: one walk plan at a time already takes the cost away.

## C. What held up

- **The economy:** bank and drop amounts (1, 5, 10, All, X, and nonsense numbers), trades, the market, the tavern's
  games and the fares.
- **Server safety:** admin rights, moderation and file paths.
- **The world:** graves (their privacy and the five-grave limit), the talk hold, the funeral at different stages, quest
  pointers and the reward window.
- **Joining:** the level-5 demo and its border, the player cap (10 at once on a cap of 5: 5 in, the rest told it's
  full), and duplicate messages (6 drops in one burst ran once).
- **Crashes:** a crash rolls everything back together, with nothing lost or duplicated.
- **Running long:** no memory leak over 10 minutes (207 MB, flat), and 60 frames a second on a desktop and a phone.

## D. Scale (before the fixes)

- **Tick time:** 4, 8 and 19 ms at 5, 20 and 50 players, out of 50 ms.
- **Data a player:** about 2 to 3.5 KB/s after compression.
- **A phone host:** estimated to run out of budget at 10 to 15 players.
