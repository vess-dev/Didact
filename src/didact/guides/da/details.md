<!-- translated from 7fe144069f94 -->
# Detaljer, krøniken og opholdssteder

SL's noter, der holder et spil sammenhængende: hvordan ting ser ud, og hvad de vil, hvad de er i gang med og planlægger, hvad der er sket med dem, og hvor alting er.

## Detaljer

Korte, navngivne noter på ethvert opslag: en person, en genstand, et sted, en fraktion.

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

- **Navne.** Hvilke der foreslås, afhænger af opslagets slags, og ethvert navn på ét ord virker:
  - personer: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - genstande: looks, history, where, powers, secret, thoughts;
  - steder: looks, state, history, secret, thoughts;
  - fraktioner: wants, plan, state, history, secret, thoughts.

  En pakke kan foreslå sine egne for hver type (`details: [mood, grudge]` i et skema).
- **Hvem ser hvad.** Spillerne ser kun `looks`: `show` og `find` udelader resten, og `--gm` viser alt. Når spillerne finder ud af en af dem, flytter `didact reveal sweeney plan` den ind i opslagets tekst under `## Revealed`.
- **`thoughts`** er dine: hvorfor du lavede det, hvor det kan føre hen, hvad der skal betale sig senere.
- **Hold dem opdaterede.** Du behøver ikke notere alt. Men når du beslutter noget (en plan, et nag, hvor nogen tog hen), så skriv det ned, så den næste scene, eller den næste spilgang, holder sig til det.

## Krøniken: hvad der skete med hvem

En begivenhed i journalen kan nævne de opslag, den handler om. Så vises den på hvert af dem.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` og `about` viser et opslags krønike: hvad det gjorde, og hvad der blev gjort ved det.
- **Hemmelige begivenheder** sker uden for spillernes syn. De vises kun i SL-visninger (`session show --gm`, `about`, `brief --gm`) og aldrig i `export --as story`.
- Brug `--about` til alt, der ændrer nogen eller noget: et forræderi, en gæld, et dødsfald, en gave, et brudt løfte.
- **Ret en begivenhed:** `didact beat edit S1.4 --about tom` sætter den på Toms krønike (eller `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), og `didact beat rm S1.4` fjerner den. Id'erne står i `session show`, og begge kan fortrydes.
- **Når id'er ændres:** en `merge` eller en ny slug tager alle henvisninger med sig: forbindelser, detaljer, de opslag, begivenheder handler om, gruppen, kampen og gruppens placering. Når et opslag slettes med `rm`, forlader det også enhver gruppe eller kamp. En `merge` på tværs af typer beholder det, som det tilbageværende opslags ark har et felt til, og siger, hvad den udelader.

## Opholdssteder: hvor tingene er

Genstande ligger i inventarer, og alt kan rumme dem: en person, et sted, en kiste.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Under en spilgang noterer det en begivenhed om giveren og modtageren, når en genstand flyttes (»Sword: Freya → Chest«). Deres krøniker fortæller så, hvor tingene blev af.
- **Personer og monstre** er et steds besøgende, ikke dets indhold: hold styr på, hvor de er, i deres `where`-detalje.

## I scener og kampe

- **`combat status --gm`** viser hver kæmpers `where`, `doing` og `plan`. Opdatér dem, efterhånden som kampen skrider frem: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (den briefing, en spilgang starter med) viser, hvad der er i spil (stedet, kæmperne, dem, denne scenes begivenheder handler om, og gruppen) med where, doing, plan og state. Den viser også de seneste begivenheder uden for scenen.
