<!-- translated from bef7b2c650cb -->
# Hraní sezení

Jak hra přes Didact probíhá: LLM vypráví a Didact uchovává každý fakt, hod i změnu.

## Před prvním sezením

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Svět si ponechá systém, s nímž byl vytvořen, a jeho kampaně se hrají podle něj: jiný systém se hraje ve vlastním světě. `didact campaign close` kampaň odloží (její svět zůstane otevřený) a `didact campaign open <id>` v ní pokračuje tam, kde skončila, i se sezením a vším ostatním.

`didact world delete <id>` a `didact campaign delete <id>` svět či kampaň odeberou, nejdřív s náhledem; `--yes` maže a `didact undo` vše vrátí.

`session zero` vypíše otázky, které je třeba s hráčem vyjasnit. Nejdřív ty z balíčku. Patří k nim i volby systému (jeho varianty a volitelná pravidla): jeho pravidla se řídí odpověďmi a přehled říká, co každá změněná volba znamená. Každý briefing obsahuje odpovědi.

## Sezení

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Tahy:** každá zpráva hráče otevře tah (hook Claude Code volá `didact capture`, jiní klienti používají `turn begin`). `didact undo --turn` vezme zpět vše, co se pro tu zprávu udělalo: změny, události i hody. Přepis to zachová.
- **Skok zpět:** `didact undo --to e40` vezme zpět vše po #e40, od nejnovějšího (`--dry-run` to vypíše): každá změna bude vrácena a každý hod označen jako vrácený. Nic se nesmaže: `redo` nebo skok zpět na pozdější změnu to obnoví.
- **Čas:** `didact time advance 1 watch` nechá doběhnout časovače, vyvolá připomínky a spustí časové spouštěče. `didact remind --list` ukáže nadcházející připomínky a `didact remind --cancel 2` jednu zruší. Kampaň začíná začátkem kalendáře, nebo datem, které dá `campaign new --date '4 July 1902'`, a `didact time set '<date>'` ho mění až do prvního sezení.
- **Místa:** `didact visit <place>` přesune družinu a označí místo jako navštívené. `didact map` ukáže, co družina zná, a neprozkoumaný východ je `?`.
- **Boje:** `didact combat start --party troll`, pak `combat next`, `combat hit freya troll weapon=d8` a `combat end`. Bojovníci přicházejí a odcházejí během boje: `didact combat join wolf-2` (v individuálním režimu si hodí na iniciativu) a `didact combat leave troll --why fled`. Nikdo o svůj tah nepřijde.
- **Věci:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (nebo do truhly, nebo na místo); `didact where rope` ho najde. `inv add` najde předmět z kompendia podle jeho ID, jména nebo aliasu.
- **Vaše poznámky:** `didact about sweeney plan='…' doing='…' where='…'` uchová, co jste o komkoli či čemkoli rozhodli. Hráči vidí jen `looks`. `didact log … --about sweeney` přidá událost do jeho záznamu (`--secret`, pokud ji hráči nevidí). Víc v `didact guide details`.
- **Svět jde dál:** `didact faction turn` a k tomu hodiny: `didact track new 'The flood' --size 6`. Příkaz, který bere jen jeden druh záznamu, bere jméno, které sdílejí jiné, jako ten druh: `didact track roll draugr` hodí poolem pojmenovaným podle nepřítele (stejně `track tick` počítadlo, `quest done` úkol a `visit` místo).

## Orákula, generátory a postavy

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

Nic, co generátor nebo tvorba postavy vytvoří, se nezapíše před `commit`. V `--prefill` popište, co hráč chce, a postup doplní mezery. Otázka vypíše, co která možnost znamená, pokud to balíček uvádí (`- Cutpurse: …`): řekněte to hráči, ať vybírá s vědomím, co dostane.

## Tajemství

Pohledy jsou ve výchozím stavu bezpečné pro hráče: `show`, `find`, `sheet`, `map`, `brief`. Vynechávají:
- tajné záznamy (`knowledge: secret`);
- sekce `## Secrets` a `## GM notes`;
- pole `secret: true`.

`--gm` ukáže vše. Když se hráči něco dozvědí:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` zapíše, co hráči vědí, jako malý web ke sdílení nebo ke čtení v telefonu: družinu, stránku pro každý záznam, deník a mapu. Vždy je bezpečný pro hráče a nový export do téže složky ho aktualizuje. `didact export --as lonelog` zapíše deník v notaci Lonelog (`@ ? d: -> =>`, scény jako `S1`, štítky jako `[N:Sweeney]`), rovněž bezpečně pro hráče.

## Znalosti: co se vrátí, když se něco zmíní

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Co se počítá:** každá CP, místo, předmět a frakce je karta s klíči podle jména a přezdívek. Položky znalostí mají `keys` a rozhodnutí se vynoří přes své pravidlo. Shoda se hledá na celých slovech a počítá se i množné číslo („wolves“ odpovídá `wolf`).
- **Kdy se znalosti vynoří:** hook Claude Code prohledá každou zprávu hráče. `log`, `scene new` a `show` také přinesou nově spuštěné znalosti a položka se několik tahů neopakuje.
- **Ladění položky:** `--secondary` s `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (v tazích nebo scénách), `--constant` (vždy v briefingu) a `--no-recurse`.
- **Rozsahy:** položky patří ke kampani, pokud `--scope` neurčí svět, systém nebo globální rozsah. Prohledávání vidí jen tuto kampaň, její svět, její systém a globální rozsah, nikdy jiný svět. Užší položka se stejným ID zastíní širší.
- **Knihy znalostí z jiných nástrojů:** `didact lore import <file>` načte SillyTavern World Info (i to z KoboldAI), knihu znalostí z karty postavy a `.lorebook` z NovelAI; `didact lore export --to <file>` zapíše World Info. Klíče, logika, priorita, pravděpodobnost, skupiny a časování se přenesou.

## Změny příběhu

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` změní fakt, ale starou hodnotu si ponechá. Také označí shrnutí, která Sweeneyho zmiňují, jako zastaralá, a `audit` to vypíše.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` zaznamená rozhodnutí. To se pak objeví v `rules lookup` a při spuštění daného pravidla.
- `didact name npc` hodí nové jméno, nikdy takové, které svět už používá. Než si nějaké vymyslíte, ověřte ho přes `didact names check <name>`. `didact names forget <name>` ho zase uvolní.

## Úklid

- `didact history --clear` ukáže, co by vymazání staré historie odstranilo; `--yes` to odstraní natrvalo, včetně smazaných záznamů, a vracení zpět, `diff`, `rewind` ani starší body uložení už k tomu nedosáhnou (`--before e120` ponechá tuto změnu a pozdější, `--rolls` odstraní i záznam hodů). Nejdřív spusťte `didact snapshot`.
- `didact save --remove 'before the dragon'` odebere bod uložení; `didact undo` ho vrátí.
- `didact transcript 3 --clear` smaže přepis sezení 3 (`--clear --all`: přepisy všech sezení). `didact undo` ho vrátí a text zůstane v historii až do `history --clear`.
- `didact compendium remove <entry>` smaže položku, kterou jste přidali; záznamy z ní vytvořené zůstanou.
- `didact snapshot --keep 3` smaže všechny zálohy kromě tří nejnovějších a `didact snapshot --remove <name>` smaže jednu. Ani jedno nelze vrátit zpět.
- `didact session end` knihovnu sám zazálohuje (`snapshot-<time>-auto.zip`) a ponechá pět nejnovějších takových záloh; `didact snapshot --list` je označí.
- `didact reset` ukáže, co by vyprázdnění knihovny vzalo; `--yes` ji uvede do stavu čerstvé instalace: zmizí všechny světy, kampaně a záznamy, historie i vyhledávací index a další změna bude znovu #e1. Nejdřív knihovnu zazálohuje (`…-before-reset.zip`) a zálohy zůstanou, stejně jako nainstalované balíčky, pokud nezadáte `--packs`. Chcete-li Didact místo toho vyzkoušet na hotové kampani, `didact sample` sestaví ukázkovou kampaň do prázdné knihovny (`--home` jí dá vlastní složku) a `didact serve --demo` ji pokaždé nabídne nově sestavenou.
- `didact snapshot --restore <name>` ukáže, co záloha obsahuje, vedle současné knihovny; `--yes` zazálohuje knihovnu v současném stavu (`…-before-restore.zip`) a pak na její místo dá zálohu. Číslování změn a hodů pokračuje. Vrácení zpět obnovení nevrátí: obnovení té bezpečnostní zálohy ano.
