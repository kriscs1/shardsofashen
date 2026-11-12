# Roadmap, round 8: polish from playing the Isle

The owner's list of 2026-11-12, from playing the game, sorted into groups. Work down it; tick a box when it's done,
tested and committed.

## The owner's decisions
- **Music by place**: the Isle has its own; some towns their own (Northport, Galaith, Emberwatch, Rupert's Keep,
  Sandtown); other towns share one; outside towns its own (two to take turns); harder zones sound more dangerous.
- **Combat music** plays while fighting a creature whose attitude is Bad (never a Good or Neutral one, never a
  sparring partner), and stays 5 seconds after the fight ends.
- **Levels**: early levels come quickly and each level needs more XP than the last. Skills that rise fast today
  (cooking, woodcutting) slow down; combat speeds up.
- **Strength is renamed Attack.**
- **Messages are short.** A rule in `dev/Rules.md` (Writing): a message says what happened and what to do, no more.
- **Shards drop and fly to the Shard bar**: no Shard Remnant item any more. A Shard drops where a creature falls, and
  picked up it flies into your Shard bar (an animation) and is counted there: never in the bag (a Shard stays a
  balance, never an item).
- **Cautious replaces no stance** (the owner left it to us): the stance you're in when you've chosen none. A little
  faster and better guarded, its blows a little weaker; it trains Defence more, as Fighting trains Attack more.
- **Creatures face four ways only if they walk towards you** (wolves, goblins, people...); small animals stay two-way.
- **Cliffs are decor**, so they go on any ground.
- **Music**: the owner's tracks are royalty free; they're made smaller to be used, and we make our own as well
  (`build_music.py`) for the places they don't cover.
- **Mary's notes are interesting**: each tells something worth knowing; none points at something that isn't there.
- **Logs go to `support@hallisium.com`.**
- **Copyright**: `© 2026 Hallisium. All rights reserved.` (on the start screen and in `CREDITS.md`, done 2026-11-12).
- **Hover text is one line**, in the form `+25% Spell Power | +50% Debuff Resistance`: no "blow", no flourishes
  ("a blow ends it"). Every entity has a hover line of its own, separate from its examine text.

## 1. Shards
- [x] A dropped Shard (on the ground, its own sprite) where a Shard Remnant dropped; picked up, it goes straight to the
      balance, never the bag. The Shard Remnant item goes (`renames.py`: one carried in an old save is absorbed as it
      loads). `Remnant_Core` looked at too.
- [x] The animation: the Shard flies from where it was to the Shard bar, which counts up as it lands (desktop and
      phone layouts).
- [x] Wim's check (`RemnantsAbsorbed`) and Brother Aldous's lesson follow: Shards picked up, said the new way (`dev/Story
      and Quests.md`).
- [x] The Isle's creatures (the NPCs) drop them as everywhere else (checked: the owner saw none from them).
- [x] A better sound as a Shard reaches the bar (`Absorb.wav`'s builder).
- [x] Tests: a Shard picked up adds to the balance and nothing to the bag; an old save's remnants; Wim's check.

## 2. Sound and music
- [x] The sounds in folders by kind (`sounds/ui`, `creatures`, `voices`, `ambient`, `skills`, `combat`, `music`...),
      found by name wherever they are, so `Entities.ini` and scripts keep their bare names. The builders, the editor,
      `export_web_assets.py` and the client all follow; `validate.py` checks no two share a name.
- [x] The owner's music (`sounds/music/*.mp3`, royalty free): in `CREDITS.md`, made smaller (about 60 MB today: mono
      or a low bitrate, a loop rather than a long track, as a phone and the page download it), and the client
      playing mp3.
- [x] Our own music too (`dev/migrate/build_music.py`): the places the owner's tracks don't cover, and the darker
      zones.
- [x] `data/Music.ini` by place: the Isle, each town with its own tune, the rest of the towns `town.mp3`, outside
      `exploration` and `exploration2` in turn; a zone's danger picks a darker one (a new tune, or the outside one
      changed).
- [x] Combat music (`combat.mp3`) while fighting an Attitude=Bad creature, held 5 s after; then back to the place's
      tune where it left off.
- [x] A quieter, less triumphant quest-complete sound.
- [x] Speech: a voice only on the first page of a conversation, and only when the player started it (not when an NPC
      speaks up or a script opens one). Slower, and better sounding (find what plays and why it's fast).

## 3. Levels and XP
- [ ] A new XP curve: each level needs more than the last, the early ones quick (every number in a data file; skills
      still go to 25). Existing characters keep their levels (their XP worked out again, never a level taken away).
- [ ] Each skill's XP looked at side by side (XP per minute of play); cooking and woodcutting slowed, combat raised.
- [ ] Stances: in Cautious a share of a fight's XP goes to Defence, in Fighting to Attack (the share in
      `Stances.ini`).
- [ ] Strength renamed Attack (data, scripts, the page, `renames.py`).
- [ ] The Isle's creatures a level or two lower.
- [ ] Tests: the curve, each stance's XP, the rename read from an old save.

## 4. Combat
- [ ] **Cautious** in place of no stance (`Stances.ini` `[Cautious]`, to start: Walk 1.1, Defence 1.15, Attack and
      Damage 0.9), its button and ring, and a save in no stance loads in Cautious.
- [ ] Its forms (`build_forms.py`), taught like the others: **Sure Step** (faster still, and away from a fight
      sooner), **Shield Wall** (more Defence, slower), **Riposte** (a blocked blow sometimes answered, less Defence).
- [ ] The attack looks like a sword swung: the held sword hidden, a sweep drawn, then shown again.
- [ ] Never trapped in a creature: you can always walk out of a fight (an overlapping sprite never blocks you).
- [ ] Never stuck among trees (find the places and fix the paths, or the trees).
- [ ] Clicking elsewhere before you get there cancels an attack or a verb on its way.
- [ ] Rabbits hop.
- [ ] Creatures that walk towards you (wolves, goblins, people...) face up and down as well as left and right; small
      animals (rabbits, rats...) stay two-way. Their builders draw the two new facings.
- [ ] Tests: cancelling a walk-to-attack, leaving a fight from inside a creature.

## 5. Quests and the journal
- [ ] "Quest objective met." in the chat when a step is done (short, with its sound, once).
- [ ] The tracked quest's arrow points the way for every step, handing in included; every quest checked for one.
- [ ] Followed quests highlighted in the journal.
- [ ] Quest complete: no "the thanks of those you helped", no "splendid"; its rewards shown with their pictures (or
      "None").
- [ ] Mary's notes rewritten to be interesting (`build_wonders.py` `NOTES`): each tells something about her, the
      Pact or the place it's found in, and none points at a thing that isn't in the game (the first, "I told him the jar
      was for the child", goes).
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
- [ ] Cliffs as decor, drawn on a clear background so they stand on any ground (grass, sand, snow...), and the stone
      that doesn't match the same; the maps that use them moved over (`build_minimaps.py` after).
- [ ] The ferry comes back to the same spot; the boats that never move are taken away.
- [ ] NPCs stand still while they talk to you.
- [ ] At the start (the funeral), the mourners walk away instead of vanishing.
- [ ] Tests: two graves, an NPC still while talking, the ferry's stop.

## 10. Sending the server's log
- [ ] A Send log button (on the admin page, and the app's server screen) sends the server's recent log to
      `support@hallisium.com` through the central server (`central/mail.py`; the address its setting
      `DS_SUPPORT_EMAIL`, that one by default), with what's sent shown first and a line in the
      privacy policy (a log has names and addresses in it).
- [ ] Not more than one in a while from one server; tests (`test_central.py`, `test_server.py`).

## 11. Copyright
- [x] `© 2026 Hallisium. All rights reserved.` at the foot of the start screen (every version) and in `CREDITS.md`.
- [ ] The same on the store pages, when they're written.

## 12. Finished
- [ ] `dev/Rules.md` (Writing: short messages, hover lines; Art and sound: the sound folders, music by place, combat
      music; Creatures: stances; Skills: the curve), `dev/Story and Quests.md`, `CREDITS.md`.
- [ ] `validate.py` 0 errors, the full tests, `export_web_assets.py`, `build_minimaps.py` if maps changed, a look in
      the browser (desktop and phone), committed and pushed.

## Still to decide
- Open or closed code: all rights reserved for now; a `LICENSE` if that changes.
