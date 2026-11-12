<!-- translated from b1dfa1159ff4 -->
# Pakiety

Pakiet to system gry, wyrocznia, setting, przygoda lub dodatek, zapisany jako pliki YAML z opcjonalną wtyczką w Pythonie. Ten poradnik pokazuje, jak go napisać: jak zamienić podręcznik w pakiet albo dodać własne treści.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Pakiet można też utworzyć z tego, co jest w twojej bibliotece. `didact pack new my-brew --from-overlay my-system` zamienia twoje własne treści do systemu (`compendium add`, wpisy przechowywane z `--scope system`, wiedzę) w dodatek, a `didact world export --as setting` zamienia świat w pakiet settingu: jego osoby, miejsca i wiedzę jako pozycje kompendium i wiedzę pakietu, wprowadzane do innego świata przez `compendium import`. Oba pomijają sekrety i notatki MG, chyba że podasz `--secrets`, i żaden nie jest oznaczony jako do udostępniania, dopóki nie ustawisz jego licencji.

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

Plik zawiera jeden element, listę elementów albo kilka elementów oddzielonych `---`. Każdy element podaje swój identyfikator pod kluczem swojego rodzaju: `table: weather`, `check: save`, `type: pc` albo `id: troll` dla pozycji kompendium. Do elementów odwołuj się przez `pack.id` (`my-system.save`) albo samym identyfikatorem, gdy ma go tylko jeden włączony pakiet.

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

Hack podaje swoją bazę w `extends` i zawiera tylko to, co się różni:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Jego element o tym samym identyfikatorze zastępuje element bazy, bez względu na rodzaj (tabela, reguła, pozycja kompendium, sekcja podręcznika, termin słowniczka). Jego `settings` nakładają się na ustawienia bazy klucz po kluczu: klucz ustawiony przez hack zastępuje całą wartość z bazy (jego tabele `names` zajmują miejsce tabel bazy), a reguły bazy też odczytują wartości hacka. `hides` pomija resztę, której hack nie potrzebuje: `*` pasuje do dowolnego ciągu znaków, rozstrzyga ostatni wzorzec pasujący do identyfikatora, a wzorzec zaczynający się od `!` zachowuje element. To, co hack zastępuje, nigdy nie jest ukrywane. Rodzaje to `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` i `term`. `didact pack validate` ostrzega o wzorcu, który do niczego nie pasuje.

## Wyrażenia

Każdy warunek i wzór używa języka kości (`didact guide dice`), a do tego:
- **Wartości:** `@name` odczytuje wartość: `@roll`, `@who.STR`, `@settings.x`. `$name` najpierw wkleja tekst parametru, więc `@who.$attr` staje się `@who.STR`. Parametr z wolnym tekstem odczytuj jako `@name`, nie w cudzysłowie (`'$name'`): apostrof w jego tekście zamknąłby cudzysłów (`pack validate` ostrzega).
- **Logika:** `and`, `or`, `not` i `in` (`'deprived' in @who.conditions`).
- **Literały:** tekst (`'travel'`) oraz `true`/`false`.
- **Funkcje:** `if(cond, a, b)` rzuca tylko w tej gałęzi, którą wybiera. `default(@thread.flashpoint, 0)` to wartość albo wartość zastępcza, gdy nie jest ustawiona. `sum`, `count` (`count(@roll.dice, 6)` liczy szóstki), `min`, `max`, `any` i `all` przyjmują listy.

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

| Rodzaj | Przechowuje | Opcje |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | zwykłą wartość | min, max; `values` dla enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` to wartość, `@hp.max` limit | range; min; max lub max_field; die |
| `counter` | liczbę | min, max, thresholds, occupies (pole slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | przedmioty (`Rope` lub `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | zgodnie z nazwą | `to` (dla refs), `allowed` |
| `derived` | wartość wyliczaną, nigdy nie zapisywaną | expr |

Każde pole przyjmuje też `label`, `help`, `default`, `required` i `roll`: `new pc Hero --fill` albo wartość `"roll"` rzuca na nie przez log. Typy z pakietu `core` przechowują w `fields` opisy niezależne od systemu. Typy systemu przechowują jego liczby w `mechanics.<system>`. `set hero hp-=2` znajduje pole, przycina wartość i zgłasza ewentualny nadmiar. `+=` dodaje do listy: pole `list` (jak `slots`) zachowuje także wartość dodaną ponownie, pola `tags`, `conditions` i `refs` przechowują ją tylko raz, a `-=` usuwa każdą jej kopię.

**Hooki** mówią, co się dzieje, gdy wartość przekroczy granicę. Uruchamiają się przy każdej zmianie (`set`, `inv`, krok `set` zasady), ale tylko wtedy, gdy granica zostanie przekroczona: 3 → 0 je uruchamia, 0 → 0 nie. Edycje z `--force` je pomijają.

| Hook | Uruchamia się, gdy |
|---|---|
| `on_zero` | liczba lub `{value}` osiąga 0 |
| `on_full` (`when_full` przy slots) | osiąga swoje maksimum, size lub capacity |
| `thresholds: {10: …, 20: …}` (pola counter) | przekracza kolejne progi |

Akcja to tekst (notatka dla LLM), `{set: {hp: 0}}` lub `{condition: paralyzed}` na tym samym wpisie, `{trigger: death}` (uruchamia tę zasadę z `who` = wpis) albo lista takich akcji.

**Ekwipunek** (`didact inv …`) działa na polu `slots` karty:
- **Miejsce:** przedmioty zajmują `size` × `count`, a liczniki, które zajmują to pole (`occupies`), zajmują swoją wartość. Przekroczenie `capacity` jest odrzucane, chyba że z `--force`.
- **Grupy:** `groups: {backpack: 6, body: 4}` daje każdej grupie własne miejsce, a także własne kolumny i sumy: `@inventory.body.armor` to tylko to, co jest noszone na sobie lub trzymane w ręku, a `@inventory.body.free` to miejsce, które jej zostało.
- **Użycia:** `uses: 3` odlicza w dół przy `inv use`. `uses: d8` to kość użycia: 1–2 obniża ją o stopień. Zużyty przedmiot znika, chyba że ma `recharge` lub `keep: true`. Spośród kilku przedmiotów o tej samej nazwie nazwa oznacza pierwszy; przy zużywaniu użycia (`inv use`, `use:` zasady, `set …uses-=1`) pierwszy, któremu zostało jakieś użycie.
- **Własne klucze przedmiotu:** `didact set freya inventory.sword.damage=d10` (także `set: who.inventory.$item.damage` w zasadzie) zmienia jeden z nich, a przedmiot wskazuje się tak jak w `inv`, częścią nazwy lub całą nazwą, ze spacjami i kropkami (`'inventory.12.7mm pistol.damage=d10'`, w cudzysłowie dla powłoki); `uses` i `charges` są liczone jak pole `uses` (`charges+=2` zatrzymuje się na maksimum), a miejsce jest sprawdzane tak jak przy `inv add`. Zasada odczytuje go jako `@{who.inventory.$item.damage}` (kość użycia jako jej kość, użycia jako ich liczbę); przedmiot lub klucz, którego nie ma, odczytuje się jako brak, więc `default(…)` daje swoją wartość zastępczą.
- **Kompendium:** pozycje typu `item` (lub weapon, armor, relic, …, lub własnego typu pakietu, który rozszerza któryś z nich przez `extends`) użyczają `inv add` swoich szczegółów, odnajdywane po identyfikatorze, nazwie lub aliasie (jeśli dwie mają wspólny: wskaż właściwą jako `pack.id`); każda inna nazwa, z `:` włącznie, jest własną nazwą przedmiotu.

## Tabele: `tables/`

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

Inne kształty:
- **Listy ważone:** `entries` jako lista, z `weight:` przy każdej pozycji.
- **Kolumny:** `columns: [a, b]` rzuca osobno na każdą kolumnę wiersza. Zwykła pozycja (nie lista) wypełnia każdą kolumnę, więc `columns: [first, second]` na liście słów oznacza „rzuć dwa razy na tę listę”. `labels: false` pomija nazwy kolumn w wyniku („Abandon · Advantage”). `read: "It's a {first} {second} with {third} {fourth} inside."` odczytuje kolumny jako zdanie.
- **Tabele odczytu:** `lookup: hp_lost` albo `[odds, chaos]` dla tabeli dwuwymiarowej.
- **Duplikaty:** `duplicates: reroll | keep | make_it_worse` dla „rzuć dwa razy”.
- **Dwa etapy:** pozycja, która rzuca na inną tabelę (`{table: lightning}` zamiast tekstu albo `then:` po niej), przynosi ze sobą dane tego rzutu: zasada lub szkic, który ją wylosuje, odczytuje oba zestawy danych, najpierw własne klucze pozycji, potem klucze pierwszej tabeli, na którą rzuca się dalej. `--prefill` może wskazać pozycję niżej, na dowolnej głębokości (`Ring of the Hunt`), z danymi każdej pozycji po drodze: z dwóch o tej samej nazwie chodzi o bliższą (potem o pierwszą), pozycja, która prowadzi dalej, rzuca dalej od tego miejsca, a taka, która jest bliska którejś z nich, ale żadną nie jest, zostaje odrzucona z podaniem najbliższej. Szkic z przewodnikiem proponuje pierwszy krok, gdy jego pozycje mówią, czym są (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): wybranie jednej rzuca na następnej tabeli, jak rzut, który na nią trafia.
- **Odczyt w obie strony:** `both_ways: true` przy tabeli d66 dodaje drugi odczyt: 31 daje też 13, a czytający wybiera.
- **Co oznacza pozycja:** `about: "Knows: {skills}. Also known as: {aka}."` wypełnia dane każdej pozycji (lista jest odczytywana jako `a, b`; `{text}` to sama pozycja), by powiedzieć, co ona daje, gdy oferuje ją wybór; własne `note:` pozycji mówi to zamiast niego. Bez żadnego z nich pozycję, której dane mają `id` wskazujące pozycję kompendium, opisuje tamta pozycja.
- **Talie i worki:** `deck: tarot` z `cards` (lub `standard: true`); `bag: initiative` z `tokens`.

Walidacja sprawdza, czy każdy wynik, jaki mogą wyrzucić kości, trafia na jakąś pozycję.

## Zasady: `rules/`

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

Akcje i procedury to listy kroków, a wyzwalacze to kroki z warunkiem `when:`. Kroki to:

| Krok | Działanie |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | rzut zapisany w logu; wiąże `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` jest najpierw wypełniane, jak w każdym tekście, więc kości, które wartość trzyma jako tekst, zostają rzucone (`{@{who.inventory.$item.damage}}`), a log je pokazuje: wartość, która nie jest kośćmi, zostaje odrzucona, podobnie jak `roll: "@die"` z takim tekstem, który niczego nie rzuca; zbiór rzutów (`{d8, d6}kh1`) pozostaje zbiorem |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | wylicza wartości; tak jak w `value` przy `set`, tekst `{…}` to szablon, a gołe słowo to tekst; w każdym wypełnianym tekście `{{` i `}}` zapisują sam nawias klamrowy |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (lub `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | zmienia wpis: z walidacją, przycięciem i możliwością cofnięcia; `set: who.$attr` ustawia pole wskazane przez parametr, a `set: who.inventory.$item.damage` ustawia klucz przedmiotu niesionego przez wpis (zob. Ekwipunek); `-=` usuwa wartość z listy, a taka, której lista nie zawiera, niczego nie zmienia (mówi o tym uwaga; taka, której nigdy nie mogłaby zawierać, zostaje odrzucona); `unset:` usuwa pole, tak jak `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | daje wpisowi przedmiot albo mu go zabiera, tak jak `inv add` i `inv drop`: szczegóły pochodzą z kompendium, wystarczy unikalna część nazwy, a miejsce i hooki pola są sprawdzane |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | używa niesionego przedmiotu tak jak `inv use`: użycia lub ładunki odliczają w dół, kość użycia jest rzucana i przy 1–2 spada o stopień, a zużyty przedmiot znika, chyba że się odnawia albo zostaje zachowany; spośród kilku o tej nazwie pierwszy, któremu zostało użycie; wiąże `@torch.out` (jego ostatnie użycie przepadło), `@torch.gone` (nic z niego nie zostało), `@torch.left`, `@torch.die` i `@torch.rolled` (`as:` domyślnie to `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | od razu tworzy wpis, opisany tak jak w kroku `entity` szkicu (niżej) i sprawdzony względem swojej karty; `as:` (w przeciwnym razie jego `key`, a w ostateczności jego typ) wiąże go jako wpis, odczytywany i ustawiany jak parametr `ref` (`pool: "@bleeding"`, `@bleeding.name`), i nigdy nie jest nazwą parametru; bez `key:` żadne pole nie jest brane za klucz (`kind: track` zostaje tak, jak zapisano); wpis tego typu i o tej nazwie, który już tu jest, zostaje wzięty bez zmian, więc ponownie uruchomiona zasada nie tworzy niczego nowego |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | wykonuje test i wiąże jego wynik |
| `do: other-action`, `with: {…}`, `as: trip` | uruchamia inną zasadę; `@trip` to jej wynik, a `@trip.<name>` to, co powiązała (`@trip.found` dla jej `let: {found: 2}`, `@trip.luck` dla jej `roll: d6`, `as: luck`); `as:` domyślnie to jej identyfikator |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | rzut na tabelę zapisany w logu; wiąże tekst i `data` pozycji (`@scar.<key>`, a klucze mapowania po ich ścieżce: `@scar.cost.hp`), wraz z danymi każdej tabeli, na którą rzuca się potem; lista przedmiotów (`[Rope, {name: Laser, damage: d8}]`) odczytuje się jako ich nazwy (`count(@scar.gear)`, `'Laser' in @scar.gear`), a przekazana krokowi bez zmian (`apply: "@scar.gear"`) jest samymi przedmiotami; listę innych mapowań odczyta tylko krok |
| `table: "setting-{@drop.difficulty}-terrain"` | tabela wyliczana: `{…}` i `$param` zostają wypełnione |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | kilka wyników jako lista (`distinct` przerzuca powtórzenia) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | rozgałęzienia |
| `repeat: "@count"`, `as: i`, `steps: […]` | pętla: kroki wykonywane tyle razy, a `@i` liczy od 1 |
| `for: pcs` (lub `party`), `as: member`, `steps: […]` | kroki wykonywane raz dla każdego bohatera gracza (lub członka drużyny), jako `@member`: wpis, taki jak ten, który wiąże `entity:` (`@member.name`, `set: member.fatigue`); `as:` nigdy nie przyjmuje nazwy parametru, więc własne `who` zasady pozostaje nienaruszone |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | wyjście dla LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (lub `every: 1 day`) | przypomnienie, które staje się aktualne w miarę upływu czasu gry, takie jak te ustawiane przez `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | przerzuca część kości rzutu (mechaniki typu push) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | rzuca na wartość będącą listą (listy wyroczni): wiąże pozycję, `@who.choose` (pusty wiersz) i `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | rzuca malejącą pulą licznika tak jak `track roll` (kości z wynikiem 1-3 odpadają; kości z `drop` odpadają najpierw, kości z `extra` są rzucane razem z nią) albo tylko odrzuca kości (`mode: drop`: push, zaznaczenie); następują powiązane fazy i zdarzenie puli; wiąże `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Wynik testu jest dostępny dla zasady, która go uruchomiła (`check: … as: answer` daje `@answer`), podobnie jak jego flagi: `'random-event' in @answer.flags`. Wartości `with:` są obliczane, gdy zawierają `@`, wypełniane, gdy zawierają `$param` lub `{…}` („Does $npc flee?”), a w pozostałych przypadkach przekazywane tak, jak je zapisano. Zasada z parametrem `oracle` dostaje wpis stanu wyroczni kampanii bez proszenia. Parametr `ref` z `to: monster` bierze wpis tego typu: nazwa, którą dzieli inny wpis (pula wroga nazwana jak jego karta), oznacza ten tego typu.

Wyzwalacze uruchamiają się same, gdy zajdzie ich zdarzenie, i tylko wtedy, gdy spełniony jest ich `when:`:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Każda zasada (także generator i tworzenie postaci) może odczytywać `@system` (identyfikator systemu, w którym gra świat, by setting napisany dla dwóch systemów mógł je rozróżnić), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` i `@time.is_night`, a przy kalendarzu z miesiącami także `@time.month`, `@time.month_name`, `@time.day_of_month` i `@time.year`; gdy trwa walka, także `@combat.round` i `@combat.fighters` (identyfikatory jej uczestników). Wyzwalacz czasowy może też odczytać `@time.passed`, czyli liczbę sekund, o które właśnie przesunięto czas, wyzwalacz `combat_start` lub `combat_end` odczytuje walkę, która się zaczyna lub kończy (uruchamiają je `combat start` i `combat end`; odejście walczącego nie kończy walki), a zasada uruchamiana przez wyzwalacz odczytuje to, co odczytuje wyzwalacz. Wyzwalacz z wymaganymi parametrami uruchamia tylko `didact do` albo hook pola (`who` = wpis). Wyzwalacze `on: manual` działają tylko wtedy, gdy się je wywoła. `for: pcs` (lub `party`) uruchamia wyzwalacz raz dla każdego bohatera gracza (lub członka drużyny), jako `who`: na przykład doświadczenie po każdej sesji. Wyzwalacz, który zawiedzie, zatrzymuje polecenie, które go odpaliło, i mówi, który to był wyzwalacz i jak działać dalej bez niego (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalendarz jest w `settings` pakietu: kalendarz pakietu settingu ma pierwszeństwo przed kalendarzem systemu, a własny kalendarz świata (`calendar:` w jego `world.yaml`) przed oboma:

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

`leap: 4` wydłuża miesiąc o dzień co 4. rok, a `leap: [4, 100, 400]` co 4., ale nie co 100., choć znowu co 400.: każda liczba unieważnia poprzednią. `weekday` podaje dzień tygodnia początku (inaczej jest to pierwszy dzień tygodnia), a `year` to sposób, w jaki data zapisuje swój rok, zarówno w datach, które Didact pokazuje, jak i w tych, które odczytuje (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` sprawdza wszystkie trzy. Kampania może zacząć się innego dnia kalendarza, przed jego początkiem albo po nim: `didact campaign new <id> --date '4 July 1902'` albo `didact time set '<date>'` do jej pierwszej sesji. Dzień tygodnia zapisany przed datą jest sprawdzany: rozstrzyga data, a uwaga mówi, kiedy wypada ona w inny dzień.

Opcje to warianty i reguły opcjonalne systemu, wybierane przez każdą kampanię na sesji zerowej:

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

`didact campaign profile lethality=deadly supplies=on` je zapisuje (albo strona Ustawienia aplikacji webowej). Reguły, tworzenie postaci i generatory je odczytują (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): odpowiedź ma pierwszeństwo przed tym, co pociąga za sobą inna opcja, a to przed wartością domyślną. To, co pociąga za sobą opcja, jest stosowane aż do końca łańcucha (klimat, który ustawia zabójczość, ustawia też to, co pociąga za sobą ta zabójczość), a z dwóch takich skutków wygrywa bliższy. Podsumowanie wymienia te, które różnią się od wartości domyślnej, wraz z ich znaczeniem, by prowadzący stosował to, czego reguły nie potrafią. Generator, który nie może przy nich działać, zatrzymuje się krokiem `stop:` z powodem i nie powstaje żaden szkic.

## Wyrocznie: `oracles/`

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

- **Pytanie:** `didact ask '…' --odds likely` uruchamia test `ask`. Odpowiedzią jest jego wynik (pasmo), a jego flagi idą razem z nim.
- **Stan:** znajduje się we wpisie, który test otrzymuje jako `oracle`. Test zmienia go przez `set: oracle.chaos += 1`.
- **Listy:** `lists: {names: […], method: sections, most: 3}` przechowuje listy ważone w tym wpisie. `didact lists add|drop|roll|show` nimi zarządza, a zasady losują z nich przez `pick`. `sections` losuje sekcję pięciu wierszy, a potem wiersz w niej (pusty wiersz oznacza wybór); `uniform` daje każdemu wierszowi taką samą szansę.
- **Więcej dla testu:** `didact ask '…' --with as_rule=true` przekazuje dodatkowe parametry do testu wyroczni.
- **Log:** każda odpowiedź jest numerowana (`#o12`) i zapisywana w logu, a `didact interpret o12 '…'` zachowuje jej znaczenie. Wyrocznia `yes-no` z pakietu core jest rozwiązaniem zapasowym.

## Generatory i tworzenie postaci: `generators/`, `chargen/`

Jedne i drugie to procedury, które budują **szkic**. Używają każdego kroku zasad (`roll`, `table`, `if`, `let`, `prompt`, …) i dodatkowo tych:

| Krok | Działanie |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | dodaje wpis do szkicu (klucze `poi-1`, `poi-2`, …); pole lub powiązanie wskazujące klucz zapisany przez pakiet (`key:` albo nazwę `as:`) staje się przy zatwierdzeniu identyfikatorem tamtego wpisu, więc wybieraj klucze, których żadne pole nie zawiera jako tekstu (encja bez żadnego z nich nie ma klucza do podmiany); `from: "@relic.id"` tworzy go na podstawie pozycji kompendium (jej typu, nazwy i pól) |
| `choose: {from: [a, b], as: x}` (lub `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | wybór; w trybie krok po kroku szkic czeka na `choose`; `exclude` wyklucza wcześniejsze wybory (wylosowany jest losowany ponownie); `records:` dodaje do opcji tutejsze wpisy tego typu, po id (utworzone w grze); `answer:` dokonuje wyboru bez pytania, gdy jego wartość jest jedną z opcji (własna ścieżka postaci) |
| `choose_or_roll: {table: backgrounds, as: background}` | wybór, którego mogą dokonać kości; dane wybranej pozycji to `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | rzuty zapisywane w postaci |
| `swap: {among: [STR, DEX, WIL], optional: true}` | zamiana dwóch wartości albo ich pozostawienie |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | rozdziela stały zestaw wartości |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | kupowanie wartości w ramach budżetu (`default: random` w trybie losowym wydaje go losowo) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | lista trafia do ekwipunku; mapowanie ustawia pola (listy się sumują) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | dodaje do pola postaci (lub obiektu ze szkicu): liczby się sumują, wszystko inne dołącza do listy; brak czegoś do dodania nie jest błędem |
| `remove: {field: talents, value: "@old"}` | usuwa coś z pola listy (wymieniony talent, rozwiązaną więź); brak czegoś do usunięcia nie jest błędem |
| `roll_tables: [physique, vice]` | rzuca na tabele do `traits`; `data.gear` pozycji trafia do ekwipunku, a `data.add: {gold: 20}` dodaje do pól |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | imię; `name: {prompt: …}`, gdy nie ma z czego losować, czeka na nie, nawet w trybie losowym |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | pytanie, na które pasuje każda odpowiedź (cel, nazwa innego wpisu): szkic czeka na nie, nawet w trybie losowym, chyba że zostało wypełnione z góry; `field:` zapisuje odpowiedź |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawl: rozrzut kości zapisany w logu, ścieżki (zawsze połączone), odległości, ukryte ścieżki (zob. niżej) |

Krok map przyjmuje więcej, na potrzeby procedur rozrzutu kości z podręcznika:

| Klucz | Działanie |
|---|---|
| `regions: terrain` | te obiekty też są rozrzucane; każde miejsce dołącza do najbliższego z nich (swojego `region`) |
| `hidden: 6`, `conditional: 5` | d6 na każdą ścieżkę: wynik równy tej liczbie lub wyższy daje ścieżkę ukrytą lub warunkową (ukryte ścieżki nie trafiają na mapę graczy) |
| `describe: [path-feature, path-condition]` | tabele, na które się rzuca dla każdej ścieżki, zachowane jako jej `details` |
| `entrance: true`, `exit: true` | miejsce najbliżej krawędzi jest wejściem; pozostałe są numerowane od niego wzdłuż ścieżek (`map.n`), ścieżki prowadzą od niego, a wyjście to odległe miejsce blisko krawędzi, numerowane jako ostatnie |
| `number: "{@dungeon_name}, room {@n}"` | zmienia nazwy ponumerowanych miejsc (ich klucze w szkicu idą za tym: `room-1` to pokój 1) |

Tabela rozrzutu kości może wskazywać kolejne tabele w danych swoich pozycji, więc procedura czyta się jak podręcznik: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, a potem `table: "{@drop.what}"`. Nieustawione pola list (conditions, lists, tags) odczytują się jako puste listy, więc `'deprived' in @who.conditions` działa od początku.

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

Procedura chargen z `advances:` zmienia wpis, zamiast go tworzyć: to awans na wyższy poziom w danym systemie.

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

- **Jeden wpis:** generator z `creates: npc` buduje ten wpis tak, jak tworzenie postaci buduje postać (`apply`, `add`, `name`, `field:`); jego kroki `entity` dodają wpisy obok, a odnośnik `to: character` wskazuje na niego.
- **Uruchamianie:** `gen run` i `char new` tworzą szkic (`#g7`, `#c3`) i niczego nie zapisują. `stop:` kończy go bez tworzenia szkicu: pod `if:`, które odczytuje opcję kampanii, jego wskazówka odsyła do opcji (`didact session zero`); w przeciwnym razie jego własne słowa mówią, co zrobić zamiast tego.
- **Rozstrzyganie:** `--prefill '{…}'` rozstrzyga sprawy z góry, według nazwy, którą wiąże krok (`as:`): pojedyncza wartość odpowiada na każde wystąpienie, lista na każde wystąpienie po jednym elemencie (lista dla `choose` z `count` to cały wybór). Wartości `let` też można wypełnić z góry (`{"hp": 6}`), a imię, `ask` lub `let` zachowuje każdy tekst dokładnie tak, jak go podano. Wartość dla wyboru spośród znanych opcji (`choose`, pozycja tabeli) wskazuje opcję wprost (także inną wielkością liter), przez `id` jej pozycji albo przez rzut, który na nią trafia (`{"group": 3}`), i przynosi dane tej pozycji; wartość bliska którejś opcji, ale niebędąca żadną z nich, zostaje odrzucona ze wskazaniem najbliższej, a każda inna jest własną odpowiedzią, bez danych. `--auto` (lub `char new --mode random`) pozwala kościom rozstrzygnąć resztę. W przeciwnym razie szkic czeka przy każdym wyborze.
- **Opisywanie:** wybór mówi wybierającemu graczowi, co oznacza każda opcja: `note:` pozycji tabeli lub `about:` jej tabeli, a w przeciwnym razie pozycja kompendium, którą wskazuje (`id` w jej danych), albo ta, którą jest sama opcja (wybór spośród identyfikatorów kompendium pokazuje nazwę każdej z nich): jej `tagline` i `summary`, jej `description` lub `effect`, a w ostateczności pierwszy akapit jej tekstu.
- **Cofanie się:** `char back` (lub `gen back`) wycofuje ostatnią odpowiedź, rzut lub edycję, więc szkic znów zadaje to pytanie; rzuty wykonane w tym kroku zostają oznaczone jako cofnięte.
- **Wznawianie:** wznowiony szkic odtwarza swój ślad: każdą wyrzuconą lub wybraną wartość, każdą użytą raz i po kolei (także rozrzut kości na mapie), więc nic nie jest rzucane dwa razy i nic już rozstrzygniętego się nie zmienia.
- **Zapisywanie:** `commit` zapisuje wpisy, sprawdzone względem ich kart.
- **Rozwój:** szkic z `advances:` zaczyna się od kopii wpisu (z domyślnymi wartościami z jego karty), jego kroki odczytują wpis jako `@who`, wartości szkicu jako `@character.*`, a `commit` zapisuje tylko to, co się zmieniło, sprawdzając to jak przy `set`; wpisy tworzone przez jego kroki `entity` (wątek nowej więzi) powstają obok: odnośnik `to: character` wskazuje na wpis, a pole wskazujące klucz przechowuje identyfikator wpisu o tym kluczu, tak jak przy tworzeniu postaci (`apply: {blood: "@pool"}`). `stop:` mówi, dlaczego jeszcze nie (za mało PD), i żaden szkic nie powstaje. System, w którym rozwój postaci to jedna zasada, zamiast tego wskazuje ją w swoim chargen: `advance: {rule: grow}`.
- **Tryby:** `modes: [guided]` sprawia, że procedura idzie tylko krok po kroku: `--mode random` jest odrzucane.

## Kompendium, podręcznik i słowniczek

- **Pozycje kompendium** zapisuje się jak `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Na wartość `"roll 2d8"` rzuca się, gdy pozycja się pojawia. Uruchom `didact spawn troll` albo wprowadź pozycje pakietu do świata przez `didact compendium import <pack>` (`--type loc`, a `--tag coast` dla tych, które mają każdy podany tag).
- **Dla kilku systemów:** klucz najwyższego poziomu trafia tam, gdzie umieszcza go `set`: do bloku systemu, gdy jego karta ma takie pole, a w przeciwnym razie do `fields`. Pozycja, którą setting pisze dla więcej niż jednego systemu, podaje liczby każdego z nich w jego własnym bloku (`mechanics: {my-system: {hp: 12}}`): `pack validate` sprawdza każdy blok z kartą tego systemu, gdy jest zainstalowany, i odnotowuje klucz najwyższego poziomu, który ma zarówno ta karta, jak i karta core. To, co mówi blok, obowiązuje: obok `mechanics: {my-system: {role: tactician}}` klucz `role: innkeeper` na najwyższym poziomie jest polem core, tak jak wszystko pod `fields:`. Blok wskazujący walidowany pakiet jest sprawdzany względem tego pakietu w takim stanie, w jakim jest w swoim folderze.
- **Sekcje podręcznika** trafiają do `reference/*.md`, z front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` je znajduje; fraza w cudzysłowie, której tam nie ma, jest sprawdzana słowo po słowie.
- **Słowniczek** to `glossary.yaml`: `term: definition` albo lista `{term, definition, aliases, see}`. `didact define <term>` go odczytuje.

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

## Udostępnianie i usuwanie pakietów

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Pakietu, który deklaruje `redistributable: false`, nie da się wyeksportować.
- **core** jest częścią Didact i jest zawsze włączony: każdy system się na nim opiera, więc nie da się go wyłączyć ani odinstalować.
- Pozostałe pakiety dołączone do Didact to pliki `.didactpack` w jego folderze `packs/`. `pack list` pokazuje je, dopóki nie zostaną zainstalowane, a instalacja jednego z nich dociąga potrzebne mu pakiety, jeśli też są dołączone.
- `pack update` szuka nowszych wersji w folderze `packs/` Didact i na GitHubie (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` wskazuje inne miejsce albo nic, jeśli nie ma szukać). Nowa wersja instaluje się obok starej: kampanie zachowują swoją aż do `didact campaign upgrade`.
- Naraz w użyciu jest jeden system gry: system otwartego świata. Świat zachowuje system, z którym go utworzono (`didact world new <id> --system <pack>`; świat utworzony bez systemu przyjmuje pierwszy, który dostanie, przez `pack enable` lub `world set system=`), jego kampanie grają w tym systemie, a pakietu, który wymaga innego systemu (settingu napisanego dla niego), nie można dodać: w innym systemie gra się w osobnym świecie.
- `uninstall` odmawia, dopóki świat lub kampania używa jedynej kopii pakietu (`--force` i tak go usuwa). Tego nie da się cofnąć: zainstaluj ponownie plik .didactpack.

## Od podręcznika do pakietu: lista kontrolna

Przejdź przez mechaniki podręcznika w tej kolejności. Każda odpowiada czemuś z powyższych:

1. **Rozstrzyganie:** kiedy rzut jest udany (test: `success`, `bands`, `auto`).
2. **Kości:** nietypowe kości, symbole, stopnie (`dice.yaml`, nazwane kości, łańcuchy).
3. **Karta:** atrybuty, liczby pochodne (`schemas/`, pola derived).
4. **Zasoby:** HP, szczęście, impet (pola resource i counter; kroki `set`).
5. **Stany:** jakie są i co robią (pola `conditions`; kroki `if`).
6. **Walka:** ataki, obrażenia, inicjatywa (akcje; `bag`/`deck` dla kolejności tur).
7. **Procedury:** eksploracja, podróż, przestój (procedury z podpowiedziami).
8. **Tabele:** każda tabela losowa (`tables/`; `pack import` dla tabel w Markdownie).
9. **Bestiariusz:** potwory i BN (`compendium/`).
10. **Przedmioty:** wyposażenie, zaklęcia, relikty (`compendium/`, pola slots).
11. **Porady dla MG:** zasady prowadzenia i rady (`GUIDE.md`, `reference/`, `guidance:` przy typach).
12. **Tworzenie postaci:** jak stworzyć postać (procedura `chargen/` albo `roll:` przy każdym polu).

Wszędzie podawaj strony przez `source:`, żeby luki wyszły na jaw. Dodaj test smoke-play, który tworzy postać, wykonuje test, walczy i uruchamia procedurę.
