<!-- translated from 5a088227a31a -->
# Browserappen

`didact serve` åbner dit bibliotek i en webbrowser: udforsk og redigér opslag, se i en graf, hvordan de hænger sammen, læs journalen, kør regler og tabeller, og brug alle kommandoer fra en formular.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Den virker offline: skrifttyper og ikoner følger med Didact.

**Demotilstand.** `--demo` viser eksempelkampagnen (`didact sample`: en floddal, en spillerperson, personer med SL's noter, steder og veje, en mission, et ur og en igangværende spilgang med en kamp) fra sit eget bibliotek ved siden af Didacts cachemappe. Alle pakker, der følger med Didact, er installeret der. Den bygges forfra, hver gang `--demo` starter, så prøv hvad som helst: dit eget bibliotek bliver ikke rørt.

## Tilvalg

| Tilvalg | Standard | Hvad det gør |
|---|---|---|
| `--port <n>` | 8765 | porten, der lyttes på |
| `--host <address>` | 127.0.0.1 | adressen, der lyttes på: kun denne maskine |
| `--open` | fra | åbn appen i en browserfane |
| `--gm` | fra | start med SL-visning slået til |
| `--demo` | fra | vis en frisk eksempelkampagne i stedet for dit bibliotek |

De globale `--home`, `--world` og `--campaign` gælder for alt, hvad appen gør. Åbner du en anden verden eller kampagne på appens side Bibliotek, skifter appen til den, ligesom `didact world use` og `didact campaign open` gør, og Luk lægger den åbne kampagne til side (`didact campaign close`).

## Hvad den indeholder

- **Oversigt:** briefingen (verden, kampagne, spilgang, scene, gruppe, hvad der forfalder), hurtige handlinger (slå med terninger, spørg oraklet med de odds, det kender, notér en begivenhed, start eller afslut en spilgang, et nyt opslag) og de seneste ændringer.
- **Status:** hvor tingene står, med ét blik: spilgangen og scenen, tiden og de kommende påmindelser, hvert gruppemedlems tal og hvad de bærer, kampen (hvis tur, tilstande), åbne missioner og tællere, og hvor gruppen er med sine veje videre. Tallene kan justeres lige dér: − og + på en egenskab, sæt kryds i en tæller, brug eller smid en genstand, tilføj en, fuldfør en mission, lad tiden gå (et tal og en enhed, kalenderen kender: timer, vagter, dage, …), sæt en påmindelse (én gang eller med jævne mellemrum) og annullér en.
- **Opslag:** alle opslag, grupperet efter type, med et filterfelt og chips for alle, verden eller kampagne. Et opslags side viser dets ark, beskrivelse, detaljer, felter, indhold, forbindelser begge veje, dets krønike og dets historik, med formularer til at ændre hver af dem og til at arkivere eller slette det. En person, hvis system har en niveaustigning, har en Level up-knap (`char advance`): en kladde, der viser, hvad der ændres, før og efter, indtil den er godkendt.
- **Kladder:** personskabelse og generatorer, ét trin ad gangen. Skab en person (trin for trin eller tilfældigt, med valg af slags, når systemet har flere: en spillerperson, en lejesvend, …) og Generér… findes på siderne Opslag; de kladder, der venter, vises dér og på Oversigt. En kladdes side viser, hvad den indeholder indtil nu (dens enheder og deres felter, kortet, en generator tegnede, slagene, bogens spørgsmål), og det spørgsmål, den venter på. Hver mulighed er en knap, der siger, hvad den betyder, når pakken gør det (hvad en baggrund giver, hvad et talent gør); vælger man flere, er der et felt at sætte kryds i for hver; værdier, der købes inden for et budget, er tal, der tæller pointene undervejs; et navn eller et andet åbent svar kan skrives ind; og Lad terningerne bestemme slår kun det ene (`char roll c3 --one`). Tilbage tager det seneste trin tilbage, så dets spørgsmål kommer igen (`char back c3`: de slag, det lavede, markeres som fortrudte, og Fortryd bringer trinnet tilbage). Derefter Slå resten, Redigér, Kassér… (den spørger først) og Godkend, som åbner den nye persons opslag eller viser, hvad generatoren lavede. En generators kladde tilhører SL: spillervisningen viser kun, at den findes.
- **Graf:** opslag som knuder og forbindelser som kanter. Træk i knuderne, træk i baggrunden for at panorere, zoom med hjulet; hold musen over et opslag for at fremhæve dets naboer; klik for at åbne et. Knappen Graf på et opslags side viser kun dets nabolag.
  - **Kort** (kontakten over grafen, eller Åbn kortet på Status): de steder, gruppen kender, vejene mellem dem (mærket road, trail, …), det område, hvert sted ligger i (stiplet), og hvor gruppen er. En vej til et sted, der endnu ikke er fundet, fører til et »?«; SL-visningen viser alle steder.
- **Journal:** spilgangene, som hver åbner sig til sine scener, begivenheder og slag. Hver begivenhed har Redigér og Fjern (hold musen over den), som åbner formularerne `beat edit` og `beat rm`.
- **Håndbog:** søg i alt (resultaterne kommer, mens du skriver), kør de aktiverede pakkers regler fra formularer, slå på deres tabeller, og læs deres regeltekst, ordliste og guider.
- **Bibliotek:** verdener og kampagner (åbn, luk, opret, slet), pakker (hver med, hvad den er; aktivér, deaktivér, installér, afinstallér; de pakker, der følger med Didact, har en Installér-knap), historikken (Fortryd, Gentag, Spring tilbage, Ryd), gemmepunkter (spol tilbage, fjern) og sikkerhedskopier (tag en sikkerhedskopi nu, gendan, slet, behold de nyeste; dem, der laves, når en spilgang slutter, er markeret auto). Når ingen kampagne er åben, viser Oversigt verdenens kampagner, så du kan åbne en.
  - At slette en verden eller kampagne spørger først, og Fortryd bringer det hele tilbage.
  - Spring tilbage (ved siden af hver ændring) tager alt efter den ændring tilbage (`didact undo --to e40`): dens side viser først, hvad der forsvinder. Hver ændring fortrydes, og hvert slag markeres som fortrudt, ikke slettet: Gentag, eller at springe tilbage til en senere ændring, bringer dem tilbage. Vis ældre ændringer viser mere af historikken.
  - Kernepakken er altid slået til. Der er kun ét spilsystem i brug ad gangen: den åbne verdens, som den beholder for altid (valgt, når den oprettes). Et andet system spilles i sin egen verden: systemets række åbner en verden, hvor det spilles, eller opretter en ny. At afinstallere en pakke kan ikke fortrydes: installér dens .didactpack igen.
  - At rydde historikken viser først præcis, hvad der forsvinder, og hvad der holder op med at virke, med en knap til at tage en sikkerhedskopi først. Det kan ikke fortrydes, og det kan sletning af en sikkerhedskopi heller ikke.
  - Start forfra: **Nulstil…** tømmer biblioteket, som om Didact lige var installeret, og nummereringen starter forfra ved #e1. Dens side viser først, hvad der forsvinder. Der tages først en sikkerhedskopi af biblioteket, og sikkerhedskopierne bliver (installerede pakker også, medmindre du sætter kryds i feltet).
  - At gendanne en sikkerhedskopi viser først, hvad den indeholder, ved siden af biblioteket, som det er nu. Der tages først en sikkerhedskopi af biblioteket, som det var: Fortryd kan ikke tage en gendannelse tilbage, men det kan en gendannelse af den sikkerhedskopi.
- **Kommandoer:** alle kommandoer som formularer og et felt, der tager en hel kommandolinje. Hvert felt tager det, dets argument tager: et tal, et id eller en hændelse (`e12`) efter sit mønster, en mængde spiltid som et tal og en enhed, og en liste at vælge fra med opslagene, kladderne, pakkerne, gemmepunkterne, oraklerne, tabellerne og reglerne her.
- **Indstillinger:** kampagnens tilvalg (dens systems varianter og valgfrie regler, som regler, personskabelse og generatorer følger; hvert siger, hvad det gør: en valgfri regel, hvad det ændrer at slå den til, et valg, hvad hver af dets værdier betyder, og en standard, som et andet tilvalg sætter, siger hvilket), appens sprog, synonymordbogen (det sprog, søgninger bruger til synonymer: hent et, med en statuslinje, skift mellem de hentede, fjern et) og kodens dokumentation.
  - Appen, dens guider og det, kommandoer viser i den, findes på 24 sprog. Uden et valg følger appen browserens sprog. Kommandolinjen og de LLM'er, der bruger den, bliver på engelsk: sproget, der vælges her, gælder kun appen.
  - Kodeknappen i topbjælken åbner kodens API-dokumentation. Den bygges ud fra koden første gang og igen, når koden ændres (`didact docs build`).

Hver ændring kører en rigtig `didact`-kommando, så den tjekkes, logges og kan fortrydes præcis som på kommandolinjen. Appen viser hver gang den kommando, den kørte (`didact set sweeney hp-=2`), med en Fortryd-knap, når der er noget at tage tilbage.

Et indtastningsfelt tager kun det, dets kommando tager. Et id (en verdens eller en kampagnes) og en opslagstype tager små bogstaver, cifre og bindestreger: mens du skriver, bliver mellemrum til bindestreger og store bogstaver til små. Et feltnavn tager ingen mellemrum (de bliver til understreger), en detaljes navn er ét ord, og talfelter tager tal. Hvad et indtastningsfelt tager, står under det, og kommandoen tjekker alligevel igen.

At gemme overskriver aldrig en ændring, du ikke har set. Hvis opslaget ændrede sig, efter at siden viste det (en LLM ændrede det fra kommandolinjen, for eksempel, eller en anden fane gjorde), afvises det at gemme, og du får at vide, hvad der står der nu. En beskrivelse, du var ved at redigere, bliver i editoren ved siden af den nye version, så du kan flette og gemme igen. − og + går altid igennem: de lægges sammen.

## Spillervisning og SL-visning

Appen viser det, spillerne ved, ligesom `didact show` gør: hemmelige opslag, `## Secrets`-afsnit, hemmelige felter og detaljer kun til SL holdes ude. Knappen **GM** i topbjælken slår SL-visning til, og et banner siger det (»SL-visning: spoilere vises«). Browseren husker valget.

I spillervisningen:
- kan en beskrivelse med linjer kun til SL ikke redigeres (at gemme den ville miste dem): slå SL-visning til først;
- kan en SL-detalje eller et hemmeligt felt, som siden ikke viser, ikke overskrives, men en ny note til SL kan tilføjes;
- nævner historikken kommandoen og de opslag, spillerne kender (`set · Freya`), aldrig værdierne, og Fortryd siger, hvilken ændring den tog tilbage, ikke hvad den var.

## Sikkerhed

Appen kan ændre dit bibliotek, så som standard lytter den kun til denne maskine.

- `--host` med en anden adresse lader andre maskiner nå den, og Didact advarer om det. Brug det kun på et netværk, du stoler på.
- Den svarer kun på forespørgsler, der er adresseret til den selv (dens egen adresse, `localhost`, `127.0.0.1` eller `[::1]`, med dens port). Det forhindrer andre hjemmesider i at nå den gennem DNS-tricks.
- Hver ændring kræver en formular fra selve appen: et hemmeligt token i hver formular skal matche en cookie, som andre sider ikke kan læse eller sende.
- Der er intet login. Alle, der kan bruge denne computers browser, kan bruge appen.
