# Roadmap

The owner's to-do list (2026-10-29), put in order. Each group is built, tested (`validate.py`, `pytest`, the page in a
browser on a desktop and a phone, maps rendered and looked at) and committed before the next. A box is ticked when it's
done and committed; what's left over, or decided differently, is said beside it.

Order: small fixes first (seen at once, little risk), then what later groups stand on (attitudes, sounds, stances),
then the big systems (stealth, locks), then the world and the story (they use all of it), then speed, then the checks.

---

## 1. Quick fixes and wording

- [x] **Farm animals leave Shard Remnants, never bones.** Chicken, Cow and Sheep: no `Bones` in `Drops=`; they get
  `Level=1` so `remnants_on_death` gives them the same chance as every beast. (A level 1 never rises: `Mob.Min.Level=2`.)
  All other animals checked the same way.
- [x] **Passive creatures.** A third attitude, `Attitude=Passive`: can be attacked, never attacks first (rabbits, deer,
  frogs, ducks, hens, cows, sheep...). `Flees=1` still makes prey run. Good stays unattackable; Bad stays hostile.
  `validate.py` knows it; the hover and the right-click menu treat it as attackable but not a threat; sleeping isn't
  stopped by it.
- [x] **No "Quest locked" messages.** `quests.py` quest_start_blocked stays silent: the NPC just talks as usual (the
  quest's answer isn't offered until you can take it).
- [x] **Signs named the right way round**: `Display.Name=Smithy Sign`, `Dairy Sign`... on every `Sign_*` (the Ids stay).
- [x] **The right-click menu says only the verb and the thing**: no "(+12 Shards)" on Dismantle, no potion effect
  (the hotbar's hover says those).
- [x] **The dismantle confirmation** puts the Shards on their own line in their own colour: the confirm box learns
  coloured extra lines (`{text, colour}`), if it can't already.
- [x] **Music much quieter by default** (`audio.js` musicVolume 80 -> 30; saved settings left alone).
- [x] **The Isle forge's chimney smoke** comes out of its chimney, not inside the building. (Anything Layer=Over on
  a roof now shows with the roof and goes when you're under it.)
- [x] **A sleep cursor for beds** (drawn in the cursor builder, `cursorOfVerb("Sleep")`).
- [x] **An NPC in the way of a pickup**: picking up a tinderbox with an NPC standing on or before it locked the player
  until the NPC moved. Reproduce in a test; reach it from beside it, or wait without freezing other actions.
  (Found: the server picks it up fine past someone; the page couldn't click it, the person in front taking every
  click. The right-click menu now offers what's under them too.)
- [x] **Frogs swim only in water**: a swimmer on a land cell by the edge walks (its swim pose only on a water cell).
- [x] **Two Jimmys**: a Jimmy and a sleeping Jimmy, then none. Find how a second one is added (entry script and
  `Add.Entity` both, or a respawn) and fix the cause; a test. (Found: at dusk his sleeping self lay down at once
  while he walked out of the door to "go home". Now `Sleeper.Of=Jimmy`: he goes to his bed, and it shows only once
  he's in it.)
- [x] **NPCs' kills count**: an NPC killed by another NPC (or a guard) still drops its loot and may leave remnants or
  raise a Shard Remnant. A Shard Remnant goes for every creature in its range, not only the killer.

## 2. Art: bones and burnt food

- [x] **Bones** redrawn as a small pile of bones (a skull, ribs, long bones), not an X (`build_items.py`).
- [x] **Burnt food is one thing**: `Burnt_Food`, a stackable heap of charred black crumbs; every `Burnt_*` is
  renamed to it in `renames.py` (old saves load), cooking scripts make it, and shops/recipes that took a burnt kind
  take it.

## 3. Sound

- [x] **Audit every sound**: list what plays where (scripts, engine, page) and mark the high-pitched or
  computer-like ones (Denied, Click, Chat, Squeak...), harsh or repeated ones. The list goes in this file.
  Measured (strongest frequency, how pure a tone): clean electronic tones in Denied, Chat, Empty, Swap, Appear, Hail
  (2.1 kHz), Rare_Shard (2.6 kHz), Kill_Small (1.8 kHz), Cage_Open; sine "chiptune" runs in LevelUp, Quest, SpellHeal,
  Absorb, Enchant, Stone_Wake, Bloom_Harvest, Portal, Gate_Built, Anchor_Shatter, Freeze (to 4.2 kHz), Vanish,
  Remnant_Rise; harsh clicks in Click (6.6 kHz) and Darts. All but Cage_Open redone in build_soundscape.py (harps,
  lutes, wood, low bells, breath); their strongest notes now 140-940 Hz.
- [x] **No computer sounds**: Denied becomes a soft wooden knock/thud (a closed shutter); Click, Chat and the menu
  sounds become soft parchment/wood ticks. CLAUDE.md's rule ("Denied, a computer's no") is changed to match.
- [x] **Failure sounds fit the setting**: Fail (a lute's sigh) kept but softened and varied; Fizzle, Empty, Locked
  redone with the same voice; two or three variations of each so repeats don't grate.
- [x] **Success sounds** (Gather_Wood/Ore/Fish, Harvest, Cooked, Crafted on 50 scripts' success lines: success_sounds.py;
  Unlock for a key, a quest's lock or a picked one; Learn for a spell learnt): new sounds for a harvest (a soft rustle-chime), crafting done (a satisfied anvil ring / a
  stitch pull, by station), an unlock (a lock's turn and click), a shardstone woken (already `Stone_Wake`: checked), a
  quest step (soft), a gathering success different from a gathering failure. Only on the event; not every swing.
- [x] **Frogs sound like frogs**: Croak resynthesised as a real ribbit (a pulsed low resonant call, two notes).
- [x] **Footsteps** (with group 6): soft steps by ground (grass, stone, wood, sand, snow), heard by others nearby and
  by monsters (stealth); quieter at higher Stealth and when sneaking.

## 4. Sitting on benches

- [x] **The jump on sitting and standing** (Found: you sat from up to 40 px away and the page glides every move in 70
  ms, so you flew onto the bench and back. Now you walk to the seat's front first and the step on or off is eased over
  a quarter of a second.): reproduce (a test and in the page), find whether it's the position the
  server sets (`sit_on` moves you onto the bench and back), the page's tweening, the pose, or what's sent; fix the
  cause so sitting down, waiting, standing up and walking on are smooth (the page eases to the seat and back).

## 5. The map editor

- [x] **Every tile relationship in files** (TileSets.ini Kind=, Tiles.ini Joins=/Below=, Shore sets: tile_joins.py;
  only the editor reads them; the mainland builder keeps its own coast table, as it makes the maps): which pieces form a set, which piece goes next to which, wall/palisade
  joins, shore diagonals... Find any still in code (`dsedit/world.py`, `tilesets`...) and move it into
  `data/TileSets.ini` (or a new file it names), so the editor reads them.
- [x] **City walls and the like drag**: a wall set drawn by dragging, choosing ends, corners and T's itself, like the
  palisades.
- [x] **Diagonal shores placed right**: the piece chosen from all eight neighbours, and the cells around it updated
  as well; tests for the cases that went wrong. (Found: grass painted mixed - Grass001, 002, 003 - never matched, so
  no diagonal went in.)

## 6. Stances and Stealth

- [x] **Stances** (a button on both layouts and a key; shown top left by the health bar; a second to change, not in
  the middle of a blow):
  - **None** (travelling): as now.
  - **Fighting**: Strength and Defence up (Config numbers), more hurt by spells and their effects.
  - **Channelling**: spells stronger, wards and spell buffs last longer, resists debuffs (Weaken, Daze, Frailty);
    slower walk, lower Defence. (Not potions: potions are herbs, Shards can't touch them.)
  - **Sneaking**: shows lookouts' sight cones and the traps you've found, offers Pickpocket/Steal/Pick Lock, quieter
    steps, slower walk. Striking or casting ends it.
- [x] **The Stealth skill** (after Homesteading in the skills' order; `renames.py`, saves, the Stats tab, its icon,
  `validate.py`).
- [x] **Hearing**: you make noise (walking, running, fighting, doors); a monster that hears you turns to look (it
  still needs line of sight to come for you). Stealth shrinks how far you're heard and how wide lookouts see.
  Nothing hears or sees through walls.
- [x] **Sight cones** drawn (a soft wedge, 180 degrees by default, `Sight.Cone=`) for lookouts while you sneak;
  cones narrow with Stealth.
- [x] **Sneak attacks**: a blow on a creature that hasn't seen you does more (Config multiplier); Stealth xp.
- [x] **Feedback**: a sound and a mark when you're seen ("!" over the creature), when you slip past a lookout, when
  you find a secret.
- [x] **Lockpicking** on locked chests, doors and cages (the existing minigame, scaled by Stealth and the lock).
  (Chests: locks.py. Cages already had it by script; locked doors stay quest Locks, opened by their quests.)
- [x] **Traps**: hidden traps in the old dungeons (and the Deep's), found by Stealth (a roll as you come near) or
  Search; a found trap shows, can be disarmed (Stealth, xp) or walked round.
- [x] **Secrets**: more to Search for (cracked walls, loose stones), found more easily with Stealth.
- [x] **Pickpocket and Steal**: from townsfolk (Pickpocket) and shop shelves/market stalls (Steal), each with a
  loot table like drops; success by Stealth; caught: the guards come (a guard put down nearby, a few levels above
  you), the shop won't trade for a while. Personal: what's stolen from a person comes back to them for others.
- [x] **Levels and xp**: every stealth action has a level and gives Stealth xp; detection, locks and traps scale with
  it.

## 7. Chests and locks

- [x] **Every chest has a lock** (by place, data\Locks.ini; 15 of 19 now), of a difficulty (`Lock=` on its map line or kind; a default by place: the Isle's
  none or easy, dungeons harder). Open: unlocked; locked: Pick Lock (Stealth level shown on hover), its key, or
  `Break Open` with a weapon (Strength; noisy, may break what's inside? no: just noisy).
- [x] Picked locks are personal (chests are per player).
- [x] Quest chests and anything quest-critical stay openable: either no lock or a key the quest gives; a test walks
  every chest script to be sure none needs what can't be had.
- [x] The hover says "Locked (Stealth 12)" or "Locked" if it needs a key.

## 8. The story: the secret of the Shards (A with C)

The heir stays. What changes is the mystery underneath it:

- **What Shards are**: the pieces of the **Heart of Ashen**, a crystal of all the world's magic that the first king
  broke to bind the dragon (the **Breaking**). Every Shard wants to be whole again: that's why remnants go for whoever
  killed their beast, and why broken magic sinks into the Shardrealm (the Heart's hollow).
- **The Pact**: the dragon took the bargain to stay bound, its price a royal firstborn each generation, whose blood
  keeps the pieces apart. The dragon itself carries the largest piece. The King's Shard Seam is where the Heart was
  broken.
- **Mary** found the pact's price while studying at the Wizards' Court, and ran to find how it was made. Her hidden
  things are her notes, found as you go.
- **Through the chapters**: Aldous's remnants lesson hints the pieces "want to go home"; the Sunken Grimoire is the
  account of the Breaking; the Ember Ring is the pact's seal; the Shardrealm's core is the hollow where the Heart lay;
  the dragon, dying, says what it carried; the King's Seam is the ending: you choose to keep the pieces apart (the
  Binding: the Crown Shards) or bind the dragon's piece into the crown (a different reward and epilogue; the game
  plays the same after).
- [x] Write it up in `dev/Story and Quests.md` and CLAUDE.md's story section.
- [x] **Before leaving the Isle you must know what Shard Remnants are**: Bess won't sail until you've Absorbed some
  (Aldous's lesson done: an attribute set when you first absorb).
- [x] Rewrite the stage texts and the people's lines along the way (`build_heir_isle.py`, `build_heir_mainland.py`,
  `build_shardgate.py`...), still discovered, never laid out.
- [x] **A stealth part** (after group 9: it needs Galaith's new City Hall, with a vault under it): in The Royal Guard, Mary's notes are in the Archive's sealed vault: get in at night past the
  archive's watchmen (lookouts) and pick its lock; a test.
- [x] The ending's choice at the King's Seam; both rewards; Jimmy as now.

## 9. The world: coasts and Galaith

(Done as passes over the built maps, not by rebuilding the mainland: the owner's hand-edited maps are kept. The owner
chose to have Galaith redrawn.)

- [x] **Hand-edited maps kept**: a list (in `dev/World Plan.md` or a data file) of maps the builder leaves alone;
  it starts with every map changed in the editor since the last build.
- [x] **A coastline in big strokes**: an outline of a few dozen points (a long peninsula in the south-east, a deep
  gulf on the north coast, a hooked headland by Ravensgate, a bay under the desert), smoothed to curves, then noise at
  about 150, 40 and 9 tiles. Land = inside the outline, not the plan's letters.
- [x] **Protected**: every settlement, quest place, road and bridge on land with a margin; coastal towns keep sea on
  their coast side (ports and jetties meet water); the Isle, Wardhaven's island, Dragon Island as they are.
- [x] **Islets and skerries** off long empty coasts.
- [x] **The west finished**: the grey block west of the range becomes land and sea on the same outline; a **swamp**
  biome there (its ground, trees, water pools, ambient and music) with a small village of huts on stilts.
- [x] **Galaith opened to the sea** on its west and south (the mountains there gone, a coast and a harbour), and the
  mountains on its other sides made natural (peaks of all sizes, no box).
- [x] **Galaith in quarters**: the royal quarter walled inside the city walls (the palace and throne room), the
  nobles' quarter beside it, the merchants' quarter round the market, the commons (hovels) furthest from the royal
  quarter. Each its own streets, stone and houses.
- [x] **The mine north of the city** (the King's Shard Seam with it; scripts' coordinates moved with it, a test).
- [x] Render the world and each changed map after every change; look; fix; minimaps rebuilt.

## 10. Buildings and settlements

- [x] **About half the buildings two storeys, a cellar, or both** (upper_floors.py: 91 upstairs, 48 cellars,
  20 both, a dormer on the roof of each upstairs; ladders under hatches): exterior (a taller front, a second row of
  windows) and an interior that matches (stairs where the outside says, ladders lined up, collision right).
- [x] **Each town its own look** (town_looks.py: a roof and wall kind per town, four houses in five; Galaith by
  quarter): a style per settlement (stone, roof colour, timber or plaster, window shape, house
  sizes), varied house to house within it.
- [x] **Walls or fences round some towns** (village_edges.py: Oakhollow, Moorcross, Thornwick, Emberwatch, Wildwood;
  Galaith, Ravensgate and Wardhaven had walls) (Galaith's, Ravensgate's and the Keep's walls; fences and palisades round
  villages), with gates on the roads.
- [x] **One path through a settlement** (village_edges.py: every street run one paving): its streets one paving from end to end, only gardens and offshoots
  different.
- [x] **An altar in every church** (build_altars.py: 17 halls; Pray: Defence +2 a while, once a day): Pray (a blessing: a short boost, once a day; a sound) and Examine.

## 11. The cold

- [x] **Cold lands hurt without warmth** (cold.py, data\Cold.ini; Wool Hood, Wool Mittens, Fur Cap, Warming Draught:
  build_cold.py): in snow lands (Frostpeak, Frosthold) health slowly drops unless you're
  warm: wearing something warm (a wool cloak, fur: new items, so wool has a use), near a fire, indoors, or after a
  warming draught (herbs). A cold mark top left; a test.

## 12. Speed

- [x] **A performance review** (2026-10-30. The server's tick, five players in busy places, 1567 NPCs: 12.1 ms
  before, 9.2 after (of 50): only the maps someone's near walked, night worked out once a tick, doors looked at
  only near doors, the secrets kept in a list. The page: 60 fps on a desktop and a phone, its own code under 3% of
  each frame, the rest the browser's drawing and idle: nothing there worth changing yet.): profile the server's tick (NPCs, sight, paths, sending) with many NPCs and players,
  and the page's frame (drawing the ground, decor, lights, fog, text) on a desktop and on a phone. Fix the worst first;
  numbers before and after in this file.

## 13. The checks before it's done

- [x] New and changed sprites draw right in the editor and the game. (renders of every new place, the game on desktop
  and phone; an eye in the editor is still the owner's)
- [x] Terrain joins and palisade/wall joins have no gaps. (validate.py: 0 errors; the camps and town walls rendered)
- [x] Map changes join the places round them. (coast, Galaith and Mirefen rendered whole; the floors-line-up test)
- [x] NPC display names, colourings and other pictures work, and nothing that pointed at them broke. (tests; no
  console errors)
- [x] Skills merged keep their levels and what they unlock. (tests)
- [x] Stealth: detection, sneak attacks, locks, secrets and traps work. (tests; the vault's watchmen)
- [x] Shards, Channeling, Shardcraft, enchanting and homestead blooms balanced and consistent. (all in Shards.ini;
  tests)
- [x] Shardstones dormant till activated; the right words. (tests)
- [x] Item names, the coin, quantities and skill icons right. (screenshots)
- [x] Success and failure sounds play at the right times. (validate.py checks every red line names one; by ear: the
  owner's)
- [x] The bench jump gone. (test)
- [x] Quests, saves, NPC talk, fighting and many players still work. (186 tests pass; five players' tick 9 ms)
- [x] No placeholders, old names or skill Ids anywhere a player reads. (validate.py; screenshots)
- [x] A summary: what was done, bugs fixed, what was decided where the list was unclear, what's left. (given at the
  end of the work, 2026-10-30)

---

## 14. The second round (2026-10-30)

- [x] **The warnings, fixed** (143 to the few known): the Royal quarter had no gate (the palace, the Guard Captain and
  the King out of reach); the coast reshape had eaten roads (its plain ground took in Dirt) and left specks of land
  in the sea (`coast_repair.py`); the Parliament's door opened on the church's back wall (Galaith's street rows kept
  clear now); the Mirefen's beach had a channel across it; a duplicate Stone_Wall tile; stray scripts and a save.
- [x] **A look for each stance**, on whoever's in it: Fighting a red ring, Channelling a blue ring and Shard motes,
  Sneaking a crouch, a little faded.
- [x] **The tinderbox walk**: a friendly creature in the way (Bess, a cow, a hen) stopped the walk dead; now it goes
  round them (and round the step it couldn't take). A test.
- [x] **A new tinderbox**: half the size, a shut tin, a fire steel and a flint, a spark.
- [x] **Iron-bound chests** can't be broken open (only picked or keyed); **the Isle's chests are locked**, the
  easiest, and Frank tells you how.
- [x] **Carts cost 1 gold.**
- [x] **The thief's guard is seen by everyone**, after the thief alone.
- [x] **Senses by kind** (`build_senses.py`): each monster's sight cone (some all round), sight range, hearing and
  chase; all in Entities.ini. Cones and hearing work in every stance (Sneaking narrows and shows them).
- [x] **Shard essence**: creatures form out of motes with a sound when they come back, and the motes lift off when
  they die.
- [x] **Lots to steal, find and spring**: Valuables in about half the houses (129), two more secrets by every
  settlement (51 in all), traps on every monster-held level and in the wild camps (48 more).
- [x] **Chase areas** raised for most monsters (a least per kind, never lowered).

## 15. One game, alone or together (done 2026-10-30, but where noted)

**Where it stands.** The story is one person's: *you* are the true heir, Mary's child, the one Rupert crowns. But up to
five people share the world, and each of them is told the same thing. The engine already splits it well: quests,
quest doors, chests, secrets, traps you've noticed and NPC attitudes are each player's own; trees, rocks, kills, shops,
the time and the weather are shared. Where it rubs: a story boss is a shared NPC whose kill script credits only the
one who landed the blow (`Kill Galaith_Dragon`); another heir may be standing in the throne room; nothing in the
game says why there are several of you; and nothing rewards being together beyond the arena.

**The rule to keep.** *Every story moment is yours; the world around it is everyone's.* Nothing in the story ever
needs a second player; being with others makes it quicker, safer and more fun, never required.

### Phase A: the story never contradicts itself (first)
- [x] **Story set pieces are personal.** (they were: every scene's actors are `Add.Entity` after `$Attr`, each
  player's own; the shared ones are the story's bosses, credited below) Audit every chapter's scenes (the funeral, Tobias's cage, the dragon, the
  throne, the Seam): the actors in them are added for that player (`Add.Entity` after `$Attr`, as the letter and
  Tobias already are), so two heirs never see each other's Rupert crowning them. A test walks two players through
  the same scene at once.
- [x] **Bosses credit everyone who fought.** (all monsters: `fought_by`, `helpers_of`; each gets a loot roll) A story boss's Kill script runs for every player who hit it (or was hit
  by it) in the last minute, not just the killer (`player_combat` already tracks who fought). Loot stays the killer's
  for 10 s, then anyone's. A test with two players and the dragon.
- [x] **Why there are several of you, in the story.** (Aldous and Rupert, `$Players.Near`; Bert's talk is
  written by several builders, so not his) The Breaking scattered the royal blood with the Shards: everyone
  the Heart has marked is an heir by its reckoning. One line from Aldous and one from Bert, said only when another
  player is near (`$World.Players>1`), and Rupert's "the Order of Heirs" for the crowned. The single-player telling
  is unchanged.

### Phase B: together is better (the reasons to play with friends)
- [x] **Parties.** (not yet: a shardstone to a party member's stone) Invite someone (right-click a player: Invite; the journal shows the party). In a party: kills,
  remnants and quest kill-counts credit everyone nearby; you see each other on the world map and minimap; a
  shardstone can take you to a party member's last stone.
- [x] **Quest sync.** (as stages: a stage one reaches, those near at the same stage reach, with the quest's
  own things; each still sees their own copy of a scene's actors) In a party at the same quest stage, each member's personal scene shows the others in it
  (they join *your* phase, not a copy).
- [x] **Scaling, never gating.** Raids (`waves.py`) and bosses get more health and more foes for each player
  present, and a little more loot; one player alone still wins at the base numbers.
- [x] **Trading.** (as gifts each way: use an item on a player, they accept; no two-sided trade window yet) A trade window between two players (each offers, both accept), and handing an item over.

### Phase C: the shared world keeps you coming back
- [x] **Town projects.** (Northport's harbour: free travel there; Galaith's market: quicker restocks;
  Mirefold's boardwalks: a shardstone; a plaque of givers each) Galaith's quarters, Northport's harbour and the Mirefold boardwalks start half-ruined; anyone
  donates materials and gold to a project at its foreman; when it's full the place changes for everyone (a new shop,
  a shardstone, a bridge), and the foreman names who gave most. The world grows because people played.
- [x] **The town crier** (an NPC, not a sign: notices never hint) tells what's happening: a raid on Ashford, a rare
  creature seen near Frosthold, a project nearly done, who won the arena.
- [x] **Daily and weekly things to do.** (the bounty clerk's daily hunt; not yet: the weekly raid) A bounty clerk's daily hunts (one at a time, any player), the King's Seam's
  daily crowns (there already), a weekly raid that needs a crowd or a very good fighter.
- [x] **Homesteads as places to visit.** (visiting from a shardstone was there already) A guestbook at the Pocket Anchor, a gift chest friends can leave things in,
  and visiting a friend's pocket from any shardstone.
- [x] **Records.** (the Keeper of Records in Northport and `/records`; not a journal page) Secrets found (out of 51), creatures slain, arena wins, Deep floors reached: a page in the journal,
  and a hall of records in Northport's City Hall.
- [x] **Welcome back.** On login after a day or more: what happened while you were gone (your blooms grew, a project
  finished, the shop restocked), so the world feels alive between visits.

### Phase D: alone, never lonely
- [x] **NPC companions for solo play.** Jimmy can follow you once you're crowned (a cat: no fighting, finds secrets);
  a hireling from a tavern for a fight you can't manage. They step aside when real players are in your party.
- [x] **The world reacts to you.** Townsfolk greet the heir by name after the crown; a town you saved from a raid
  remembers it.

### Order and checks
A first: it fixes what's wrong now. Then parties and boss credit (B), the cheapest big win for friends. Then town
projects and the crier (C), the biggest pull to come back. D last. Each item gets a test in `tests/test_engine.py`
and both layouts checked in the browser. Players on the server: the tick stays inside its 50 ms budget at 40 players
on the PC server (17 ms average, 31 ms worst, steady); the phone host should stay at 5. So these plans don't need a
bigger server, only `DS_MAX_PLAYERS` raised where the server is a PC.

## 16. Friends, trading, records, a public server (2026-10-30)

- [x] **A friends list**: right-click a player or `/friend Name`; the journal's Friends page; told when one comes or
  goes; homestead friends are the same list.
- [x] **Bert explains the other heirs** too (his usual talk, when one's near).
- [x] **A trade window**: both offers side by side, gold too; both accept; a change undoes the accepts. One column
  on a phone.
- [x] **Records in the journal**: its own page, each record's top three and yours.
- [x] **A public server on a cloud VM**: `deploy/docker-compose.cloud.yml` (the game, Caddy, the updater),
  `deploy/cloud-setup.sh` (a fresh Ubuntu or Debian VM in one command), README-Server.md's steps; each player's own
  address behind the proxy (the password wait and the sign-up limit had all gone by Caddy's); sign-ups: a password of
  `DS_PASSWORD_MIN`, `DS_REGISTER_PER_DAY` from one address, names like Admin kept back; admins' `/kick`, `/ban`,
  `/unban`, `/bans`, `/mute`, `/unmute`.

## 17. Passwords, the app's first screen, names (2026-10-30)

- [x] **A forgotten password, reset by the player**: a recovery code at sign-up (and a new one in Options), the login
  screen's "Forgotten your password?". No email: a server would need one set up to send it.
- [x] **The app opens on Play alone or Play with others**: alone, a world of your own on the phone (closed to the
  network); with others, host one for the network (named), the network's games by name, or an address.
- [x] **Every game has a name**: on the login screen and in the app's list; the host renames it in Options.

## Decisions made where the list was unclear

- Every NPC an NPC kills leaves its loot for anyone (no killer's 10 s), and a Shard Remnant rising from it goes for
  the NPC that killed it. A Shard Remnant goes for any creature that can be fought (`Hunts=All`), not townsfolk or a
  quest's named ones.
- Farm animals' remnants: they're level 1, so they leave Shard Remnants now and then but never rise as one.
- A sound with takes (Fail, Fail_2, Fail_3) is picked at random by the page; Denied has two.
- Stances change with the round button by your health (or Q), and take a second. Channelling never touches potions.
- A guard who comes for a caught thief is that player's own (no one else sees them) and goes after two minutes or
  when they're left behind; the town's other guards stay friendly.
- Chest locks are by place (Locks.ini), not written into the maps (the mainland's maps are rebuilt), and Break Open
  (Strength, loud) is always there besides Pick Lock (Stealth), so no chest is out of reach. Locked doors stay quest
  Locks: picking them would skip the story.
- Traps and secrets you've noticed, and chests you've unlocked, are your own; unlocked chests are saved, noticed
  traps are forgotten when you leave (they're easy to notice again).
- Galaith redrawn by lifting every building whole and setting it down in its quarter (no townsperson renumbered,
  every script still works); the coast reshaped on the maps as they are (only wild ground and open sea). The swamp is
  the Mirefen, its hamlet Mirefold (huts on boardwalks), reached along the beach round the West Range's north end.
- Signs keep their Ids (Sign_Smithy...): only their Display.Name changed, so no script or map needed touching.

- "Passive" is a new `Attitude=Passive`, so `Good` (can't be attacked) and `Bad` (hostile) keep their meaning.
- Stances replace "modes": one at a time, a short change time. Channelling makes spell buffs last longer, not potions
  (the potion/spell rule).
- Chest locks are per player, like chests' loot. A chest never needs something that can't be had.
- A failed pickpocket brings a guard a few levels above the player rather than every guard in town.
- The story keeps the heir (option A) and adds the Heart of Ashen (option C); the game after the ending plays the same
  whichever choice is made.
