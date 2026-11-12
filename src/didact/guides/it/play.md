<!-- translated from bef7b2c650cb -->
# Giocare una sessione

Come si svolge una partita con Didact: l'LLM narra, e Didact conserva ogni fatto, tiro e cambiamento.

## Prima della prima sessione

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Un mondo mantiene il sistema con cui è stato creato, e le sue campagne si giocano con esso: un altro sistema si gioca in un mondo tutto suo. `didact campaign close` mette da parte una campagna (il suo mondo resta aperto) e `didact campaign open <id>` la riprende da dove si era interrotta, sessione compresa.

`didact world delete <id>` e `didact campaign delete <id>` ne eliminano uno, mostrando prima un'anteprima; `--yes` elimina, e `didact undo` ripristina tutto.

`session zero` elenca le domande da chiarire con il giocatore. Quelle del pack vengono prima. Tra queste ci sono le opzioni del sistema (le sue varianti e regole opzionali): le sue regole seguono le risposte, e il riepilogo dice cosa significa ogni opzione cambiata. Ogni riepilogo riporta le risposte.

## Una sessione

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turni:** ogni messaggio del giocatore apre un turno (l'hook di Claude Code chiama `didact capture`, e gli altri client usano `turn begin`). `didact undo --turn` annulla tutto ciò che è stato fatto per quel messaggio: modifiche, eventi e tiri. La trascrizione lo conserva.
- **Tornare indietro:** `didact undo --to e40` annulla tutto ciò che segue #e40, dal più recente (`--dry-run` lo elenca): ogni modifica viene annullata e ogni tiro segnato come annullato. Nulla viene eliminato: `redo`, o tornare a una modifica successiva, riporta tutto indietro.
- **Tempo:** `didact time advance 1 watch` fa scadere i timer, fa emergere i promemoria e avvia i trigger temporali. `didact remind --list` mostra i promemoria in arrivo, e `didact remind --cancel 2` ne elimina uno. Una campagna inizia all'inizio del calendario, o alla data che indica `campaign new --date '4 July 1902'`, e `didact time set '<date>'` la cambia fino alla prima sessione.
- **Luoghi:** `didact visit <place>` sposta il gruppo e segna il luogo come visitato. `didact map` mostra ciò che il gruppo conosce, e un'uscita inesplorata è `?`.
- **Combattimenti:** `didact combat start --party troll`, poi `combat next`, `combat hit freya troll weapon=d8` e `combat end`. I combattenti entrano ed escono a combattimento in corso: `didact combat join wolf-2` (in modalità individuale tirano l'iniziativa) e `didact combat leave troll --why fled`. Il turno di nessuno viene saltato.
- **Oggetti:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (o in un forziere, o in un luogo); `didact where rope` lo ritrova. `inv add` trova un oggetto del compendio per id, nome o alias.
- **I tuoi appunti:** `didact about sweeney plan='…' doing='…' where='…'` conserva ciò che hai deciso su qualcuno o qualcosa. I giocatori vedono solo `looks`. `didact log … --about sweeney` mette un evento sulla sua scheda (`--secret` se i giocatori non lo vedono). `didact guide details` ne dice di più.
- **Il mondo va avanti:** `didact faction turn`, più gli orologi: `didact track new 'The flood' --size 6`. Un comando che accetta un solo tipo di scheda prende un nome condiviso da altre come di quel tipo: `didact track roll draugr` tira la riserva che porta il nome di un nemico (lo stesso `track tick` con un contatore, `quest done` con una missione e `visit` con un luogo).

## Oracoli, generatori e personaggi

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

Nulla di ciò che crea un generatore o una creazione del personaggio viene scritto prima di `commit`. Descrivi ciò che vuole il giocatore in `--prefill`, e la procedura riempie i vuoti. Una domanda elenca cosa significa ogni opzione quando il pack lo indica (`- Cutpurse: …`): dillo al giocatore, così sceglie sapendo cosa ottiene.

## Segreti

Le viste sono sicure per i giocatori per impostazione predefinita: `show`, `find`, `sheet`, `map`, `brief`. Tralasciano:
- le schede segrete (`knowledge: secret`);
- le sezioni `## Secrets` e `## GM notes`;
- i campi `secret: true`.

`--gm` mostra tutto. Quando i giocatori scoprono qualcosa:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` scrive ciò che sanno i giocatori come un piccolo sito web da condividere o leggere su un telefono: il gruppo, una pagina per scheda, il diario e la mappa. È sempre sicuro per i giocatori, e riesportare nella stessa cartella lo aggiorna. `didact export --as lonelog` scrive il diario in notazione Lonelog (`@ ? d: -> =>`, le scene come `S1`, tag come `[N:Sweeney]`), anch'esso sicuro per i giocatori.

## Lore: cosa riaffiora quando si nomina qualcosa

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Cosa conta:** ogni PNG, luogo, oggetto e fazione è una carta con chiave il suo nome e i suoi alias. Le voci di lore hanno `keys`, e le decisioni arbitrali emergono tramite la loro regola. La corrispondenza è su parole intere, e i plurali contano ("wolves" corrisponde a `wolf`).
- **Quando riaffiora il lore:** l'hook di Claude Code analizza ogni messaggio del giocatore. Anche `log`, `scene new` e `show` riportano il lore appena attivato, e una voce non si ripete per qualche turno.
- **Regolare una voce:** `--secondary` con `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (in turni o scene), `--constant` (sempre nel riepilogo) e `--no-recurse`.
- **Ambiti:** le voci vanno nella campagna, a meno che `--scope` indichi world, system o global. Un'analisi vede solo questa campagna, il suo mondo, il suo sistema e il globale, mai un altro mondo. Una voce più ristretta con lo stesso id nasconde una più ampia.
- **Lorebook di altri strumenti:** `didact lore import <file>` legge il World Info di SillyTavern (anche quello di KoboldAI), il lorebook di una scheda personaggio e il `.lorebook` di NovelAI; `didact lore export --to <file>` scrive World Info. Chiavi, logica, priorità, probabilità, gruppi e durate vengono riportati.

## Cambiare la storia

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` cambia il fatto ma conserva il vecchio valore. Segna anche come superati i riassunti che nominano Sweeney, e `audit` lo elenca.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` registra una decisione arbitrale. Poi compare in `rules lookup` e quando quella regola viene eseguita.
- `didact name npc` tira un nome nuovo, mai uno già usato nel mondo. Prima di inventarne uno, controllalo con `didact names check <name>`. `didact names forget <name>` ne libera uno.

## Manutenzione

- `didact history --clear` mostra cosa eliminerebbe la cancellazione della vecchia cronologia; `--yes` la elimina per sempre, schede eliminate comprese, e undo, `diff`, `rewind` e i punti di salvataggio più vecchi non possono più raggiungerla (`--before e120` conserva quell'evento e i successivi, `--rolls` elimina anche lo storico dei dadi). Esegui prima `didact snapshot`.
- `didact save --remove 'before the dragon'` rimuove un punto di salvataggio; `didact undo` lo ripristina.
- `didact transcript 3 --clear` elimina la trascrizione della sessione 3 (`--clear --all`: quelle di tutte le sessioni). `didact undo` la ripristina, e il testo resta nella cronologia fino a `history --clear`.
- `didact compendium remove <entry>` elimina una voce che hai aggiunto; le schede create da essa restano.
- `didact snapshot --keep 3` elimina tutti i backup tranne i tre più recenti, e `didact snapshot --remove <name>` ne elimina uno. Nessuno dei due si può annullare.
- `didact session end` fa da solo il backup della libreria (`snapshot-<time>-auto.zip`), conservando i cinque più recenti; `didact snapshot --list` li contrassegna.
- `didact reset` mostra cosa porterebbe via lo svuotamento della libreria; `--yes` la rende come appena installata: ogni mondo, campagna e scheda, la cronologia e l'indice di ricerca spariscono, e la modifica successiva torna a essere #e1. Prima fa il backup della libreria (`…-before-reset.zip`), e i backup restano, così come i pack installati, a meno di `--packs`. Per provare invece Didact su una campagna già pronta, `didact sample` costruisce la campagna di esempio in una libreria vuota (`--home` le dà una cartella tutta sua), e `didact serve --demo` la serve da zero.
- `didact snapshot --restore <name>` mostra il contenuto di un backup accanto alla libreria attuale; `--yes` fa il backup della libreria così com'è (`…-before-restore.zip`), poi mette il backup al suo posto. I numeri di eventi e tiri proseguono. Undo non può annullare un ripristino: ripristinare quel backup di sicurezza sì.
