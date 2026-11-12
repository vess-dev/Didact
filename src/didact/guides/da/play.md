<!-- translated from bef7b2c650cb -->
# Sådan spiller du en spilgang

Sådan kører et spil gennem Didact: LLM'en fortæller, og Didact holder styr på hvert faktum, hvert slag og hver ændring.

## Før den første spilgang

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

En verden beholder det system, den blev oprettet med, og dens kampagner spilles med det: et andet system spilles i sin egen verden. `didact campaign close` lægger en kampagne til side (dens verden forbliver åben), og `didact campaign open <id>` tager den op igen, hvor den slap, med spilgang og det hele.

`didact world delete <id>` og `didact campaign delete <id>` fjerner en af dem, med en forhåndsvisning først; `--yes` sletter, og `didact undo` bringer det hele tilbage.

`session zero` viser de spørgsmål, der skal afklares med spilleren. Pakkens egne kommer først. Systemets tilvalg (dets varianter og valgfrie regler) er blandt dem: reglerne følger svarene, og briefingen siger, hvad hvert ændret tilvalg betyder. Hver briefing har svarene med.

## En spilgang

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Ture:** hver besked fra spilleren åbner en tur (Claude Code-hooket kalder `didact capture`, og andre klienter bruger `turn begin`). `didact undo --turn` tager alt tilbage, der blev gjort for den besked: ændringer, begivenheder og slag. Transskriptet beholder det.
- **At springe tilbage:** `didact undo --to e40` tager alt efter #e40 tilbage, nyeste først (`--dry-run` viser det): hver ændring fortrydes, og hvert slag markeres som fortrudt. Intet slettes: `redo`, eller at springe tilbage til en senere ændring, bringer det tilbage.
- **Tid:** `didact time advance 1 watch` lader timere løbe ud, fremkalder påmindelser og kører tidsudløsere. `didact remind --list` viser de kommende påmindelser, og `didact remind --cancel 2` dropper en. En kampagne begynder på kalenderens start eller på den dato, `campaign new --date '4 July 1902'` angiver, og `didact time set '<date>'` ændrer den indtil første spilgang.
- **Steder:** `didact visit <place>` flytter gruppen og markerer stedet som besøgt. `didact map` viser, hvad gruppen kender, og en uudforsket udgang er `?`.
- **Kampe:** `didact combat start --party troll`, derefter `combat next`, `combat hit freya troll weapon=d8` og `combat end`. Kæmpere kommer og går midt i kampen: `didact combat join wolf-2` (i individuel tilstand slår de initiativ) og `didact combat leave troll --why fled`. Ingens tur springes over.
- **Ting:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (eller ned i en kiste eller hen på et sted); `didact where rope` finder den. `inv add` finder en genstand i kompendiet via dens id, dens navn eller et alias.
- **Dine noter:** `didact about sweeney plan='…' doing='…' where='…'` gemmer det, du har besluttet om nogen eller noget. Spillerne ser kun `looks`. `didact log … --about sweeney` sætter en begivenhed på deres opslag (`--secret`, hvis spillerne ikke ser den). `didact guide details` fortæller mere.
- **Verden går videre:** `didact faction turn` plus ure: `didact track new 'The flood' --size 6`. En kommando, der kun tager én slags opslag, tager et navn, som andre deler, som den slags: `didact track roll draugr` slår den pulje, der bærer en fjendes navn (ligeså `track tick` en tæller, `quest done` en quest og `visit` et sted).

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

Intet, som en generator eller personskabelse laver, gemmes før `commit`. Beskriv, hvad spilleren vil have, i `--prefill`, så udfylder proceduren resten. Et spørgsmål viser, hvad hver mulighed betyder, når pakken siger det (`- Cutpurse: …`): fortæl spilleren det, så de ved, hvad de får, når de vælger.

## Hemmeligheder

Visninger er som standard sikre for spillerne: `show`, `find`, `sheet`, `map`, `brief`. De udelader:
- hemmelige opslag (`knowledge: secret`);
- afsnittene `## Secrets` og `## GM notes`;
- felter med `secret: true`.

`--gm` viser alt. Når spillerne finder ud af noget:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` skriver det, spillerne ved, som en lille hjemmeside, der kan deles eller læses på en telefon: gruppen, en side pr. opslag, journalen og kortet. Den er altid sikker for spillerne, og eksporterer du igen til samme mappe, opdateres den. `didact export --as lonelog` skriver journalen i Lonelog-notation (`@ ? d: -> =>`, scener som `S1`, tags som `[N:Sweeney]`), også sikker for spillerne.

## Lore: det, der dukker op, når noget nævnes

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Hvad tæller med:** hver biperson, hvert sted, hver genstand og hver fraktion er et kort med navn og aliasser som nøgler. Lore-indgange har `keys`, og afgørelser dukker op gennem deres regel. Der matches på hele ord, og flertal tæller med (»wolves« matcher `wolf`).
- **Hvornår lore dukker op:** Claude Code-hooket gennemsøger hver besked fra spilleren. `log`, `scene new` og `show` har også nyudløst lore med, og en indgang gentages ikke før efter nogle ture.
- **Finjustér en indgang:** `--secondary` med `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (i ture eller scener), `--constant` (altid i briefingen) og `--no-recurse`.
- **Omfang:** indgange hører til kampagnen, medmindre `--scope` siger world, system eller global. En søgning ser kun denne kampagne, dens verden, dens system og global, aldrig en anden verden. En snævrere indgang med samme id skygger for en bredere.
- **Andre værktøjers lorebøger:** `didact lore import <file>` læser SillyTavern World Info (også KoboldAI's), lorebogen i et personkort og NovelAI's `.lorebook`; `didact lore export --to <file>` skriver World Info. Nøgler, logik, prioritet, sandsynlighed, grupper og timing tages med.

## Ændr historien

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` ændrer faktummet, men beholder den gamle værdi. Den markerer også resuméer, der nævner Sweeney, som forældede, og `audit` viser dem.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` registrerer en afgørelse. Den dukker så op i `rules lookup`, og når reglen kører.
- `didact name npc` slår et nyt navn, aldrig et, verdenen allerede bruger. Før du selv finder på et, så tjek det med `didact names check <name>`. `didact names forget <name>` frigiver et igen.

## Oprydning

- `didact history --clear` viser, hvad rydning af gammel historik ville fjerne; `--yes` fjerner det for altid, slettede opslag inklusive, og fortryd, `diff`, `rewind` og ældre gemmepunkter kan ikke længere nå det (`--before e120` beholder den hændelse og de senere, `--rolls` fjerner også terningloggen). Kør `didact snapshot` først.
- `didact save --remove 'before the dragon'` fjerner et gemmepunkt; `didact undo` bringer det tilbage.
- `didact transcript 3 --clear` sletter transskriptet for spilgang 3 (`--clear --all`: for alle spilgange). `didact undo` bringer det tilbage, og teksten bliver i historikken indtil `history --clear`.
- `didact compendium remove <entry>` sletter en indgang, du har tilføjet; opslag, der er skabt ud fra den, bliver.
- `didact snapshot --keep 3` sletter alle sikkerhedskopier undtagen de tre nyeste, og `didact snapshot --remove <name>` sletter én. Ingen af dem kan fortrydes.
- `didact session end` tager selv en sikkerhedskopi af biblioteket (`snapshot-<time>-auto.zip`) og beholder de fem nyeste af dem; `didact snapshot --list` markerer dem.
- `didact reset` viser, hvad det ville fjerne at tømme biblioteket; `--yes` gør det som nyinstalleret: alle verdener, kampagner og opslag, historikken og søgeindekset forsvinder, og den næste ændring er #e1 igen. Den tager først en sikkerhedskopi af biblioteket (`…-before-reset.zip`), og sikkerhedskopierne bliver, ligesom installerede pakker, medmindre `--packs`. Vil du i stedet prøve Didact på en færdig kampagne, bygger `didact sample` eksempelkampagnen i et tomt bibliotek (`--home` giver den sin egen mappe), og `didact serve --demo` viser den helt frisk.
- `didact snapshot --restore <name>` viser, hvad en sikkerhedskopi indeholder, ved siden af biblioteket, som det er nu; `--yes` tager en sikkerhedskopi af biblioteket, som det er (`…-before-restore.zip`), og sætter så sikkerhedskopien i stedet. Hændelses- og slagnumre fortsætter. Fortryd kan ikke tage en gendannelse tilbage: det kan en gendannelse af den sikkerhedskopi.
