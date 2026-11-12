<!-- translated from bef7b2c650cb -->
# Slik spiller du en økt

Slik går et spill gjennom Didact: LLM-en forteller, og Didact tar vare på hvert faktum, hvert kast og hver endring.

## Før den første økta

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

En verden beholder systemet den ble opprettet med, og kampanjene dens spilles med det: et annet system spilles i en egen verden. `didact campaign close` legger en kampanje til side (verdenen dens forblir åpen), og `didact campaign open <id>` tar den opp igjen der den slapp, med økt og alt.

`didact world delete <id>` og `didact campaign delete <id>` fjerner en av dem, med forhåndsvisning først; `--yes` sletter, og `didact undo` henter alt tilbake.

`session zero` viser spørsmålene som må avklares med spilleren. Pakkens egne kommer først. Systemets valg (dets varianter og valgfrie regler) er blant dem: reglene følger svarene, og oppsummeringen sier hva hvert endret valg betyr. Hver briefing har med svarene.

## En økt

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turer:** hver melding fra spilleren åpner en tur (Claude Code-hooken kaller `didact capture`, og andre klienter bruker `turn begin`). `didact undo --turn` tar tilbake alt som ble gjort for den meldingen: endringer, hendelser og kast. Transkripsjonen beholder det.
- **Hoppe tilbake:** `didact undo --to e40` tar tilbake alt etter #e40, nyeste først (`--dry-run` viser det): hver endring angres og hvert kast markeres som angret. Ingenting slettes: `redo`, eller å hoppe tilbake til en senere endring, henter det tilbake.
- **Tid:** `didact time advance 1 watch` lar tidtakere løpe ut, henter fram påminnelser og kjører tidsutløsere. `didact remind --list` viser påminnelsene som kommer, og `didact remind --cancel 2` dropper en. En kampanje begynner på kalenderens start, eller på datoen `campaign new --date '4 July 1902'` gir, og `didact time set '<date>'` endrer den fram til første økt.
- **Steder:** `didact visit <place>` flytter gruppen og markerer stedet som besøkt. `didact map` viser det gruppen kjenner til, og en uutforsket utgang er `?`.
- **Kamper:** `didact combat start --party troll`, så `combat next`, `combat hit freya troll weapon=d8` og `combat end`. Kjempere kommer og går midt i kampen: `didact combat join wolf-2` (i individuell modus kaster de initiativ) og `didact combat leave troll --why fled`. Ingen mister turen sin.
- **Ting:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (eller ned i en kiste, eller på et sted); `didact where rope` finner den. `inv add` finner en gjenstand i kompendiet via ID-en, navnet eller et alias.
- **Notatene dine:** `didact about sweeney plan='…' doing='…' where='…'` tar vare på det du har bestemt om noen eller noe. Spillerne ser bare `looks`. `didact log … --about sweeney` setter en hendelse på oppslaget deres (`--secret` hvis spillerne ikke ser den). `didact guide details` har mer.
- **Verden går videre:** `didact faction turn`, pluss klokker: `didact track new 'The flood' --size 6`. En kommando som bare tar én slags oppslag, tar et navn andre deler, som den slagsen: `didact track roll draugr` slår puljen som bærer en fiendes navn (likeså `track tick` en teller, `quest done` et oppdrag og `visit` et sted).

## Orakler, generatorer og personer

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

Ingenting en generator eller personskaping lager, lagres før `commit`. Beskriv det spilleren ønsker i `--prefill`, så fyller prosedyren inn resten. Et spørsmål viser hva hvert alternativ betyr når pakken sier det (`- Cutpurse: …`): fortell det til spilleren, så de velger med kunnskap om hva de får.

## Hemmeligheter

Visninger er trygge for spillerne som standard: `show`, `find`, `sheet`, `map`, `brief`. De utelater:
- hemmelige oppslag (`knowledge: secret`);
- avsnittene `## Secrets` og `## GM notes`;
- felter med `secret: true`.

`--gm` viser alt. Når spillerne får vite noe:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` skriver det spillerne vet, som et lite nettsted å dele eller lese på en telefon: gruppen, en side per oppslag, journalen og kartet. Det er alltid trygt for spillerne, og eksporterer du på nytt til samme mappe, oppdateres det. `didact export --as lonelog` skriver journalen i Lonelog-notasjon (`@ ? d: -> =>`, scener som `S1`, merker som `[N:Sweeney]`), også trygt for spillerne.

## Lore: det som dukker opp når noe nevnes

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Hva som teller:** hver bifigur, hvert sted, hver gjenstand og hver fraksjon er et kort med navnet og aliasene som nøkler. Lore-oppføringer har `keys`, og avgjørelser dukker opp gjennom regelen sin. Det matches på hele ord, og flertall teller («wolves» matcher `wolf`).
- **Når lore dukker opp:** Claude Code-hooken skanner hver melding fra spilleren. `log`, `scene new` og `show` har også med nyutløst lore, og en oppføring gjentas ikke før etter noen turer.
- **Finjustere en oppføring:** `--secondary` med `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (i turer eller scener), `--constant` (alltid i briefingen) og `--no-recurse`.
- **Omfang:** oppføringer havner i kampanjen med mindre `--scope` sier world, system eller global. En skanning ser bare denne kampanjen, dens verden, dens system og global, aldri en annen verden. En smalere oppføring med samme ID skygger for en bredere.
- **Andre verktøys lorebooks:** `didact lore import <file>` leser SillyTavern World Info (også KoboldAIs), lorebooken i et figurkort og NovelAIs `.lorebook`; `didact lore export --to <file>` skriver World Info. Nøkler, logikk, prioritet, sannsynlighet, grupper og timing blir med.

## Endre historien

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` endrer faktumet, men beholder den gamle verdien. Den markerer også sammendrag som nevner Sweeney, som utdaterte, og `audit` viser dem.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` registrerer en avgjørelse. Den dukker så opp i `rules lookup` og når den regelen kjører.
- `didact name npc` kaster et nytt navn, aldri et som verdenen allerede bruker. Før du finner på et selv, sjekk det med `didact names check <name>`. `didact names forget <name>` frigjør et igjen.

## Rydding

- `didact history --clear` viser hva tømming av gammel historikk ville fjerne; `--yes` fjerner det for godt, slettede oppslag inkludert, og angre, `diff`, `rewind` og eldre lagringspunkter kan ikke lenger nå det (`--before e120` beholder den hendelsen og senere, `--rolls` fjerner også terningloggen). Kjør `didact snapshot` først.
- `didact save --remove 'before the dragon'` fjerner et lagringspunkt; `didact undo` henter det tilbake.
- `didact transcript 3 --clear` sletter transkripsjonen av økt 3 (`--clear --all`: alle øktene). `didact undo` henter den tilbake, og teksten blir værende i historikken til `history --clear`.
- `didact compendium remove <entry>` sletter en oppføring du har lagt til; oppslag som er laget fra den, blir værende.
- `didact snapshot --keep 3` sletter alle sikkerhetskopier unntatt de tre nyeste, og `didact snapshot --remove <name>` sletter én. Ingen av dem kan angres.
- `didact session end` tar selv sikkerhetskopi av biblioteket (`snapshot-<time>-auto.zip`) og beholder de fem nyeste av dem; `didact snapshot --list` markerer dem.
- `didact reset` viser hva tømming av biblioteket ville fjerne; `--yes` gjør det som nyinstallert: alle verdener, kampanjer og oppslag, historikken og søkeindeksen forsvinner, og neste endring er #e1 igjen. Den tar sikkerhetskopi av biblioteket først (`…-before-reset.zip`), og sikkerhetskopiene blir værende, det samme gjør installerte pakker med mindre `--packs`. Vil du heller prøve Didact på en ferdig kampanje, bygger `didact sample` eksempelkampanjen i et tomt bibliotek (`--home` gir den en egen mappe), og `didact serve --demo` viser den helt fersk.
- `didact snapshot --restore <name>` viser hva en sikkerhetskopi inneholder, ved siden av biblioteket slik det er nå; `--yes` tar sikkerhetskopi av biblioteket slik det er (`…-before-restore.zip`), og setter så sikkerhetskopien på plass. Hendelses- og kastnumre fortsetter. Angre kan ikke ta tilbake en gjenoppretting: det kan en gjenoppretting av den sikkerhetskopien.
