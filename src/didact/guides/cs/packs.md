<!-- translated from b1dfa1159ff4 -->
# Balíčky

Balíček je herní systém, orákulum, herní prostředí, dobrodružství nebo doplněk, zapsaný jako soubory YAML s volitelným pluginem v Pythonu. Tento průvodce ukazuje, jak ho napsat: jak převést knihu pravidel na balíček, nebo přidat vlastní obsah.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Balíček lze vytvořit i z toho, co máte v knihovně. `didact pack new my-brew --from-overlay my-system` udělá z vašeho vlastního obsahu pro systém (`compendium add`, záznamy vedené s `--scope system`, znalosti) doplněk a `didact world export --as setting` udělá ze světa balíček herního prostředí: jeho osoby, místa a znalosti jako položky kompendia a znalosti balíčku, které `compendium import` přenese do jiného světa. Oba vynechají tajemství a poznámky PJ, pokud není `--secrets`, a ani jeden není označen jako sdílitelný, dokud mu nenastavíte licenci.

## Struktura

```
my-hack/
  pack.yaml        id, name, kind, version, requires, extends, license, plugins, settings
  GUIDE.md         how to run it: an LLM reads this first
  dice.yaml        named dice, macros, dice chains
  schemas/         record types and their fields (sheets)
  tables/          random and lookup tables, decks, bags
  rules/           checks, actions, procedures, triggers
  compendium/      monsters, items, spells, backgrounds…
  reference/       the rules text, one short section per file (Markdown)
  glossary.yaml    terms and definitions
  tests/           examples `pack test` runs
  plugins/         Python, for what YAML can't express (off until trusted)
```

Soubor obsahuje jednu položku, seznam položek nebo několik položek oddělených `---`. Každá položka uvádí své ID pod klíčem svého druhu: `table: weather`, `check: save`, `type: pc`, nebo `id: troll` u položek kompendia. Na položky se odkazujte jako `pack.id` (`my-system.save`), nebo holým ID, když ho má jen jeden zapnutý balíček.

```yaml
# pack.yaml
id: my-hack
name: My Hack
kind: system                 # system | oracle | supplement | setting | adventure
version: 0.1.0
alias: hack                  # the name in expressions: hack.attack(d8, d8)
requires: {didact: ">=0.1", packs: [core]}
extends: []                  # for a hack: [my-system]; same-id items replace the base's
license: {spdx: CC-BY-SA-4.0, redistributable: true, attribution: "…"}
settings: {torch_uses: 3}    # rules read these as @settings.torch_uses
```

Hack uvádí svůj základ v `extends` a obsahuje jen to, co se liší:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Jeho položka se stejným ID nahrazuje položku základu, ať je jakéhokoli druhu (tabulka, pravidlo, položka kompendia, referenční oddíl, pojem glosáře). Jeho `settings` překrývají nastavení základu klíč po klíči: klíč, který hack nastaví, nahradí celou hodnotu základu (jeho tabulky `names` zastupují tabulky základu) a pravidla základu čtou také hodnoty hacku. `hides` vypouští to ostatní, co hack nepotřebuje: `*` odpovídá libovolné posloupnosti znaků, rozhoduje poslední vzor, který ID odpovídá, a vzor začínající `!` položku ponechá. Co hack nahrazuje, se nikdy neskryje. Druhy jsou `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` a `term`. `didact pack validate` upozorní na vzor, který neodpovídá ničemu.

## Výrazy

Každá podmínka a vzorec používá jazyk kostek (`didact guide dice`) a navíc:
- **Hodnoty:** `@name` čte hodnotu: `@roll`, `@who.STR`, `@settings.x`. `$name` nejdřív vloží text parametru, takže z `@who.$attr` se stane `@who.STR`. Parametr s volným textem čtěte jako `@name`, ne v uvozovkách (`'$name'`): apostrof v jeho textu by je ukončil (`pack validate` varuje).
- **Logika:** `and`, `or`, `not` a `in` (`'deprived' in @who.conditions`).
- **Literály:** text (`'travel'`) a `true`/`false`.
- **Funkce:** `if(cond, a, b)` hází jen ve větvi, kterou zvolí. `default(@thread.flashpoint, 0)` je hodnota, nebo náhradní hodnota, když není nastavená. `sum`, `count` (`count(@roll.dice, 6)` spočítá šestky), `min`, `max`, `any` a `all` berou seznamy.

## Karty: `schemas/`

```yaml
type: character
fields:
  STR: {kind: stat, range: [0, 18], roll: 3d6, on_zero: {trigger: death}}
  hp: {kind: resource, min: 0, roll: d6}
  armor: {kind: derived, expr: "min(3, sum(@inventory.armor))"}
  inventory: {kind: slots, capacity: 10, sizes: {petty: 0, normal: 1, bulky: 2},
              when_full: {set: {hp: 0}}}
  fatigue: {kind: counter, min: 0, occupies: inventory}
guidance: "3 HP is an average monster, 6 a hardy one, 10+ a serious threat."
---
type: pc
extends: character
```

| Druh | Obsahuje | Volby |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | prostou hodnotu | min, max; `values` pro enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` je hodnota, `@hp.max` strop | range; min; max nebo max_field; die |
| `counter` | číslo | min, max, thresholds, occupies (pole slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | předměty (`Rope` nebo `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | podle názvu | `to` (pro refs), `allowed` |
| `derived` | vypočtenou hodnotu, nikdy neukládanou | expr |

Každé pole bere také `label`, `help`, `default`, `required` a `roll`: `new pc Hero --fill` nebo hodnota `"roll"` na ně hodí přes protokol. Typy z balíčku `core` drží v `fields` popisy nezávislé na systému. Typy systému drží jeho čísla v `mechanics.<system>`. `set hero hp-=2` najde pole, hodnotu ořízne a ohlásí případný přebytek. `+=` přidává do seznamu: `list` (jako `slots`) si ponechá i znovu přidanou hodnotu, `tags`, `conditions` a `refs` ji drží jen jednou a `-=` odebere všechny její kopie.

**Hooky** říkají, co se stane, když hodnota překročí hranici. Spouštějí se při každé změně (`set`, `inv`, krok `set` pravidla), ale jen když se hranice překročí: 3 → 0 je spustí, 0 → 0 ne. Úpravy s `--force` je přeskočí.

| Hook | Spustí se, když |
|---|---|
| `on_zero` | číslo nebo `{value}` dosáhne 0 |
| `on_full` (`when_full` u slots) | dosáhne svého maxima, size nebo capacity |
| `thresholds: {10: …, 20: …}` (pole counter) | přeleze každou značku |

Akce je text (poznámka pro LLM), `{set: {hp: 0}}` nebo `{condition: paralyzed}` na tomtéž záznamu, `{trigger: death}` (spustí to pravidlo s `who` = záznam), nebo seznam těchto akcí.

**Výbava** (`didact inv …`) pracuje s polem `slots` karty:
- **Místo:** předměty zabírají `size` × `count` a počítadla, která toto pole zabírají (`occupies`), zabírají svou hodnotu. Překročení `capacity` se odmítne, pokud není uvedeno `--force`.
- **Skupiny:** `groups: {backpack: 6, body: 4}` dá každé skupině vlastní místo a také vlastní sloupce a součty: `@inventory.body.armor` je jen to, co se nosí na těle nebo drží v ruce, `@inventory.body.free` místo, které ve skupině zbývá.
- **Použití:** `uses: 3` se při `inv use` odpočítává. `uses: d8` je kostka použití: 1–2 ji sníží o stupeň. Spotřebovaný předmět zmizí, pokud nemá `recharge` nebo `keep: true`. Z několika předmětů stejného jména označuje jméno ten první; při utrácení použití (`inv use`, `use:` pravidla, `set …uses-=1`) první, kterému nějaké použití zbývá.
- **Vlastní klíče předmětu:** `didact set freya inventory.sword.damage=d10` (v pravidle i `set: who.inventory.$item.damage`) změní jeden z nich, přičemž předmět se uvádí stejně jako u `inv`, částí jména nebo celým jménem, i s mezerami a tečkami (`'inventory.12.7mm pistol.damage=d10'`, v uvozovkách kvůli shellu); `uses` a `charges` se počítají jako pole `uses` (`charges+=2` se zastaví na maximu) a místo se ověřuje stejně jako u `inv add`. Pravidlo ho čte jako `@{who.inventory.$item.damage}` (kostku použití jako její kostku, použití jako jejich počet); předmět nebo klíč, který tam není, se čte jako chybějící, takže `default(…)` dá svou náhradní hodnotu.
- **Kompendium:** položky typu `item` (nebo weapon, armor, relic, …, nebo vlastního typu balíčku, který některý z nich rozšiřuje přes `extends`) propůjčí `inv add` své podrobnosti, nalezené podle ID, jména nebo aliasu (sdílejí-li dvě jeden: uveďte tu pravou jako `pack.id`); jakékoli jiné jméno, i s `:`, je vlastní jméno předmětu.

## Tabulky: `tables/`

```yaml
table: weather
dice: d6                     # any expression: 2d6, d66, d100, d20 + @corruption
clamp: true                  # a total past the ends uses the first or last entry
entries:
  1-2: Clear
  3-4: {text: Rain, data: {travel: slow}}
  5: {text: Storm, then: [{table: lightning}]}
  6: {text: Two fronts, roll: 2}
refs: {noun: nouns}          # "{noun}" in a text rolls on table nouns; "{1d4}" rolls dice
source: "Core Rules p. 12"
```

Další podoby:
- **Vážené seznamy:** `entries` jako seznam, s `weight:` u každé položky.
- **Sloupce:** `columns: [a, b]` hází na každý sloupec řádku zvlášť. Prostá položka (ne seznam) vyplní každý sloupec, takže `columns: [first, second]` nad seznamem slov znamená „hoď dvakrát na tento seznam“. `labels: false` vynechá názvy sloupců z výsledku („Abandon · Advantage“). `read: "It's a {first} {second} with {third} {fourth} inside."` přečte sloupce jako větu.
- **Vyhledávací tabulky:** `lookup: hp_lost`, nebo `[odds, chaos]` pro dvourozměrnou tabulku.
- **Duplicity:** `duplicates: reroll | keep | make_it_worse` pro „hoď dvakrát“.
- **Dvoustupňové hody:** položka, která hází na jinou tabulku (`{table: lightning}` místo vlastního výsledku, nebo `then:` po něm), s sebou přinese data toho hodu: pravidlo nebo koncept, jehož hod na ni padne, čte obojí, nejdřív vlastní klíče položky, pak klíče první tabulky, na kterou se hází následně. `--prefill` může uvést položku níže, v jakékoli hloubce (`Ring of the Hunt`), s daty každé položky po cestě: ze dvou stejného jména platí ta bližší (pak ta první), položka, která navazuje, hází odtamtud dál, a ta, která se některé z nich blíží, ale žádnou není, se odmítne a uvede se nejbližší. Řízený koncept nabídne první krok, když jeho položky říkají, čím jsou (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): volba jedné hází na další tabulku jako hod, který na ni padne.
- **Čtení oběma směry:** `both_ways: true` u tabulky d66 přidá druhé čtení: 31 dá i 13 a vybere si ten, kdo čte.
- **Co položka znamená:** `about: "Knows: {skills}. Also known as: {aka}."` se vyplní daty každé položky (seznam se čte jako `a, b`; `{text}` je položka samotná) a řekne, co položka dává, když ji nabízí nějaká volba; vlastní `note:` položky to řekne místo něj. Bez obojího popíše položku, jejíž data mají `id` odkazující na položku kompendia, právě tato položka kompendia.
- **Karty a pytlíky:** `deck: tarot` s `cards` (nebo `standard: true`); `bag: initiative` s `tokens`.

Validace ověří, že každý výsledek, který kostky mohou hodit, padne na nějakou položku.

## Pravidla: `rules/`

```yaml
check: save
params: {who: ref, attr: {enum: [STR, DEX, WIL]}}
prompt: State the risk before rolling.
before: [{table: chart, with: {odds: $odds}, as: cell}]   # optional: steps first (a `roll` step can replace `roll:`)
roll: d20                              # or several: {action: "d6 + @stat", challenge: 2d10}
success: "@roll <= @who.$attr"         # or bands: {strong: "@roll >= 10", weak: "@roll >= 7", miss: else}
auto: {1: success, 20: failure}        # natural rolls
flags: {crit: "count(@roll.dice, 6) >= 2"}
on: {failure: ["The risk comes true."]}
options:                               # the roll comes back pending: `didact resolve r12 push`
  push: {label: "Push", steps: [{reroll: roll, keep_if: "@face == 6"}]}
```

Akce a postupy jsou seznamy kroků a spouštěče jsou kroky s podmínkou `when:`. Kroky jsou:

| Krok | Dělá |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | hod zapsaný do protokolu; váže `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` se nejdřív vyplní, jako v každém textu, takže kostky, které hodnota drží jako text, se hodí (`{@{who.inventory.$item.damage}}`), a protokol je ukáže: hodnota, která nejsou kostky, se odmítne, stejně jako `roll: "@die"` s takovým textem, který nic nehází; sada hodů (`{d8, d6}kh1`) zůstane sadou |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | spočítá hodnoty; stejně jako u `value` v `set` je text `{…}` šablona a holé slovo je text; v jakémkoli doplňovaném textu zapíšou `{{` a `}}` samotnou závorku |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (nebo `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | změní záznam: ověřeně, s oříznutím, vratně; `set: who.$attr` nastaví pole určené parametrem a `set: who.inventory.$item.damage` klíč předmětu, který záznam nese (viz Výbava); `-=` odebere hodnotu ze seznamu a ta, kterou neobsahuje, nic nezmění (poznámka to řekne; ta, kterou by nikdy obsahovat nemohl, se odmítne); `unset:` odebere pole jako `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | dá záznamu předmět nebo mu nějaký vezme, stejně jako `inv add` a `inv drop`: podrobnosti převezme z kompendia, stačí jedinečná část jeho názvu a ověří se místo i hooky pole |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | použije nesený předmět jako `inv use`: použití nebo náboje se odpočítávají, kostkou použití se hodí a při 1–2 klesne o stupeň a spotřebovaný předmět zmizí, pokud se nedobíjí nebo se neponechává; z několika toho jména první, kterému zbývá použití; váže `@torch.out` (jeho poslední použití je pryč), `@torch.gone` (nic z něj nezbylo), `@torch.left`, `@torch.die` a `@torch.rolled` (`as:` je výchozí `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | hned vytvoří záznam, popsaný stejně jako v kroku `entity` konceptu (níže) a ověřený podle své karty; `as:` (jinak jeho `key`, jinak jeho typ) ho naváže jako záznam, který se čte a nastavuje jako parametr `ref` (`pool: "@bleeding"`, `@bleeding.name`), a nikdy to není jméno parametru; bez `key:` se žádné pole nebere jako klíč (`kind: track` zůstane, jak je napsáno); záznam toho typu a jména, který tu už je, se vezme tak, jak je, takže pravidlo spuštěné znovu nic nového nevytvoří |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | provede ověření a naváže jeho výsledek |
| `do: other-action`, `with: {…}`, `as: trip` | spustí jiné pravidlo; `@trip` je jeho výsledek a `@trip.<name>` to, co navázalo (`@trip.found` pro jeho `let: {found: 2}`, `@trip.luck` pro jeho `roll: d6`, `as: luck`); `as:` je výchozí jeho ID |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | hod na tabulku zapsaný do protokolu; váže text a `data` položky (`@scar.<key>` a klíče mapování podle jejich cesty: `@scar.cost.hp`) spolu s daty každé tabulky, na kterou se potom hází; seznam předmětů (`[Rope, {name: Laser, damage: d8}]`) se čte jako jejich jména (`count(@scar.gear)`, `'Laser' in @scar.gear`) a předaný kroku tak, jak je (`apply: "@scar.gear"`), jsou to samotné předměty; seznam jiných mapování přečte jen krok |
| `table: "setting-{@drop.difficulty}-terrain"` | vypočtená tabulka: `{…}` a `$param` se doplní |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | několik výsledků jako seznam (`distinct` přehazuje opakování) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | větvení |
| `repeat: "@count"`, `as: i`, `steps: […]` | smyčka: kroky se zopakují tolikrát, kolikrát je zadáno, a `@i` přitom počítá od 1 |
| `for: pcs` (nebo `party`), `as: member`, `steps: […]` | spustí kroky jednou pro každou hráčskou postavu (nebo člena družiny), jako `@member`: záznam obdobný tomu, který váže `entity:` (`@member.name`, `set: member.fatigue`); `as:` se nikdy nesmí jmenovat jako parametr, takže vlastní `who` pravidla zůstane nedotčené |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | výstup pro LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (nebo `every: 1 day`) | připomínka, která nastane s plynutím herního času, jakou nastavuje `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | přehodí některé kostky hodu (mechaniky typu push) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | hází na hodnotu, která je seznamem (seznamy orákula): váže položku, `@who.choose` (prázdný řádek) a `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | hodí ubývající sadou kostek počítadla stejně jako `track roll` (kostky s 1-3 odpadají; kostky z `drop` se odeberou nejdřív, kostky z `extra` se hází spolu s ní), nebo jen odebere kostky (`mode: drop`: push, odškrtnutí); navazují propojené fáze a událost sady; váže `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Výsledek ověření může číst pravidlo, které ho spustilo (`check: … as: answer` dá `@answer`), stejně jako jeho příznaky: `'random-event' in @answer.flags`. Hodnoty `with:` se vyhodnotí, když obsahují `@`, doplní, když obsahují `$param` nebo `{…}` („Does $npc flee?“), a jinak se předají, jak jsou zapsané. Pravidlo s parametrem `oracle` dostane záznam stavu orákula kampaně, aniž by se o něj muselo říct. Parametr `ref` s `to: monster` bere záznam toho typu: jméno, které sdílí jiný záznam (pool nepřítele pojmenovaný podle jeho karty), je ten toho typu.

Spouštěče běží samy, když nastane jejich událost, a jen pokud platí jejich `when:`:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Každé pravidlo (i generátory a tvorba postav) může číst `@system` (ID systému, podle kterého se ve světě hraje, takže herní prostředí napsané pro dva systémy je dokáže rozlišit), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` a `@time.is_night` a, pokud má kalendář měsíce, také `@time.month`, `@time.month_name`, `@time.day_of_month` a `@time.year`; když probíhá boj, i `@combat.round` a `@combat.fighters` (ID jeho účastníků). Časový spouštěč může číst i `@time.passed`, tedy právě uplynulé sekundy, spouštěč `combat_start` nebo `combat_end` čte boj, který začíná nebo končí (spouštějí je `combat start` a `combat end`; odchodem bojovníka boj nekončí), a pravidlo, které spouštěč spustí, čte totéž co spouštěč. Spouštěč s povinnými parametry spustí jen `didact do` nebo hook pole (`who` = záznam). Spouštěče `on: manual` běží jen na vyvolání. `for: pcs` (nebo `party`) spustí spouštěč jednou pro každou hráčskou postavu (nebo člena družiny), jako `who`: třeba zkušenosti po každém sezení. Spouštěč, který selže, zastaví příkaz, který ho spustil, a řekne, který spouštěč to byl a jak pokračovat bez něj (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalendář je v `settings` balíčku: kalendář balíčku herního prostředí má přednost před kalendářem systému a vlastní kalendář světa (`calendar:` v jeho `world.yaml`) před oběma:

```yaml
settings:
  watches: [morning, afternoon, night]   # the day's watches
  calendar:
    week: [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
    months: [{name: January, days: 31}, {name: February, days: 28, leap: [4, 100, 400]}, …]
    start: {year: 1890, month: 3, day: 14, weekday: Friday}   # where a campaign opens
    year: "{year} AD"                     # how a date writes its year
    seasons: [{name: spring, month: 3, day: 20}, …]           # each from its first day
    holidays: [{name: Midsummer, month: 6, day: 24, text: "…"}]
```

`leap: 4` prodlouží měsíc o den každý 4. rok a `leap: [4, 100, 400]` každý 4., ale ne každý 100., a zase ano každý 400.: každé číslo přebíjí to předchozí. `weekday` určuje, jaký den v týdnu je začátek (jinak je to první den týdne), a `year` je to, jak datum píše svůj rok, v datech, která Didact ukazuje, i v těch, která čte (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` kontroluje všechny tři. Kampaň může začít jiným datem kalendáře, před jeho začátkem i po něm: `didact campaign new <id> --date '4 July 1902'`, nebo `didact time set '<date>'` až do jejího prvního sezení. Den v týdnu napsaný před datem se kontroluje: rozhoduje datum a poznámka řekne, když připadne na jiný den.

Volby jsou varianty a volitelná pravidla systému, které si každá kampaň vybere na nulté session:

```yaml
option: lethality                       # rules read it as @option.lethality
ask: How deadly should it be?           # session zero asks it (in place of Didact's own of that key)
choices: {gentle: "…", standard: "As the book has it.", deadly: "…"}   # each with what it means
default: standard
---
option: supplies                        # a flag: on or off (@option.supplies is true or false)
kind: flag
ask: Can the PCs run out of supplies?
help: Each PC has a 4d Supplies pool.
---
option: flavor
choices: {heroic: "…", grimdark: "…"}
implies: {grimdark: {lethality: deadly, supplies: true}}   # a choice that sets others (a flag's: on)
```

`didact campaign profile lethality=deadly supplies=on` je uloží (nebo stránka Nastavení webové aplikace). Pravidla, tvorba postav a generátory je čtou (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): odpověď má přednost před tím, co vyplývá z jiné volby, a to před výchozí hodnotou. To, co z volby vyplývá, se sleduje až do konce (nálada, která nastaví smrtelnost, nastaví i to, co vyplývá z této smrtelnosti) a ze dvou důsledků vyhrává ten bližší. Přehled uvádí ty, které se liší od výchozí hodnoty, i s tím, co znamenají, aby vypravěč uplatnil, co pravidla neumějí. Generátor, který za nich nemůže běžet, skončí krokem `stop:` s důvodem a nic se nevytvoří.

## Orákula: `oracles/`

```yaml
oracle: chart
title: Chart oracle
ask: chart-question          # the check that answers; it may take question, odds and oracle
odds: [unlikely, 50-50, likely]
meaning: [actions, descriptions]   # tables for `didact meaning` (a word from each)
state: {chaos: {start: 5, min: 1, max: 9}}  # kept per campaign; rules read @oracle.chaos
lists: {names: [threads, characters], method: sections}   # weighted lists (`didact lists`)
prompt: Interpret the answer in the fiction.
```

- **Otázky:** `didact ask '…' --odds likely` spustí ověření `ask`. Odpovědí je jeho výsledek (pásmo) a jeho příznaky jdou s ním.
- **Stav:** je uložený v záznamu, který ověření dostane jako `oracle`. Ověření ho mění pomocí `set: oracle.chaos += 1`.
- **Seznamy:** `lists: {names: […], method: sections, most: 3}` drží na tom záznamu vážené seznamy. `didact lists add|drop|roll|show` je spravuje a pravidla na ně hází pomocí `pick`. `sections` hodí na sekci pěti řádků, pak na řádek v ní (prázdný řádek znamená volbu); `uniform` dá každému řádku stejnou šanci.
- **Víc pro ověření:** `didact ask '…' --with as_rule=true` předá ověření orákula další parametry.
- **Protokol:** každá odpověď je očíslovaná (`#o12`) a zapsaná do protokolu a `didact interpret o12 '…'` uchová, co znamenala. Záložním orákulem je `yes-no` z balíčku core.

## Generátory a tvorba postav: `generators/`, `chargen/`

Obojí jsou postupy, které staví **koncept**. Používají každý krok pravidel (`roll`, `table`, `if`, `let`, `prompt`, …) a navíc tyto:

| Krok | Dělá |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | přidá do konceptu záznam (klíče `poi-1`, `poi-2`, …); pole nebo odkaz, který uvádí klíč zapsaný balíčkem (`key:` nebo jméno `as:`), se při potvrzení stane ID toho záznamu, takže vybírejte klíče, které žádné pole nemá jako text (entita bez obojího nemá žádný klíč k záměně); `from: "@relic.id"` ho založí podle položky kompendia (jejího typu, jména a polí) |
| `choose: {from: [a, b], as: x}` (nebo `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | volba; v režimu krok za krokem koncept čeká na `choose`; `exclude` vyloučí dřívější výběry (hozený se hází znovu); `records:` přidá mezi možnosti zdejší záznamy toho typu, podle ID (vytvořené ve hře); `answer:` provede volbu bez ptaní, když je jeho hodnota jednou z možností (vlastní cesta postavy) |
| `choose_or_roll: {table: backgrounds, as: background}` | volba, kterou mohou udělat kostky; data zvolené položky jsou `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | hody zapsané do postavy |
| `swap: {among: [STR, DEX, WIL], optional: true}` | prohodit dvě hodnoty, nebo ponechat |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | rozdělí pevnou sadu hodnot |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | nákup hodnot v rámci rozpočtu (`default: random` ho v náhodném režimu utratí náhodně) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | seznam jde do výbavy; mapování nastaví pole (seznamy se sčítají) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | přidá do pole postavy (nebo entity v konceptu): čísla se sčítají, cokoli jiného se připojí do seznamu; když není co přidat, nevadí |
| `remove: {field: talents, value: "@old"}` | odebere něco ze seznamového pole (vyměněný talent, vyřešené pouto); když tam nic není, nevadí |
| `roll_tables: [physique, vice]` | hází na tabulky do `traits`; `data.gear` položky jde do výbavy a `data.add: {gold: 20}` přidá do polí |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | jméno; `name: {prompt: …}` bez něčeho, na co hodit, na jméno počká, i v náhodném režimu |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | otázka, na kterou poslouží jakákoli odpověď (cíl, jméno jiného záznamu): koncept na ni počká i v náhodném režimu, pokud není předvyplněná; `field:` odpověď uloží |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawl: rozhoz kostek zapsaný do protokolu, cesty (vždy propojené), vzdálenosti, skryté cesty (viz níže) |

Krok map umí víc, pro postupy s rozhozem kostek z knih:

| Klíč | Dělá |
|---|---|
| `regions: terrain` | tyto entity se rozhazují také; každé místo se přidá k nejbližší z nich (svému `region`) |
| `hidden: 6`, `conditional: 5` | d6 na každou cestu: na toto číslo nebo víc je cesta skrytá nebo podmíněná (skryté cesty zůstanou mimo mapu hráčů) |
| `describe: [path-feature, path-condition]` | tabulky, na které se hází pro každou cestu, uložené jako její `details` |
| `entrance: true`, `exit: true` | místo nejblíž okraji je vchod; ostatní se číslují od něj podél cest (`map.n`), cesty vedou od něj a východ je vzdálené místo u okraje, očíslované jako poslední |
| `number: "{@dungeon_name}, room {@n}"` | přejmenuje očíslovaná místa (jejich klíče v konceptu to následují: `room-1` je místnost 1) |

Tabulka pro rozhoz kostek může v datech svých položek uvést další tabulky, takže postup se čte jako v knize: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, pak `table: "{@drop.what}"`. Nenastavená seznamová pole (conditions, lists, tags) se čtou jako prázdné seznamy, takže `'deprived' in @who.conditions` funguje od začátku.

```yaml
chargen: pc
creates: pc
modes: [random, guided]
steps:
  - choose_or_roll: {table: backgrounds, as: background, field: background}
  - apply: "@background.gear"
  - roll: {each: [STR, DEX, WIL], dice: 3d6}
  - swap: {among: [STR, DEX, WIL], optional: true}
  - name: {from: "@background.names"}
```

Postup chargen s `advances:` záznam nevytváří, ale mění: je to zvýšení úrovně v daném systému.

```yaml
chargen: level-up
advances: pc                   # `didact char advance <pc>`, or Level up on its page
params: {who: ref}
steps:
  - if: "@who.xp < @who.level + 1"
    then: [stop: "{@who.name} needs more XP"]
  - apply: {level: "{@who.level + 1}", xp: "{@who.xp - @who.level - 1}"}
  - choose: {table: paths, as: path, answer: "@who.path"}     # the character's own: not asked
  - choose: {from: "@path.talents", records: talent, as: talent, exclude: "@character.talents"}
  - add: {field: talents, value: "@talent"}
```

- **Jeden záznam:** generátor s `creates: npc` sestaví tento záznam tak, jako tvorba postavy sestaví postavu (`apply`, `add`, `name`, `field:`); jeho kroky `entity` přidají záznamy vedle něj a odkaz `to: character` ukazuje na něj.
- **Spuštění:** `gen run` a `char new` vytvoří koncept (`#g7`, `#c3`) a nic nezapíšou. `stop:` ho ukončí, aniž vznikne koncept: pod `if:`, které čte volbu kampaně, ukazuje jeho rada na volby (`didact session zero`); jinak jeho vlastní slova říkají, co udělat místo toho.
- **Rozhodování:** `--prefill '{…}'` rozhodne věci předem, podle názvu, který krok váže (`as:`): jedna hodnota odpoví na každý výskyt, seznam na každý výskyt po jedné položce (seznam pro `choose` s `count` je celý výběr). Předvyplnit jde i hodnoty `let` (`{"hp": 6}`); jméno, `ask` nebo `let` ponechá jakýkoli text tak, jak byl zadán. Hodnota pro volbu mezi známými možnostmi (`choose`, položka tabulky) je možnost, kterou uvádí svým zněním (i s jinou velikostí písmen), pomocí `id` její položky nebo hodem, který na ni padne (`{"group": 3}`), a přinese s sebou data této položky; hodnota, která se některé možnosti blíží, ale žádnou z nich není, se odmítne s uvedením té nejbližší a každá jiná je vlastní odpovědí, bez dat. `--auto` (nebo `char new --mode random`) nechá zbytek na kostkách. Jinak koncept čeká u každé volby.
- **Popis:** volba říká hráči, který vybírá, co která možnost znamená: `note:` položky tabulky nebo `about:` její tabulky, jinak položka kompendia, kterou uvádí (`id` v jejích datech), nebo ta, kterou možnost sama je (volba mezi ID z kompendia ukáže jméno každé z nich): její `tagline` a `summary`, její `description` nebo `effect`, jinak první odstavec jejího textu.
- **Krok zpět:** `char back` (nebo `gen back`) vezme zpět poslední odpověď, hod nebo úpravu, takže koncept položí tu otázku znovu; hody, které přitom padly, se označí jako vrácené.
- **Pokračování:** koncept, ve kterém se pokračuje, přehraje svou stopu: každou hozenou či zvolenou hodnotu, každou použitou jednou a v pořadí (i rozhoz kostek na mapě), takže se nic nehází dvakrát a nic už rozhodnutého se nezmění.
- **Zápis:** `commit` zapíše záznamy, ověřené podle jejich karet.
- **Rozvoj:** koncept s `advances:` začíná kopií záznamu (s výchozími hodnotami z jeho karty), jeho kroky čtou záznam jako `@who` a hodnoty konceptu jako `@character.*`; `commit` pak zapíše jen to, co se změnilo, s ověřením jako u `set`; záznamy z jeho kroků `entity` (dějová linka nového pouta) vzniknou vedle něj a odkaz `to: character` ukazuje na záznam. Pole, které uvádí klíč, obsahuje ID záznamu, který z toho klíče vznikne, stejně jako při tvorbě postavy (`apply: {blood: "@pool"}`). `stop:` řekne, proč to ještě nejde (málo XP), a žádný koncept nevznikne. Systém, jehož růst je jediné pravidlo, ho místo toho uvede ve svém chargen: `advance: {rule: grow}`.
- **Režimy:** `modes: [guided]` nechá postup běžet jen krok za krokem: `--mode random` se odmítne.

## Kompendium, příručka a glosář

- **Položky kompendia** se píšou jako `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Na hodnotu `"roll 2d8"` se hodí, když položka vznikne. Spusťte `didact spawn troll`, nebo přeneste položky balíčku do světa pomocí `didact compendium import <pack>` (`--type loc` a `--tag coast` pro ty, které mají všechny zadané štítky).
- **Pro více systémů:** klíč na nejvyšší úrovni jde tam, kam ho dává `set`: do bloku systému, když má jeho karta takové pole, jinak do `fields`. Položka, kterou herní prostředí píše pro víc systémů, dává čísla každého z nich do jeho vlastního bloku (`mechanics: {my-system: {hp: 12}}`): `pack validate` každý blok ověří podle karty jeho systému, je-li nainstalovaný, a upozorní na klíč na nejvyšší úrovni, který má ta karta i karta core. Co říká blok, platí: vedle `mechanics: {my-system: {role: tactician}}` je `role: innkeeper` na nejvyšší úrovni polem core, stejně jako cokoli pod `fields:`. Blok, který uvádí ověřovaný balíček, se kontroluje podle toho balíčku tak, jak je ve své složce.
- **Sekce příručky** patří do `reference/*.md`, s front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` je najde; fráze v uvozovkách, která tam není, se zkusí slovo po slovu.
- **Glosář** je `glossary.yaml`: `term: definition`, nebo seznam `{term, definition, aliases, see}`. `didact define <term>` ho čte.

## Testy: `tests/`

```yaml
test: weather-lands     # roll a table many times: every roll must land
table: weather
times: 50
---
test: fair-save         # exact odds
odds: "d20 <= 10"
chance: 0.5
---
test: every-table       # each of the pack's tables (a lookup table once per key)
table: all
---
test: play              # a smoke-play script: real commands in a scratch library
script:
  - world new t --system {pack} --seed smoke    # seeded: it plays the same every time
  - new pc Hero --fill
  - run: do save who=hero attr=STR
    expect: "→"                                  # text the step must print (or a list)
  - run: table list
    expect_not: my-system.spell-fire             # text it must not print (or a list)
  - run: table roll my-system.spell-fire
    fails: true                                  # it must fail (`expect` reads its error too)
```

## Sdílení a odebírání balíčků

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Balíček, který deklaruje `redistributable: false`, nelze exportovat.
- **core** je součástí Didactu a je vždy zapnutý: staví na něm každý systém, takže ho nelze vypnout ani odinstalovat.
- Ostatní balíčky dodávané s Didactem jsou soubory `.didactpack` v jeho složce `packs/`. `pack list` je ukazuje, dokud nejsou nainstalované, a instalace jednoho z nich přinese i balíčky, které potřebuje, pokud jsou také dodávané.
- `pack update` hledá novější verze ve složce `packs/` Didactu a na GitHubu (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` určí jiné místo, nebo nic, pokud se hledat nemá). Nová verze se nainstaluje vedle staré: kampaně si ponechají tu svou až do `didact campaign upgrade`.
- V jednu chvíli se používá jeden herní systém: ten otevřeného světa. Svět si ponechá systém, s nímž byl vytvořen (`didact world new <id> --system <pack>`; svět vytvořený bez systému dostane první, který mu dáte, pomocí `pack enable` nebo `world set system=`), jeho kampaně se hrají podle něj a balíček, který potřebuje jiný systém (herní prostředí napsané pro něj), přidat nelze: jiný systém se hraje ve vlastním světě.
- `uninstall` odmítne, dokud svět nebo kampaň používá jedinou kopii balíčku (`--force` ho přesto odebere). Nelze to vrátit zpět: znovu nainstalujte .didactpack.

## Od knihy pravidel k balíčku: kontrolní seznam

Projděte mechaniky knihy v tomto pořadí. Každá odpovídá něčemu z výše uvedeného:

1. **Vyhodnocení:** kdy je hod úspěšný (ověření: `success`, `bands`, `auto`).
2. **Kostky:** neobvyklé kostky, symboly, stupně (`dice.yaml`, pojmenované kostky, řady).
3. **Karta:** vlastnosti, odvozená čísla (`schemas/`, pole derived).
4. **Zdroje:** HP, štěstí, momentum (pole resource a counter; kroky `set`).
5. **Stavy:** jaké jsou a co dělají (pole `conditions`; kroky `if`).
6. **Boj:** útoky, zranění, iniciativa (akce; `bag`/`deck` pro pořadí tahů).
7. **Postupy:** průzkum, cestování, volno mezi dobrodružstvími (postupy s pokyny).
8. **Tabulky:** každá náhodná tabulka (`tables/`; `pack import` pro tabulky v Markdownu).
9. **Bestiář:** netvoři a CP (`compendium/`).
10. **Předměty:** vybavení, kouzla, relikvie (`compendium/`, pole slots).
11. **Rady pro PJ:** zásady a rady (`GUIDE.md`, `reference/`, `guidance:` u typů).
12. **Tvorba postavy:** jak vytvořit postavu (postup `chargen/`, nebo `roll:` u každého pole).

Všude uvádějte stránky pomocí `source:`, aby se ukázaly mezery. Přidejte test smoke-play, který vytvoří postavu, hodí na ověření, bojuje a spustí postup.
