---
id: gm-challenges
title: "Challenges"
tags: [gm, challenges, pools, suspense, moves, impact-moves]
page: 104
mechanics: [push, suspense]
---
A framework to represent tasks, obstacles, enemies, and scenarios that have greater tenacity and complexity than a single action can accomplish. Challenges allow you to track progress towards them, but also proactively oppose the PCs. These can be introduced as the GM sees fit, but often alongside the Build Up suspense move. Each challenge gives the GM 2 bonus suspense to be spent on moves relating to it, and uses a task pool to represent its complexity or resilience. They can also have:
- ✱ **Traits:** Qualities they have with strong narrative impact, inflicting thorns, denying permissions, changing vantage, even occasionally prompting impact moves.
- ◉ **Moves:** Suggested impact moves they might make. These are examples, not limitations.
- ✘ **Fail state:** A trigger that signals the challenge failed, like a competing timer pool or a specific event. Fail states can also be triggered with a Lock Down impact move, cutting off any chance of success for the PCs when it feels appropriate. Consider Foreshadowing the move to give the PCs a chance to intervene and keep the action coherent.

Challenges don't always have all three. *Examples:* **8d | Navigate Channel** (✱ shark-infested waters, ✱ treacherous currents; ◉ Graze Reef, ◉ Violent Winds, ◉ Dense Fog; ✘ 6d Storm blows in) · **6d | Escaping Thief** (◉ Blend Into Crowd, ◉ Narrow Alleys, ◉ Street Musicians) · **6d | Stop the Ritual** (✘ 4d Ritual completed).

Interpret these short, evocative phrases to fit the situation. Keep your own created challenges similarly brief and flexible. Some uses:
- **Create a dangerous enemy or exceptionally tough task.** *Navigate a mountain pass. Fight the rogue wizard. Make the mayor pay up.*
- **Zoom in on pivotal moments.** *Disable a complex trap. Complete the ritual. Court the prince.*
- **Zoom out to collapse related tasks into one objective.** *Evade castle guards. Track down the criminals. Organize a mutiny.*
- **Turn a broad concept into an actionable objective.** *Restore the desecrated temple. Secure enough alliances. Atone for your sins.*

*Didact:* `didact gen run grimwild-ce.challenge` makes its task pool with its 2 bonus suspense on it: `didact do suspense spend=1 challenge=<challenge>`.
