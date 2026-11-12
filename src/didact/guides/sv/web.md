<!-- translated from 5a088227a31a -->
# Webbläsarappen

`didact serve` öppnar ditt bibliotek i en webbläsare: utforska och redigera uppslag, se hur de hänger ihop i en graf, läs journalen, kör regler och tabeller, och använd varje kommando via ett formulär.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Den fungerar offline: typsnitten och ikonerna följer med Didact.

**Demoläge.** `--demo` visar exempelkampanjen (`didact sample`: en floddal, en rollperson, personer med SL:s anteckningar, platser och vägar, ett uppdrag, en klocka och ett pågående spelmöte med en strid) från ett eget bibliotek, bredvid Didacts cachemapp. Där är alla paket som följer med Didact installerade. Den byggs på nytt varje gång `--demo` startar, så prova vad du vill: ditt eget bibliotek rörs inte.

## Alternativ

| Alternativ | Standard | Vad det gör |
|---|---|---|
| `--port <n>` | 8765 | porten att lyssna på |
| `--host <address>` | 127.0.0.1 | adressen att lyssna på: bara den här datorn |
| `--open` | av | öppna appen i en webbläsarflik |
| `--gm` | av | starta med SL-vyn på |
| `--demo` | av | visa en ny exempelkampanj i stället för ditt bibliotek |

De globala `--home`, `--world` och `--campaign` gäller allt appen gör. Att öppna en annan värld eller kampanj på appens sida Bibliotek byter till den, som `didact world use` och `didact campaign open` gör, och Stäng lägger undan den öppna kampanjen (`didact campaign close`).

## Vad som finns i den

- **Översikt:** lägesbilden (värld, kampanj, spelmöte, scen, grupp, vad som står på tur), snabbåtgärder (slå tärningar, fråga oraklet med de odds det känner till, logga en händelse, starta eller avsluta ett spelmöte, ett nytt uppslag) och de senaste ändringarna.
- **Läge:** hur saker står till, i en blick: spelmötet och scenen, tiden och kommande påminnelser, varje gruppmedlems siffror och vad de bär, striden (vems tur, tillstånd), öppna uppdrag och räknare, och var gruppen är och vägarna därifrån. Siffrorna kan justeras direkt: − och + på ett värde, bocka av på en räknare, använd eller släpp ett föremål, lägg till ett, slutför ett uppdrag, flytta fram tiden (ett tal och en enhet som kalendern känner till: timmar, vakter, dagar, …), ställ in en påminnelse (en gång, eller med jämna mellanrum) och avbryt en.
- **Uppslag:** varje uppslag, grupperat efter typ, med en filterruta och valen Alla, Värld och Kampanj. Ett uppslags sida visar dess ark, beskrivning, detaljer, fält, innehåll, kopplingar åt båda hållen, dess krönika och dess historik, med formulär för att ändra vart och ett av dem, och för att arkivera eller radera det. En rollperson vars system har en procedur för ny nivå har en Level up-knapp (`char advance`): ett utkast som visar vad som ändras, före och efter, tills det är godkänt.
- **Utkast:** rollpersonsskapande och generatorer, ett steg i taget. Skapa en rollperson (steg för steg eller slumpmässigt, och med val av sort när systemet har flera: en rollperson, en hyrling, …) och Generera… finns på sidorna Uppslag; de väntande utkasten listas där och på Översikt. Ett utkasts sida visar vad det innehåller hittills (dess entiteter och deras fält, kartan en generator ritade, slagen, bokens uppmaningar) och frågan det väntar på. Varje alternativ är en knapp som säger vad det betyder när paketet gör det (vad en bakgrund ger, vad en talang gör); när flera ska väljas finns en ruta att kryssa i för vart och ett; värden som köps inom en budget är tal som räknar poängen medan du skriver; ett namn eller annat fritt svar kan skrivas in; och Låt tärningarna avgöra slår just det (`char roll c3 --one`). Tillbaka tar tillbaka det senaste steget, så att dess fråga kommer igen (`char back c3`: slagen det gjorde markeras som ångrade, och Ångra tar tillbaka steget). Sedan Slå resten, Redigera, Kasta… (det frågar först) och Godkänn, som öppnar den nya rollpersonens uppslag, eller listar vad generatorn skapade. En generators utkast är SL:s: spelarvyn visar bara att det finns.
- **Graf:** uppslag som noder och kopplingar som kanter. Dra noder, dra bakgrunden för att panorera, zooma med hjulet; hovra för att lysa upp ett uppslags grannar; klicka för att öppna ett. Knappen Graf på ett uppslags sida visar bara dess närmaste grannskap.
  - **Karta** (reglaget ovanför grafen, eller Öppna kartan på Läge): platserna gruppen känner till, vägarna mellan dem (märkta väg, stig, …), regionen var och en ligger i (streckad) och var gruppen är. En väg till en plats som inte hittats än leder till ett ”?”; SL-vyn visar alla platser.
- **Journal:** spelmötena, som vart och ett öppnas till sina scener, händelser och slag. Varje händelse har Redigera och Ta bort (hovra över den), som öppnar formulären för `beat edit` och `beat rm`.
- **Referens:** sök i allt (resultaten visas medan du skriver), kör de aktiverade paketens regler via formulär, slå på deras tabeller och läs deras regeltext, ordlista och guider.
- **Bibliotek:** världar och kampanjer (öppna, stäng, skapa, radera), paket (vart och ett med vad det är; aktivera, inaktivera, installera, avinstallera; paketen som följer med Didact har en Installera-knapp), historiken (Ångra, Gör om, Hoppa tillbaka, Rensa), sparpunkter (spola tillbaka, ta bort) och säkerhetskopior (säkerhetskopiera nu, återställ, radera, behåll de nyaste; de som görs när ett spelmöte avslutas är märkta auto). När ingen kampanj är öppen listar Översikt världens kampanjer, så att du kan öppna en.
  - Att radera en värld eller kampanj frågar först, och Ångra tar tillbaka allt.
  - Hoppa tillbaka (bredvid varje ändring) tar tillbaka allt efter den ändringen (`didact undo --to e40`): dess sida visar först vad som försvinner. Varje ändring ångras och varje slag markeras som ångrat, utan att något raderas: Gör om, eller att hoppa tillbaka till en senare ändring, tar tillbaka dem. Visa äldre ändringar visar mer av historiken.
  - Kärnpaketet är alltid på. Bara ett spelsystem används i taget: den öppna världens, som den behåller för gott (valt när den skapas). Ett annat system spelas i en egen värld: systemets rad öppnar en värld där det spelas, eller skapar en ny. Att avinstallera ett paket kan inte ångras: installera dess .didactpack igen.
  - Att rensa historiken visar först exakt vad som försvinner och vad som slutar fungera, med en knapp för att säkerhetskopiera först. Det kan inte ångras, och det kan inte heller radering av en säkerhetskopia.
  - Börja om: **Nollställ…** tömmer biblioteket, som om Didact vore nyinstallerat, och numreringen börjar om från #e1. Dess sida visar först vad som försvinner. Biblioteket säkerhetskopieras först, och säkerhetskopiorna finns kvar (installerade paket också, om du inte kryssar i rutan).
  - Att återställa en säkerhetskopia visar först vad den innehåller jämfört med biblioteket nu. Biblioteket som det var säkerhetskopieras först: Ångra kan inte ta tillbaka en återställning, men det kan en återställning av den säkerhetskopian.
- **Kommandon:** varje kommando som ett formulär, och en ruta som tar en hel kommandorad. Varje ruta tar det dess argument tar: ett tal, ett id eller en händelse (`e12`) enligt sitt mönster, en mängd speltid som ett tal och en enhet, och en lista att välja från med uppslagen, utkasten, paketen, sparpunkterna, oraklen, tabellerna och reglerna här.
- **Inställningar:** kampanjens alternativ (dess systems varianter och valfria regler, som reglerna, rollpersonsskapandet och generatorerna följer; vart och ett säger vad det gör: en valfri regel vad det ändrar att slå på den, ett val vad vart och ett av dess värden betyder, och ett standardvärde som ett annat alternativ sätter säger vilket), appens språk, synonymordboken (språket sökningar använder för synonymer: ladda ner ett, med en förloppsindikator, växla mellan de nedladdade, ta bort ett) och kodens dokumentation.
  - Appen, dess guider och det som kommandon visar i den finns på 24 språk. Utan ett val följer appen webbläsarens språk. Kommandoraden och de LLM:er som använder den stannar på engelska: språket som väljs här gäller bara appen.
  - Kodknappen i rubrikfältet öppnar kodens API-dokumentation. Den byggs från koden första gången, och igen när koden ändras (`didact docs build`).

Varje ändring kör ett riktigt `didact`-kommando, så den kontrolleras, loggas och kan ångras precis som på kommandoraden. Appen visar kommandot den körde varje gång (`didact set sweeney hp-=2`), med en Ångra-knapp när det finns något att ta tillbaka.

En ruta tar bara det dess kommando tar. Ett id (en världs eller en kampanjs) och en uppslagstyp tar gemener, siffror och bindestreck: medan du skriver blir mellanslag bindestreck och versaler gemener. Ett fältnamn tar inga mellanslag (de blir understreck), en detaljs namn är ett ord, och talrutor tar tal. Vad en ruta tar står under den, och kommandot kontrollerar ändå igen.

Att spara skriver aldrig över en ändring du inte har sett. Om uppslaget ändrades efter att sidan visade det (om en LLM ändrade det från kommandoraden, till exempel, eller en annan flik gjorde det) nekas sparningen, och du får se vad som finns där nu. En beskrivning du redigerade stannar kvar i redigeraren, bredvid den nya versionen, så att du kan slå ihop och spara igen. − och + går alltid igenom: de läggs ihop.

## Spelarvy och SL-vy

Appen visar det spelarna vet, som `didact show` gör: hemliga uppslag, `## Secrets`-avsnitt, hemliga fält och detaljer endast för SL hålls utanför. Knappen **GM** i rubrikfältet slår på SL-vyn, och en banderoll säger det (”SL-vy: spoilers visas”). Webbläsaren kommer ihåg valet.

I spelarvyn:
- en beskrivning med rader endast för SL kan inte redigeras (att spara den skulle förlora dem): slå på SL-vyn först;
- en SL-detalj eller ett hemligt fält som sidan inte visar kan inte skrivas över, men en ny anteckning för SL kan läggas till;
- historiken anger kommandot och de uppslag spelarna känner till (`set · Freya`), aldrig värdena, och Ångra säger vilken ändring den tog tillbaka, inte vad den var.

## Säkerhet

Appen kan ändra ditt bibliotek, så som standard lyssnar den bara på den här datorn.

- `--host` med en annan adress låter andra datorer nå den, och Didact varnar för det. Använd det bara på ett nätverk du litar på.
- Den svarar bara på förfrågningar som är adresserade till den själv (dess egen adress, `localhost`, `127.0.0.1` eller `[::1]`, med dess port). Det hindrar andra webbplatser från att nå den via DNS-trick.
- Varje ändring kräver ett formulär från appen själv: en hemlig token i varje formulär måste matcha en cookie som andra webbplatser inte kan läsa eller skicka.
- Det finns ingen inloggning. Den som kan använda den här datorns webbläsare kan använda appen.
