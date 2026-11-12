---
id: gm-factions
title: "Factions and Campaign Pools"
tags: [gm, factions, campaign, pools, downtime]
page: 114
mechanics: [story-roll, faction-turn, faction-goal]
---
Track off-screen developments of major forces, creating a feeling of a living world beyond the PCs. They have:
- **Resources** that show their power and influence, like assets, traits, and relationships.
- **Goals** that show their ambitions. Track them with a timer called a faction pool, rolled between sessions or when triggered by events in the story.

When a faction pool depletes, the goal is either accomplished or they make their move against another faction, with a story roll in their favor determining how it plays out. Keep 4-6 active factions, balancing major and minor ones, with competing goals. Replace factions that are no longer relevant to the story.

**Campaign pools.** Timers that pace long-term events across sessions (*lunar eclipse, wyvern migration*). They work like faction pools but don't require faction details. Use them to signal upcoming events or remind you to reintroduce plotlines (*betrayed NPC seeking revenge*).

*Example, the Pemtown Powderkeg: Baron Prog's coffers run dry, his troops grow restless, and whispers of rebellion stir in the ranks, while Shaz's warband, the goblin horde, and the druids of the Oldgrove edge closer to confrontation.* Baron of Pemtown (tax collectors (corrupt), paying off Shaz; 4d squander treasury, 6d discipline troops) · Baron's Unpaid Troops (veterans of goblin war, Captain Morris (charismatic); 4d abandon posts, 6d depose the baron) · Druids of Oldgrove (sworn to non-interference, magical wards; 6d quiet the horrors, 8d parley with Shaz) · Goblin Horde (nomadic forest dwellers, heavily trapped territory; 4d crown the goblin king, 6d march on Pemtown) · Shaz, Orc Warlord (small, elite warband, secret Pemtown tribute; 6d subjugate the goblins, 8d subjugate the druids) · Woodland Horrors (goblin war remnants, ominous whispers; 4d troops disappear, 8d night of terror). Smaller ones: Village of Ellit (elders (wise, cautious), fine archers; 4d ask baron for help, 8d build a wall); Twisted Forest (growing eldritch roots, ancient spirits); War in the East, campaign pools only (4d war refugees arrive, 8d baron dies).

*Didact:* a faction pool is a tracker, listed on its faction as pool_1, pool_2, … (the faction generator does it): `didact track new 'March on Pemtown' --kind pool --size 6 --pool campaign --for <faction>`, then `didact set <faction> pool_3=<track>`. `didact faction turn` rolls every faction's pools; at 0d, `didact do faction-goal` (in downtime, `pool=` depletes one completely first).
