---
name: new-campaign
description: Set up a new Didact campaign - pick the system and oracle, create the world and campaign, run session zero, and make the characters.
argument-hint: "[system or idea]"
---

Set up a new campaign with the player ("$ARGUMENTS").

Packs available here:

!`"${CLAUDE_PLUGIN_ROOT}/bin/didact" pack list`

1. Agree on the system (a `system` pack above) and, for solo play, an oracle (an `oracle` pack;
   some systems bring their own, and the core pack's `yes-no` oracle is the fallback), plus any
   setting pack.
2. `didact world new <id> --system <system>` (or `--gen <generator> --auto` for a generated
   world), then `didact pack enable <oracle or setting>`, then `didact campaign new <id>`
   (`--date '<date>'` opens it on a date of the calendar other than its start; until the first
   session, `didact time set '<date>'` changes it).
3. Session zero: `didact session zero` lists the questions; ask them one or two at a time and
   save the answers with `didact campaign profile …`.
4. Characters: `didact char new` (guided, the player chooses) or `--mode random`; turn any
   description into `--prefill '{…}'`. Commit with `didact char commit <draft>`.
5. Start play with `/didact:start`.
