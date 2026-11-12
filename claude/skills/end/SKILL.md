---
name: end
description: End a Didact play session cleanly - close the scene and session with summaries, do what's due, and say where things stand.
---

End play for now.

!`"${CLAUDE_PLUGIN_ROOT}/bin/didact" status`

1. If a scene is open: `didact scene end --summary '<two or three sentences>'`.
2. `didact session end --summary '<what happened this session, in a short paragraph>'`.
3. `didact summary due`: write anything still due.
4. If the system or oracle has end-of-scene or end-of-session bookkeeping (an oracle's chaos
   factor and lists, growth, faction turns), do it now.
5. Tell the player, briefly, where things stand and what's waiting next time.
