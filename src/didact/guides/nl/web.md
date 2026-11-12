<!-- translated from 5a088227a31a -->
# De browserapp

`didact serve` opent je bibliotheek in een webbrowser: items verkennen en bewerken, in een graaf zien hoe ze gekoppeld zijn, het logboek lezen, regels en tabellen uitvoeren, en elke opdracht via een formulier gebruiken.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Ze werkt offline: de lettertypen en pictogrammen worden met Didact meegeleverd.

**Demomodus.** `--demo` serveert de voorbeeldcampagne (`didact sample`: een riviervallei, een PC, personen met de notities van de SL, plaatsen en paden, een quest, een klok, en een lopende sessie met een gevecht) uit een eigen bibliotheek, naast de cachemap van Didact. Alle pakketten die met Didact meekomen, zijn daar geïnstalleerd. Die wordt bij elke start van `--demo` vers opgebouwd, dus probeer gerust alles: je eigen bibliotheek blijft onaangeroerd.

## Opties

| Optie | Standaard | Wat het doet |
|---|---|---|
| `--port <n>` | 8765 | de poort om op te luisteren |
| `--host <address>` | 127.0.0.1 | het adres om op te luisteren: alleen deze computer |
| `--open` | uit | de app openen in een browsertabblad |
| `--gm` | uit | starten met de SL-weergave aan |
| `--demo` | uit | een verse voorbeeldcampagne serveren in plaats van je bibliotheek |

De globale opties `--home`, `--world` en `--campaign` gelden voor alles wat de app doet. Open je op de pagina Bibliotheek een andere wereld of campagne, dan schakelt de app daarnaar over, zoals bij `didact world use` en `didact campaign open`, en Sluiten legt de geopende campagne weg (`didact campaign close`).

## Wat erin zit

- **Overzicht:** de briefing (wereld, campagne, sessie, scène, groep, wat er aan de beurt is), snelle acties (dobbelstenen gooien, het orakel raadplegen met de kansen die het kent, een gebeurtenis vastleggen, een sessie starten of beëindigen, een nieuw item) en de laatste wijzigingen.
- **Status:** hoe alles ervoor staat, in één oogopslag: de sessie en scène, de tijd en de komende herinneringen, de waarden van elk groepslid en wat het bij zich heeft, het gevecht (wie aan de beurt is, toestanden), openstaande quests en tellers, en waar de groep is met haar uitwegen. De waarden kun je daar meteen bijstellen: − en + bij een waarde, een teller afvinken, een voorwerp gebruiken of weggooien, er een toevoegen, een quest afronden, de tijd vooruitzetten (een getal, en een eenheid die de kalender kent: uren, wachten, dagen, …), een herinnering instellen (eenmalig of geregeld) en er een annuleren.
- **Items:** elk item, gegroepeerd per type, met een filtervak en de chips Alles, Wereld of Campagne. De pagina van een item toont het blad, de beschrijving, details, velden, inhoud, koppelingen in beide richtingen, de kroniek en de geschiedenis, met formulieren om elk daarvan te wijzigen en om het te archiveren of te verwijderen. Een personage waarvan het systeem een level-up kent, heeft een knop Level up (`char advance`): een concept dat laat zien wat er verandert, ervoor en erna, tot het is vastgelegd.
- **Concepten:** personages maken en generatoren, stap voor stap. Een personage maken (stap voor stap of willekeurig, waarbij je kiest welke soort als het systeem er meerdere heeft: een spelerspersonage, een huurling, …) en Genereren… staan op de pagina's Items; de wachtende concepten staan daar en op het Overzicht. De pagina van een concept toont wat het tot nu toe bevat (de entiteiten en hun velden, de kaart die een generator tekende, de worpen, de vragen van het boek) en de vraag waarop het wacht. Elke optie is een knop die zegt wat ze betekent als het pakket dat doet (wat een achtergrond geeft, wat een talent doet); wie er meerdere kiest, vinkt voor elk een vakje aan; scores die je met een budget koopt, zijn getallen die de punten meteen bijhouden; een naam of ander open antwoord kun je intypen; en De dobbelstenen laten beslissen gooit alleen voor die ene (`char roll c3 --one`). Terug draait de laatste stap terug, zodat de vraag ervan opnieuw komt (`char back c3`: de worpen die hij deed, worden als ongedaan gemarkeerd, en Ongedaan maken haalt de stap terug). Dan De rest gooien, Bewerken, Weggooien… (vraagt eerst) en Vastleggen, dat het item van het nieuwe personage opent, of toont wat de generator heeft gemaakt. Het concept van een generator is van de SL: de spelersweergave toont alleen dat het er is.
- **Graaf:** items als knopen en koppelingen als lijnen. Sleep knopen, sleep de achtergrond om te verschuiven, zoom met het scrollwiel; beweeg de muis erover om de buren van een item op te laten lichten; klik om er een te openen. De knop Graaf op de pagina van een item toont alleen de omgeving ervan.
  - **Kaart** (de schakelaar boven de graaf, of De kaart openen op Status): de plaatsen die de groep kent, de paden ertussen (met labels als road, trail, …), de regio waarin elke plaats ligt (gestreept), en waar de groep is. Een pad naar een plaats die nog niet gevonden is, leidt naar een “?”; de SL-weergave toont elke plaats.
- **Logboek:** de sessies, die elk openklappen tot hun scènes, gebeurtenissen en worpen. Elke gebeurtenis heeft Bewerken en Verwijderen (beweeg de muis erover), die de formulieren van `beat edit` en `beat rm` openen.
- **Naslag:** alles doorzoeken (resultaten verschijnen terwijl je typt), de regels van de ingeschakelde pakketten via formulieren uitvoeren, op hun tabellen gooien, en hun regeltekst, woordenlijst en gidsen lezen.
- **Bibliotheek:** werelden en campagnes (openen, sluiten, maken, verwijderen), pakketten (elk met wat het is; inschakelen, uitschakelen, installeren, deïnstalleren; de pakketten die met Didact meekomen hebben een knop Installeren), de geschiedenis (Ongedaan maken, Opnieuw, Terugspringen, Wissen), herstelpunten (terugspoelen, verwijderen) en back-ups (nu een back-up maken, herstellen, verwijderen, de nieuwste paar bewaren; die bij het einde van een sessie zijn gemaakt, zijn gemarkeerd met auto). Is er geen campagne geopend, dan toont het Overzicht de campagnes van de wereld om er een te openen.
  - Een wereld of campagne verwijderen vraagt eerst, en Ongedaan maken haalt alles terug.
  - Terugspringen (naast elke wijziging) draait alles na die wijziging terug (`didact undo --to e40`): de pagina ervan toont eerst wat er verdwijnt. Elke wijziging wordt ongedaan gemaakt en elke worp als ongedaan gemarkeerd, niet verwijderd: Opnieuw, of terugspringen naar een latere wijziging, haalt ze terug. Oudere wijzigingen tonen toont meer van de geschiedenis.
  - Het pakket core staat altijd aan. Er is maar één spelsysteem tegelijk in gebruik: dat van de geopende wereld, die het voorgoed houdt (gekozen bij het maken). Een ander systeem wordt in een eigen wereld gespeeld: de rij ervan opent een wereld waarin het gespeeld wordt, of maakt een nieuwe. Een pakket deïnstalleren kan niet ongedaan worden gemaakt: installeer de .didactpack opnieuw.
  - Het wissen van de geschiedenis toont eerst precies wat er verdwijnt en wat niet meer werkt, met een knop om eerst een back-up te maken. Het kan niet ongedaan worden gemaakt, en het verwijderen van een back-up ook niet.
  - Opnieuw beginnen: **Resetten…** maakt de bibliotheek leeg, alsof Didact net geïnstalleerd is, en de nummering begint weer bij #e1. De pagina ervan toont eerst wat er verdwijnt. Eerst wordt er een back-up van de bibliotheek gemaakt, en back-ups blijven (geïnstalleerde pakketten ook, tenzij je het vakje aanvinkt).
  - Een back-up herstellen toont eerst wat die bevat naast de huidige bibliotheek. Van de bibliotheek zoals ze was wordt eerst een back-up gemaakt: Ongedaan maken kan een herstel niet terugdraaien, maar die back-up herstellen wel.
- **Opdrachten:** elke opdracht als formulier, en een vak dat een hele opdrachtregel aanneemt. Elk vak neemt aan wat zijn argument aanneemt: een getal, een id of een event (`e12`) volgens zijn patroon, een hoeveelheid speltijd als een getal en een eenheid, en een lijst om uit te kiezen van de items, concepten, pakketten, herstelpunten, orakels, tabellen en regels hier.
- **Instellingen:** de opties van de campagne (de varianten en optionele regels van haar systeem, die regels, personages maken en generatoren volgen; elk zegt wat het doet: een optionele regel wat aanzetten verandert, een keuze wat elk van haar waarden betekent, en een standaard die een andere optie instelt, zegt welke), de taal van de app, de thesaurus (de taal die zoekopdrachten voor synoniemen gebruiken: een downloaden, met een voortgangsbalk, wisselen tussen de gedownloade, een verwijderen) en de documentatie van de code.
  - De app, de gidsen en wat opdrachten erin tonen zijn er in 24 talen. Zonder keuze volgt de app de taal van de browser. De opdrachtregel en de LLM's die hem gebruiken blijven Engels: de taal die je hier kiest, geldt alleen voor de app.
  - De codeknop in de kopbalk opent de API-documentatie van de code. Die wordt de eerste keer uit de code opgebouwd, en opnieuw zodra de code verandert (`didact docs build`).

Elke wijziging voert een echte `didact`-opdracht uit, dus ze wordt precies zoals op de opdrachtregel gecontroleerd, gelogd en kan ongedaan worden gemaakt. De app toont elke keer de opdracht die ze uitvoerde (`didact set sweeney hp-=2`), met een knop Ongedaan maken als er iets terug te draaien valt.

Een vak neemt alleen aan wat zijn opdracht aanneemt. Een id (van een wereld of een campagne) en een itemtype nemen kleine letters, cijfers en streepjes: terwijl je typt, worden spaties streepjes en hoofdletters kleine letters. De naam van een veld neemt geen spaties (die worden underscores), de naam van een detail is één woord, en getalvakken nemen getallen. Wat een vak aanneemt, staat eronder, en de opdracht controleert het toch nog een keer.

Opslaan overschrijft nooit een wijziging die je niet hebt gezien. Is het item veranderd nadat de pagina het toonde (bijvoorbeeld doordat een LLM het via de opdrachtregel wijzigde, of een ander tabblad), dan wordt het opslaan geweigerd en zie je wat er nu staat. Een beschrijving die je aan het bewerken was, blijft in de editor, naast de nieuwe versie, om samen te voegen en opnieuw op te slaan. − en + gaan altijd door: ze tellen op.

## Spelersweergave en SL-weergave

De app toont wat de spelers weten, zoals `didact show`: geheime items, secties `## Secrets`, geheime velden en details alleen voor de SL blijven buiten beeld. De knop **GM** in de kopbalk zet de SL-weergave aan, en een banner meldt dat (“SL-weergave: spoilers zichtbaar”). De browser onthoudt de keuze.

In de spelersweergave:
- kan een beschrijving met regels alleen voor de SL niet worden bewerkt (bij opslaan zouden die verloren gaan): zet eerst de SL-weergave aan;
- kan een SL-detail of geheim veld dat de pagina niet toont niet worden overschreven, al kan er wel een nieuwe notitie voor de SL bij;
- noemt de geschiedenis de opdracht en de items die de spelers kennen (`set · Freya`), nooit de waarden, en Ongedaan maken zegt welke wijziging het terugdraaide, niet wat die inhield.

## Veiligheid

De app kan je bibliotheek wijzigen, dus luistert ze standaard alleen naar deze computer.

- Met `--host` en een ander adres kunnen andere computers haar bereiken, en Didact waarschuwt daarvoor. Gebruik het alleen op een netwerk dat je vertrouwt.
- Ze beantwoordt alleen verzoeken die aan haarzelf gericht zijn (haar eigen adres, `localhost`, `127.0.0.1` of `[::1]`, met haar poort). Zo kunnen andere websites haar niet via DNS-trucs bereiken.
- Elke wijziging vereist een formulier van de app zelf: een geheim token in elk formulier moet overeenkomen met een cookie dat andere sites niet kunnen lezen of versturen.
- Er is geen login. Iedereen die de browser van deze computer kan gebruiken, kan de app gebruiken.
