<!-- translated from 5a088227a31a -->
# Die Browser-App

`didact serve` öffnet deine Bibliothek in einem Webbrowser: Einträge erkunden und bearbeiten, in einem Graph sehen, wie sie verknüpft sind, das Journal lesen, Regeln und Tabellen ausführen und jeden Befehl über ein Formular verwenden.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Sie funktioniert offline: Schriften und Symbole werden mit Didact ausgeliefert.

**Demo-Modus.** `--demo` stellt die Beispielkampagne bereit (`didact sample`: ein Flusstal, ein SC, Personen mit den Notizen der SL, Orte und Wege, eine Quest, eine Uhr und eine laufende Sitzung mit einem Kampf), aus einer eigenen Bibliothek neben dem Cache-Ordner von Didact. Dort sind alle Pakete installiert, die mit Didact kommen. Sie wird bei jedem Start von `--demo` frisch gebaut, also probier ruhig alles aus: Deine eigene Bibliothek bleibt unberührt.

## Optionen

| Option | Standard | Wirkung |
|---|---|---|
| `--port <n>` | 8765 | der Port, auf dem sie lauscht |
| `--host <address>` | 127.0.0.1 | die Adresse, auf der sie lauscht: nur dieser Rechner |
| `--open` | aus | die App in einem Browser-Tab öffnen |
| `--gm` | aus | mit eingeschalteter SL-Ansicht starten |
| `--demo` | aus | eine frische Beispielkampagne statt deiner Bibliothek bereitstellen |

Die globalen Optionen `--home`, `--world` und `--campaign` gelten für alles, was die App tut. Öffnest du auf der Seite Bibliothek eine andere Welt oder Kampagne, wechselt die App zu ihr, wie bei `didact world use` und `didact campaign open`, und Schließen legt die geöffnete Kampagne beiseite (`didact campaign close`).

## Was drin ist

- **Übersicht:** das Briefing (Welt, Kampagne, Sitzung, Szene, Gruppe, was ansteht), Schnellaktionen (würfeln, das Orakel mit den Chancen befragen, die es kennt, ein Ereignis protokollieren, eine Sitzung starten oder beenden, ein neuer Eintrag) und die letzten Änderungen.
- **Status:** der Stand der Dinge auf einen Blick: Sitzung und Szene, die Zeit und die anstehenden Erinnerungen, die Werte jedes Gruppenmitglieds und was es mitführt, der Kampf (wer am Zug ist, Zustände), offene Quests und Zähler, und wo die Gruppe ist, samt ihren Ausgängen. Die Werte lassen sich direkt dort anpassen: − und + an einem Wert, einen Zähler abhaken, einen Gegenstand benutzen oder ablegen, einen hinzufügen, eine Quest abschließen, die Zeit vorrücken (eine Zahl und eine Einheit, die der Kalender kennt: Stunden, Wachen, Tage, …), eine Erinnerung setzen (einmal oder regelmäßig) und eine abbrechen.
- **Einträge:** jeder Eintrag, nach Typ gruppiert, mit einem Filterfeld und den Chips Alle, Welt oder Kampagne. Die Seite eines Eintrags zeigt seinen Bogen, seine Beschreibung, Details, Felder, Inhalt, Verknüpfungen in beide Richtungen, seine Chronik und seinen Verlauf, mit Formularen, um jedes davon zu ändern und ihn zu archivieren oder zu löschen. Ein Charakter, dessen System einen Stufenaufstieg hat, hat einen Knopf Level up (`char advance`), der einen Entwurf anlegt: Er zeigt, was sich ändert, vorher und nachher, bis er übernommen wird.
- **Entwürfe:** Charaktererschaffung und Generatoren, Schritt für Schritt. Charakter erschaffen (Schritt für Schritt oder zufällig, wobei du die Art wählst, wenn das System mehrere hat: ein Spielercharakter, ein Mietling, …) und Generieren… sind auf den Seiten Einträge; die wartenden Entwürfe sind dort und in der Übersicht aufgelistet. Die Seite eines Entwurfs zeigt, was er bisher enthält (seine Einträge und deren Felder, die Karte, die ein Generator gezeichnet hat, die Würfe, die Fragen des Buchs) und die Frage, auf die er wartet. Jede Option ist ein Knopf, der sagt, was sie bedeutet, wenn das Paket es sagt (was ein Hintergrund gibt, was ein Talent bewirkt); wer mehrere wählt, hakt für jede ein Kästchen an; mit einem Budget gekaufte Werte sind Zahlen, die die Punkte gleich mitzählen; ein Name oder eine andere offene Antwort lässt sich eintippen; und Die Würfel entscheiden lassen würfelt nur diese eine (`char roll c3 --one`). Zurück nimmt den letzten Schritt zurück, sodass seine Frage erneut kommt (`char back c3`: Die Würfe, die er gemacht hat, werden als rückgängig markiert, und Rückgängig holt den Schritt zurück). Dann Den Rest auswürfeln, Bearbeiten, Verwerfen… (fragt vorher nach) und Übernehmen, das den Eintrag des neuen Charakters öffnet oder auflistet, was der Generator erzeugt hat. Der Entwurf eines Generators gehört der SL: Die Spieleransicht zeigt nur, dass er da ist.
- **Graph:** Einträge als Knoten und Verknüpfungen als Kanten. Knoten ziehen, den Hintergrund ziehen zum Verschieben, mit dem Mausrad zoomen; mit der Maus darüberfahren, um die Nachbarn eines Eintrags hervorzuheben; anklicken, um einen zu öffnen. Der Knopf Graph auf der Seite eines Eintrags zeigt nur seine Nachbarschaft.
  - **Karte** (der Umschalter über dem Graph, oder Karte öffnen auf Status): die Orte, die die Gruppe kennt, die Wege zwischen ihnen (beschriftet mit road, trail, …), die Region, in der jeder liegt (gestrichelt), und wo die Gruppe ist. Ein Weg zu einem noch nicht gefundenen Ort führt zu einem „?“; die SL-Ansicht zeigt jeden Ort.
- **Journal:** die Sitzungen, jede aufklappbar zu ihren Szenen, Ereignissen und Würfen. Jedes Ereignis hat Bearbeiten und Entfernen (mit der Maus darüberfahren), die die Formulare für `beat edit` und `beat rm` öffnen.
- **Referenz:** alles durchsuchen (Ergebnisse erscheinen beim Tippen), die Regeln der aktivierten Pakete über Formulare ausführen, auf ihren Tabellen würfeln und ihren Regeltext, ihr Glossar und ihre Anleitungen lesen.
- **Bibliothek:** Welten und Kampagnen (öffnen, schließen, erstellen, löschen), Pakete (jedes mit dem, was es ist; aktivieren, deaktivieren, installieren, deinstallieren; die mit Didact ausgelieferten Pakete haben einen Knopf Installieren), der Verlauf (Rückgängig, Wiederholen, Zurückspringen, Leeren), Speicherpunkte (zurückspulen, entfernen) und Backups (jetzt ein Backup machen, wiederherstellen, löschen, die neuesten paar behalten; die beim Beenden einer Sitzung angelegten sind mit auto markiert). Ist keine Kampagne geöffnet, listet die Übersicht die Kampagnen der Welt auf, um eine davon zu öffnen.
  - Das Löschen einer Welt oder Kampagne fragt vorher nach, und Rückgängig holt alles zurück.
  - Zurückspringen (neben jeder Änderung) nimmt alles nach dieser Änderung zurück (`didact undo --to e40`): Seine Seite listet zuerst auf, was verschwindet. Jede Änderung wird rückgängig gemacht und jeder Wurf als rückgängig markiert, nicht gelöscht: Wiederholen oder ein Zurückspringen zu einer späteren Änderung holt sie zurück. Ältere Änderungen zeigen listet mehr vom Verlauf auf.
  - Das Paket core ist immer aktiv. Es ist immer nur ein Spielsystem in Verwendung: das der geöffneten Welt, die es endgültig behält (gewählt, wenn sie erstellt wird). Ein anderes System wird in einer eigenen Welt gespielt: Seine Zeile öffnet eine Welt, in der es gespielt wird, oder erstellt eine neue. Das Deinstallieren eines Pakets lässt sich nicht rückgängig machen: Installiere seine .didactpack erneut.
  - Das Leeren des Verlaufs zeigt zuerst genau, was verschwindet und was nicht mehr funktioniert, mit einem Knopf, um vorher ein Backup zu machen. Es lässt sich nicht rückgängig machen, das Löschen eines Backups ebenso wenig.
  - Neu anfangen: **Zurücksetzen…** leert die Bibliothek, als wäre Didact frisch installiert, und die Nummerierung beginnt wieder bei #e1. Seine Seite zeigt zuerst, was verschwindet. Die Bibliothek wird vorher gesichert, und Backups bleiben (installierte Pakete auch, außer du setzt das Häkchen).
  - Das Wiederherstellen eines Backups zeigt zuerst, was es enthält, neben der aktuellen Bibliothek. Die Bibliothek wird vorher so gesichert, wie sie war: Rückgängig kann eine Wiederherstellung nicht zurücknehmen, das Wiederherstellen dieses Backups aber schon.
- **Befehle:** jeder Befehl als Formular, und ein Feld, das eine ganze Befehlszeile annimmt. Jedes Feld nimmt an, was sein Argument annimmt: eine Zahl, eine ID oder einen Vorgang (`e12`) nach seinem Muster, eine Menge Spielzeit als Zahl und Einheit, und eine Liste zum Auswählen aus den Einträgen, Entwürfen, Paketen, Speicherpunkten, Orakeln, Tabellen und Regeln hier.
- **Einstellungen:** die Optionen der Kampagne (die Varianten und optionalen Regeln ihres Systems, denen Regeln, Charaktererschaffung und Generatoren folgen; jede sagt, was sie bewirkt: eine optionale Regel, was das Einschalten ändert, eine Wahl, was jeder ihrer Werte bedeutet, und ein Standardwert, den eine andere Option setzt, sagt, welche), die Sprache der App, der Thesaurus (die Sprache, die Suchen für Synonyme verwenden: eine herunterladen, mit Fortschrittsbalken, zwischen den heruntergeladenen wechseln, eine entfernen) und die Dokumentation des Codes.
  - Die App, ihre Anleitungen und was Befehle in ihr anzeigen, gibt es in 24 Sprachen. Ohne eigene Wahl folgt die App der Sprache des Browsers. Die Befehlszeile und die LLMs, die sie nutzen, bleiben auf Englisch: Die hier gewählte Sprache gilt nur für die App.
  - Der Code-Knopf in der Kopfzeile öffnet die API-Dokumentation des Codes. Sie wird beim ersten Mal aus dem Code gebaut und erneut, sobald sich der Code ändert (`didact docs build`).

Jede Änderung führt einen echten `didact`-Befehl aus, wird also genau wie auf der Kommandozeile geprüft, protokolliert und lässt sich rückgängig machen. Die App zeigt jedes Mal den ausgeführten Befehl (`didact set sweeney hp-=2`), mit einem Knopf Rückgängig, wenn es etwas zurückzunehmen gibt.

Ein Eingabefeld nimmt nur an, was sein Befehl annimmt. Eine ID (die einer Welt oder einer Kampagne) und ein Eintragstyp nehmen Kleinbuchstaben, Ziffern und Bindestriche: Beim Tippen werden Leerzeichen zu Bindestrichen und Großbuchstaben zu Kleinbuchstaben. Ein Feldname nimmt keine Leerzeichen (sie werden zu Unterstrichen), der Name eines Details ist ein Wort, und Zahlenfelder nehmen Zahlen. Was ein Eingabefeld annimmt, steht darunter, und der Befehl prüft es trotzdem noch einmal.

Speichern überschreibt nie eine Änderung, die du nicht gesehen hast. Hat sich der Eintrag geändert, nachdem die Seite ihn angezeigt hat (etwa weil ein LLM ihn über die Kommandozeile geändert hat oder ein anderer Tab), wird das Speichern abgelehnt und zeigt, was jetzt dort steht. Eine Beschreibung, die du gerade bearbeitet hast, bleibt im Editor, neben der neuen Fassung, zum Zusammenführen und erneuten Speichern. − und + gehen immer durch: Sie summieren sich.

## Spieleransicht und SL-Ansicht

Die App zeigt, was die Spieler wissen, wie `didact show`: Geheime Einträge, `## Secrets`-Abschnitte, geheime Felder und Details nur für die SL bleiben draußen. Der Knopf **GM** in der Kopfzeile schaltet die SL-Ansicht ein, und ein Banner sagt es („SL-Ansicht: Spoiler sichtbar“). Der Browser merkt sich die Wahl.

In der Spieleransicht:
- lässt sich eine Beschreibung mit Zeilen nur für die SL nicht bearbeiten (beim Speichern gingen sie verloren): Schalte zuerst die SL-Ansicht ein;
- lässt sich ein SL-Detail oder geheimes Feld, das die Seite nicht zeigt, nicht überschreiben, aber eine neue Notiz für die SL lässt sich hinzufügen;
- nennt der Verlauf den Befehl und die Einträge, die die Spieler kennen (`set · Freya`), nie die Werte, und Rückgängig sagt, welche Änderung es zurückgenommen hat, nicht, worin sie bestand.

## Sicherheit

Die App kann deine Bibliothek ändern, deshalb hört sie standardmäßig nur auf diesen Rechner.

- `--host` mit einer anderen Adresse lässt andere Rechner darauf zugreifen, und Didact warnt davor. Verwende es nur in einem Netzwerk, dem du vertraust.
- Sie beantwortet nur Anfragen, die an sie selbst gerichtet sind (ihre eigene Adresse, `localhost`, `127.0.0.1` oder `[::1]`, mit ihrem Port). Das hält andere Websites davon ab, sie über DNS-Tricks zu erreichen.
- Jede Änderung braucht ein Formular aus der App selbst: Ein geheimes Token in jedem Formular muss zu einem Cookie passen, das andere Websites weder lesen noch senden können.
- Es gibt keine Anmeldung. Wer den Browser dieses Computers benutzen kann, kann die App benutzen.
