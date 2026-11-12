<!-- translated from b1dfa1159ff4 -->
# Csomagok

A csomag egy játékrendszer, orákulum, háttérvilág, kaland vagy kiegészítő, YAML-fájlokként megírva, egy opcionális Python-bővítménnyel. Ez az útmutató megmutatja, hogyan írj egyet: hogyan alakíts egy szabálykönyvet csomaggá, vagy hogyan adj hozzá saját tartalmat.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Csomag abból is készülhet, ami a könyvtáradban van. A `didact pack new my-brew --from-overlay my-system` kiegészítővé alakítja egy rendszerhez írt saját anyagaidat (`compendium add`, a `--scope system` hatókörrel őrzött bejegyzések, háttértudás), a `didact world export --as setting` pedig háttérvilág-csomaggá alakít egy világot: a személyei, helyszínei és háttértudása kompendiumtételek és csomagháttértudás lesznek, amelyeket a `compendium import` hoz be egy másik világba. Mindkettő kihagyja a titkokat és a KM jegyzeteit, hacsak nincs `--secrets`, és egyik sincs megoszthatónak jelölve, amíg be nem állítod a licencét.

## Felépítés

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

Egy fájl egy elemet, elemek listáját, vagy több, `---` jellel elválasztott elemet tartalmaz. Minden elem a fajtája kulcsával adja meg az azonosítóját: `table: weather`, `check: save`, `type: pc`, vagy kompendium-bejegyzéseknél `id: troll`. Az elemekre `pack.id` alakban hivatkozz (`my-system.save`), vagy csupasz azonosítóval, ha csak egy bekapcsolt csomagban van ilyen.

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

Egy hack az `extends` alatt nevezi meg az alapját, és csak azt tartalmazza, ami eltér:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Az azonos azonosítójú eleme az alap elemének helyébe lép, bármilyen fajta is (táblázat, szabály, kompendium-bejegyzés, hivatkozási szakasz, szószedet-fogalom). A `settings` alatti értékei kulcsonként az alap értékeire rétegződnek: a hack által megadott kulcs egészében lecseréli az alap értékét (a `names` alatti táblázatai az alap névtáblázatait váltják fel), és az alap szabályai is a hack értékeit olvassák. A `hides` elhagyja azt, ami megmarad, és amire a hacknek nincs szüksége: a `*` bármilyen karaktersorozatra illik, az azonosítóra illő utolsó minta dönt, a `!` jellel kezdődő minta pedig megtartja az elemet. Amit a hack lecserél, az soha nincs elrejtve. A fajták: `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` és `term`. A `didact pack validate` figyelmeztet az olyan mintára, amely semmire sem illik.

## Kifejezések

Minden feltétel és képlet a kockanyelvet használja (`didact guide dice`), továbbá:
- **Értékek:** a `@name` egy értéket olvas: `@roll`, `@who.STR`, `@settings.x`. A `$name` előbb beilleszti egy paraméter szövegét, így a `@who.$attr` ebből lesz: `@who.STR`. Szabad szöveges paramétert `@name` alakban olvass, ne idézőjelben (`'$name'`): a szövegében lévő aposztróf lezárná az idézőjelet (a `pack validate` figyelmeztet).
- **Logika:** `and`, `or`, `not` és `in` (`'deprived' in @who.conditions`).
- **Literálok:** szöveg (`'travel'`) és `true`/`false`.
- **Függvények:** az `if(cond, a, b)` csak azt az ágat dobja, amelyiket választja. A `default(@thread.flashpoint, 0)` az érték, vagy a tartalék, ha nincs beállítva. A `sum`, a `count` (`count(@roll.dice, 6)` a hatosokat számolja), a `min`, a `max`, az `any` és az `all` listákat fogad.

## Lapok: `schemas/`

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

| Fajta | Mit tárol | Beállítások |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | egyszerű értéket | min, max; `values` az enumhoz |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: a `@hp` az érték, a `@hp.max` a plafon | range; min; max vagy max_field; die |
| `counter` | egy számot | min, max, thresholds, occupies (egy slots mező) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | tárgyakat (`Rope` vagy `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | amit a neve mond | `to` (refs esetén), `allowed` |
| `derived` | számított, sosem tárolt | expr |

Minden mező elfogadja a `label`, `help`, `default`, `required` és `roll` beállítást is: a `new pc Hero --fill`, vagy a `"roll"` érték a naplón keresztül dob rá. A `core` csomag típusai rendszerfüggetlen szöveget tárolnak a `fields` alatt. Egy rendszer típusai a számaikat a `mechanics.<system>` alatt tárolják. A `set hero hp-=2` megtalálja a mezőt, korlátozza az értéket, és jelzi a túlcsordulást. A `+=` listához ad hozzá: egy `list` (mint a `slots`) az újra hozzáadott értéket is megtartja, a `tags`, a `conditions` és a `refs` csak egyszer tárolja, a `-=` pedig minden példányát eltávolítja.

**A hookok** megmondják, mi történik, ha egy érték átlép egy határt. Minden változáskor lefutnak (`set`, `inv`, egy szabály `set` lépése), de csak ha a határt átlépik: 3 → 0 kivált, 0 → 0 nem. A `--force` szerkesztések kihagyják őket.

| Hook | Mikor fut le |
|---|---|
| `on_zero` | egy szám vagy `{value}` eléri a 0-t |
| `on_full` (slots esetén `when_full`) | eléri a max, size vagy capacity értékét |
| `thresholds: {10: …, 20: …}` (számlálók) | túllép az egyes jelzéseken |

Egy akció lehet szöveg (jegyzet az LLM-nek), `{set: {hp: 0}}` vagy `{condition: paralyzed}` ugyanazon a bejegyzésen, `{trigger: death}` (lefuttatja azt a szabályt, `who` = a bejegyzés), vagy ezek listája.

**A felszerelés** (`didact inv …`) a lap `slots` mezőjén működik:
- **Hely:** a tárgyak `size` × `count` helyet foglalnak, a mezőt `occupies` kulccsal elfoglaló számlálók pedig az értéküket. A `capacity` túllépését elutasítja, hacsak nincs `--force`.
- **Csoportok:** a `groups: {backpack: 6, body: 4}` minden csoportnak saját helyet ad, valamint saját oszlopokat és összegeket: a `@inventory.body.armor` csak az, ami viselve vagy kézben van, a `@inventory.body.free` pedig a csoport maradék helye.
- **Használat:** a `uses: 3` az `inv use` hatására visszaszámol. A `uses: d8` használati kocka: 1–2 esetén egy lépcsővel kisebb lesz. Az elhasznált tárgy eltűnik, hacsak nincs `recharge` vagy `keep: true` beállítása. Több azonos nevű tárgy közül a név az elsőt jelenti; használat elköltésekor (`inv use`, egy szabály `use:` lépése, `set …uses-=1`) az elsőt, amelynek még van használata.
- **A tárgy saját kulcsai:** a `didact set freya inventory.sword.damage=d10` (egy szabályban a `set: who.inventory.$item.damage` is) ezek egyikét módosítja, a tárgyat úgy megnevezve, ahogy az `inv` is megnevezi, a neve egy részével vagy a teljes nevével, szóközökkel és pontokkal együtt (`'inventory.12.7mm pistol.damage=d10'`, a shell kedvéért idézőjelben); a `uses` és a `charges` úgy működik, mint egy `uses` mező (a `charges+=2` megáll a maximumánál), a helyet pedig ugyanúgy ellenőrzi, mint az `inv add`. Egy szabály `@{who.inventory.$item.damage}` alakban olvas ki egyet (a használati kockát kockaként, a használatokat számukként); az a tárgy vagy kulcs, amely nincs ott, hiányzóként olvasandó, így a `default(…)` adja a tartalékértékét.
- **Kompendium:** az `item` típusú (vagy weapon, armor, relic, … típusú, illetve a csomag olyan saját típusú, amely `extends` révén ezek egyikét bővíti) bejegyzések kölcsönzik a részleteiket az `inv add` parancsnak, azonosító, név vagy álnév alapján megtalálva (ha kettőnek ugyanaz: nevezd meg a kívántat `pack.id` alakban); minden más név, `:` jellel együtt, a tárgy saját neve.

## Táblázatok: `tables/`

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

Más formák:
- **Súlyozott listák:** az `entries` lista, soronként `weight:` értékkel.
- **Oszlopok:** a `columns: [a, b]` egy sor minden oszlopára külön dob. Egy egyszerű bejegyzés (nem lista) minden oszlopot kitölt, így a `columns: [first, second]` egy szólistán azt jelenti: „dobj kétszer erre a listára”. A `labels: false` kihagyja az oszlopneveket az eredményből („Abandon · Advantage”). A `read: "It's a {first} {second} with {third} {fourth} inside."` mondattá olvassa az oszlopokat.
- **Kikeresés:** `lookup: hp_lost`, vagy `[odds, chaos]` egy kétdimenziós táblához.
- **Ismétlődések:** `duplicates: reroll | keep | make_it_worse` a „dobj kétszer” esetekre.
- **Két lépésben:** az a bejegyzés, amely egy másik táblázatra dob (helyette `{table: lightning}`, vagy utána `then:`), magával hozza annak a dobásnak az adatait: az a szabály vagy vázlat, amely kidobja, mindkettőt olvassa, előbb a bejegyzés saját kulcsait, aztán az utána elsőként dobott táblázatéit. Egy `--prefill` megnevezhet egy lejjebb lévő bejegyzést is, bármilyen mélységben (`Ring of the Hunt`), az út minden bejegyzésének adataival: két azonos nevű közül a közelebbi számít (aztán az első), a továbblépő onnan dob tovább, az pedig, amely valamelyikhez közel esik, de egyik sem, elutasításra kerül, és a legközelebbit megnevezi. Egy vezetett vázlat felkínálja az első lépést, ha a bejegyzései megmondják, mik (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): egyet választva a következő táblázatra dob, mint egy rá eső dobás.
- **Mindkét irányú olvasás:** a `both_ways: true` egy d66-os táblázaton hozzáadja a másik olvasatot: a 31 a 13-at is adja, és az olvasó választ.
- **Mit jelent egy bejegyzés:** az `about: "Knows: {skills}. Also known as: {aka}."` minden bejegyzés adataival töltődik ki (egy lista így olvasható: `a, b`; a `{text}` maga a bejegyzés), hogy elmondja, mit ad a bejegyzés, amikor egy választás felkínálja; egy bejegyzés saját `note:` kulcsa ehelyett mondja el. Ha egyik sincs, azt a bejegyzést, amelynek adataiban egy kompendium-bejegyzést megnevező `id` van, az a kompendium-bejegyzés írja le.
- **Paklik és zsákok:** `deck: tarot` `cards` kulccsal (vagy `standard: true`); `bag: initiative` `tokens` kulccsal.

Az ellenőrzés megnézi, hogy minden eredmény, amit a kockák dobhatnak, egy bejegyzésre esik-e.

## Szabályok: `rules/`

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

Az akciók és az eljárások lépéslisták, a kiváltók pedig `when:` feltétellel ellátott lépések. A lépések:

| Lépés | Mit csinál |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | naplózott dobás; köti a `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>` értékeket; egy `{…}` először kitöltődik, mint bármely szövegben, így a kockák, amelyeket egy érték szövegként tart, el lesznek dobva (`{@{who.inventory.$item.damage}}`), és a napló megmutatja őket: az az érték, amely nem kocka, elutasításra kerül, akárcsak az ilyen szövegű `roll: "@die"`, amely nem dob semmit; a dobások csoportja (`{d8, d6}kh1`) csoport marad |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | értékeket számol; ahogy a `set` `value` kulcsánál, a `{…}` szöveg sablon, a csupasz szó pedig szöveg; minden kitöltött szövegben a `{{` és a `}}` magát a kapcsos zárójelet írja |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (vagy `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | módosít egy bejegyzést: ellenőrizve, korlátozva, visszavonhatóan; a `set: who.$attr` azt a mezőt állítja be, amelyet egy paraméter megnevez, a `set: who.inventory.$item.damage` pedig egy nála lévő tárgy egyik kulcsát (lásd: Felszerelés); a `-=` kivesz egy értéket egy listából, és az, ami nincs benne, nem változtat semmin (egy megjegyzés jelzi; az, ami sosem lehetne benne, elutasításra kerül); az `unset:` eltávolít egy mezőt, ahogy a `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | tárgyat ad egy bejegyzésnek, vagy elvesz tőle egyet, ahogy az `inv add` és az `inv drop` is: a részletei a kompendiumból jönnek, elég a nevének egy egyedi része, a helyet és a mező hookjait pedig ellenőrzi |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | használ egy nála lévő tárgyat, ahogy az `inv use`: a használatok vagy töltések visszaszámolnak, a használati kockával dob, és 1–2 esetén egy lépcsővel kisebb lesz, az elfogyott pedig eltűnik, hacsak nem töltődik újra vagy nem tartják meg; több ilyen nevű közül az elsőt, amelynek van még használata; köti a `@torch.out` (elment az utolsó használata), a `@torch.gone` (semmi sem maradt belőle), a `@torch.left`, a `@torch.die` és a `@torch.rolled` értékét (az `as:` alapértéke `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | azonnal létrehoz egy bejegyzést, úgy leírva, mint egy vázlat `entity` lépésében (lásd lent), és a lapjához ellenőrizve; az `as:` (különben a `key` kulcsa, különben a típusa) bejegyzésként köti, amely úgy olvasható és állítható be, mint egy `ref` paraméter (`pool: "@bleeding"`, `@bleeding.name`), és sosem egy paraméter neve; `key:` nélkül egyetlen mezőt sem tekint kulcsnak (a `kind: track` úgy marad, ahogy írva van); az itt már meglévő, azonos típusú és nevű bejegyzést úgy veszi át, ahogy van, így az újra lefuttatott szabály semmi újat nem hoz létre |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | lefuttat egy próbát, és köti a kimenetelét |
| `do: other-action`, `with: {…}`, `as: trip` | lefuttat egy másik szabályt; a `@trip` az eredménye, a `@trip.<name>` pedig az, amit kötött (`@trip.found` a `let: {found: 2}` lépéséből, `@trip.luck` a `roll: d6`, `as: luck` lépéséből); az `as:` alapértéke az azonosítója |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | naplózott táblázatdobás; köti a szöveget és a bejegyzés `data` értékét (`@scar.<key>`, egy leképezés kulcsait pedig útvonaluk szerint: `@scar.cost.hp`), valamint bármely utána dobott táblázatét; egy tárgylista (`[Rope, {name: Laser, damage: d8}]`) a tárgyak neveiként olvasandó (`count(@scar.gear)`, `'Laser' in @scar.gear`), egy lépésnek úgy átadva, ahogy van (`apply: "@scar.gear"`), pedig maguk a tárgyak; más leképezések listáját csak egy lépés olvashatja |
| `table: "setting-{@drop.difficulty}-terrain"` | számított táblázat: a `{…}` és a `$param` kitöltődik |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | több eredmény listaként (a `distinct` újradobja az ismétlődéseket) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | elágazás |
| `repeat: "@count"`, `as: i`, `steps: […]` | ciklus: annyiszor futtatja a lépéseket, amennyi az érték, a `@i` 1-től számol |
| `for: pcs` (vagy `party`), `as: member`, `steps: […]` | minden játékos karakterre (vagy csapattagra) egyszer lefuttatja a lépéseket, `@member` néven: ez egy bejegyzés, mint amilyet az `entity:` köt (`@member.name`, `set: member.fatigue`); az `as:` sosem kaphatja egy paraméter nevét, így a szabály saját `who` paramétere érintetlen marad |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | kimenet az LLM-nek |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (vagy `every: 1 day`) | emlékeztető, amely a játékidő múlásával esedékessé válik, olyan, amilyet a `didact remind` is beállít |
| `reroll: roll`, `keep_if: "@face == 6"` | egy dobás néhány kockáját újradobja (a dobás erőltetése) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | dob egy listaértékre (egy orákulum listáira): köti a bejegyzést, a `@who.choose` (üres sor) és a `@who.empty` értéket |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | dob egy számláló fogyó kockakészletével, ahogy a `track roll` is (az 1-3-at mutató kockák kiesnek; a `drop` kockái esnek ki elsőként, az `extra` kockái együtt gurulnak velük), vagy csak elvet kockákat (`mode: drop`: erőltetés, bejelölés); ezt követik az összekapcsolt fázisok és a készlet eseménye; köti a `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` értékeket |

Egy próba kimenetelét az őt futtató szabály olvashatja (a `check: … as: answer` a `@answer` értéket adja), és a jelzőit is: `'random-event' in @answer.flags`. A `with:` értékei kiértékelődnek, ha `@` van bennük, kitöltődnek, ha `$param` vagy `{…}` van bennük („Does $npc flee?”), egyébként úgy adódnak át, ahogy írva vannak. Az `oracle` paraméterrel rendelkező szabály külön kérés nélkül megkapja a kampány orákulumának állapotbejegyzését. Egy `to: monster` megadású `ref` paraméter ilyen típusú bejegyzést vesz: az a név, amelyen egy másik bejegyzés osztozik (egy ellenség készlete, a kártyája után elnevezve), az ilyen típusút jelenti.

A kiváltók maguktól futnak le, amikor az eseményük bekövetkezik, és csak akkor, ha a `when:` feltételük teljesül:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Bármely szabály (a generátor és a karakteralkotás is) olvashatja a `@system` (a világban játszott rendszer azonosítója, így egy két rendszerhez írt háttérvilág meg tudja különböztetni őket), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` és `@time.is_night` értékeket, hónapokat tartalmazó naptárral pedig a `@time.month`, `@time.month_name`, `@time.day_of_month` és `@time.year` értékeket is; amíg harc folyik, a `@combat.round` és a `@combat.fighters` értékeket is (a harcban részt vevők azonosítóit). Egy időkiváltó a `@time.passed` értéket is olvashatja, az épp léptetett másodperceket, egy `combat_start` vagy `combat_end` kiváltó a kezdődő vagy véget érő harcot olvassa (a `combat start` és a `combat end` futtatja őket; egy harcoló kilépése nem vet véget a harcnak), a kiváltó által futtatott szabály pedig ugyanazt olvashatja, amit a kiváltó. A kötelező paraméterekkel rendelkező kiváltót csak a `didact do` vagy egy mezőhook futtatja (`who` = a bejegyzés). Az `on: manual` kiváltók csak hívásra futnak. A `for: pcs` (vagy `party`) minden játékos karakterre (vagy csapattagra) egyszer futtatja le a kiváltót, `who` néven: így jár például tapasztalat minden alkalom után. A hibára futó kiváltó leállítja az őt elindító parancsot, és megmondja, melyik kiváltó volt, és hogyan lehet nélküle továbblépni (`didact override add trigger <id> --data '{"on": "manual"}'`).

A naptár egy csomag `settings` beállításai között van: egy háttérvilág-csomag naptára felülírja a rendszerét, egy világ saját naptára (`calendar:` a `world.yaml` fájljában) pedig mindkettőt:

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

A `leap: 4` egy hónapot minden 4. évben egy nappal hosszabbá tesz, a `leap: [4, 100, 400]` pedig minden 4. évben, de nem minden 100. évben, viszont minden 400. évben igen: minden szám felülírja az előzőt. A `weekday` megnevezi, a hét melyik napja a kezdet (különben a hét első napja), a `year` pedig azt adja meg, hogyan írja egy dátum az évét, a Didact által mutatott és az általa olvasott dátumokban egyaránt (`"3A {year}"`: `17 Frost 3A 201`); a `pack validate` mindhármat ellenőrzi. Egy kampány a naptár egy másik dátumán is kezdődhet, a kezdete előtt vagy után: `didact campaign new <id> --date '4 July 1902'`, vagy `didact time set '<date>'` az első alkalmáig. A dátum elé írt napot ellenőrzi: a dátum dönt, és egy megjegyzés jelzi, ha másik napra esik.

A beállítások a rendszer változatai és választható szabályai, amelyeket minden kampány a nulladik alkalmon választ ki:

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

A `didact campaign profile lethality=deadly supplies=on` menti őket (vagy a webalkalmazás Beállítások oldala). A szabályok, a karakteralkotás és a generátorok olvassák őket (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): egy válasz megelőzi azt, amit egy másik beállítás maga után von, az pedig az alapértéket. Amit egy beállítás maga után von, azt a Didact végigköveti (egy hangvétel, amely megadja a halálosságot, azt is megadja, amit az a halálosság maga után von), és két következmény közül a közelebbi nyer. Az összefoglaló felsorolja azokat, amelyek eltérnek az alapértéküktől, a jelentésükkel együtt, hogy a mesélő alkalmazza, amit a szabályok nem tudnak. Az a generátor, amely ezekkel nem futhat, `stop:` lépéssel és az okkal leáll, és nem készül vázlat.

## Orákulumok: `oracles/`

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

- **Kérdezés:** a `didact ask '…' --odds likely` lefuttatja az `ask` próbát. A válasz a kimenetele (egy sáv), és a jelzői vele tartanak.
- **Állapot:** egy bejegyzésben él, amelyet a próba `oracle` néven kap meg. A próba a `set: oracle.chaos += 1` lépéssel módosítja.
- **Listák:** a `lists: {names: […], method: sections, most: 3}` súlyozott listákat tart azon a bejegyzésen. A `didact lists add|drop|roll|show` kezeli őket, a szabályok pedig a `pick` lépéssel dobnak rájuk. A `sections` előbb egy ötsoros szakaszra dob, aztán azon belül egy sorra (az üres sor azt jelenti: válassz); a `uniform` minden sornak ugyanakkora esélyt ad.
- **Több adat a próbának:** a `didact ask '…' --with as_rule=true` további paramétereket ad át az orákulum próbájának.
- **A napló:** minden válasz sorszámot kap (`#o12`) és naplózódik, a `didact interpret o12 '…'` pedig megőrzi, mit jelentett. A core csomag `yes-no` orákuluma a tartalék.

## Generátorok és karakteralkotás: `generators/`, `chargen/`

Mindkettő olyan eljárás, amely **vázlatot** épít. Minden szabálylépést használnak (`roll`, `table`, `if`, `let`, `prompt`, …), továbbá ezeket:

| Lépés | Mit csinál |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | bejegyzést ad a vázlathoz (kulcsok: `poi-1`, `poi-2`, …); egy mező vagy kapcsolat, amely a csomag által írt kulcsot nevez meg (`key:` vagy egy `as:` név), jóváhagyáskor annak a bejegyzésnek az azonosítója lesz, ezért olyan kulcsokat válassz, amelyeket egyetlen mező sem tartalmaz szövegként (az az entitás, amelynek egyik sincs, nem kap cserélendő kulcsot); a `from: "@relic.id"` egy kompendiumtételből indítja (annak típusával, nevével és mezőivel) |
| `choose: {from: [a, b], as: x}` (vagy `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | választás; vezetett módban a vázlat a `choose` parancsra vár; az `exclude` kizárja a korábbi választásokat (a kidobottat újradobja); a `records:` a lehetőségek közé veszi az itteni, adott típusú bejegyzéseket, azonosítóval (a játék közben készülteket); az `answer:` kérdés nélkül meghozza a választást, ha az értéke az egyik lehetőség (a karakter saját ösvénye) |
| `choose_or_roll: {table: backgrounds, as: background}` | választás, amelyet a kockák is meghozhatnak; a választott bejegyzés adata `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | a karakterbe dob |
| `swap: {among: [STR, DEX, WIL], optional: true}` | két érték cseréje, vagy megtartás |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | rögzített értéksor szétosztása |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | értékek vásárlása keretből (a `default: random` véletlen módban véletlenszerűen költi el) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | a lista a felszerelésbe kerül; a leképezés mezőket állít (a listák összeadódnak) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | hozzáad a karakter (vagy egy vázlatbeli entitás) egy mezőjéhez: a számok összeadódnak, minden más listához csatlakozik; ha nincs mit hozzáadni, az sem baj |
| `remove: {field: talents, value: "@old"}` | kivesz valamit egy listamezőből (egy lecserélt tehetséget, egy lezárt köteléket); ha nincs ott, az sem baj |
| `roll_tables: [physique, vice]` | táblázatokra dob a `traits` mezőbe; a bejegyzés `data.gear` értéke a felszerelésbe kerül, a `data.add: {gold: 20}` pedig mezőkhöz ad hozzá |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | a név; a `name: {prompt: …}`, ha nincs miből dobni, vár egyre, még véletlen módban is |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | kérdés, amelyre bármilyen válasz megfelel (egy cél, egy másik bejegyzés neve): a vázlat vár rá, még véletlen módban is, hacsak nincs előre kitöltve; a `field:` eltárolja a választ |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawl: naplózott kockaejtés, utak (mindig összefüggők), távolságok, rejtett utak (lásd lent) |

A map lépés a könyvek kockaejtős eljárásaihoz többet is elfogad:

| Kulcs | Mit csinál |
|---|---|
| `regions: terrain` | ezek az entitások is leesnek; minden helyszín a legközelebbihez csatlakozik (az a `region` értéke) |
| `hidden: 6`, `conditional: 5` | utanként egy d6: ha eléri vagy meghaladja a számot, rejtett vagy feltételes út (a rejtett utak nem kerülnek a játékosok térképére) |
| `describe: [path-feature, path-condition]` | minden útra dobott táblázatok, a `details` értékeként megőrizve |
| `entrance: true`, `exit: true` | a széléhez legközelebbi helyszín a bejárat; a többi innen számozódik az utak mentén (`map.n`), az utak tőle elvezetnek, a kijárat pedig egy távoli, szélhez közeli helyszín, utolsóként számozva |
| `number: "{@dungeon_name}, room {@n}"` | átnevezi a számozott helyszíneket (a vázlatkulcsaik követik: `room-1` az 1-es terem) |

Egy kockaejtős táblázat a bejegyzései adataiban megnevezheti a következő táblázatokat, így az eljárás úgy olvasható, mint a könyv: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, aztán `table: "{@drop.what}"`. A beállítatlan listamezők (conditions, lists, tags) üres listaként olvasódnak, így a `'deprived' in @who.conditions` kezdettől működik.

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

Az `advances:` kulcsot tartalmazó chargen nem új bejegyzést készít, hanem egy meglévőt módosít: ez a rendszer szintlépése.

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

- **Egyetlen bejegyzés:** a `creates: npc` megadású generátor úgy építi fel azt a bejegyzést, ahogy a karakteralkotás a karaktert (`apply`, `add`, `name`, `field:`); az `entity` lépései mellé további bejegyzéseket adnak, és egy `to: character` hivatkozás rá mutat.
- **Futtatás:** a `gen run` és a `char new` vázlatot készít (`#g7`, `#c3`), és semmit sem ír be. Egy `stop:` vázlat nélkül fejezi be: egy kampányopciót olvasó `if:` alatt a tippje az opciókra mutat (`didact session zero`); különben a saját szavai mondják meg, mit tegyél helyette.
- **Döntés:** a `--prefill '{…}'` előre eldönt dolgokat, azon a néven, amelyet egy lépés köt (`as:`): egyetlen érték minden előfordulásra válaszol, egy lista előfordulásonként egyet (`count` melletti `choose` esetén a lista a teljes választás). A `let` értékek is előre kitölthetők (`{"hp": 6}`), egy név, egy `ask` vagy egy `let` pedig bármilyen szöveget úgy őriz meg, ahogy megadtad. Az ismert lehetőségek közötti választásra (egy `choose`, egy táblázat bejegyzése) adott érték az a lehetőség, amelyet megnevez, ahogy írva van vagy más kis- és nagybetűkkel, a bejegyzése `id` értékével, vagy egy rá eső dobással (`{"group": 3}`), és magával hozza annak a bejegyzésnek az adatait; az olyan értéket, amely közel áll egy lehetőséghez, de egyikkel sem egyezik, elutasítja, és megnevezi a legközelebbit, minden más érték pedig saját válasz, adatok nélkül. Az `--auto` (vagy a `char new --mode random`) a többit a kockákra bízza. Egyébként a vázlat minden választásnál vár.
- **Leírás:** egy választás megmondja a választó játékosnak, mit jelentenek az egyes lehetőségek: egy táblázatbejegyzés `note:` kulcsa vagy a táblázata `about:` kulcsa, különben az általa megnevezett kompendium-bejegyzés (az adatai `id` értéke), vagy az, amelyik maga a lehetőség (a kompendium-azonosítók közötti választás mindegyik nevét mutatja): annak `tagline` és `summary` mezője, `description` vagy `effect` mezője, különben a szövege első bekezdése.
- **Visszalépés:** a `char back` (vagy a `gen back`) visszavonja az utolsó választ, dobást vagy szerkesztést, így a vázlat újra felteszi azt a kérdést; a lépés dobásai visszavontként lesznek megjelölve.
- **Folytatás:** a folytatott vázlat újrajátssza a nyomvonalát: minden dobott vagy választott értéket, mindegyiket egyszer és sorrendben (a térkép kockaejtését is), így semmi sem dobódik kétszer, és semmi már eldöntött nem változik.
- **Beírás:** a `commit` beírja a bejegyzéseket, a lapjukhoz ellenőrizve.
- **Fejlesztés:** egy `advances:` vázlat a bejegyzés másolatából indul (a lapja alapértékeivel), a lépései `@who` néven olvassák a bejegyzést, a vázlat értékeit pedig `@character.*` néven, és a `commit` csak azt írja be, ami változott, a `set`-hez hasonlóan ellenőrizve; az `entity` lépései által készített bejegyzések (egy új kötelék szála) mellette jönnek létre: egy `to: character` hivatkozás a bejegyzésre mutat, egy kulcsot megnevező mező pedig a kulcshoz tartozó bejegyzés azonosítóját tartalmazza, ahogy karakteralkotáskor is (`apply: {blood: "@pool"}`). Egy `stop:` megmondja, miért nem lehet még (nincs elég XP), és nem készül vázlat. Ha egy rendszerben a fejlődés egyetlen szabály, a karakteralkotása inkább azt nevezi meg: `advance: {rule: grow}`.
- **Módok:** a `modes: [guided]` mellett az eljárás lépésről lépésre halad: a `--mode random` kapcsolót elutasítja.

## Kompendium, kézikönyv és szószedet

- **A kompendium-bejegyzések** úgy íródnak, mint a `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. A `"roll 2d8"` érték akkor dob, amikor a bejegyzés létrejön. Futtasd a `didact spawn troll` parancsot, vagy hozd be egy csomag bejegyzéseit a világba a `didact compendium import <pack>` paranccsal (`--type loc`, és `--tag coast` azokhoz, amelyeken minden megadott címke rajta van).
- **Több rendszerhez:** egy legfelső szintű kulcs oda kerül, ahová a `set` teszi: a rendszer blokkjába, ha a lapján van ilyen mező, különben a `fields` alá. Egy bejegyzés, amelyet egy háttérvilág több rendszerhez ír, mindegyik rendszer számait a saját blokkjában adja meg (`mechanics: {my-system: {hp: 12}}`): a `pack validate` mindegyiket ellenőrzi a rendszere lapja alapján, ha az telepítve van, és jelzi azt a legfelső szintű kulcsot, amely ezen a lapon és a core lapján is megvan. Amit egy blokk mond, az érvényes: a `mechanics: {my-system: {role: tactician}}` mellett egy legfelső szintű `role: innkeeper` a core mezője, ahogy minden, ami a `fields:` alatt van. Az ellenőrzés alatt álló csomagot megnevező blokkot ehhez a csomaghoz méri, úgy, ahogy a mappájában van.
- **A kézikönyv szakaszai** a `reference/*.md` fájlokba kerülnek, front matterrel (`id`, `title`, `tags`, `page`, `mechanics: [save]`). A `didact rules lookup <topic>` megtalálja őket; egy idézőjeles kifejezést, amely nem fordul elő, szavanként is megpróbál.
- **A szószedet** a `glossary.yaml`: `term: definition`, vagy `{term, definition, aliases, see}` elemek listája. A `didact define <term>` olvassa.

## Tesztek: `tests/`

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

## Csomagok megosztása és eltávolítása

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- A `redistributable: false` értéket megadó csomag nem exportálható.
- A **core** a Didact része, és mindig be van kapcsolva: minden rendszer rá épül, ezért nem kapcsolható ki és nem távolítható el.
- A Didacttal együtt érkező többi csomag `.didactpack` fájl a `packs/` mappájában. A `pack list` a telepítésükig mutatja őket, és egy telepítése a szükséges, szintén vele érkező csomagokat is hozza.
- A `pack update` újabb változatokat keres a Didact `packs/` mappájában és a GitHubon (`vess-dev/Didact`; a `DIDACT_PACK_UPDATES` más helyet nevez meg, vagy üresen hagyva semmit sem keres). Az új változat a régi mellé települ: a kampányok a sajátjukat tartják meg a `didact campaign upgrade`-ig.
- Egyszerre egy játékrendszer van használatban: a megnyitott világé. Egy világ megtartja azt a rendszert, amellyel létrehozták (`didact world new <id> --system <pack>`; a rendszer nélkül létrehozott világ az elsőt kapja meg, amelyet adnak neki, a `pack enable` vagy a `world set system=` paranccsal), a kampányai azzal játszanak, és olyan csomag, amely másik rendszert igényel (egy hozzá írt háttérvilág), nem adható hozzá: másik rendszer saját világban játszható.
- Az `uninstall` megtagadja a műveletet, amíg egy világ vagy kampány a csomag egyetlen példányát használja (a `--force` ennek ellenére eltávolítja). Nem vonható vissza: telepítsd újra a .didactpack fájlt.

## Szabálykönyvből csomag: az ellenőrzőlista

Ebben a sorrendben haladj végig a könyv mechanikáin. Mindegyik a fentiek valamelyikére képeződik le:

1. **Feloldás:** hogyan sikerül egy dobás (egy próba: `success`, `bands`, `auto`).
2. **Kockák:** szokatlan kockák, szimbólumok, lépcsők (`dice.yaml`, elnevezett kockák, láncok).
3. **A lap:** tulajdonságok, származtatott számok (`schemas/`, derived mezők).
4. **Erőforrások:** HP, szerencse, lendület (resource és counter mezők; `set` lépések).
5. **Állapotok:** állapotok és hatásaik (`conditions` mezők; `if` lépések).
6. **Harc:** támadások, sebzés, kezdeményezés (akciók; `bag`/`deck` a sorrendhez).
7. **Eljárások:** felfedezés, utazás, pihenőidő (eljárások kérdésekkel).
8. **Táblázatok:** minden véletlentáblázat (`tables/`; `pack import` a Markdown-táblázatokhoz).
9. **A bestiárium:** szörnyek és NJK-k (`compendium/`).
10. **Tárgyak:** felszerelés, varázslatok, ereklyék (`compendium/`, slots mezők).
11. **KM-útmutatás:** elvek és tanácsok (`GUIDE.md`, `reference/`, `guidance:` a típusokon).
12. **Karakteralkotás:** hogyan készül egy karakter (egy `chargen/` eljárás, vagy `roll:` minden mezőn).

Mindenhol hivatkozz az oldalakra a `source:` kulccsal, hogy kiderüljenek a hiányok. Adj hozzá egy próbajáték-tesztet, amely karaktert készít, próbát dob, harcol és lefuttat egy eljárást.
