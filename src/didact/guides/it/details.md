<!-- translated from 7fe144069f94 -->
# Dettagli, cronaca e ubicazione

Gli appunti del GM che mantengono coerente una partita: che aspetto hanno le cose e cosa vogliono, cosa stanno facendo e cosa hanno in mente, cosa è successo loro, e dove si trova ogni cosa.

## Dettagli

Brevi note con un nome su qualsiasi scheda: una persona, un oggetto, un luogo, una fazione.

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

- **Nomi.** Quelli suggeriti dipendono dal tipo di scheda, e va bene qualsiasi nome di una sola parola:
  - persone: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - oggetti: looks, history, where, powers, secret, thoughts;
  - luoghi: looks, state, history, secret, thoughts;
  - gruppi: wants, plan, state, history, secret, thoughts.

  Un pack può suggerire i propri per ogni tipo (`details: [mood, grudge]` in uno schema).
- **Chi vede cosa.** I giocatori vedono solo `looks`: `show` e `find` tralasciano il resto, e `--gm` mostra tutto. Quando i giocatori ne scoprono uno, `didact reveal sweeney plan` lo sposta nel testo della scheda, sotto `## Revealed`.
- **`thoughts`** sono tuoi: perché l'hai creato, dove potrebbe portare, cosa ripagare più avanti.
- **Tienili aggiornati.** Non serve annotare tutto. Ma quando decidi qualcosa (un piano, un rancore, dove è andato qualcuno), scrivilo, così la scena successiva, o la sessione successiva, vi resta fedele.

## La cronaca: cosa è successo a chi

Un evento del diario può nominare le schede che riguarda. Compare allora su ciascuna di esse.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` e `about` elencano la cronaca di una scheda: cosa ha fatto, e cosa le è stato fatto.
- **Gli eventi segreti** avvengono lontano dagli occhi dei giocatori. Compaiono solo nelle viste del GM (`session show --gm`, `about`, `brief --gm`), e mai in `export --as story`.
- Usa `--about` per tutto ciò che cambia qualcuno o qualcosa: un tradimento, un debito, una morte, un dono, una promessa infranta.
- **Correggere un evento:** `didact beat edit S1.4 --about tom` lo mette nella cronaca di Tom (oppure `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), e `didact beat rm S1.4` lo rimuove. Gli id sono in `session show`, ed entrambi si possono annullare.
- **Quando gli id cambiano:** un `merge` o un nuovo slug si porta dietro ogni riferimento: collegamenti, dettagli, le schede riguardate dagli eventi, il gruppo, il combattimento e la posizione del gruppo. Quando una scheda viene eliminata con `rm`, lascia anche il gruppo o il combattimento in cui si trovava. Un `merge` tra tipi tiene ciò per cui il foglio della scheda che resta ha un campo, e dice cosa lascia fuori.

## Ubicazione: dove sono le cose

Gli oggetti stanno negli inventari, e qualsiasi cosa può contenerli: un personaggio, un luogo, un forziere.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Durante una sessione, spostare un oggetto registra un evento su chi lo dà e chi lo riceve ("Sword: Freya → Chest"). Le loro cronache dicono così dove sono finite le cose.
- **Persone e mostri** sono visitatori dei luoghi, non il loro contenuto: annota dove si trovano nel loro dettaglio `where`.

## In scena e in combattimento

- **`combat status --gm`** mostra `where`, `doing` e `plan` di ogni combattente. Aggiornali man mano che il combattimento procede: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (il riepilogo con cui inizia una sessione) elenca ciò che è in gioco (il luogo, i combattenti, chiunque sia riguardato dagli eventi di questa scena, e il gruppo) con where, doing, plan e state. Elenca anche gli ultimi eventi fuori scena.
