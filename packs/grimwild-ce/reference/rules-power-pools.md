---
id: rules-power-pools
title: "Power Pools"
tags: [core, pools, talents, magic]
page: 19
mechanics: [pool-action]
---
This pool tracks an ability which diminishes with use. If the use of this pool isn't risky, the action is always successful, but the pool is still rolled to remove dice. If you add extra dice (such as spark) to a power pool, track them separately—they don't affect dropped dice and don't add to the pool. Bonus dice pools (p. 55) are special power pools that are added in addition to the original roll. Roll this pool as an action roll in place of a stat: take the highest die as the action's result, then remove dice with a 1–3 result as normal. *8d Blasting Wand | 6d Healing Rite | 4d Clever Disguise.*

*Didact:* `didact track new 'Blasting Wand' --kind pool --size 8 --pool power`; roll it as an action roll with `didact do pool-action who=<pc> pool=<pool>` (spark=1 rolls along and never drops; drop=1 for a potent spell), or just roll it with `didact track roll <pool>`.
