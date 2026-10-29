# Roadmap

The owner's to-do list (2026-10-29), put in order. Each group is built, tested (`validate.py`, `pytest`, the page in a
browser on a desktop and a phone, maps rendered and looked at) and committed before the next. A box is ticked when it's
done and committed; what's left over, or decided differently, is said beside it.

Order: small fixes first (seen at once, little risk), then what later groups stand on (attitudes, sounds, stances),
then the big systems (stealth, locks), then the world and the story (they use all of it), then speed, then the checks.

---

## 1. Quick fixes and wording

- [ ] **Farm animals leave Shard Remnants, never bones.** Chicken, Cow and Sheep: no `Bones` in `Drops=`; they get
  `Level=1` so `remnants_on_death` gives them the same chance as every beast. (A level 1 never rises: `Mob.Min.Level=2`.)
  All other animals checked the same way.
- [ ] **Passive creatures.** A third attitude, `Attitude=Passive`: can be attacked, never attacks first (rabbits, deer,
  frogs, ducks, hens, cows, sheep...). `Flees=1` still makes prey run. Good stays unattackable; Bad stays hostile.
  `validate.py` knows it; the hover and the right-click menu treat it as attackable but not a threat; sleeping isn't
  stopped by it.
- [ ] **No "Quest locked" messages.** `quests.py` quest_start_blocked stays silent: the NPC just talks as usual (the
  quest's answer isn't offered until you can take it).
- [ ] **Signs named the right way round**: `Display.Name=Smithy Sign`, `Dairy Sign`... on every `Sign_*` (the Ids stay).
- [ ] **The right-click menu says only the verb and the thing**: no "(+12 Shards)" on Dismantle, no potion effect
  (the hotbar's hover says those).
- [ ] **The dismantle confirmation** puts the Shards on their own line in their own colour: the confirm box learns
  coloured extra lines (`{text, colour}`), if it can't already.
- [ ] **Music much quieter by default** (`audio.js` musicVolume 80 -> 30; saved settings left alone).
- [ ] **The Isle forge's chimney smoke** comes out of its chimney, not inside the building.
- [ ] **A sleep cursor for beds** (drawn in the cursor builder, `cursorOfVerb("Sleep")`).
- [ ] **An NPC in the way of a pickup**: picking up a tinderbox with an NPC standing on or before it locked the player
  until the NPC moved. Reproduce in a test; reach it from beside it, or wait without freezing other actions.
- [ ] **Frogs swim only in water**: a swimmer on a land cell by the edge walks (its swim pose only on a water cell).
- [ ] **Two Jimmys**: a Jimmy and a sleeping Jimmy, then none. Find how a second one is added (entry script and
  `Add.Entity` both, or a respawn) and fix the cause; a test.
- [ ] **NPCs' kills count**: an NPC killed by another NPC (or a guard) still drops its loot and may leave remnants or
  raise a Shard Remnant. A Shard Remnant goes for every creature in its range, not only the killer.

## 2. Art: bones and burnt food

- [ ] **Bones** redrawn as a small pile of bones (a skull, ribs, long bones), not an X (`build_items.py`).
- [ ] **Burnt food is one thing**: `Burnt_Food`, a stackable heap of charred black crumbs; every `Burnt_*` is
  renamed to it in `renames.py` (old saves load), cooking scripts make it, and shops/recipes that took a burnt kind
  take it.

## 3. Sound

- [ ] **Audit every sound**: list what plays where (scripts, engine, page) and mark the high-pitched or
  computer-like ones (Denied, Click, Chat, Squeak...), harsh or repeated ones. The list goes in this file.
- [ ] **No computer sounds**: Denied becomes a soft wooden knock/thud (a closed shutter); Click, Chat and the menu
  sounds become soft parchment/wood ticks. CLAUDE.md's rule ("Denied, a computer's no") is changed to match.
- [ ] **Failure sounds fit the setting**: Fail (a lute's sigh) kept but softened and varied; Fizzle, Empty, Locked
  redone with the same voice; two or three variations of each so repeats don't grate.
- [ ] **Success sounds**: new sounds for a harvest (a soft rustle-chime), crafting done (a satisfied anvil ring / a
  stitch pull, by station), an unlock (a lock's turn and click), a shardstone woken (already `Stone_Wake`: checked), a
  quest step (soft), a gathering success different from a gathering failure. Only on the event; not every swing.
- [ ] **Frogs sound like frogs**: Croak resynthesised as a real ribbit (a pulsed low resonant call, two notes).
- [ ] **Footsteps** (with group 6): soft steps by ground (grass, stone, wood, sand, snow), heard by others nearby and
  by monsters (stealth); quieter at higher Stealth and when sneaking.

## 4. Sitting on benches

- [ ] **The jump on sitting and standing**: reproduce (a test and in the page), find whether it's the position the
  server sets (`sit_on` moves you onto the bench and back), the page's tweening, the pose, or what's sent; fix the
  cause so sitting down, waiting, standing up and walking on are smooth (the page eases to the seat and back).

## 5. The map editor

- [ ] **Every tile relationship in files**: which pieces form a set, which piece goes next to which, wall/palisade
  joins, shore diagonals... Find any still in code (`dsedit/world.py`, `tilesets`...) and move it into
  `data/TileSets.ini` (or a new file it names), so the editor reads them.
- [ ] **City walls and the like drag**: a wall set drawn by dragging, choosing ends, corners and T's itself, like the
  palisades.
- [ ] **Diagonal shores placed right**: the piece chosen from all eight neighbours, and the cells around it updated
  as well; tests for the cases that went wrong.

## 6. Stances and Stealth

- [ ] **Stances** (a button on both layouts and a key; shown top left by the health bar; a second to change, not in
  the middle of a blow):
  - **None** (travelling): as now.
  - **Fighting**: Strength and Defence up (Config numbers), more hurt by spells and their effects.
  - **Channelling**: spells stronger, wards and spell buffs last longer, resists debuffs (Weaken, Daze, Frailty);
    slower walk, lower Defence. (Not potions: potions are herbs, Shards can't touch them.)
  - **Sneaking**: shows lookouts' sight cones and the traps you've found, offers Pickpocket/Steal/Pick Lock, quieter
    steps, slower walk. Striking or casting ends it.
- [ ] **The Stealth skill** (after Homesteading in the skills' order; `renames.py`, saves, the Stats tab, its icon,
  `validate.py`).
- [ ] **Hearing**: you make noise (walking, running, fighting, doors); a monster that hears you turns to look (it
  still needs line of sight to come for you). Stealth shrinks how far you're heard and how wide lookouts see.
  Nothing hears or sees through walls.
- [ ] **Sight cones** drawn (a soft wedge, 180 degrees by default, `Sight.Cone=`) for lookouts while you sneak;
  cones narrow with Stealth.
- [ ] **Sneak attacks**: a blow on a creature that hasn't seen you does more (Config multiplier); Stealth xp.
- [ ] **Feedback**: a sound and a mark when you're seen ("!" over the creature), when you slip past a lookout, when
  you find a secret.
- [ ] **Lockpicking** on locked chests, doors and cages (the existing minigame, scaled by Stealth and the lock).
- [ ] **Traps**: hidden traps in the old dungeons (and the Deep's), found by Stealth (a roll as you come near) or
  Search; a found trap shows, can be disarmed (Stealth, xp) or walked round.
- [ ] **Secrets**: more to Search for (cracked walls, loose stones), found more easily with Stealth.
- [ ] **Pickpocket and Steal**: from townsfolk (Pickpocket) and shop shelves/market stalls (Steal), each with a
  loot table like drops; success by Stealth; caught: the guards come (a guard put down nearby, a few levels above
  you), the shop won't trade for a while. Personal: what's stolen from a person comes back to them for others.
- [ ] **Levels and xp**: every stealth action has a level and gives Stealth xp; detection, locks and traps scale with
  it.

## 7. Chests and locks

- [ ] **Every chest has a lock**, of a difficulty (`Lock=` on its map line or kind; a default by place: the Isle's
  none or easy, dungeons harder). Open: unlocked; locked: Pick Lock (Stealth level shown on hover), its key, or
  `Break Open` with a weapon (Strength; noisy, may break what's inside? no: just noisy).
- [ ] Picked locks are personal (chests are per player).
- [ ] Quest chests and anything quest-critical stay openable: either no lock or a key the quest gives; a test walks
  every chest script to be sure none needs what can't be had.
- [ ] The hover says "Locked (Stealth 12)" or "Locked" if it needs a key.

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
- [ ] Write it up in `dev/Story and Quests.md` and CLAUDE.md's story section.
- [ ] **Before leaving the Isle you must know what Shard Remnants are**: Bess won't sail until you've Absorbed some
  (Aldous's lesson done: an attribute set when you first absorb).
- [ ] Rewrite the stage texts and the people's lines along the way (`build_heir_isle.py`, `build_heir_mainland.py`,
  `build_shardgate.py`...), still discovered, never laid out.
- [ ] **A stealth part**: in The Royal Guard, Mary's notes are in the Archive's sealed vault: get in at night past the
  archive's watchmen (lookouts) and pick its lock; a test.
- [ ] The ending's choice at the King's Seam; both rewards; Jimmy as now.

## 9. The world: coasts and Galaith

(The builder rewrites every mainland map: first, it keeps the maps the owner has edited by hand, listed in a file,
and the new land meets them at their edges.)

- [ ] **Hand-edited maps kept**: a list (in `dev/World Plan.md` or a data file) of maps the builder leaves alone;
  it starts with every map changed in the editor since the last build.
- [ ] **A coastline in big strokes**: an outline of a few dozen points (a long peninsula in the south-east, a deep
  gulf on the north coast, a hooked headland by Ravensgate, a bay under the desert), smoothed to curves, then noise at
  about 150, 40 and 9 tiles. Land = inside the outline, not the plan's letters.
- [ ] **Protected**: every settlement, quest place, road and bridge on land with a margin; coastal towns keep sea on
  their coast side (ports and jetties meet water); the Isle, Wardhaven's island, Dragon Island as they are.
- [ ] **Islets and skerries** off long empty coasts.
- [ ] **The west finished**: the grey block west of the range becomes land and sea on the same outline; a **swamp**
  biome there (its ground, trees, water pools, ambient and music) with a small village of huts on stilts.
- [ ] **Galaith opened to the sea** on its west and south (the mountains there gone, a coast and a harbour), and the
  mountains on its other sides made natural (peaks of all sizes, no box).
- [ ] **Galaith in quarters**: the royal quarter walled inside the city walls (the palace and throne room), the
  nobles' quarter beside it, the merchants' quarter round the market, the commons (hovels) furthest from the royal
  quarter. Each its own streets, stone and houses.
- [ ] **The mine north of the city** (the King's Shard Seam with it; scripts' coordinates moved with it, a test).
- [ ] Render the world and each changed map after every change; look; fix; minimaps rebuilt.

## 10. Buildings and settlements

- [ ] **About half the buildings two storeys, a cellar, or both**: exterior (a taller front, a second row of
  windows) and an interior that matches (stairs where the outside says, ladders lined up, collision right).
- [ ] **Each town its own look**: a style per settlement (stone, roof colour, timber or plaster, window shape, house
  sizes), varied house to house within it.
- [ ] **Walls or fences round some towns** (Galaith's, Ravensgate's and the Keep's walls; fences and palisades round
  villages), with gates on the roads.
- [ ] **One path through a settlement**: its streets one paving from end to end, only gardens and offshoots
  different.
- [ ] **An altar in every church**: Pray (a blessing: a short boost, once a day; a sound) and Examine.

## 11. The cold

- [ ] **Cold lands hurt without warmth**: in snow lands (Frostpeak, Frosthold) health slowly drops unless you're
  warm: wearing something warm (a wool cloak, fur: new items, so wool has a use), near a fire, indoors, or after a
  warming draught (herbs). A cold mark top left; a test.

## 12. Speed

- [ ] **A performance review**: profile the server's tick (NPCs, sight, paths, sending) with many NPCs and players,
  and the page's frame (drawing the ground, decor, lights, fog, text) on a desktop and on a phone. Fix the worst first;
  numbers before and after in this file.

## 13. The checks before it's done

- [ ] New and changed sprites draw right in the editor and the game.
- [ ] Terrain joins and palisade/wall joins have no gaps.
- [ ] Map changes join the places round them.
- [ ] NPC display names, colourings and other pictures work, and nothing that pointed at them broke.
- [ ] Skills merged keep their levels and what they unlock.
- [ ] Stealth: detection, sneak attacks, locks, secrets and traps work.
- [ ] Shards, Channeling, Shardcraft, enchanting and homestead blooms balanced and consistent.
- [ ] Shardstones dormant till activated; the right words.
- [ ] Item names, the coin, quantities and skill icons right.
- [ ] Success and failure sounds play at the right times.
- [ ] The bench jump gone.
- [ ] Quests, saves, NPC talk, fighting and many players still work.
- [ ] No placeholders, old names or skill Ids anywhere a player reads.
- [ ] A summary: what was done, bugs fixed, what was decided where the list was unclear, what's left.

---

## Decisions made where the list was unclear

- "Passive" is a new `Attitude=Passive`, so `Good` (can't be attacked) and `Bad` (hostile) keep their meaning.
- Stances replace "modes": one at a time, a short change time. Channelling makes spell buffs last longer, not potions
  (the potion/spell rule).
- Chest locks are per player, like chests' loot. A chest never needs something that can't be had.
- A failed pickpocket brings a guard a few levels above the player rather than every guard in town.
- The story keeps the heir (option A) and adds the Heart of Ashen (option C); the game after the ending plays the same
  whichever choice is made.
