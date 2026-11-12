# Details, the chronicle and whereabouts

The GM's notes that keep a game consistent: what things look like and want, what they're doing and plan next, what happened to them, and where everything is.

## Details

Short named notes on any record: a person, an item, a place, a faction.

```
didact about sweeney looks='tall, one eye clouded' personality='jovial, greedy'
didact about sweeney wants='buy back the mill' plan='sell the route to the raiders'
didact about sweeney doing='whittling by the fire' where='the back room of the inn'
didact about item:old-sword history='forged for the last king' powers='cuts through wards'
didact about loc:the-ford state='flooded' secret='a drowned shrine under the stones'
didact about sweeney thoughts='built to foreshadow the betrayal; pay it off at the ford'
didact about sweeney                  # the notes, what's still open, chronicle, whereabouts
didact about sweeney --clear doing    # or doing='' 
```

- **Names.** The suggested ones depend on the kind of record, and any one-word name works:
  - people: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - items: looks, history, where, powers, secret, thoughts;
  - places: looks, state, history, secret, thoughts;
  - groups: wants, plan, state, history, secret, thoughts.

  A pack can suggest its own per type (`details: [mood, grudge]` in a schema).
- **Who sees what.** Players see only `looks`: `show` and `find` leave out the rest, and `--gm` shows everything. When the players learn one, `didact reveal sweeney plan` moves it into the record's text under `## Revealed`.
- **`thoughts`** are yours: why you made it, where it could lead, what to pay off later.
- **Keep them current.** You don't have to note everything. But when you decide something (a plan, a grudge, where someone went), write it down, so the next scene, or the next session, stays true to it.

## The chronicle: what happened to whom

A journal beat can name the records it concerns. It then shows on each of them.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` and `about` list a record's chronicle: what it did, and what was done to it.
- **Secret beats** happen out of the players' sight. They appear only in GM views (`session show --gm`, `about`, `brief --gm`), and never in `export --as story`.
- Use `--about` for anything that changes someone or something: a betrayal, a debt, a death, a gift, a broken promise.
- **Fixing a beat:** `didact beat edit S1.4 --about tom` puts it on Tom's chronicle (or `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), and `didact beat rm S1.4` removes it. The ids are in `session show`, and both are undoable.
- **When ids change:** a `merge` or a new slug carries every reference with it: links, details, the records beats are about, the party, the fight and the party's location. When a record is deleted with `rm`, it leaves any party or fight too. A `merge` across types keeps what the survivor's sheet has a field for, and says what it leaves out.

## Whereabouts: where things are

Items live in inventories, and anything can hold them: a character, a place, a chest.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- During a session, moving an item logs a beat about the giver and the receiver ("Sword: Freya → Chest"). Their chronicles then say where things went.
- **People and monsters** are places' visitors, not their contents: keep where they are in their `where` detail.

## In scenes and fights

- **`combat status --gm`** shows each fighter's `where`, `doing` and `plan`. Update them as the fight moves: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (the brief a session starts with) lists what's in play (the place, the fighters, whoever this scene's beats are about, and the party) with where, doing, plan and state. It also lists the latest off-screen beats.
