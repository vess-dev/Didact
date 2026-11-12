<!-- translated from bef7b2c650cb -->
# Att spela ett spelmöte

Hur ett spel går till genom Didact: LLM:en berättar, och Didact håller reda på varje fakta, slag och ändring.

## Före första spelmötet

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

En värld behåller systemet den skapades med, och dess kampanjer spelas med det: ett annat system spelas i en egen värld. `didact campaign close` lägger undan en kampanj (dess värld förblir öppen) och `didact campaign open <id>` tar upp den igen där den slutade, med spelmöte och allt.

`didact world delete <id>` och `didact campaign delete <id>` tar bort en värld eller kampanj, med förhandsvisning först; `--yes` raderar, och `didact undo` tar tillbaka allt.

`session zero` listar frågorna att komma överens om med spelaren. Paketets egna kommer först. Systemets alternativ (dess varianter och valfria regler) hör dit: dess regler följer svaren, och sammanfattningen säger vad varje ändrat alternativ betyder. Varje lägesbild har med svaren.

## Ett spelmöte

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turer:** varje spelarmeddelande öppnar en tur (Claude Code-hooken anropar `didact capture`, och andra klienter använder `turn begin`). `didact undo --turn` tar tillbaka allt som gjordes för det meddelandet: ändringar, händelser och slag. Transkriptet behåller det.
- **Hoppa tillbaka:** `didact undo --to e40` tar tillbaka allt efter #e40, nyaste först (`--dry-run` listar det): varje ändring ångras och varje slag markeras som ångrat. Inget raderas: `redo`, eller att hoppa tillbaka till en senare ändring, tar tillbaka det.
- **Tid:** `didact time advance 1 watch` låter timers löpa ut, tar fram påminnelser och kör tidsutlösare. `didact remind --list` visar kommande påminnelser, och `didact remind --cancel 2` stryker en. En kampanj börjar på kalenderns start, eller på datumet som `campaign new --date '4 July 1902'` anger, och `didact time set '<date>'` ändrar det fram till första spelmötet.
- **Platser:** `didact visit <place>` flyttar gruppen och markerar platsen som besökt. `didact map` visar vad gruppen känner till, och en outforskad utgång är `?`.
- **Strider:** `didact combat start --party troll`, sedan `combat next`, `combat hit freya troll weapon=d8` och `combat end`. Kämpar kommer och går mitt i striden: `didact combat join wolf-2` (i individuellt läge slår de initiativ) och `didact combat leave troll --why fled`. Ingens tur hoppas över.
- **Saker:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (eller ner i en kista, eller till en plats); `didact where rope` hittar det. `inv add` hittar ett föremål i kompendiet via dess id, dess namn eller ett alias.
- **Dina anteckningar:** `didact about sweeney plan='…' doing='…' where='…'` sparar det du har bestämt om någon eller något. Spelarna ser bara `looks`. `didact log … --about sweeney` lägger en händelse på deras uppslag (`--secret` om spelarna inte ser den). `didact guide details` har mer.
- **Världen går vidare:** `didact faction turn`, plus klockor: `didact track new 'The flood' --size 6`. Ett kommando som bara tar ett slags uppslag tar ett namn som andra delar som det slaget: `didact track roll draugr` slår poolen som bär en fiendes namn (likaså `track tick` en räknare, `quest done` ett uppdrag och `visit` en plats).

## Orakel, generatorer och rollpersoner

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

Inget som en generator eller rollpersonsskapandet gör skrivs förrän `commit`. Beskriv vad spelaren vill ha i `--prefill`, så fyller proceduren i luckorna. En fråga listar vad varje alternativ betyder när paketet säger det (`- Cutpurse: …`): berätta det för spelaren, så att de vet vad de får när de väljer.

## Hemligheter

Vyerna är säkra för spelarna som standard: `show`, `find`, `sheet`, `map`, `brief`. De utelämnar:
- hemliga uppslag (`knowledge: secret`);
- avsnitten `## Secrets` och `## GM notes`;
- fält med `secret: true`.

`--gm` visar allt. När spelarna får veta något:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` skriver det spelarna vet som en liten webbplats att dela eller läsa på telefonen: gruppen, en sida per uppslag, journalen och kartan. Den är alltid säker för spelarna, och en ny export till samma mapp uppdaterar den. `didact export --as lonelog` skriver journalen i Lonelog-notation (`@ ? d: -> =>`, scener som `S1`, taggar som `[N:Sweeney]`), också säker för spelarna.

## Lore: det som dyker upp när något nämns

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Vad som räknas:** varje SLP, plats, föremål och faktion är ett kort med sitt namn och sina alias som nycklar. Lore-poster har `keys`, och avgöranden dyker upp via sin regel. Matchningen sker på hela ord, och pluralformer räknas (”wolves” matchar `wolf`).
- **När lore dyker upp:** Claude Code-hooken skannar varje spelarmeddelande. `log`, `scene new` och `show` tar också med nyutlöst lore, och en post upprepas inte förrän några turer har gått.
- **Finjustera en post:** `--secondary` med `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (i turer eller scener), `--constant` (alltid i lägesbilden) och `--no-recurse`.
- **Omfång:** poster hamnar i kampanjen om inte `--scope` säger world, system eller global. En skanning ser bara den här kampanjen, dess värld, dess system och global, aldrig en annan värld. En smalare post med samma id skuggar en bredare.
- **Andra verktygs loreböcker:** `didact lore import <file>` läser SillyTavern World Info (även KoboldAI:s), ett karaktärskorts lorebok och NovelAI:s `.lorebook`; `didact lore export --to <file>` skriver World Info. Nycklar, logik, prioritet, sannolikhet, grupper och timing följer med.

## Ändra berättelsen

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` ändrar faktumet men behåller det gamla värdet. Den markerar också sammanfattningar som nämner Sweeney som inaktuella, och `audit` listar den.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` registrerar ett avgörande. Det visas sedan i `rules lookup` och när den regeln körs.
- `didact name npc` slår fram ett nytt namn, aldrig ett som världen redan använder. Innan du hittar på ett, kontrollera det med `didact names check <name>`. `didact names forget <name>` frigör ett igen.

## Städning

- `didact history --clear` visar vad en rensning av gammal historik skulle ta bort; `--yes` tar bort det för gott, raderade uppslag inräknade, och ångra, `diff`, `rewind` och äldre sparpunkter når det inte längre (`--before e120` behåller e120 och allt senare, `--rolls` tar bort tärningsregistret också). Kör `didact snapshot` först.
- `didact save --remove 'before the dragon'` tar bort en sparpunkt; `didact undo` tar tillbaka den.
- `didact transcript 3 --clear` raderar transkriptet för spelmöte 3 (`--clear --all`: alla spelmötens). `didact undo` tar tillbaka det, och texten finns kvar i historiken tills `history --clear`.
- `didact compendium remove <entry>` raderar en post du har lagt till; uppslag som skapats från den finns kvar.
- `didact snapshot --keep 3` raderar alla utom de tre nyaste säkerhetskopiorna, och `didact snapshot --remove <name>` raderar en. Ingen av dem kan ångras.
- `didact session end` säkerhetskopierar biblioteket av sig självt (`snapshot-<time>-auto.zip`) och behåller de fem nyaste av dem; `didact snapshot --list` markerar dem.
- `didact reset` visar vad en tömning av biblioteket skulle ta; `--yes` gör det som nyinstallerat: varje värld, kampanj och uppslag, historiken och sökindexet försvinner, och nästa ändring är #e1 igen. Det säkerhetskopierar biblioteket först (`…-before-reset.zip`), och säkerhetskopiorna finns kvar, liksom installerade paket om inte `--packs` anges. För att i stället prova Didact på en färdig kampanj bygger `didact sample` exempelkampanjen i ett tomt bibliotek (`--home` ger den en egen mapp), och `didact serve --demo` visar en nybyggd kopia av den.
- `didact snapshot --restore <name>` visar vad en säkerhetskopia innehåller jämfört med biblioteket nu; `--yes` säkerhetskopierar biblioteket som det är (`…-before-restore.zip`) och lägger sedan säkerhetskopian på dess plats. Ändrings- och slagnumren löper vidare. Ångra kan inte ta tillbaka en återställning: det kan en återställning av den säkerhetskopian.
