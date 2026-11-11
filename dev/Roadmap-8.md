# Roadmap, round 8: polish from playing the Isle

The owner's list of 2026-11-12, from playing the game, sorted into groups. Work down it; tick a box when it's done,
tested and committed. Group 1 comes first: a player on the Isle can be stuck without Shard Remnants (Wim won't sail
till some are absorbed).

## The owner's decisions
- **Music by place**: the Isle has its own; some towns their own (Northport, Galaith, Emberwatch, Rupert's Keep,
  Sandtown); other towns share one; outside towns its own (two to take turns); harder zones sound more dangerous.
- **Combat music** plays while fighting a creature whose attitude is Bad (never a Good or Neutral one, never a
  sparring partner), and stays 5 seconds after the fight ends.
- **Levels**: early levels come quickly and each level needs more XP than the last. Skills that rise fast today
  (cooking, woodcutting) slow down; combat speeds up.
- **Strength is renamed Attack.**
- **Messages are short.** A rule in `dev/Rules.md` (Writing): a message says what happened and what to do, no more.
- **Hover text is one line**, in the form `+25% Spell Power | +50% Debuff Resistance`: no "blow", no flourishes
  ("a blow ends it"). Every entity has a hover line of its own, separate from its examine text.

## 1. Shards (the Isle first)
- [ ] Find why no Shard Remnants appeared on the Isle, and fix it (Wim asks for `RemnantsAbsorbed`, so this blocks the
      story).
- [ ] The Shard Remnant becomes the Shard: one name, picked up into the bag and absorbed as the remnant was. (See
      "Still to decide": a Shard is a balance, never an item, today.) The old name goes in `dsengine/renames.py`.
- [ ] Absorb 5, as well as Absorb (and Absorb all?), on a stack.
- [ ] A better absorbing sound (`build_*` that makes `Absorb.wav`).
- [ ] Tests: remnants (Shards) on the Isle, absorbing 1 and 5, Wim's check still passes.

## 2. Sound and music
- [ ] The sounds in folders by kind (`sounds/ui`, `creatures`, `voices`, `ambient`, `skills`, `combat`, `music`...),
      found by name wherever they are, so `Entities.ini` and scripts keep their bare names. The builders, the editor,
      `export_web_assets.py` and the client all follow; `validate.py` checks no two share a name.
- [ ] The owner's music (`sounds/music/*.mp3`): its source and licence in `CREDITS.md` (see "Still to decide"), smaller
      files (about 60 MB today: a phone and the page download it), and the client playing mp3.
- [ ] `data/Music.ini` by place: the Isle, each town with its own tune, the rest of the towns `town.mp3`, outside
      `exploration` and `exploration2` in turn; a zone's danger picks a darker one (a new tune, or the outside one
      changed).
- [ ] Combat music (`combat.mp3`) while fighting an Attitude=Bad creature, held 5 s after; then back to the place's
      tune where it left off.
- [ ] A quieter, less triumphant quest-complete sound.
- [ ] Speech: a voice only on the first page of a conversation, and only when the player started it (not when an NPC
      speaks up or a script opens one). Slower, and better sounding (find what plays and why it's fast).

## 3. Levels and XP
- [ ] A new XP curve: each level needs more than the last, the early ones quick (every number in a data file; skills
      still go to 25). Existing characters keep their levels (their XP worked out again, never a level taken away).
- [ ] Each skill's XP looked at side by side (XP per minute of play); cooking and woodcutting slowed, combat raised.
- [ ] Stances: Cautious gives more Defence XP, Fighting more Attack XP.
- [ ] Strength renamed Attack (data, scripts, the page, `renames.py`).
- [ ] The Isle's creatures a level or two lower.
- [ ] Tests: the curve, each stance's XP, the rename read from an old save.

## 4. Combat
- [ ] Normal stance becomes **Cautious** (faster, more Defence), with forms (see "Still to decide").
- [ ] The attack looks like a sword swung: the held sword hidden, a sweep drawn, then shown again.
- [ ] Never trapped in a creature: you can always walk out of a fight (an overlapping sprite never blocks you).
- [ ] Never stuck among trees (find the places and fix the paths, or the trees).
- [ ] Clicking elsewhere before you get there cancels an attack or a verb on its way.
- [ ] Rabbits hop.
- [ ] Creatures facing up and down as well as left and right (see "Still to decide").
- [ ] Tests: cancelling a walk-to-attack, leaving a fight from inside a creature.

## 5. Quests and the journal
- [ ] "Quest objective met." in the chat when a step is done (short, with its sound, once).
- [ ] The tracked quest's arrow points the way for every step, handing in included; every quest checked for one.
- [ ] Followed quests highlighted in the journal.
- [ ] Quest complete: no "the thanks of those you helped", no "splendid"; its rewards shown with their pictures (or
      "None").
- [ ] Mary's first note ("I told him the jar was for the child") points at a jar that's nowhere in the game: write
      what it means and pay it off, or change the line.
- [ ] Tests: the objective message, an arrow for each step of each quest.

## 6. The bag, the bank and the hotbar
- [ ] Bank X: type how many. The choices follow the stack (1, 5, 10, All, X; only those it has).
- [ ] Drop X, the same way.
- [ ] No [Add to hotbar] in the right-click menu: drag to the hotbar, drag to rearrange it, drag out of the bag to drop.
- [ ] Desktop and phone (a finger's drag; a long press where a drag won't do).
- [ ] Tests: banking and dropping a typed amount, more than the stack, nothing.

## 7. Words on screen
- [ ] Every entity: a hover line (one line) and examine text, separate (`Hover.Info`? in `validate.py`).
- [ ] Every hover line to the rules above (`+25% Spell Power | +50% Debuff Resistance`; no "blow").
- [ ] A shorter death notice, and the Writing rule.
- [ ] Locks and chests say Easy, Medium or Hard on hover; the level needed only when you try and can't.
- [ ] The ferry shows no level; clicking it before you may sail opens Wim's conversation, not a chat line.
- [ ] Character creation: "This character will be saved..." on several lines.

## 8. The screen
- [ ] The Journal, Stats, Gear and Spells buttons easier to see.
- [ ] Full screen on a desktop works (the browser and the desktop app).
- [ ] The lock-picking window never changes size when a button goes; Give Up at its top right, in red.
- [ ] Cursors: a gravestone isn't the eye; the cheat cursor isn't the door.
- [ ] Meat drawn smaller.
- [ ] Checked in the browser, desktop and phone (915 x 412, both ways up).

## 9. The world
- [ ] More than one grave: each death leaves its own.
- [ ] A wooden bridge's first choice is Walk, not Examine.
- [ ] Examine on wall decor (mirrors, pictures...).
- [ ] The yellow circle doesn't flash on the stairs after you go up or down.
- [ ] The Isle chapel's downstairs drawn with proper walls, not the thick ones.
- [ ] The grass by the cliffs, and the stone that doesn't match, drawn with the grass texture (see "Still to decide").
- [ ] The ferry comes back to the same spot; the boats that never move are taken away.
- [ ] NPCs stand still while they talk to you.
- [ ] At the start (the funeral), the mourners walk away instead of vanishing.
- [ ] Tests: two graves, an NPC still while talking, the ferry's stop.

## 10. Sending the server's log
- [ ] A Send log button (on the admin page, and the app's server screen) sends the server's recent log to the
      game's email through the central server (`central/mail.py`), with what's sent shown first and a line in the
      privacy policy (a log has names and addresses in it).
- [ ] Not more than one in a while from one server; tests (`test_central.py`, `test_server.py`).

## 11. Copyright
- [ ] A copyright line (`© 2026 Hallisium. All rights reserved.`) on the start screen's About, in `CREDITS.md`,
      the README, and the store pages; a `LICENSE` saying all rights are reserved (unless the code is to be open).

## 12. Finished
- [ ] `dev/Rules.md` (Writing: short messages, hover lines; Art and sound: the sound folders, music by place, combat
      music; Creatures: stances; Skills: the curve), `dev/Story and Quests.md`, `CREDITS.md`.
- [ ] `validate.py` 0 errors, the full tests, `export_web_assets.py`, `build_minimaps.py` if maps changed, a look in
      the browser (desktop and phone), committed and pushed.

## Still to decide
- **The Shard as an item.** Today a Shard is a balance, never an item (a rule for every change), and the remnant is the
  item you absorb. Is the plan to rename the remnant "Shard" (picked up, absorbed into the balance), or for Shards to be
  carried in the bag and spent from there, which would change the rule and every Shard price?
- **Cautious**: what it costs for being faster and better defended (less damage, less Attack?), and which forms come
  with it.
- **Creatures facing four ways.** Every creature builder draws two more facings: a lot of art. The suggestion:
  start with those that walk at you (wolves, goblins, people), leaving the small ones (rabbits, rats) two-way.
- **The cliff grass.** The suggestion: draw it with the grass texture in the ground builder (it then follows the
  seasons), not decor on top.
- **The music's licence.** Where the mp3s come from. Anything not made here must be CC0 and in `CREDITS.md`; if they're
  AI-made, the service's terms must allow selling the game with them.
- **The game's email** for sent logs (an address, e.g. `DS_SUPPORT_EMAIL` on the central server).
- **Open or closed code**: all rights reserved, or a licence for the code and the art kept.
