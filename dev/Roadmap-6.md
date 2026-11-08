# Roadmap, round 6: choices that count, and the Mending

The owner's plan of 2026-11-08, in groups. Work down it; tick a box when it's done, tested and committed. Standing,
sides and stolen goods come first: the Mending's choices and the other quests are built on them.

## The owner's decisions
- **Standing in every town** (the Isle's village, Mirefold and the fourteen of `WorldMap.ini`), each player's own.
- **An Outlaw can buy their way back**: a fine to the town's guard captain.
- **Stolen things are marked**; only a fence buys them.
- **Stance forms stack**: six bound at most, more learnt by quests and their choices; binding a different form
  costs Shards.
- **Choices are made in the conversation itself**, said plainly ("Hand them over to Holt." / "Keep Meg's secret."),
  no "are you sure?", and they can't be undone. The journal says which way a quest went.
- **The Mending is a new cult**, not the Ashen Hand reworked. The Hand (fire, the dragon) is its hired help; the
  Mending is the Shards' own (cold, blue).
- **The Mending**; its people are "of the Mending" (an Acolyte of the Mending, Brother Hollis of the Mending), never
  a one-word name for them. Townsfolk say "the Mending folk" or "them in grey".
- **No joining the Mending**: a disguise only (the robe), with the Tithe as the temptation.
- **Its hidden hall under Shardglass Field**; **its end in Wardhaven** (open once the dragon is dead, empty till now).
- **Mary's voice**: the great Shard speaks to the heir as their mother (a lie, and the player knows it).

## What stays true
- **The main quest is never blocked**: no main-quest door asks for standing or a side, story NPCs talk even to an
  Outlaw, and Galaith's guards never turn on you before The True Heir.
- **All of it is personal**: standing, sides, endings and stolen marks. Shop stock stays everyone's; only your price
  is yours. Nothing needs a second player.
- **Every number in a data file**: `data/Towns.ini` for standing, `data/Thieving.ini` for fences, `data/Shards.ini`
  `[Mending]` for the cult's Shards.

## 1. Standing (the engine)
- [x] `data/Towns.ini`: each town's maps, its guard kind and captain, the ranks (Outlaw, Distrusted, Stranger,
      Welcome, Trusted, Honoured, from -100 to 100; everyone starts a Stranger), each rank's prices, and what each deed
      is worth.
- [x] A script's `Change.Standing TOWN AMOUNT` and `$Standing.<Town>`; `Reward.Standing=` in `Quests.ini`;
      `validate.py`.
- [x] Shops: a shopkeeper's town and your rank set your price (dearer to 25%, cheaper to 15%; selling the other way);
      an Outlaw isn't served.
- [x] Guards: Trusted, the first time you're caught in a day a guard warns you instead ("Put it back. I didn't see
      that."); Honoured, a fine instead of a chase; Distrusted, two come, sooner; Outlaw, the town's guards come for
      you on sight (the foe check, `world.py`). (A guard who's a character, with a Talk script of their own, isn't
      the watch and doesn't turn.)
- [ ] An Outlaw's town gates shut to them at night (left for later: a gate's Lock line with a `$Standing` and an
      hour condition needs the hour in conditions first).
- [x] The fine: the guard captain takes gold for your name, and you're Distrusted again.
- [x] Doors: a lock's condition `$Standing.<Town>>=45` (no new option needed); Ashford's locked house
      (11,-1,0) opens at Trusted.
- [ ] More doors that open at Trusted, one in each town, each with something behind it worth the trust (Oakhollow's
      rangers' lodge, Galaith's noble quarter...): with the towns' quests, groups 4 onwards.
- [x] What moves it: the town's quests, its raids fought off, its projects given to, its bounty hunts; caught
      thieving, seen breaking in, a hand raised to its guards. A theft nobody sees costs nothing.
- [x] The journal's Standing list; a line and a sound in the log when a rank changes ("Ashford thinks better of
      you."), never on every point.
- [x] Guards' and townsfolk's greetings by rank (`[if $Standing.Ashford>=40]`, `Banter.ini`).
- [x] Old saves: the quests already done give their standing once, as the save loads.
- [x] The admin panel's Town standing: each town with yours and its rank, set to any number.
- [x] Tests for each.

## 2. Sides and endings (the engine)
- [x] `Side=<Name>` on a kind or a map line; a script's `Set.Side.Attitude <Name> Good|Bad`, each player's own
      (in the save; `$Side.<Name>` is Good, Bad or none).
- [x] A quest's endings: which way it went kept (`Ending=<attribute>`), and its own line in the journal (`Ending1=`,
      `Ending2=`...); `validate.py`.
- [x] An NPC there only for some: `Here.After=<attribute>:<N>`, and `Gone.After=` now on NPCs too (both on objects).
- [x] Tests.

## 3. Stolen goods (the engine)
- [x] What's pickpocketed, stolen from a shelf or taken from a house's Valuables is marked stolen, and keeps its
      mark wherever it goes (the bank, the ground, a trade, a grave), like an item's wear; marked and unmarked don't
      stack. It shows when you look at it.
- [x] No shop buys it and the market won't list it; a **fence** does, for less (`Thieving.ini`). A fence or two in
      the back streets (Northport's docks, Galaith's lower town, the Keep's harbour...); Red Meg pays best, to those
      who sided with her.
- [x] Tests.

## 4. The Smugglers' Run, three ways
- [x] **Side with Holt**: lead his men into the cove and fight beside them. The Court's standing up a lot (Holt keeps its watch); the watch's
      quartermaster sells to you; the smugglers are foes; Meg is gone, for you.
- [x] **The truce** (as now): Meg's deal carried to Holt; a little standing; Meg's shop. Whoever finished it before
      has this.
- [x] **Side with Meg**: send Holt to the wrong cove. A little standing lost (Holt suspects); Meg's shop, the cove a
      hideout (a bed, a stash chest), her tunnel into Ashford (in even as an Outlaw), and Meg the best fence.
- [x] Later: **The Tide Turns** (Holt's: Meg got away; catch her for good) or **Under the Tide** (Meg's: a cargo past
      the gate guards, Sneaking). The guards' words for each.

## 5. Other choices
- [ ] **Old Hob**: his savings given back or kept move Oakhollow's standing.
- [ ] **Bandits on the Road**: the strongbox's goods back to Captain Hale (Frosthold's standing), or to Meg, if you
      sided with her.
- [ ] **The Redrock Signet**: to Ambrose (the manor his again, a place to rest), or sold to the bandits (Ambrose
      gone; the bandits at Redrock friendly to you).
- [ ] **The Chancellor's Grain** (new, Galaith, after The True Heir): the Archivist wants the ledger that shows the
      Chancellor hoarded grain while the city starved. To the captain: the Chancellor jailed, the Archivist in his
      place, bread cheaper, Galaith's standing up. Or his bribe: gold, his stores' shop, the treasury key, and the
      Archivist never trusts you again.
- [ ] **The Old Grove** (new, Oakhollow): a timber merchant wants it felled, Ranger Ash wants it kept. Felled: a
      sawmill (cheap planks). Kept: rare herbs and the rangers' lodge. The village is split: each way pleases some.
- [ ] More towns' choices as they're thought of: each town should have at least one quest that moves its standing.

## 6. Stance forms
Each stance (Fighting, Channelling, Sneaking) has forms, taught by people round the world as quest rewards, some only
on one side of a choice. The four stances stay as they are, from the start, and their buttons stay four (the story
needs Sneaking and Channelling: the Smugglers' Run, The Royal Guard, the Listening Room).

- [ ] **They stack**: every bound form of the stance you're in works at once, its numbers times the stance's and the
      others' (`Stances.ini` `[Fighting.Shieldwall]`...; what a form doesn't say is the stance's). Every number held
      within limits (`Stances.ini` `[Limits]`) so a stack can't run away. A form of another stance does nothing till
      you're in that stance: six on one stance is a specialist, two on each is all-round.
- [ ] **Six bound at most** (`Shards.ini` `[Forms]` `Most=6`). A form learnt is yours for good (`Learn.Stance
      <Stance> <Form>`, kept in the save); learnt with a place free, it's bound at once, for nothing.
- [ ] **Binding costs Shards**: at any shardstone you've activated, Bind Forms opens your forms; tick up to six. Each
      form newly bound costs Shards (`[Forms]`; unbinding is free), through `Pay.Shards`, with Shardcraft xp. A form is
      a way of holding the Shards in you, so it's bound where the Shards run.
- [ ] Shown: the Stats box (or the journal's Skills tab) lists the forms you know, which are bound and what each
      does; the stance's ring on you shows its bound forms' colours (`render.js` drawStance). The Bind Forms window
      works on a phone, both ways up.
- [ ] The forms (most are only numbers; the four marked * need code of their own):

| Stance | Form | Taught by | What it does |
|---|---|---|---|
| Fighting | Shieldwall* | Sergeant Holt (sided with him) | A much firmer guard, slower on foot; monsters near come for you before your friends |
| | Reckless | the Arena Master (the arena's wins) | Harder blows, a weaker guard; a kill gives a moment's rush |
| | Duellist | Galaith's captain (after The Royal Guard) | More blows land; a parry now and then |
| | Dirty Fighting | the bandits' chief at Redrock (the signet sold to him) | Blows that daze; a weaker guard |
| Channelling | Stormcaller | Bert (after The Shardgate) | Spells much stronger, dearer in Shards |
| | Wardkeeper | Ysolde (after The Last Watch) | Wards twice as long; drains hardly touch you |
| | Listening* | the Glass Wardens (the Listening Room) | You hear Shards: remnants, clusters and Shard secrets near you show |
| | Drinking* | the Mending (their secret kept) | Remnants absorbed from further off, and they heal you; a very weak guard; the Shards whisper |
| Sneaking | Cutpurse | Red Meg (sided with her) | Better hands for pockets, and guards look the other way more |
| | Shadow | Ambrose (the signet given back: forty years catching thieves, he knows how they're seen) | Harder to see; a harder sneak attack |
| | Ranger's Tread* | Ranger Ash (the Old Grove kept) | Quicker than Sneaking is; quieter in woods and grass; animals don't run |

- [ ] The admin panel's Stance forms: every form, ticked if you know it and bound or not (learnt or forgotten, bound
      or unbound, for nothing and past the six if wanted).
- [ ] `validate.py` (the new keys and command), tests (stacking, the limits, six at most, binding paid, unbinding
      free, a form of another stance doing nothing).

## 7. The Mending: what it is
Shards tell you what you want to hear. The Mending are those who believed them: a widow hears her husband, a sick man
hears he'll be well. They hold the Cutting was a wound and the scraps want to be whole; they don't know (or won't
say) that "whole" is the dragon. The Glass Wardens listened and never answered; the Mending answered. It sold the
Ashen Hand the Shards it fed the dragon through the wall (chapter 18). Its aim is the first cut: the King's Seam.
Kept gentle, for a twelve-year-old and still worth an adult's time, like the Glass Wardens.

- [ ] A section for the Mending in `dev/Story and Quests.md` (its quests step by step as they're built), a line in
      `dev/Rules.md` The story, and the Ashen Hand's loose thread answered.

## 8. The Mending: the engine
- [ ] The disguise: an `Entities.ini` key (`Friend.If.Wearing=Mending_Robe`) in the foe check (`world.py`), each
      player's own gear. A blow, or a spell in sight of one of them, ends it for the map, and those near come.
      `validate.py`; a test.
- [ ] A boss that takes in remnants (`Absorbs.Remnants=1`): it goes to Shard Remnants near it and heals by them, unless
      you absorb them first. `validate.py`; a test.

## 9. The Mending: art and sound (a builder)
- [ ] Grey robes with glass growing through them: the Acolyte (blows), the Cantor (spells, the Channelling stance),
      the Glassbound (a brute, more remnants), the Eldest of the Mending (the boss, more glass than man).
- [ ] The robe of the Mending, carried and worn.
- [ ] Cold blue shrine fire, the Shard Font, the great Shard, Mary's Whisper (a splinter).
- [ ] A low choir's chant and a whisper.

## 10. The Mending: places
- [ ] The hall under Shardglass Field (its way in hidden, lookouts, the sermon hall, the Font, the locked sanctum
      with the great Shard), named in `WorldMap.ini`.
- [ ] The Mending's house in a town (its shop of Shard goods, for those in the robe).
- [ ] Wardhaven taken quietly by the Mending (the Eldest's sanctum).
- [ ] The Ashwold's three shrines lit blue once The Ember Ring is done; the Hand's camp where the Mending pays it.

## 11. The Mending: the quests (`dev/migrate/build_mending.py`; takes over the Ashen Shrine scripts: `story_kit.TAKES_OVER`)
- [ ] **Cold Fire** (level 12, after The Ember Ring): the shrines relit cold and blue; sneak up on the Hand's camp
      and hear strangers in grey pay it in Shards "for the one beyond the wall".
- [ ] **The Kind Stranger** (13): a townsman's mother has gone to the Mending's house; the Shard talks to her in her
      late husband's voice. Bring proof (Cael's confession) and talk her home (the town's standing up), or leave her:
      she's in the hall later, and at the end.
- [ ] **In Grey** (15, after The Shardgate): a robe (picked from a pocket, or off a washing line); worn, they take you
      for one of them. The sermon (the road's gift remembered by name); Listen to the great Shard and it speaks to you
      in Mary's voice (`$Player.Son`). Their aim: the first cut. **The choice**: tell the guards (Ashford's and
      Galaith's standing up; the Mending's house raided and shut; the mother taken, if she's still there), or keep
      their secret (the house and its shop stay open to you in the robe).
- [ ] **The Tithe** (the same visit): into the sanctum by Shards poured into the Font (`Pay.Shards`), a picked lock
      (Stealth), or a fight (the disguise gone). The way you chose is remembered: the Eldest greets one who tithed as
      faithful (your first blow free), and doesn't know one who picked the lock.
- [ ] **The Eldest of the Mending** (20, after The Dragon of Galaith), in Wardhaven: a boss (`Boss=1`) with a choir
      of Cantors; he heals by their remnants. **The choice**: break the great Shard (the Mending scatters; a few come
      home, penitents in the towns), or keep a splinter, **Mary's Whisper** (a few Shards a day, in her voice; while
      you carry it, Unmake at the Seam is closed to you).
- [ ] Every number in `data/Shards.ini` `[Mending]`; stages, endings, markers and rumours in `Quests.ini`; tests.

## 12. The Mending: the world round it
- [ ] On the road (`Encounters.ini`): one of the Mending offers a few Shards "for nothing, friend"; taken, it's
      remembered (`MendingGift`).
- [ ] The townsfolk's talk of them (`Banter.ini`); no notice, sign or map text points to them.
- [ ] After The True Heir, the Mending raids the mine behind Galaith now and then (`Waves.ini`), only while someone's
      there.
- [ ] After Unmake at the Seam, their sermons change: the hope's gone, and some go home.

## 13. Finished
- [ ] `dev/Rules.md` (Thieving, Creatures' stances, Shared vs personal, Writing: standing, sides, endings, fences, forms), `dev/Story and
      Quests.md` (every changed and new quest), `dev/Data Formats.md` (`Towns.ini`, the new keys),
      `dev/Script Commands.txt` (the new commands).
- [ ] `validate.py` 0 errors, the full tests, `export_web_assets.py`, the minimaps, a look in the browser (desktop
      and phone), committed and pushed.
