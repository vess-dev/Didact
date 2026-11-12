<!-- translated from 7fe144069f94 -->
# Details, de kroniek en verblijfplaatsen

De notities van de SL die een spel consistent houden: hoe dingen eruitzien en wat ze willen, wat ze doen en wat ze van plan zijn, wat hun is overkomen en waar alles is.

## Details

Korte notities met een naam, bij elk item: een persoon, een voorwerp, een plaats, een factie.

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

- **Namen.** Welke worden voorgesteld hangt af van het soort item, en elke naam van één woord werkt:
  - personen: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - voorwerpen: looks, history, where, powers, secret, thoughts;
  - plaatsen: looks, state, history, secret, thoughts;
  - groeperingen: wants, plan, state, history, secret, thoughts.

  Een pakket kan per type eigen namen voorstellen (`details: [mood, grudge]` in een schema).
- **Wie wat ziet.** Spelers zien alleen `looks`: `show` en `find` laten de rest weg, en `--gm` toont alles. Als de spelers er een te weten komen, zet `didact reveal sweeney plan` het in de tekst van het item onder `## Revealed`.
- **`thoughts`** zijn van jou: waarom je het hebt gemaakt, waar het heen kan, wat later moet terugkomen.
- **Houd ze bij.** Je hoeft niet alles te noteren. Maar als je iets beslist (een plan, een wrok, waar iemand heen ging), schrijf het op, zodat de volgende scène, of de volgende sessie, er trouw aan blijft.

## De kroniek: wat er met wie gebeurde

Een logboekgebeurtenis kan de items noemen waar ze over gaat. Ze verschijnt dan bij elk daarvan.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` en `about` tonen de kroniek van een item: wat het deed, en wat ermee gedaan werd.
- **Geheime gebeurtenissen** vinden plaats buiten het zicht van de spelers. Ze verschijnen alleen in SL-weergaven (`session show --gm`, `about`, `brief --gm`), en nooit in `export --as story`.
- Gebruik `--about` voor alles wat iemand of iets verandert: een verraad, een schuld, een dood, een geschenk, een gebroken belofte.
- **Een gebeurtenis corrigeren:** `didact beat edit S1.4 --about tom` zet haar in de kroniek van Tom (of `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), en `didact beat rm S1.4` verwijdert haar. De id's staan in `session show`, en beide kun je ongedaan maken.
- **Als id's veranderen:** een `merge` of een nieuwe slug neemt elke verwijzing mee: koppelingen, details, de items waar gebeurtenissen over gaan, de groep, het gevecht en de locatie van de groep. Als een item met `rm` wordt verwijderd, verlaat het ook elke groep en elk gevecht. Een `merge` tussen types houdt wat het blad van het blijvende item een veld voor heeft, en zegt wat het weglaat.

## Verblijfplaatsen: waar dingen zijn

Voorwerpen zitten in inventarissen, en alles kan ze bevatten: een personage, een plaats, een kist.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Tijdens een sessie legt het verplaatsen van een voorwerp een gebeurtenis vast over de gever en de ontvanger (“Sword: Freya → Chest”). Hun kronieken vertellen dan waar dingen heen gingen.
- **Personen en monsters** zijn bezoekers van een plaats, niet de inhoud ervan: houd bij waar ze zijn in hun detail `where`.

## In scènes en gevechten

- **`combat status --gm`** toont van elke vechter `where`, `doing` en `plan`. Werk ze bij terwijl het gevecht verloopt: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (de briefing waarmee een sessie begint) toont wat er in het spel is (de plaats, de vechters, iedereen waar de gebeurtenissen van deze scène over gaan, en de groep) met where, doing, plan en state. Ook toont het de laatste gebeurtenissen buiten beeld.
