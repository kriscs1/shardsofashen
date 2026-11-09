# Every spell

Every spell in the game: the level to learn it, where to find it, what it does, and what it costs. Update this when a
spell, its scroll, or where it's found changes. The numbers come from `data/Spells.ini` and the `Upgrade` sections of
`data/Shards.ini`.

- **Level** is the Channeling level needed to learn the scroll. A higher rank's Level is only that requirement: your
  chance to cast it uses rank 1's Level.
- **Shards** is the cost at Channeling 1. Each level past 1 takes 1.5% off, up to 30% off, and never below 1 Shard.
  Each level past 1 also adds 5% to the damage.
- **Prices** are a shop's `Value` × `Buy.Rate` (Bert and the Mending sisters charge 1.2), before standing changes it.
  A scroll that a quest gives or a chest holds is never for sale (`Value=0`, and `validate.py` checks that).
- Bert's shop is upstairs in the Wizards' Court (map 21,5,1).

| Spell | Level | Where to learn it (cost) | Effect | Cooldown | Shards |
|---|---|---|---|---|---|
| Fire Bolt | 1 | Bert, Wizards' Court: free the first time you talk to him | 2–5 damage, 8 tiles | 1.5 s | 3 |
| Grasp | 1 | Brother Aldous, the Isle's catacombs (Amulet of Succession): free, and you keep the scroll | Fetches a thing within 6 tiles | 2 s | 2 |
| Teleport Home | 3 | Bert, 264 gold; 2 in each of the Northport and Galaith Trusted chests | Home to the Isle | 60 s | 12 |
| Fire Bolt II | 4 | The Steward's Hunt (the Steward, King Rupert's Keep) | 4–9 damage | 1.4 s | 4 |
| Ice Bolt | 5 | On the floor of a cave under the Redrock Hills (map 15,18,-1) | 2–6 damage, slowed to 50% for 8 s, 8 tiles | 3 s | 6 |
| Swap | 5 | Pip, Wizards' Court: The Invisible Apprentice (after Passage to the Mainland), and again in his spectacles errand | Swap bodies with a creature or person within 5 tiles for 30 s | 90 s | 8 |
| Frost Nova | 6 | Magister Quill: The Shard Scholar (bring 15 Shards) | 2–5 damage within 3 tiles, frozen 5 s | 8 s | 15 |
| Homestead | 6 | A Settler (Ashford, Greyford, Wardhaven, Galaith, and map -6,4,0), 340 gold | To your homestead | 90 s | 12 |
| Silence | 6 | Bert or a Mending sister, 408 gold | Fights make no sound for 30 s | 60 s | 6 |
| Grasp II | 6 | Bert, 408 gold | Grasp's reach is 10 tiles | 2 s | 3 |
| Shard Ward | 7 | Bert or a Mending sister, 456 gold; 2 in the Wizards' Court Trusted chest | +5 Defence for 60 s | 60 s | 10 |
| Fire Bolt III | 8 | The Barrow King (the Gravekeeper near the Keep; level 8, after The Withering Wood) | 6–12 damage | 1.3 s | 5 |
| Dread | 8 | Redrock Manor's vault, Redrock Hills | 1–2 damage, the foe flees for 6 s (not bosses), 7 tiles | 20 s | 7 |
| Ice Bolt II | 9 | The Sunken Grimoire (the Scholar, Dunerest) | 4–10 damage, slowed to 35% for 10 s | 3 s | 8 |
| Thunderclap | 9 | Bert, 552 gold | 4–9 damage within 4 tiles, stunned 2 s | 10 s | 18 |
| Lightning | 10 | The stone circle's chest on the Isle | 10–20 damage, 10 tiles, leaps to 1 more foe at half damage | 2 s | 10 |
| Frost Nova II | 11 | Bert's Three Treasures | 3–8 damage within 4 tiles, frozen 7 s | 8 s | 18 |
| Blizzard | 13 | Bert, 744 gold | 6–12 damage within 5 tiles, frozen 4 s | 15 s | 25 |
| Lightning II | 14 | The Ember Ring (the Warden, Emberwatch; level 10) | 14–28 damage, 12 tiles, leaps to 2 more | 1.5 s | 13 |
| Fire Storm | 15 | A chest in the Cinder Peaks (map 25,11,0) | 9–18 damage within 5 tiles | 18 s | 30 |
| Fire Storm II | 20 | The Dragon of Galaith (Bert; level 20, after The Deep Anvil) | 14–28 damage within 6 tiles | 18 s | 36 |
| Your own spell | — | Quill's The Spellwright, then the lectern in the Court's great hall | A bolt, burst, frost, mire or ward, as you design it | as designed | as designed; 10 to rewrite |

The demo (the Isle) has Grasp and Lightning. Lightning needs Channeling 10 to learn.
