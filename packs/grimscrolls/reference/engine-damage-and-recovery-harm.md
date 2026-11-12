---
id: engine-damage-and-recovery-harm
title: "Damage & Recovery: Harm"
tags: [engine, damage-and-recovery]
source: the-core-engine/damage-and-recovery#harm
mechanics: [harm, dropped, end-story, bleeding-out]
---
- **Harm** — the serious ladder:
  - **Bloodied** — pressing physical damage (or stacked marks to Brawn or Agility): +1t on physical rolls.
  - **Rattled** — pressing mental damage (or stacked marks to Wits or Presence): +1t on mental rolls.
  - **Desperate** — a second bloodied, or a second rattled, puts you here: +1t on *everything*. You're running on fumes.
  - **Dropped** — harm that would make you desperate a second time takes you out of the scene: once you're desperate, a bloodied or rattled you already carry drops you (one you don't carry yet just fills its box). Make a story roll (usually 2d): perfect, you're just out until the scene ends; messy, it costs you (a condition — *4d Bleeding Out*, a broken arm, a disease); grim, it's dire — a permanent condition, or the end of your story: **sacrifice** (one last automatic action, then the bards take over), **retirement** (bow out soon — if you're dropped again first, you die), or another end you choose. Long-term and permanent changes to your hero — including death — are always yours to call.

*Didact:* `didact do harm who=<hero> kind=bloodied` (deadlier lethality's Bleeding Out comes with desperate: `didact do bleeding-out who=<hero>`); `didact do dropped who=<hero>`; `didact do end-story`.
