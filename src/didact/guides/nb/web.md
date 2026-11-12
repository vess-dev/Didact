<!-- translated from 5a088227a31a -->
# Nettleserappen

`didact serve` åpner biblioteket ditt i en nettleser: utforsk og rediger oppslag, se i en graf hvordan de henger sammen, les journalen, kjør regler og tabeller, og bruk alle kommandoer fra et skjema.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Den virker uten nett: skriftene og ikonene følger med Didact.

**Demomodus.** `--demo` viser eksempelkampanjen (`didact sample`: en elvedal, en spillerperson, personer med SLs notater, steder og veier, et oppdrag, en klokke og en pågående økt med en kamp) fra et eget bibliotek ved siden av Didacts hurtigbuffermappe. Alle pakkene som følger med Didact, er installert der. Den bygges på nytt hver gang `--demo` starter, så prøv hva du vil: ditt eget bibliotek blir ikke rørt.

## Valg

| Valg | Standard | Hva det gjør |
|---|---|---|
| `--port <n>` | 8765 | porten det lyttes på |
| `--host <address>` | 127.0.0.1 | adressen det lyttes på: bare denne maskinen |
| `--open` | av | åpne appen i en nettleserfane |
| `--gm` | av | start med SL-visning på |
| `--demo` | av | vis en fersk eksempelkampanje i stedet for biblioteket ditt |

De globale `--home`, `--world` og `--campaign` gjelder for alt appen gjør. Åpner du en annen verden eller kampanje på appens side Bibliotek, bytter appen til den, slik `didact world use` og `didact campaign open` gjør, og Lukk legger den åpne kampanjen til side (`didact campaign close`).

## Hva den inneholder

- **Oversikt:** briefingen (verden, kampanje, økt, scene, gruppe, hva som forfaller), hurtighandlinger (kast terninger, spør oraklet med oddsene det kjenner, noter en hendelse, start eller avslutt en økt, et nytt oppslag) og de siste endringene.
- **Status:** hvor ting står, med ett blikk: økta og scenen, tiden og påminnelsene som kommer, hvert gruppemedlems tall og hva de bærer, kampen (hvem sin tur, tilstander), åpne oppdrag og tellere, og hvor gruppen er og veiene videre. Tallene kan justeres rett der: − og + på en egenskap, kryss av en teller, bruk eller slipp en gjenstand, legg til en, fullfør et oppdrag, la tiden gå (et tall og en enhet kalenderen kjenner: timer, vakter, dager, …), sett en påminnelse (én gang, eller med jevne mellomrom) og avbryt en.
- **Oppslag:** alle oppslag, gruppert etter type, med et filterfelt og brikker for alle, verden eller kampanje. Et oppslags side viser arket, beskrivelsen, detaljene, feltene, innholdet, koblinger begge veier, krøniken og historikken, med skjemaer for å endre hver av dem, og for å arkivere eller slette det. En person hvis system har en prosedyre for nytt nivå, har en Level up-knapp (`char advance`): et utkast som viser hva som endres, før og etter, til det er godkjent.
- **Utkast:** personskaping og generatorer, ett steg om gangen. Lag en person (steg for steg eller tilfeldig, og velg hvilken sort når systemet har flere: en spillerperson, en leiesvenn, …) og Generer… ligger på Oppslag-sidene; utkastene som venter, vises der og på Oversikt. Et utkasts side viser hva det inneholder så langt (enhetene og feltene deres, kartet en generator tegnet, kastene, bokas spørsmål) og spørsmålet det venter på. Hvert alternativ er en knapp som sier hva det betyr når pakken gjør det (hva en bakgrunn gir, hva et talent gjør); når flere skal velges, får hvert en boks å krysse av; verdier som kjøpes med et budsjett, er tall som teller poengene underveis; et navn eller et annet åpent svar kan skrives inn; og La terningene bestemme kaster bare for det ene (`char roll c3 --one`). Tilbake tar det siste steget tilbake, så spørsmålet kommer igjen (`char back c3`: kastene det gjorde, markeres som angret, og Angre henter steget tilbake). Så Kast resten, Rediger, Forkast… (det spør først) og Godkjenn, som åpner den nye personens oppslag, eller viser hva generatoren laget. En generators utkast tilhører SL: spillervisningen viser bare at det finnes.
- **Graf:** oppslag som noder og koblinger som kanter. Dra i noder, dra i bakgrunnen for å panorere, zoom med hjulet; hold musepekeren over et oppslag for å lyse opp naboene; klikk for å åpne et. Graf-knappen på et oppslags side viser bare nabolaget til det.
  - **Kart** (bryteren over grafen, eller Åpne kartet på Status): stedene gruppen kjenner, veiene mellom dem (merket road, trail, …), området hvert sted ligger i (stiplet), og hvor gruppen er. En vei til et sted som ikke er funnet ennå, fører til et «?»; SL-visningen viser alle steder.
- **Journal:** øktene, som hver åpner seg til scenene, hendelsene og kastene sine. Hver hendelse har Rediger og Fjern (hold musepekeren over den), som åpner skjemaene `beat edit` og `beat rm`.
- **Håndbok:** søk i alt (resultatene kommer mens du skriver), kjør de aktiverte pakkenes regler fra skjemaer, kast på tabellene deres, og les regelteksten, ordlisten og veiledningene deres.
- **Bibliotek:** verdener og kampanjer (åpne, lukk, opprett, slett), pakker (hver med hva den er; aktiver, deaktiver, installer, avinstaller; pakkene som følger med Didact, har en Installer-knapp), historikken (Angre, Gjør om, Hopp tilbake, Tøm), lagringspunkter (spol tilbake, fjern) og sikkerhetskopier (ta sikkerhetskopi nå, gjenopprett, slett, behold de nyeste; de som lages når en økt avsluttes, er merket auto). Når ingen kampanje er åpen, viser Oversikt verdenens kampanjer, så du kan åpne en.
  - Sletting av en verden eller kampanje spør først, og Angre henter alt tilbake.
  - Hopp tilbake (ved siden av hver endring) tar tilbake alt etter den endringen (`didact undo --to e40`): siden viser først hva som forsvinner. Hver endring angres og hvert kast markeres som angret, ikke slettet: Gjør om, eller å hoppe tilbake til en senere endring, henter dem tilbake. Vis eldre endringer viser mer av historikken.
  - Kjernepakken er alltid på. Bare ett spillsystem er i bruk om gangen: den åpne verdenens, som den beholder for godt (valgt når den opprettes). Et annet system spilles i en egen verden: systemets rad åpner en verden der det spilles, eller oppretter en ny. Avinstallering av en pakke kan ikke angres: installer .didactpack-filen på nytt.
  - Tømming av historikken viser først nøyaktig hva som forsvinner og hva som slutter å virke, med en knapp for å ta sikkerhetskopi først. Det kan ikke angres, og det kan heller ikke sletting av en sikkerhetskopi.
  - Start på nytt: **Tilbakestill…** tømmer biblioteket, som om Didact var nyinstallert, og nummereringen starter på nytt fra #e1. Siden viser først hva som forsvinner. Det tas sikkerhetskopi av biblioteket først, og sikkerhetskopiene blir værende (installerte pakker også, med mindre du krysser av i boksen).
  - Gjenoppretting av en sikkerhetskopi viser først hva den inneholder, ved siden av biblioteket slik det er nå. Det tas først sikkerhetskopi av biblioteket slik det var: Angre kan ikke ta tilbake en gjenoppretting, men å gjenopprette den sikkerhetskopien kan.
- **Kommandoer:** alle kommandoer som skjemaer, og et felt som tar en hel kommandolinje. Hvert felt tar det argumentet sitt tar: et tall, en ID eller en hendelse (`e12`) etter mønsteret sitt, en mengde spilltid som et tall og en enhet, og en liste å velge fra med oppslagene, utkastene, pakkene, lagringspunktene, oraklene, tabellene og reglene her.
- **Innstillinger:** kampanjens valg (systemets varianter og valgfrie regler, som reglene, personskapingen og generatorene følger; hvert valg sier hva det gjør: en valgfri regel hva som endres når den slås på, et valg med alternativer hva hvert alternativ betyr, og en standard som et annet valg setter, sier hvilket), appens språk, synonymordboka (språket søk bruker for synonymer: last ned et, med en fremdriftsindikator, bytt mellom dem som er lastet ned, fjern et) og kodens dokumentasjon.
  - Appen, veiledningene og det kommandoer viser i den, finnes på 24 språk. Uten et valg følger appen nettleserens språk. Kommandolinjen og LLM-ene som bruker den, forblir på engelsk: språket som velges her, gjelder bare appen.
  - Kodeknappen i topplinjen åpner kodens API-dokumentasjon. Den bygges fra koden første gang, og på nytt hver gang koden endres (`didact docs build`).

Hver endring kjører en ekte `didact`-kommando, så den sjekkes, logges og kan angres nøyaktig som på kommandolinjen. Appen viser hver gang kommandoen den kjørte (`didact set sweeney hp-=2`), med en Angre-knapp når det er noe å ta tilbake.

Et felt tar bare det kommandoen tar. En ID (en verdens eller en kampanjes) og en oppslagstype tar små bokstaver, sifre og bindestreker: mellomrom blir bindestreker og store bokstaver blir små mens du skriver. Navnet på et oppslagsfelt tar ingen mellomrom (de blir understreker), navnet på en detalj er ett ord, og tallfelt tar bare tall. Hva et felt tar, står under det, og kommandoen sjekker uansett på nytt.

Lagring overskriver aldri en endring du ikke har sett. Hvis oppslaget endret seg etter at siden viste det (en LLM endret det fra kommandolinjen, for eksempel, eller en annen fane gjorde det), avvises lagringen, og du får vite hva som står der nå. En beskrivelse du holdt på å redigere, blir værende i redigeringsfeltet ved siden av den nye versjonen, så du kan slå dem sammen og lagre på nytt. − og + går alltid gjennom: de legges sammen.

## Spillervisning og SL-visning

Appen viser det spillerne vet, slik `didact show` gjør: hemmelige oppslag, `## Secrets`-avsnitt, hemmelige felter og detaljer bare for SL holdes utenfor. **GM**-knappen i topplinjen slår på SL-visning, og et banner sier fra («SL-visning: spoilere vises»). Nettleseren husker valget.

I spillervisningen:
- kan en beskrivelse med linjer bare for SL ikke redigeres (å lagre den ville miste dem): slå på SL-visning først;
- kan en SL-detalj eller et hemmelig felt som siden ikke viser, ikke overskrives, men et nytt notat for SL kan legges til;
- nevner historikken kommandoen og oppslagene spillerne kjenner (`set · Freya`), aldri verdiene, og Angre sier hvilken endring den tok tilbake, ikke hva den var.

## Sikkerhet

Appen kan endre biblioteket ditt, så som standard lytter den bare til denne maskinen.

- `--host` med en annen adresse lar andre maskiner nå den, og Didact advarer om det. Bruk det bare på et nettverk du stoler på.
- Den svarer bare på forespørsler adressert til seg selv (sin egen adresse, `localhost`, `127.0.0.1` eller `[::1]`, med sin port). Det hindrer andre nettsteder i å nå den gjennom DNS-triks.
- Hver endring krever et skjema fra selve appen: et hemmelig token i hvert skjema må stemme med en informasjonskapsel som andre nettsteder ikke kan lese eller sende.
- Det finnes ingen innlogging. Alle som kan bruke denne datamaskinens nettleser, kan bruke appen.
