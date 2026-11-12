<!-- translated from 7fe144069f94 -->
# Detaljer, krönikan och var saker finns

SL:s anteckningar som håller ett spel konsekvent: hur saker ser ut och vad de vill, vad de gör och planerar härnäst, vad som har hänt dem och var allt finns.

## Detaljer

Korta namngivna anteckningar på vilket uppslag som helst: en person, ett föremål, en plats, en faktion.

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

- **Namn.** Vilka som föreslås beror på vilken sorts uppslag det är, och vilket namn på ett ord som helst fungerar:
  - personer: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - föremål: looks, history, where, powers, secret, thoughts;
  - platser: looks, state, history, secret, thoughts;
  - grupper: wants, plan, state, history, secret, thoughts.

  Ett paket kan föreslå egna per typ (`details: [mood, grudge]` i ett schema).
- **Vem ser vad.** Spelarna ser bara `looks`: `show` och `find` utelämnar resten, och `--gm` visar allt. När spelarna får veta en detalj flyttar `didact reveal sweeney plan` den till uppslagets text under `## Revealed`.
- **`thoughts`** är dina: varför du skapade det, vart det kan leda, vad du ska knyta ihop senare.
- **Håll dem aktuella.** Du behöver inte anteckna allt. Men när du bestämmer något (en plan, ett agg, vart någon tog vägen), skriv ner det, så att nästa scen, eller nästa spelmöte, håller sig till det.

## Krönikan: vad som hände vem

En journalhändelse kan ange vilka uppslag den gäller. Den visas då på vart och ett av dem.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` och `about` listar ett uppslags krönika: vad det gjorde, och vad som gjordes mot det.
- **Hemliga händelser** sker utom synhåll för spelarna. De syns bara i SL-vyer (`session show --gm`, `about`, `brief --gm`), och aldrig i `export --as story`.
- Använd `--about` för allt som förändrar någon eller något: ett svek, en skuld, en död, en gåva, ett brutet löfte.
- **Rätta en händelse:** `didact beat edit S1.4 --about tom` lägger den i Toms krönika (eller `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), och `didact beat rm S1.4` tar bort den. Id:na står i `session show`, och båda går att ångra.
- **När id:n ändras:** en `merge` eller en ny slug tar med sig varje referens: kopplingar, detaljer, uppslagen som händelser handlar om, gruppen, striden och gruppens plats. När ett uppslag raderas med `rm` lämnar det också den grupp eller strid det ingick i. En `merge` mellan typer behåller det som det kvarvarande uppslagets ark har fält för, och säger vad den utelämnar.

## Var saker finns

Föremål ligger i inventarier, och vad som helst kan hålla dem: en rollperson, en plats, en kista.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Under ett spelmöte loggar en flytt av ett föremål en händelse om givaren och mottagaren (”Sword: Freya → Chest”). Deras krönikor visar sedan vart saker tog vägen.
- **Personer och monster** är platsers besökare, inte deras innehåll: håll reda på var de är i deras `where`-detalj.

## I scener och strider

- **`combat status --gm`** visar varje kämpes `where`, `doing` och `plan`. Uppdatera dem allteftersom striden rör sig: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (lägesbilden ett spelmöte börjar med) listar det som är i spel (platsen, kämparna, alla som den här scenens händelser handlar om, och gruppen) med where, doing, plan och state. Den listar också de senaste händelserna utanför scenen.
