<!-- translated from 7fe144069f94 -->
# Detalii, cronica și locul lucrurilor

Notele MJ-ului care țin jocul coerent: cum arată lucrurile și ce vor, ce fac și ce plănuiesc, ce li s-a întâmplat și unde se află totul.

## Detalii

Note scurte, cu nume, pe orice fișă: o persoană, un obiect, un loc, o facțiune.

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

- **Nume.** Cele sugerate depind de felul fișei, dar merge orice nume dintr-un singur cuvânt:
  - persoane: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - obiecte: looks, history, where, powers, secret, thoughts;
  - locuri: looks, state, history, secret, thoughts;
  - grupări: wants, plan, state, history, secret, thoughts.

  Un pachet poate sugera propriile nume pentru fiecare tip (`details: [mood, grudge]` într-o schemă).
- **Cine ce vede.** Jucătorii văd doar `looks`: `show` și `find` omit restul, iar `--gm` arată tot. Când jucătorii află unul, `didact reveal sweeney plan` îl mută în textul fișei, sub `## Revealed`.
- **`thoughts`** sunt ale tale: de ce ai creat-o, unde poate duce, ce trebuie valorificat mai târziu.
- **Ține-le la zi.** Nu trebuie să notezi totul. Dar când hotărăști ceva (un plan, o ranchiună, unde a plecat cineva), scrie-l, ca următoarea scenă sau următoarea sesiune să-i rămână fidelă.

## Cronica: ce i s-a întâmplat cui

Un eveniment din jurnal poate numi fișele la care se referă. Apare apoi pe fiecare dintre ele.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` și `about` listează cronica unei fișe: ce a făcut și ce i s-a făcut.
- **Evenimentele secrete** au loc departe de ochii jucătorilor. Apar doar în vederile MJ (`session show --gm`, `about`, `brief --gm`) și niciodată în `export --as story`.
- Folosește `--about` pentru orice schimbă pe cineva sau ceva: o trădare, o datorie, o moarte, un dar, o promisiune încălcată.
- **Corectarea unui eveniment:** `didact beat edit S1.4 --about tom` îl pune în cronica lui Tom (sau `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), iar `didact beat rm S1.4` îl elimină. ID-urile sunt în `session show`, și ambele se pot desface.
- **Când se schimbă ID-urile:** un `merge` sau un slug nou poartă cu el fiecare referință: legăturile, detaliile, fișele la care se referă evenimentele, grupul, lupta și locul grupului. Când o fișă e ștearsă cu `rm`, iese și din orice grup sau luptă. Un `merge` între tipuri păstrează ce are drept câmp foaia fișei care rămâne și spune ce lasă deoparte.

## Locul lucrurilor: unde se află

Obiectele stau în inventare, și orice le poate ține: un personaj, un loc, un cufăr.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- În timpul unei sesiuni, mutarea unui obiect notează un eveniment despre cel care dă și cel care primește („Sword: Freya → Chest”). Cronicile lor spun apoi unde au ajuns lucrurile.
- **Oamenii și monștrii** sunt vizitatorii locurilor, nu conținutul lor: păstrează unde se află în detaliul lor `where`.

## În scene și lupte

- **`combat status --gm`** arată `where`, `doing` și `plan` pentru fiecare luptător. Actualizează-le pe măsură ce lupta avansează: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (rezumatul cu care începe o sesiune) listează ce e în joc (locul, luptătorii, cei la care se referă evenimentele acestei scene și grupul), cu where, doing, plan și state. Listează și cele mai recente evenimente din afara scenei.
