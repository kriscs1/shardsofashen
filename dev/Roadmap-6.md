# Roadmap, round 6: the Mending

The owner's plan of 2026-11-08: a Shard cult, in groups. Work down it; tick a box when it's done, tested and
committed.

## The owner's decisions
- **A new cult**, not the Ashen Hand reworked. The Hand (fire, the dragon) is its hired help; the Mending is the
  Shards' own (cold, blue).
- **The Mending**; its people are "of the Mending" (an Acolyte of the Mending, Brother Hollis of the Mending), never
  a one-word name for them. Townsfolk say "the Mending folk" or "them in grey".
- **No joining**: a disguise only (the robe), with the Tithe as the temptation.
- **The hidden hall under Shardglass Field**; **the end in Wardhaven** (open once the dragon is dead, empty till now).
- **Mary's voice**: the great Shard speaks to the heir as their mother (a lie, and the player knows it).

## What it is
Shards tell you what you want to hear. The Mending are those who believed them: a widow hears her husband, a sick man
hears he'll be well. They hold the Cutting was a wound and the scraps want to be whole; they don't know (or won't
say) that "whole" is the dragon. The Glass Wardens listened and never answered; the Mending answered. It sold the
Ashen Hand the Shards it fed the dragon through the wall (chapter 18). Its aim is the first cut: the King's Seam.
Kept gentle, for a twelve-year-old and still worth an adult's time, like the Glass Wardens.

## 1. The story written down
- [ ] A section for the Mending in `dev/Story and Quests.md` (its quests step by step as they're built), a line in
      `dev/Rules.md` The story, and the Ashen Hand's loose thread answered.

## 2. The engine
- [ ] The disguise: an `Entities.ini` key (`Friend.If.Wearing=Mender_Robe`) in the foe check (`world.py`), each
      player's own gear. A blow, or a spell in sight of one of them, ends it for the map, and those near come.
      `validate.py`; a test.
- [ ] A boss that takes in remnants (`Absorbs.Remnants=1`): it goes to Shard Remnants near it and heals by them, unless
      you absorb them first. `validate.py`; a test.

## 3. Art and sound (a builder)
- [ ] Grey robes with glass growing through them: the Acolyte (blows), the Cantor (spells, the Channelling stance),
      the Glassbound (a brute, more remnants), the First Mender (the boss, more glass than man).
- [ ] The Mender robe, carried and worn.
- [ ] Cold blue shrine fire, the Shard Font, the great Shard.
- [ ] A low choir's chant and a whisper.

## 4. Places
- [ ] The hall under Shardglass Field (its way in hidden, lookouts, the sermon hall, the Font, the locked sanctum
      with the great Shard), named in `WorldMap.ini`.
- [ ] Wardhaven taken quietly by the Mending (the First Mender's sanctum).
- [ ] The Ashwold's three shrines lit blue once The Ember Ring is done; the Hand's camp where the Mending pays it.

## 5. The quests (`dev/migrate/build_mending.py`; takes over the Ashen Shrine scripts: `story_kit.TAKES_OVER`)
- [ ] **Cold Fire** (level 12, after The Ember Ring): the shrines relit cold and blue; sneak up on the Hand's camp
      and hear strangers in grey pay it in Shards "for the one beyond the wall".
- [ ] **The Kind Stranger** (13): a townsman's mother has gone to the Mending's house in a town; the Shard talks to
      her in her late husband's voice. Bring proof (Cael's confession) and talk her home, or leave her: a reward each.
- [ ] **In Grey** (15, after The Shardgate): a robe (picked from a pocket, or off a washing line); worn, they take you
      for one of them. The sermon (the road's gift remembered by name); Listen to the great Shard and it speaks to you
      in Mary's voice (`$Player.Son`). Their aim: the first cut.
- [ ] **The Tithe** (the same visit): into the sanctum by Shards poured into the Font (`Pay.Shards`), a picked lock
      (Stealth), or a fight (the disguise gone).
- [ ] **The First Mender** (20, after The Dragon of Galaith), in Wardhaven: a boss (`Boss=1`) with a choir of
      Cantors; he heals by their remnants.
- [ ] Every number in `data/Shards.ini` `[Mending]`; stages, markers and rumours in `Quests.ini`; tests.

## 6. The world round it
- [ ] On the road (`Encounters.ini`): one of the Mending offers a few Shards "for nothing, friend"; taken, it's
      remembered (`MendingGift`).
- [ ] The townsfolk's talk of them (`Banter.ini`); no notice, sign or map text points to them.
- [ ] After The True Heir, the Mending raids the mine behind Galaith now and then (`Waves.ini`), only while someone's
      there.
- [ ] After Unmake at the Seam, their sermons change: the hope's gone, and some go home.

## 7. Finished
- [ ] `validate.py` 0 errors, the full tests, `export_web_assets.py`, the minimaps, a look in the browser (desktop
      and phone), committed and pushed.
