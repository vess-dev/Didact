---
id: rules-diminishing-pools
title: "Diminishing Pools"
tags: [core, pools]
page: 18
mechanics: [push]
---
A group of d6s used to track progression towards a narrative event, like completing a task, encountering a threat, depleting a resource, or passing time. When the pool is triggered, roll all dice in the pool and remove those that land with a 1-3 result. Once the pool drops to 0d, its event comes to pass and the pool is discarded.

Pools usually start at 2d/short, 4d/medium, or 8d/long. Make sure to reflect the fiction—if a pool and the fiction don't match up, adjust or scrap the pool.

If no dice are dropped from a task pool, you can either push or pivot your action:
- **Push** yourself (take a mark) to drop 1d anyway. This has a much greater effect on small pools. *Through gritted teeth, you break the blade lock and leave a fresh cut on his cheek.*
- **Pivot** to gain a secondary effect, the effects of a perfect on a different, but related roll, instead. *He's prepared for a cross cut, so instead you switch it up and twist the saber from his grasp.*

Similarly, if no dice drop from any other pool, the GM can spend suspense (p. 96) to drop 1d anyway.

The greater effect critical bonus, potency, and some talents call for dropping 1d before rolling. This stacks, and has a greater mechanical effect on small pools.

Pools are always notated with the size of the pool in front of it, written in italics (*4d Barroom Brawl*). They can be flexibly applied in many situations, usually by the GM. Keep in mind that larger pools only require slightly more rolls to clear—there are diminishing returns when it comes to the size (2d clear in ~2.7 rolls, 4d clear in ~3.5 rolls, 8d clear in ~4.4 rolls). Adding any dice past 8d doesn't change the average number of rolls needed to drop it to zero by much.

The types: task, pressure, timer, resource, power, linked and campaign pools (pp. 18-19).

*Didact:* `didact track new '<name>' --kind pool --size 4 --pool task` makes a pool, and `didact track roll <pool>` rolls it and drops each 1-3; `--drop 1` drops 1d before rolling.
