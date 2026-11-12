---
id: extras-hex-flowers
title: "Hex Flowers"
tags: [extras, gm-tools, solo, exploration, random]
page: 189
---
These are an alternative to random tables. Instead of each result having a static chance, the result is dependent on starting position, changing as the game moves forward. Hex flowers are especially useful for exploration and solo-play, helping to give only semi-random answers to the questions you pose. *What is today's weather like? | What will the terrain be in a day's travel? | Will the winds be in our favor today?*

**How to use hex flowers.** You may recognize these as a tool in other tabletop games. Grimwild strives to be smooth and quick-to-play—with that in mind, these hex flowers are smaller and more simple than others.

There are 7 hexagons, each representing an answer. The party begins at the bottom hex, and moves to an adjacent hex based on a 1d roll. If the resulting movement would take you off of the flower, you instead wrap around and appear in the same row or column on the side opposite. The bottom and top most hex have walls preventing you from moving off the hex in that direction, keeping you in place instead. This keeps the bottom hexes most common, and those at the top more rare. After landing on a hex (or staying on the same one because of a wall), look to the key to see the result.

The flower, as drawn: hex 1 at the bottom, 2 lower right, 3 lower left, 4 in the center, 5 upper right, 6 upper left, 7 at the top. The die's directions: 1 up-left, 2 up, 3 up-right, 4 down-right, 5 down, 6 down-left.

*Example keys:* `hex-flower-spring-weather` and `hex-flower-kalthazar-foothills`, looked up by hex (`--with hex=4`).

*Didact:* keep the current hex in a note (it starts at 1); move with `didact table roll hex-flower-move --with hex=<current>`, then read the key: `didact table roll hex-flower-spring-weather --with hex=<new>`.
