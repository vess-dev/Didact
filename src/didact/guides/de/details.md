<!-- translated from 7fe144069f94 -->
# Details, Chronik und Aufenthaltsorte

Die Notizen der SL, die ein Spiel stimmig halten: wie Dinge aussehen und was sie wollen, was sie gerade tun und als Nächstes planen, was ihnen passiert ist und wo sich alles befindet.

## Details

Kurze, benannte Notizen zu jedem Eintrag: einer Person, einem Gegenstand, einem Ort, einer Fraktion.

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

- **Namen.** Welche vorgeschlagen werden, hängt von der Art des Eintrags ab, und jeder Name aus einem Wort funktioniert:
  - Personen: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - Gegenstände: looks, history, where, powers, secret, thoughts;
  - Orte: looks, state, history, secret, thoughts;
  - Gruppierungen: wants, plan, state, history, secret, thoughts.

  Ein Paket kann pro Typ eigene vorschlagen (`details: [mood, grudge]` in einem Schema).
- **Wer was sieht.** Die Spieler sehen nur `looks`: `show` und `find` lassen den Rest weg, und `--gm` zeigt alles. Erfahren die Spieler eines davon, verschiebt `didact reveal sweeney plan` es in den Text des Eintrags unter `## Revealed`.
- **`thoughts`** gehören dir: warum du es angelegt hast, wohin es führen könnte, was sich später auszahlen soll.
- **Halte sie aktuell.** Du musst nicht alles notieren. Aber wenn du etwas entscheidest (einen Plan, einen Groll, wohin jemand gegangen ist), schreib es auf, damit die nächste Szene oder die nächste Sitzung dabei bleibt.

## Die Chronik: was wem passiert ist

Ein Journal-Ereignis kann die Einträge nennen, die es betrifft. Es erscheint dann bei jedem von ihnen.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` und `about` listen die Chronik eines Eintrags auf: was er getan hat und was ihm angetan wurde.
- **Geheime Ereignisse** geschehen außerhalb der Sicht der Spieler. Sie erscheinen nur in SL-Ansichten (`session show --gm`, `about`, `brief --gm`) und nie in `export --as story`.
- Verwende `--about` für alles, was jemanden oder etwas verändert: einen Verrat, eine Schuld, einen Tod, ein Geschenk, ein gebrochenes Versprechen.
- **Ein Ereignis korrigieren:** `didact beat edit S1.4 --about tom` setzt es in Toms Chronik (oder `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), und `didact beat rm S1.4` entfernt es. Die IDs stehen in `session show`, und beides lässt sich rückgängig machen.
- **Wenn sich IDs ändern:** Ein `merge` oder ein neuer Slug nimmt jeden Verweis mit: Verknüpfungen, Details, die Einträge, die Ereignisse betreffen, die Gruppe, den Kampf und den Standort der Gruppe. Wird ein Eintrag mit `rm` gelöscht, verlässt er auch jede Gruppe und jeden Kampf. Ein `merge` über Typen hinweg behält, wofür der Bogen des bleibenden Eintrags ein Feld hat, und sagt, was er weglässt.

## Aufenthaltsorte: wo die Dinge sind

Gegenstände liegen in Inventaren, und alles kann sie aufnehmen: ein Charakter, ein Ort, eine Truhe.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Während einer Sitzung protokolliert das Bewegen eines Gegenstands ein Ereignis über Gebenden und Empfangenden („Sword: Freya → Chest“). Ihre Chroniken sagen dann, wohin die Dinge gegangen sind.
- **Personen und Monster** sind Besucher eines Ortes, nicht sein Inhalt: Halte fest, wo sie sind, im Detail `where`.

## In Szenen und Kämpfen

- **`combat status --gm`** zeigt für jeden Kämpfer `where`, `doing` und `plan`. Aktualisiere sie, während sich der Kampf entwickelt: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (das Briefing, mit dem eine Sitzung beginnt) listet auf, was im Spiel ist (der Ort, die Kämpfer, wen die Ereignisse dieser Szene betreffen, und die Gruppe), mit where, doing, plan und state. Es listet auch die neuesten Ereignisse außerhalb der Szene auf.
