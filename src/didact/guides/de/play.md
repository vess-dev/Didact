<!-- translated from bef7b2c650cb -->
# Eine Sitzung spielen

Wie ein Spiel über Didact läuft: Das LLM erzählt, und Didact hält jede Tatsache, jeden Wurf und jede Änderung fest.

## Vor der ersten Sitzung

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Eine Welt behält das System, mit dem sie erstellt wurde, und ihre Kampagnen werden damit gespielt: Ein anderes System wird in einer eigenen Welt gespielt. `didact campaign close` legt eine Kampagne beiseite (ihre Welt bleibt geöffnet), und `didact campaign open <id>` nimmt sie dort wieder auf, wo sie aufgehört hat, samt Sitzung.

`didact world delete <id>` und `didact campaign delete <id>` entfernen eine Welt bzw. Kampagne, mit Vorschau vorab; `--yes` löscht, und `didact undo` holt alles zurück.

`session zero` listet die Fragen auf, die mit dem Spieler zu klären sind. Die des Pakets kommen zuerst. Dazu gehören die Optionen des Systems (seine Varianten und optionalen Regeln): Seine Regeln folgen den Antworten, und das Briefing sagt, was jede geänderte Option bedeutet. Jedes Briefing enthält die Antworten.

## Eine Sitzung

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Züge:** Jede Nachricht des Spielers eröffnet einen Zug (der Claude-Code-Hook ruft `didact capture` auf, andere Clients verwenden `turn begin`). `didact undo --turn` nimmt alles zurück, was für diese Nachricht getan wurde: Änderungen, Ereignisse und Würfe. Das Transkript behält es.
- **Zurückspringen:** `didact undo --to e40` nimmt alles nach #e40 zurück, neueste zuerst (`--dry-run` listet es auf): Jede Änderung wird rückgängig gemacht und jeder Wurf als rückgängig markiert. Nichts wird gelöscht: `redo` oder ein Zurückspringen zu einer späteren Änderung holt es zurück.
- **Zeit:** `didact time advance 1 watch` lässt Timer ablaufen, bringt Erinnerungen hoch und führt Zeit-Auslöser aus. `didact remind --list` zeigt die anstehenden Erinnerungen, und `didact remind --cancel 2` streicht eine. Eine Kampagne beginnt am Beginn des Kalenders oder an dem Datum, das `campaign new --date '4 July 1902'` angibt, und `didact time set '<date>'` ändert es bis zur ersten Sitzung.
- **Orte:** `didact visit <place>` bewegt die Gruppe und markiert den Ort als besucht. `didact map` zeigt, was die Gruppe kennt, und ein unerkundeter Ausgang ist `?`.
- **Kämpfe:** `didact combat start --party troll`, dann `combat next`, `combat hit freya troll weapon=d8` und `combat end`. Kämpfer kommen und gehen mitten im Kampf: `didact combat join wolf-2` (im Einzelmodus würfeln sie Initiative) und `didact combat leave troll --why fled`. Niemandes Zug wird übersprungen.
- **Dinge:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (oder in eine Truhe oder an einen Ort); `didact where rope` findet es. `inv add` findet einen Kompendiumsgegenstand über seine ID, seinen Namen oder einen Alias.
- **Deine Notizen:** `didact about sweeney plan='…' doing='…' where='…'` hält fest, was du über jemanden oder etwas entschieden hast. Die Spieler sehen nur `looks`. `didact log … --about sweeney` setzt ein Ereignis auf seinen Eintrag (`--secret`, wenn die Spieler es nicht sehen). Mehr dazu in `didact guide details`.
- **Die Welt dreht sich weiter:** `didact faction turn`, dazu Uhren: `didact track new 'The flood' --size 6`. Ein Befehl für eine Art von Eintrag nimmt einen Namen, den andere teilen, als diese Art: `didact track roll draugr` würfelt den Pool, nach dem ein Feind benannt ist (ebenso `track tick` einen Zähler, `quest done` eine Quest und `visit` einen Ort).

## Orakel, Generatoren und Charaktere

```
didact ask 'Is the ferryman home?' --odds likely        # #o3 ? … → Yes, but…
didact interpret o3 'Home, but drunk and grieving.'     # what it meant, kept with it
didact meaning                                          # two words to interpret: betray · oath
didact gen run pointcrawl --prefill '{"terrain": "Swamp"}' --auto   # a draft: #g4
didact gen edit g4 poi-1.name='Amber Grave'
didact gen commit g4
didact char new                                         # guided: answer with `char choose c5 …`
didact char back c5                                     # take the last answer back: ask it again
didact char new --mode random --prefill '{"name": "Wren", "background": "Cutpurse"}'
didact char advance wren                                # the system's level-up, step by step (#c6)
didact world new fenmoor --system my-system --gen <generator> --prefill '{…}'
```

Nichts, was ein Generator oder die Charaktererschaffung erzeugt, wird vor `commit` geschrieben. Beschreib in `--prefill`, was der Spieler möchte, und der Ablauf füllt die Lücken. Eine Frage listet auf, was jede Option bedeutet, wenn das Paket es sagt (`- Cutpurse: …`): Sag es dem Spieler, damit er beim Wählen weiß, was er bekommt.

## Geheimnisse

Ansichten sind standardmäßig spielersicher: `show`, `find`, `sheet`, `map`, `brief`. Sie lassen weg:
- geheime Einträge (`knowledge: secret`);
- die Abschnitte `## Secrets` und `## GM notes`;
- Felder mit `secret: true`.

`--gm` zeigt alles. Wenn die Spieler etwas erfahren:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` schreibt, was die Spieler wissen, als kleine Website zum Teilen oder zum Lesen auf dem Handy: die Gruppe, eine Seite pro Eintrag, das Journal und die Karte. Sie ist immer spielersicher, und ein erneuter Export in denselben Ordner aktualisiert sie. `didact export --as lonelog` schreibt das Journal in Lonelog-Notation (`@ ? d: -> =>`, Szenen als `S1`, Tags wie `[N:Sweeney]`), ebenfalls spielersicher.

## Lore: was zurückkommt, wenn etwas erwähnt wird

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Was zählt:** Jeder NSC, jeder Ort, jeder Gegenstand und jede Fraktion ist eine Karte mit ihrem Namen und ihren Aliasen als Schlüssel. Lore-Einträge haben `keys`, und Regelentscheidungen kommen über ihre Regel hoch. Verglichen werden ganze Wörter, und Pluralformen zählen („wolves“ passt zu `wolf`).
- **Wann Lore hochkommt:** Der Claude-Code-Hook durchsucht jede Nachricht des Spielers. Auch `log`, `scene new` und `show` bringen neu ausgelöste Lore mit, und ein Eintrag wird ein paar Züge lang nicht wiederholt.
- **Einen Eintrag feinjustieren:** `--secondary` mit `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (in Zügen oder Szenen), `--constant` (immer im Briefing) und `--no-recurse`.
- **Geltungsbereiche:** Einträge gehören zur Kampagne, außer `--scope` sagt world, system oder global. Eine Suche sieht nur diese Kampagne, ihre Welt, ihr System und global, nie eine andere Welt. Ein engerer Eintrag mit derselben ID verdeckt einen weiteren.
- **Lorebooks anderer Tools:** `didact lore import <file>` liest SillyTavern World Info (auch das von KoboldAI), das Lorebook einer Charakterkarte und das `.lorebook` von NovelAI; `didact lore export --to <file>` schreibt World Info. Schlüssel, Logik, Priorität, Wahrscheinlichkeit, Gruppen und Timing werden übernommen.

## Die Geschichte ändern

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` ändert die Tatsache, behält aber den alten Wert. Außerdem markiert es Zusammenfassungen, die Sweeney erwähnen, als veraltet, und `audit` listet sie auf.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` hält eine Regelentscheidung fest. Sie erscheint dann in `rules lookup` und wenn diese Regel ausgeführt wird.
- `didact name npc` würfelt einen neuen Namen, nie einen, den die Welt schon verwendet. Bevor du einen erfindest, prüf ihn mit `didact names check <name>`. `didact names forget <name>` gibt einen wieder frei.

## Aufräumen

- `didact history --clear` zeigt, was das Leeren des alten Verlaufs verwerfen würde; `--yes` verwirft es endgültig, gelöschte Einträge eingeschlossen, und Rückgängig, `diff`, `rewind` und ältere Speicherpunkte kommen nicht mehr daran (`--before e120` behält dieses Ereignis und spätere, `--rolls` verwirft auch die Würfelaufzeichnung). Führe vorher `didact snapshot` aus.
- `didact save --remove 'before the dragon'` entfernt einen Speicherpunkt; `didact undo` holt ihn zurück.
- `didact transcript 3 --clear` löscht das Transkript von Sitzung 3 (`--clear --all`: das aller Sitzungen). `didact undo` holt es zurück, und der Text bleibt im Verlauf, bis `history --clear`.
- `didact compendium remove <entry>` löscht einen Eintrag, den du hinzugefügt hast; daraus erzeugte Einträge bleiben.
- `didact snapshot --keep 3` löscht alle Backups außer den neuesten drei, und `didact snapshot --remove <name>` löscht eines. Beides lässt sich nicht rückgängig machen.
- `didact session end` sichert die Bibliothek von selbst (`snapshot-<time>-auto.zip`) und behält davon die neuesten fünf; `didact snapshot --list` markiert sie.
- `didact reset` zeigt, was das Leeren der Bibliothek mitnehmen würde; `--yes` macht sie wie frisch installiert: Jede Welt, Kampagne und jeder Eintrag, der Verlauf und der Suchindex verschwinden, und die nächste Änderung ist wieder #e1. Vorher wird die Bibliothek gesichert (`…-before-reset.zip`), und die Backups bleiben, ebenso installierte Pakete, außer mit `--packs`. Um Didact stattdessen an einer fertigen Kampagne auszuprobieren, baut `didact sample` die Beispielkampagne in eine leere Bibliothek (`--home` gibt ihr einen eigenen Ordner), und `didact serve --demo` stellt sie jedes Mal frisch bereit.
- `didact snapshot --restore <name>` zeigt, was ein Backup enthält, neben der aktuellen Bibliothek; `--yes` sichert die Bibliothek so, wie sie ist (`…-before-restore.zip`), und setzt dann das Backup an ihre Stelle. Ereignis- und Wurfnummern laufen weiter. Rückgängig kann eine Wiederherstellung nicht zurücknehmen: Das Wiederherstellen dieses Sicherheits-Backups kann es.
