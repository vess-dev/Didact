<!-- translated from 7fe144069f94 -->
# Detaljer, krøniken og oppholdssteder

SLs notater som holder et spill sammenhengende: hvordan ting ser ut og hva de vil, hva de holder på med og planlegger, hva som har skjedd med dem, og hvor alt er.

## Detaljer

Korte, navngitte notater på et hvilket som helst oppslag: en person, en gjenstand, et sted, en fraksjon.

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

- **Navn.** Hvilke som foreslås, avhenger av hva slags oppslag det er, og ethvert navn på ett ord fungerer:
  - personer: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - gjenstander: looks, history, where, powers, secret, thoughts;
  - steder: looks, state, history, secret, thoughts;
  - fraksjoner: wants, plan, state, history, secret, thoughts.

  En pakke kan foreslå sine egne for hver type (`details: [mood, grudge]` i et skjema).
- **Hvem ser hva.** Spillerne ser bare `looks`: `show` og `find` utelater resten, og `--gm` viser alt. Når spillerne får vite en av dem, flytter `didact reveal sweeney plan` den inn i oppslagets tekst under `## Revealed`.
- **`thoughts`** er dine: hvorfor du laget det, hvor det kan føre, hva som skal lønne seg senere.
- **Hold dem oppdatert.** Du trenger ikke notere alt. Men når du bestemmer noe (en plan, et nag, hvor noen dro), så skriv det ned, slik at neste scene, eller neste økt, holder seg til det.

## Krøniken: hva som skjedde med hvem

En hendelse i journalen kan nevne oppslagene den handler om. Da vises den på hvert av dem.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` og `about` viser et oppslags krønike: hva det gjorde, og hva som ble gjort med det.
- **Hemmelige hendelser** skjer utenfor spillernes syn. De vises bare i SL-visninger (`session show --gm`, `about`, `brief --gm`), og aldri i `export --as story`.
- Bruk `--about` for alt som endrer noen eller noe: et svik, en gjeld, et dødsfall, en gave, et brutt løfte.
- **Rette en hendelse:** `didact beat edit S1.4 --about tom` setter den på Toms krønike (eller `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), og `didact beat rm S1.4` fjerner den. ID-ene står i `session show`, og begge kan angres.
- **Når ID-er endres:** en `merge` eller en ny slug tar med seg alle henvisninger: koblinger, detaljer, oppslagene hendelser handler om, gruppen, kampen og gruppens plassering. Når et oppslag slettes med `rm`, forlater det også en eventuell gruppe eller kamp. En `merge` på tvers av typer beholder det det gjenværende oppslagets ark har et felt for, og sier hva den utelater.

## Oppholdssteder: hvor ting er

Gjenstander ligger i inventarer, og alt kan holde på dem: en person, et sted, en kiste.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Under en økt fører flytting av en gjenstand til en hendelse om giveren og mottakeren («Sword: Freya → Chest»). Krønikene deres forteller så hvor ting ble av.
- **Personer og monstre** er besøkende på et sted, ikke innholdet i det: hold rede på hvor de er, i `where`-detaljen deres.

## I scener og kamper

- **`combat status --gm`** viser hver kjempers `where`, `doing` og `plan`. Oppdater dem etter hvert som kampen skrider fram: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (briefingen en økt starter med) viser det som er i spill (stedet, kjemperne, dem denne scenens hendelser handler om, og gruppen) med where, doing, plan og state. Den viser også de siste hendelsene utenfor scenen.
