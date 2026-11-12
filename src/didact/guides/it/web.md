<!-- translated from 5a088227a31a -->
# L'app nel browser

`didact serve` apre la tua libreria in un browser: esplora e modifica le schede, guarda come si collegano in un grafo, leggi il diario, esegui regole e tabelle, e usa ogni comando da un modulo.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Funziona offline: i font e le icone sono inclusi in Didact.

**Modalità demo.** `--demo` serve la campagna di esempio (`didact sample`: una valle fluviale, un PG, personaggi con gli appunti del GM, luoghi e sentieri, una missione, un orologio, e una sessione in corso con un combattimento) da una libreria tutta sua, accanto alla cartella della cache di Didact. Lì sono installati tutti i pack forniti con Didact. Viene ricostruita ogni volta che parte `--demo`, quindi prova quello che vuoi: la tua libreria non viene toccata.

## Opzioni

| Opzione | Predefinito | Cosa fa |
|---|---|---|
| `--port <n>` | 8765 | la porta su cui ascoltare |
| `--host <address>` | 127.0.0.1 | l'indirizzo su cui ascoltare: solo questa macchina |
| `--open` | no | apre l'app in una scheda del browser |
| `--gm` | no | parte con la vista GM attiva |
| `--demo` | no | serve una campagna di esempio nuova invece della tua libreria |

Le opzioni globali `--home`, `--world` e `--campaign` valgono per tutto ciò che fa l'app. Aprire un altro mondo o un'altra campagna nella pagina Libreria fa passare l'app a quel mondo o a quella campagna, come fanno `didact world use` e `didact campaign open`, e Chiudi mette da parte la campagna aperta (`didact campaign close`).

## Cosa contiene

- **Panoramica:** il riepilogo (mondo, campagna, sessione, scena, gruppo, scadenze), azioni rapide (tirare i dadi, interrogare l'oracolo con le probabilità che conosce, registrare un evento, iniziare o chiudere una sessione, una nuova scheda) e le ultime modifiche.
- **Stato:** la situazione a colpo d'occhio: la sessione e la scena, l'ora e i promemoria in arrivo, i valori di ogni membro del gruppo e cosa porta con sé, il combattimento (di chi è il turno, condizioni), le missioni e i contatori aperti, e dove si trova il gruppo con le sue vie d'uscita. I valori si ritoccano sul posto: − e + su una statistica, spuntare un contatore, usare o gettare un oggetto, aggiungerne uno, completare una missione, far avanzare il tempo (un numero, e un'unità che il calendario conosce: ore, turni di guardia, giorni, …), impostare un promemoria (una volta, o periodicamente) e annullarne uno.
- **Schede:** tutte le schede, raggruppate per tipo, con una casella di filtro e i chip tutto, mondo o campagna. La pagina di una scheda mostra il foglio, la descrizione, i dettagli, i campi, il contenuto, i collegamenti in entrambe le direzioni, la cronaca e la cronologia, con moduli per modificare ciascuno, e per archiviarla o eliminarla. Un personaggio il cui sistema prevede un avanzamento di livello ha un pulsante Level up (`char advance`): una bozza che mostra cosa cambia, prima e dopo, finché non viene confermata.
- **Bozze:** creazione del personaggio e generatori, un passo alla volta. Crea un personaggio (passo per passo o a caso, scegliendo il tipo quando il sistema ne ha più d'uno: un personaggio giocante, un gregario, …) e Genera… sono nelle pagine Schede; le bozze in attesa sono elencate lì e nella Panoramica. La pagina di una bozza mostra cosa contiene finora (le sue entità e i loro campi, la mappa disegnata da un generatore, i tiri, le domande del manuale) e la domanda a cui è in attesa. Ogni opzione è un pulsante che dice cosa significa quando il pack lo indica (cosa dà un background, cosa fa un talento); sceglierne più d'una è una casella da spuntare per ciascuna; i punteggi acquistati con un budget sono numeri che contano i punti man mano; un nome o un'altra risposta libera si può digitare; e Lascia decidere ai dadi tira solo quella (`char roll c3 --one`). Indietro annulla l'ultimo passo, così la sua domanda torna (`char back c3`: i tiri che ha fatto vengono segnati come annullati, e Annulla riporta indietro il passo). Poi Tira il resto, Modifica, Scarta… (chiede conferma) e Conferma, che apre la scheda del nuovo personaggio, o elenca ciò che il generatore ha creato. La bozza di un generatore è del GM: la vista giocatore mostra solo che esiste.
- **Grafo:** le schede come nodi e i collegamenti come archi. Trascina i nodi, trascina lo sfondo per spostarti, zooma con la rotellina; passa sopra una scheda per illuminare le vicine; clicca per aprirne una. Il pulsante Grafo nella pagina di una scheda mostra solo il suo vicinato.
  - **Mappa** (l'interruttore sopra il grafo, o Apri la mappa in Stato): i luoghi che il gruppo conosce, i percorsi tra di essi (etichettati strada, sentiero, …), la regione in cui si trova ciascuno (tratteggiata), e dove si trova il gruppo. Un percorso verso un luogo non ancora scoperto porta a un "?"; la vista GM mostra ogni luogo.
- **Diario:** le sessioni, ognuna si apre sulle sue scene, eventi e tiri. Ogni evento ha Modifica e Rimuovi (passandoci sopra), che aprono i moduli `beat edit` e `beat rm`.
- **Riferimento:** cerca in tutto (i risultati compaiono mentre scrivi), esegui le regole dei pack attivi dai moduli, tira sulle loro tabelle, e leggi il testo delle regole, il glossario e le guide.
- **Libreria:** mondi e campagne (apri, chiudi, crea, elimina), pack (ognuno con la sua descrizione; attiva, disattiva, installa, disinstalla; i pack inclusi in Didact hanno un pulsante Installa), la cronologia (Annulla, Ripeti, Torna a questo punto, Cancella), i punti di salvataggio (torna indietro, rimuovi) e i backup (fai un backup ora, ripristina, elimina, tieni i più recenti; quelli fatti alla fine di una sessione sono segnati auto). Senza una campagna aperta, la Panoramica elenca le campagne del mondo per aprirne una.
  - Eliminare un mondo o una campagna chiede prima conferma, e Annulla ripristina tutto.
  - Torna a questo punto (accanto a ogni modifica) annulla tutto ciò che segue quella modifica (`didact undo --to e40`): la sua pagina elenca prima cosa sparisce. Ogni modifica viene annullata e ogni tiro segnato come annullato, senza eliminare nulla: Ripeti, o tornare a una modifica successiva, li riporta indietro. Mostra le modifiche più vecchie elenca una parte più ampia della cronologia.
  - Il pack core è sempre attivo. Si usa un solo sistema di gioco alla volta: quello del mondo aperto, che lo mantiene per sempre (scelto quando il mondo viene creato). Un altro sistema si gioca in un mondo tutto suo: la sua riga apre un mondo che si gioca con esso, o ne crea uno nuovo. Disinstallare un pack non si può annullare: installa di nuovo il suo .didactpack.
  - Cancellare la cronologia mostra prima esattamente cosa sparisce e cosa smette di funzionare, con un pulsante per fare prima un backup. Non si può annullare, e nemmeno l'eliminazione di un backup.
  - Ricominciare da capo: **Reimposta…** svuota la libreria, come se Didact fosse appena stato installato, e la numerazione riparte da #e1. La sua pagina mostra prima cosa sparisce. Prima viene fatto il backup della libreria, e i backup restano (anche i pack installati, a meno che tu non spunti la casella).
  - Ripristinare un backup mostra prima cosa contiene accanto alla libreria attuale. Prima viene fatto il backup della libreria com'era: Annulla non può annullare un ripristino, ma ripristinare quel backup sì.
- **Comandi:** ogni comando come modulo, e una casella che accetta un'intera riga di comando. Ogni casella accetta ciò che accetta il suo argomento: un numero, un ID o un evento (`e12`) secondo il suo formato, una quantità di tempo di gioco come numero e unità, e un elenco da cui scegliere tra le schede, le bozze, i pack, i punti di salvataggio, gli oracoli, le tabelle e le regole presenti.
- **Impostazioni:** le opzioni della campagna (le varianti e le regole opzionali del suo sistema, che le regole, la creazione del personaggio e i generatori seguono; ognuna dice cosa fa: per una regola opzionale, cosa cambia attivandola, per una scelta, cosa significa ciascuno dei suoi valori, e un valore predefinito impostato da un'altra opzione dice quale), la lingua dell'app, il dizionario dei sinonimi (la lingua che le ricerche usano per i sinonimi: scaricarne una, con una barra di avanzamento, passare dall'una all'altra tra quelle scaricate, rimuoverne una) e la documentazione del codice.
  - L'app, le sue guide e ciò che i comandi mostrano al suo interno sono disponibili in 24 lingue. Senza una scelta, l'app segue la lingua del browser. La riga di comando e gli LLM che la usano restano in inglese: la lingua scelta qui vale solo per l'app.
  - Il pulsante del codice nella barra in alto apre la documentazione dell'API del codice. Viene generata dal codice la prima volta, e di nuovo ogni volta che il codice cambia (`didact docs build`).

Ogni modifica esegue un vero comando `didact`, quindi è controllata, registrata e annullabile esattamente come dalla riga di comando. L'app mostra ogni volta il comando eseguito (`didact set sweeney hp-=2`), con un pulsante Annulla quando c'è qualcosa da annullare.

Una casella accetta solo ciò che accetta il suo comando. Un ID (di un mondo o di una campagna) e un tipo di scheda accettano lettere minuscole, cifre e trattini: gli spazi diventano trattini e le maiuscole diventano minuscole mentre scrivi. Il nome di un campo non accetta spazi (diventano trattini bassi), il nome di un dettaglio è una sola parola, e i campi numerici accettano solo numeri. Ciò che una casella accetta è scritto sotto di essa, e il comando ricontrolla comunque.

Un salvataggio non sovrascrive mai una modifica che non hai visto. Se la scheda è cambiata dopo che la pagina l'ha mostrata (l'ha modificata un LLM dalla riga di comando, per esempio, o un'altra scheda del browser), il salvataggio viene rifiutato e dice cosa c'è adesso. Una descrizione che stavi modificando resta nell'editor, accanto alla nuova versione, da unire e salvare di nuovo. − e + passano sempre: si sommano.

## Vista giocatore e vista GM

L'app mostra ciò che sanno i giocatori, come fa `didact show`: schede segrete, sezioni `## Secrets`, campi segreti e dettagli riservati al GM restano fuori. Il pulsante **GM** nella barra in alto attiva la vista GM, e un banner lo segnala ("Vista GM: spoiler visibili"). Il browser ricorda la scelta.

Nella vista giocatore:
- una descrizione con righe riservate al GM non si può modificare (salvarla le farebbe perdere): attiva prima la vista GM;
- un dettaglio del GM o un campo segreto che la pagina non mostra non si può sovrascrivere, anche se si può aggiungere una nuova nota per il GM;
- la cronologia nomina il comando e le schede che i giocatori conoscono (`set · Freya`), mai i valori, e Annulla dice quale modifica ha annullato, non cosa fosse.

## Sicurezza

L'app può modificare la tua libreria, quindi per impostazione predefinita ascolta solo questa macchina.

- `--host` con un altro indirizzo permette ad altre macchine di raggiungerla, e Didact lo segnala. Usalo solo su una rete di cui ti fidi.
- Risponde solo alle richieste indirizzate a sé (il proprio indirizzo, `localhost`, `127.0.0.1` o `[::1]`, con la sua porta). Questo impedisce ad altri siti web di raggiungerla con trucchi DNS.
- Ogni modifica richiede un modulo dell'app stessa: un token segreto in ogni modulo deve corrispondere a un cookie che gli altri siti non possono leggere né inviare.
- Non c'è login. Chiunque possa usare il browser di questo computer può usare l'app.
