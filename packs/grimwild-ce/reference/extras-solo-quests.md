---
id: extras-solo-quests
title: "Solo Rules: Quests and Peril"
tags: [extras, solo, quests, pools, experience]
page: 194
mechanics: [experience]
---
These are large-scale adventure goals that are broken up into smaller story arcs represented by task pools. These pools are linked, and used to track their progress. The number and size of the pools vary based on the quest difficulty (*a daunting quest is 4d+4d+6d*). When you make meaningful progress towards an arc, roll that pool. When a task pool reaches 0d, the fiction changes as you get closer to completing the quest. Most task pools are locked behind the first, though some quests may have goals that can be completed in any order. Completing each story arc awards 1 XP, +1 bonus XP for completing the quest.

Each quest also has **peril**, linked pressure pools to represent your antagonists' plans. There should be 1 fewer pool for peril than for the quest. The pool is triggered when the threat is ignored, significant time passes, or you suffer a meaningful failure at a critical moment while on the quest (often a disaster). Similar to challenges, quests may also have a fail state—a single break point that ends the quest. If the peril pools empty to 0d, or if the fail state occurs, the quest ends with the antagonists getting their way.

**Quest difficulty:** trivial 4d · moderate 4d+4d · daunting 4d+4d+6d · epic 4d+4d+6d+6d · legendary 4d+4d+6d+6d+8d.

*Examples:*
- *Cure the Plague — quest: 4d Find Witch of Thadia, 4d Gather Odd Reagents, 6d Defeat Dark Source; peril: 4d Law Breaks Down, 4d District Risen as Undead.*
- *Save the Galliad Kingdom — quest: 4d Find the Heir, 4d Secure Passage, 6d Defend Stronghold, 6d Drive off Orcs; peril: 4d Orcs Cut Supply Lines, 4d The Siege Begins, 6d The Stronghold Falls; ✘ The Heir Dies.*
- *Enjoy the Fall Festival — quest: 4d Help Festival Goers, 4d Put on a Good Show; peril: 4d Townies Get Bored; ✘ Chaos in the Streets.*

*Didact:* a quest and its peril are linked pools: `didact track new 'Cure the Plague' --kind pool --linked 4+4+6 --pool task` and `didact track new 'Plague peril' --kind pool --linked 4+4 --pool pressure`.
