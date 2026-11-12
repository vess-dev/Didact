---
name: undo
description: Take back the last turn (everything Didact did for the last player message), or jump back further.
disable-model-invocation: true
---

The player wants to take something back.

1. Their last turn: preview it with `didact undo --turn --dry-run`, and tell the player in a line
   what would be undone (changes, rolls, journal beats). When they confirm, run
   `didact undo --turn`. The transcript keeps what was said.
2. Further back (to before a fight, say): find the last change to keep with `didact history`,
   preview everything after it with `didact undo --to e40 --dry-run`, and tell the player what
   goes. When they confirm, run `didact undo --to e40`. Nothing is deleted: `didact redo`, or
   jumping back to a later change, brings it back.
