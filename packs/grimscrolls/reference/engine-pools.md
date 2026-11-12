---
id: engine-pools
title: "Pools"
tags: [engine, pools]
source: the-core-engine/pools
mechanics: [pool-action, refresh, tick]
---
Diminishing pools track anything that runs out: progress, threats, resources, time. Roll the pool; dice landing 1–3 drop out. At **0d** the thing happens or runs dry. Pools usually start at 2d (short), 4d (medium), or 8d (long) — 6d sits between, for stubborn problems — and the pools a talent gives you run 2d–6d. Pools are written size-first, in italics: *3d Potions*.

- **Task pools** — effort to overcome: *6d Open the Barrow Door*, *4d Bandit Camp*.
- **Pressure pools** — trouble closing in: *6d The Guards Close In*.
- **Timer pools** — events unfolding: *8d Sunrise*, *4d The Gate Opens Wider*.
- **Resource pools** — stock running out: *4d Torches*, *3d Potions*. Use it, then roll it: the use always works, and the roll only shows how much is left. At 0d it's gone. The GM can also roll one as an impact move when losing some makes sense.
- **Power pools** — rolled in place of a stat: take the highest die as your result, then drop the 1–3s. Spark or assist dice rolled alongside stay separate — they never drop and never join the pool. If a use isn't risky, it simply succeeds — but you still roll the pool and drop the 1–3s. *4d Thrall.*
- **Bonus-dice pools** — a blessing you draw on: roll the pool *alongside* your own dice and count its best die with yours, then drop its 1–3s. *3d Courage.*
- **Linked pools** — chained phases: *6d Its Wings* + *8d The Dragon*. Beat the first to reach the second.
- **Campaign pools** — long-fuse events rolled between sessions and in downtime, faction pools among them: *8d The Thalmor Find the Shrine*.

*Didact:* `didact track new 'Bandit Camp' --kind pool --size 4`, then `didact track roll <pool>`; a power pool in place of a stat: `didact do pool-action who=<hero> pool=<pool>`.
