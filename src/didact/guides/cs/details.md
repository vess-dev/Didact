<!-- translated from 7fe144069f94 -->
# Podrobnosti, kronika a místa pobytu

Poznámky PJ, které udržují hru soudržnou: jak věci vypadají a co chtějí, co dělají a co plánují dál, co se jim stalo a kde co je.

## Podrobnosti

Krátké pojmenované poznámky u libovolného záznamu: osoby, předmětu, místa, frakce.

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

- **Názvy.** Navrhované závisí na druhu záznamu a funguje jakýkoli jednoslovný název:
  - osoby: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - předměty: looks, history, where, powers, secret, thoughts;
  - místa: looks, state, history, secret, thoughts;
  - skupiny: wants, plan, state, history, secret, thoughts.

  Balíček může pro každý typ navrhnout vlastní (`details: [mood, grudge]` ve schématu).
- **Kdo co vidí.** Hráči vidí jen `looks`: `show` a `find` zbytek vynechají a `--gm` ukáže vše. Když se hráči některou podrobnost dozvědí, `didact reveal sweeney plan` ji přesune do textu záznamu pod `## Revealed`.
- **`thoughts`** jsou vaše: proč jste to vytvořili, kam to může vést, co později zúročit.
- **Udržujte je aktuální.** Nemusíte zapisovat všechno. Ale když něco rozhodnete (plán, zášť, kam kdo odešel), zapište to, aby tomu další scéna i další sezení zůstaly věrné.

## Kronika: co se komu stalo

Událost v deníku může uvést záznamy, kterých se týká. Pak se zobrazí u každého z nich.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` a `about` vypíšou kroniku záznamu: co udělal a co bylo uděláno jemu.
- **Tajné události** se dějí mimo zraky hráčů. Objeví se jen v pohledech PJ (`session show --gm`, `about`, `brief --gm`) a nikdy v `export --as story`.
- `--about` použijte u všeho, co někoho nebo něco změní: u zrady, dluhu, smrti, daru, porušeného slibu.
- **Oprava události:** `didact beat edit S1.4 --about tom` ji zařadí do Tomovy kroniky (nebo `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`) a `didact beat rm S1.4` ji odebere. ID najdete v `session show` a obojí lze vrátit zpět.
- **Když se mění ID:** `merge` nebo nový slug s sebou přenese každou zmínku: odkazy, podrobnosti, záznamy, kterých se události týkají, družinu, boj i polohu družiny. Záznam smazaný pomocí `rm` opustí i družinu a boj. `merge` napříč typy ponechá to, pro co má karta zůstávajícího záznamu pole, a řekne, co vynechá.

## Místa pobytu: kde co je

Předměty patří do výbavy a mít je může cokoli: postava, místo, truhla.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Během sezení přesun předmětu zapíše událost o dárci a příjemci („Sword: Freya → Chest“). Jejich kroniky pak říkají, kam věci putovaly.
- **Osoby a netvoři** jsou v místech hosty, ne jejich obsahem: kde jsou, vedete v jejich podrobnosti `where`.

## Ve scénách a bojích

- **`combat status --gm`** ukazuje `where`, `doing` a `plan` každého bojovníka. Aktualizujte je, jak se boj vyvíjí: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (briefing, kterým sezení začíná) vypíše, co je ve hře (místo, bojovníky, koho se týkají události této scény, a družinu), s where, doing, plan a state. Vypíše i nejnovější události mimo scénu.
