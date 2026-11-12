---
name: start
description: Start or resume a Didact play session - read the brief, open a session if none is open, recap briefly, and ask the player what they do.
argument-hint: "[session title]"
---

Start (or resume) play with Didact.

Where things stand:

!`"${CLAUDE_PLUGIN_ROOT}/bin/didact" brief`

1. If no campaign is active, stop and use `/didact:new-campaign` instead.
2. If no session is open, open one: `didact session start` (with the title "$ARGUMENTS" if
   one was given). If the previous session left summaries due, write them first.
3. Recap the story so far in a few sentences, from the brief and the last summary.
4. Frame the scene (or open one: `didact scene new '…'`), then ask the player what they do.
