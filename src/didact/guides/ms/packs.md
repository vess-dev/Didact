<!-- translated from b1dfa1159ff4 -->
# Pek

Pek ialah sistem permainan, peramal, latar, pengembaraan atau bahan tambahan, yang ditulis sebagai fail YAML serta pemalam Python pilihan. Panduan ini menunjukkan cara menulisnya: menukar buku peraturan menjadi pek, atau menambah kandungan sendiri.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Pek juga boleh dibuat daripada apa yang ada dalam pustaka anda. `didact pack new my-brew --from-overlay my-system` menukar homebrew anda untuk sesuatu sistem (`compendium add`, rekod yang disimpan dengan `--scope system`, lore) menjadi bahan tambahan, dan `didact world export --as setting` menukar dunia menjadi pek latar: orang, tempat dan lorenya sebagai entri kompendium dan lore pek, dibawa ke dunia lain dengan `compendium import`. Kedua-duanya meninggalkan rahsia dan nota GM melainkan `--secrets`, dan tiada satu pun ditanda boleh dikongsi sehingga anda menetapkan lesennya.

## Susun atur

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

Satu fail mengandungi satu item, senarai item, atau beberapa item yang dipisahkan dengan `---`. Setiap item menamakan ID-nya dengan kunci jenisnya: `table: weather`, `check: save`, `type: pc`, atau `id: troll` untuk entri kompendium. Rujuk item sebagai `pack.id` (`my-system.save`), atau dengan ID sahaja apabila hanya satu pek yang didayakan memilikinya.

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

Sebuah hack menamakan asasnya dalam `extends` dan hanya mengandungi apa yang berbeza:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Itemnya dengan ID yang sama menggantikan item asas, apa jua jenisnya (jadual, peraturan, entri kompendium, bahagian rujukan, istilah glosari). `settings`-nya dilapiskan di atas tetapan asas, kunci demi kunci: kunci yang ditetapkannya menggantikan keseluruhan nilai asas (jadual `names`-nya mengambil tempat jadual nama asas), dan peraturan asas turut membaca nilai hack itu. `hides` menggugurkan selebihnya yang tidak diperlukan oleh hack: `*` sepadan dengan sebarang rentetan aksara, corak terakhir yang sepadan dengan sesuatu ID yang menentukan, dan corak yang bermula dengan `!` mengekalkan item itu. Apa yang digantikan oleh hack tidak pernah disembunyikan. Jenisnya ialah `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` dan `term`. `didact pack validate` memberi amaran tentang corak yang tidak sepadan dengan apa-apa.

## Ungkapan

Setiap syarat dan formula menggunakan bahasa dadu (`didact guide dice`), serta:
- **Nilai:** `@name` membaca nilai: `@roll`, `@who.STR`, `@settings.x`. `$name` menampal teks parameter terlebih dahulu, jadi `@who.$attr` menjadi `@who.STR`. Baca parameter teks bebas sebagai `@name`, bukan dalam petikan (`'$name'`): apostrofi dalam teksnya akan menutup petikan (`pack validate` memberi amaran).
- **Logik:** `and`, `or`, `not`, dan `in` (`'deprived' in @who.conditions`).
- **Literal:** teks (`'travel'`) dan `true`/`false`.
- **Fungsi:** `if(cond, a, b)` hanya membaling cabang yang diambilnya. `default(@thread.flashpoint, 0)` ialah nilainya, atau nilai sandaran apabila ia belum ditetapkan. `sum`, `count` (`count(@roll.dice, 6)` mengira angka enam), `min`, `max`, `any` dan `all` menerima senarai.

## Helaian: `schemas/`

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

| Jenis | Menyimpan | Pilihan |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | nilai biasa | min, max; `values` untuk enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` ialah nilainya, `@hp.max` hadnya | range; min; max atau max_field; die |
| `counter` | satu nombor | min, max, thresholds, occupies (medan slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | barang (`Rope` atau `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | seperti namanya | `to` (untuk refs), `allowed` |
| `derived` | dikira, tidak pernah disimpan | expr |

Setiap medan juga menerima `label`, `help`, `default`, `required` dan `roll`: `new pc Hero --fill`, atau nilai `"roll"`, membalingnya melalui log. Jenis daripada pek `core` menyimpan prosa yang tidak terikat pada sistem dalam `fields`. Jenis milik sesuatu sistem menyimpan nombornya dalam `mechanics.<system>`. `set hero hp-=2` mencari medan itu, mengapitnya, dan melaporkan sebarang lebihan. `+=` menambah kepada senarai: dalam `list` (seperti `slots`), nilai yang ditambah semula disimpan sekali lagi, `tags`, `conditions` dan `refs` menyimpannya sekali sahaja, dan `-=` membuang setiap salinannya.

**Hook** menentukan apa yang berlaku apabila sesuatu nilai melepasi garisan. Ia dicetuskan pada setiap perubahan (`set`, `inv`, langkah `set` dalam peraturan), tetapi hanya apabila garisan itu dilepasi: 3 → 0 mencetuskannya, 0 → 0 tidak. Suntingan `--force` melangkaunya.

| Hook | Dicetuskan apabila |
|---|---|
| `on_zero` | nombor atau `{value}` mencapai 0 |
| `on_full` (`when_full` pada slots) | ia mencapai max, size atau capacity-nya |
| `thresholds: {10: …, 20: …}` (counter) | ia naik melepasi setiap tanda |

Sesuatu tindakan ialah teks (nota untuk LLM), `{set: {hp: 0}}` atau `{condition: paralyzed}` pada rekod yang sama, `{trigger: death}` (menjalankan peraturan itu dengan `who` = rekod tersebut), atau senarai daripadanya.

**Inventori** (`didact inv …`) berfungsi pada medan `slots` helaian:
- **Ruang:** barang mengambil `size` × `count`-nya, dan counter yang `occupies` medan itu mengambil nilainya. Melebihi `capacity` ditolak melainkan dengan `--force`.
- **Kumpulan:** `groups: {backpack: 6, body: 4}` memberi setiap kumpulan ruangnya sendiri, serta lajur dan jumlahnya sendiri: `@inventory.body.armor` hanyalah apa yang dipakai atau dipegang, `@inventory.body.free` baki ruangnya.
- **Penggunaan:** `uses: 3` berkurang dengan `inv use`. `uses: d8` ialah dadu penggunaan: 1–2 menurunkannya satu tingkat. Barang yang habis digunakan hilang melainkan ia mempunyai `recharge` atau `keep: true`. Daripada beberapa barang yang sama nama, nama itu bermaksud yang pertama; untuk menghabiskan satu penggunaan (`inv use`, `use:` sesuatu peraturan, `set …uses-=1`), yang pertama yang masih ada baki penggunaan.
- **Kunci milik barang:** `didact set freya inventory.sword.damage=d10` (begitu juga `set: who.inventory.$item.damage` dalam peraturan) mengubah salah satunya, dengan barang dinamakan seperti yang dilakukan oleh `inv`, dengan sebahagian namanya atau keseluruhannya, termasuk ruang dan titik (`'inventory.12.7mm pistol.damage=d10'`, berpetik untuk shell); `uses` dan `charges` dikira seperti medan `uses` (`charges+=2` berhenti pada maksimumnya), dan ruang disemak seperti yang dilakukan oleh `inv add`. Peraturan membaca kunci sedemikian sebagai `@{who.inventory.$item.damage}` (dadu penggunaan sebagai dadunya, penggunaan sebagai bilangannya); barang atau kunci yang tiada dibaca sebagai tiada, jadi `default(…)` memberikan nilai gantinya.
- **Kompendium:** entri berjenis `item` (atau weapon, armor, relic, …, atau jenis milik pek sendiri yang meluaskan salah satunya dengan `extends`) meminjamkan butirannya kepada `inv add`, ditemui mengikut ID, nama atau alias (jika dua berkongsi satu: namakan yang dimaksudkan sebagai `pack.id`); sebarang nama lain, termasuk `:`, ialah nama barang itu sendiri.

## Jadual: `tables/`

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

Bentuk lain:
- **Senarai berpemberat:** `entries` sebagai senarai, dengan `weight:` bagi setiap entri.
- **Lajur:** `columns: [a, b]` membaling setiap lajur sesuatu baris secara berasingan. Entri biasa (bukan senarai) mengisi setiap lajur, jadi `columns: [first, second]` pada senarai perkataan bermaksud "baling dua kali pada senarai ini". `labels: false` meninggalkan nama lajur daripada hasilnya ("Abandon · Advantage"). `read: "It's a {first} {second} with {third} {fourth} inside."` membaca lajur-lajurnya sebagai satu ayat.
- **Jadual rujukan:** `lookup: hp_lost`, atau `[odds, chaos]` untuk carta 2-D.
- **Pendua:** `duplicates: reroll | keep | make_it_worse` untuk "baling dua kali".
- **Dua peringkat:** entri yang membaling jadual lain (`{table: lightning}` sebagai ganti teks, atau `then:` selepasnya) membawa bersama data balingan itu: peraturan atau draf yang balingannya jatuh pada entri itu membaca kedua-duanya, kunci entri itu sendiri dahulu, kemudian kunci jadual pertama yang dibaling selepas itu. `--prefill` boleh menamakan entri yang lebih ke bawah, pada sebarang kedalaman (`Ring of the Hunt`), dengan data setiap entri di sepanjang jalan: daripada dua yang sama nama, yang lebih dekat dimaksudkan (kemudian yang pertama), entri yang diteruskan membaling seterusnya dari situ, dan nama yang hampir dengan salah satunya tetapi bukan mana-mana ditolak, dengan yang terdekat dinamakan. Draf berpandu menawarkan langkah pertama apabila entrinya menyatakan apa ia (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): memilih satu membaling jadual seterusnya, seperti balingan yang jatuh padanya.
- **Dibaca dua hala:** `both_ways: true` pada jadual d66 menambah bacaan sebaliknya: 31 juga memberi 13, dan pembaca yang memilih.
- **Maksud sesuatu entri:** `about: "Knows: {skills}. Also known as: {aka}."` diisi dengan data setiap entri (senarai dibaca `a, b`; `{text}` ialah entri itu sendiri) untuk menyatakan apa yang diberikannya apabila sesuatu pilihan menawarkannya; `note:` entri itu sendiri menyatakannya sebagai ganti. Tanpa kedua-duanya, entri yang datanya mempunyai `id` yang menamakan entri kompendium diterangkan oleh entri kompendium itu.
- **Dek dan beg:** `deck: tarot` dengan `cards` (atau `standard: true`); `bag: initiative` dengan `tokens`.

Pengesahan menyemak bahawa setiap hasil yang boleh dibaling oleh dadu jatuh pada satu entri.

## Peraturan: `rules/`

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

Tindakan dan prosedur ialah senarai langkah, dan pencetus ialah langkah dengan pengawal `when:`. Langkah-langkahnya:

| Langkah | Fungsi |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | balingan yang dilog; mengikat `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` diisi dahulu, seperti dalam mana-mana teks, jadi dadu yang dipegang oleh sesuatu nilai sebagai teks dibaling (`{@{who.inventory.$item.damage}}`), dan log menunjukkannya: nilai yang bukan dadu ditolak, begitu juga `roll: "@die"` dengan teks sedemikian, yang tidak membaling apa-apa; set balingan (`{d8, d6}kh1`) kekal set |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | mengira nilai; seperti `value` bagi `set`, teks `{…}` ialah templat dan perkataan tanpa tanda ialah teks; dalam mana-mana teks yang diisi, `{{` dan `}}` menulis kurungan kerinting itu sendiri |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (atau `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | mengubah rekod: disahkan, diapit, boleh dibuat asal; `set: who.$attr` menetapkan medan yang dinamakan oleh sesuatu parameter, dan `set: who.inventory.$item.damage` menetapkan kunci sesuatu barang yang dibawanya (lihat Inventori); `-=` mengeluarkan nilai daripada senarai, dan nilai yang tiada di dalamnya tidak mengubah apa-apa (nota menyatakannya; nilai yang tidak mungkin ada di dalamnya ditolak); `unset:` membuang medan, seperti `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | memberikan barang kepada rekod atau mengambil barang daripadanya, seperti yang dilakukan oleh `inv add` dan `inv drop`: butirannya diambil daripada kompendium, bahagian unik namanya sudah memadai, dan ruang serta hook medan itu disemak |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | menggunakan barang yang dibawa seperti `inv use`: penggunaan atau cas berkurang, dadu penggunaan dibaling dan turun satu tingkat pada 1–2, dan yang habis hilang melainkan ia dicas semula atau disimpan; daripada beberapa yang sama nama, yang pertama yang masih ada baki penggunaan; mengikat `@torch.out` (penggunaan terakhirnya sudah habis), `@torch.gone` (tiada apa-apa lagi yang tinggal), `@torch.left`, `@torch.die` dan `@torch.rolled` (`as:` lalainya `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | mencipta rekod serta-merta, diterangkan seperti `entity` dalam draf (di bawah) dan disemak berdasarkan helaiannya; `as:` (jika tiada, `key`nya, jika tiada juga, jenisnya) mengikatnya sebagai rekod, yang dibaca dan ditetapkan seperti parameter `ref` (`pool: "@bleeding"`, `@bleeding.name`), dan tidak pernah menjadi nama parameter; tanpa `key:` tiada medan diambil sebagai kunci (`kind: track` kekal seperti yang ditulis); jika rekod dengan jenis dan nama itu sudah ada di sini, rekod itu diambil seadanya, jadi peraturan yang dijalankan semula tidak mencipta apa-apa yang baharu |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | menjalankan semakan dan mengikat hasilnya |
| `do: other-action`, `with: {…}`, `as: trip` | menjalankan peraturan lain; `@trip` ialah hasilnya dan `@trip.<name>` apa yang diikatnya (`@trip.found` untuk `let: {found: 2}`nya, `@trip.luck` untuk `roll: d6`, `as: luck`nya); `as:` lalainya ID peraturan itu |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | balingan jadual yang dilog; mengikat teks dan `data` entrinya (`@scar.<key>`, dan kunci sesuatu pemetaan mengikut laluannya: `@scar.cost.hp`), berserta data mana-mana jadual yang dibaling selepas itu; senarai barang (`[Rope, {name: Laser, damage: d8}]`) dibaca sebagai nama-namanya (`count(@scar.gear)`, `'Laser' in @scar.gear`), dan apabila diberikan kepada langkah seadanya (`apply: "@scar.gear"`) ia ialah barang-barang itu sendiri; senarai pemetaan lain hanya dibaca oleh langkah |
| `table: "setting-{@drop.difficulty}-terrain"` | jadual yang dikira: `{…}` dan `$param` diisi |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | beberapa hasil sebagai senarai (`distinct` membaling semula yang berulang) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | cabang |
| `repeat: "@count"`, `as: i`, `steps: […]` | gelung: langkah-langkahnya diulang sebanyak bilangan itu, dengan `@i` mengira dari 1 |
| `for: pcs` (atau `party`), `as: member`, `steps: […]` | langkah-langkahnya dijalankan sekali bagi setiap watak pemain (atau ahli kumpulan), sebagai `@member`: satu rekod, seperti yang diikat oleh `entity:` (`@member.name`, `set: member.fatigue`); `as:` tidak pernah mengambil nama parameter, jadi `who` milik peraturan itu sendiri kekal tidak terusik |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | output untuk LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (atau `every: 1 day`) | peringatan yang tiba masanya apabila masa permainan berlalu, seperti yang ditetapkan oleh `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | membaling semula sebahagian dadu sesuatu balingan (mekanik push) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | membaling pada nilai senarai (senarai peramal): mengikat entrinya, `@who.choose` (baris kosong) dan `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | membaling kumpulan dadu yang menyusut milik penjejak seperti `track roll` (dadu yang menunjukkan 1-3 dibuang; dadu `drop` dibuang dahulu, dadu `extra` turut dibaling) atau hanya membuang dadu (`mode: drop`: push, tick); fasa yang dipautkan dan peristiwa kumpulan dadu itu menyusul; mengikat `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Hasil sesuatu semakan boleh dibaca oleh peraturan yang menjalankannya (`check: … as: answer` memberi `@answer`), begitu juga penandanya: `'random-event' in @answer.flags`. Nilai `with:` dinilai apabila ia mengandungi `@`, diisi apabila ia mengandungi `$param` atau `{…}` ("Does $npc flee?"), dan dihantar seperti yang ditulis dalam kes lain. Peraturan dengan parameter `oracle` mendapat rekod keadaan peramal kempen tanpa perlu diberitahu. Parameter `ref` dengan `to: monster` mengambil rekod jenis itu: nama yang turut dimiliki rekod lain (pool seorang musuh, dinamakan seperti kadnya) bermaksud rekod jenis itu.

Pencetus berjalan dengan sendirinya apabila event-nya berlaku, dan hanya jika `when:`-nya dipenuhi:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Mana-mana peraturan (termasuk penjana dan penciptaan watak) boleh membaca `@system` (ID sistem yang dimainkan oleh dunia, supaya latar yang ditulis untuk dua sistem dapat membezakan keduanya), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` dan `@time.is_night`, dan, jika kalendernya mempunyai bulan, `@time.month`, `@time.month_name`, `@time.day_of_month` dan `@time.year`; semasa pertarungan berlangsung, `@combat.round` dan `@combat.fighters` (ID mereka yang terlibat). Pencetus masa juga boleh membaca `@time.passed`, iaitu saat yang baru dimajukan, pencetus `combat_start` atau `combat_end` membaca pertarungan yang bermula atau tamat (`combat start` dan `combat end` menjalankannya; pejuang yang keluar tidak menamatkan pertarungan), dan peraturan yang dijalankan oleh pencetus membaca apa yang dibaca oleh pencetus itu. Pencetus dengan parameter wajib hanya dijalankan oleh `didact do` atau hook medan (`who` = rekod tersebut). Pencetus `on: manual` hanya berjalan apabila dipanggil. `for: pcs` (atau `party`) menjalankan pencetus sekali bagi setiap watak pemain (atau ahli kumpulan), sebagai `who`: contohnya untuk pengalaman selepas setiap sesi. Pencetus yang gagal menghentikan arahan yang mencetuskannya, dan menyatakan pencetus mana itu dan cara meneruskan tanpanya (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalendar terletak dalam `settings` sesuatu pek: kalendar pek latar mengatasi kalendar sistem, dan kalendar dunia sendiri (`calendar:` dalam `world.yaml`nya) mengatasi kedua-duanya:

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

`leap: 4` menjadikan sesuatu bulan sehari lebih panjang setiap tahun ke-4, dan `leap: [4, 100, 400]` setiap tahun ke-4, tetapi tidak setiap tahun ke-100, namun tetap setiap tahun ke-400: setiap nombor mengatasi nombor sebelumnya. `weekday` menamakan hari dalam minggu bagi permulaan (jika tidak, hari pertama minggu itu), dan `year` ialah cara sesuatu tarikh menulis tahunnya, dalam tarikh yang ditunjukkan Didact dan juga yang dibacanya (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` menyemak ketiga-tiganya. Kempen boleh bermula pada tarikh lain kalendar, sebelum permulaannya atau selepasnya: `didact campaign new <id> --date '4 July 1902'`, atau `didact time set '<date>'` sehingga sesi pertamanya. Hari dalam minggu yang ditulis sebelum tarikh disemak: tarikh yang menentukan, dan nota menyatakannya apabila ia jatuh pada hari lain.

Pilihan ialah varian dan peraturan pilihan sistem, yang dipilih setiap kempen pada sesi sifar:

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

`didact campaign profile lethality=deadly supplies=on` menyimpannya (atau halaman Tetapan aplikasi web). Peraturan, penciptaan watak dan penjana membacanya (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): jawapan mengatasi apa yang ditetapkan pilihan lain, dan itu mengatasi nilai lalai. Apa yang disiratkan oleh sesuatu pilihan diikuti hingga ke hujungnya (suasana yang menetapkan tahap maut turut menetapkan apa yang disiratkan oleh tahap maut itu), dan antara dua implikasi, yang lebih dekat menang. Ringkasan menyenaraikan pilihan yang berbeza daripada nilai lalainya berserta maknanya, supaya GM melaksanakan apa yang tidak dapat dilakukan peraturan. Penjana yang tidak dapat berjalan dengan pilihan itu berhenti melalui `stop:` berserta sebabnya, dan tiada draf dibuat.

## Peramal: `oracles/`

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

- **Bertanya:** `didact ask '…' --odds likely` menjalankan semakan `ask`. Jawapannya ialah hasil semakan itu (satu jalur), dan penandanya turut dibawa.
- **Keadaan:** ia disimpan dalam rekod yang diterima semakan sebagai `oracle`. Semakan mengubahnya dengan `set: oracle.chaos += 1`.
- **Senarai:** `lists: {names: […], method: sections, most: 3}` menyimpan senarai berpemberat pada rekod itu. `didact lists add|drop|roll|show` menguruskannya, dan peraturan membalingnya dengan `pick`. `sections` membaling untuk satu bahagian lima baris, kemudian satu baris di dalamnya (baris kosong bermaksud pilih sendiri); `uniform` memberi setiap baris peluang yang sama.
- **Tambahan untuk semakan:** `didact ask '…' --with as_rule=true` menghantar parameter tambahan kepada semakan peramal.
- **Log:** setiap jawapan dinomborkan (`#o12`) dan dilog, dan `didact interpret o12 '…'` menyimpan maksudnya. Peramal `yes-no` daripada pek core ialah sandarannya.

## Penjana dan penciptaan watak: `generators/`, `chargen/`

Kedua-duanya ialah prosedur yang membina **draf**. Kedua-duanya menggunakan setiap langkah peraturan (`roll`, `table`, `if`, `let`, `prompt`, …) serta langkah-langkah ini:

| Langkah | Fungsi |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | menambah rekod ke draf (kunci `poi-1`, `poi-2`, …); medan atau pautan yang menamakan kunci yang ditulis oleh pek (`key:`, atau nama `as:`) menjadi ID rekod itu apabila disahkan, jadi pilih kunci yang tidak dipegang oleh mana-mana medan sebagai teks (entiti tanpa kedua-duanya tiada kunci untuk ditukar); `from: "@relic.id"` memulakannya daripada entri kompendium (jenis, nama dan medannya) |
| `choose: {from: [a, b], as: x}` (atau `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | satu pilihan; dalam mod berpandu draf menunggu `choose`; `exclude` mengecualikan pilihan terdahulu (yang dibaling akan dibaling semula); `records:` menambah rekod jenis itu yang ada di sini, mengikut ID (yang dicipta semasa bermain); `answer:` membuat pilihan tanpa bertanya jika nilainya salah satu pilihan (laluan watak itu sendiri) |
| `choose_or_roll: {table: backgrounds, as: background}` | pilihan yang boleh dibuat oleh dadu; data entri yang dipilih ialah `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | membaling ke dalam watak |
| `swap: {among: [STR, DEX, WIL], optional: true}` | menukar dua skor, atau kekal |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | mengagihkan tatasusunan tetap |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | membeli skor dalam bajet (`default: random` membelanjakannya secara rawak dalam mod rawak) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | senarai masuk ke inventori; pemetaan menetapkan medan (senarai dijumlahkan) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | menambah kepada medan watak (atau entiti dalam draf): nombor dijumlahkan, selainnya disertakan ke dalam senarai; tiada apa untuk ditambah pun tidak mengapa |
| `remove: {field: talents, value: "@old"}` | membuang sesuatu daripada medan senarai (bakat yang ditukar, ikatan yang sudah selesai); tiada apa untuk dibuang pun tidak mengapa |
| `roll_tables: [physique, vice]` | membaling jadual ke dalam `traits`; `data.gear` sesuatu entri masuk ke inventori dan `data.add: {gold: 20}` menambah kepada medan |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | namanya; `name: {prompt: …}` tanpa sumber untuk dibaling akan menunggu nama, walaupun dalam mod rawak |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | soalan yang boleh dijawab apa sahaja (matlamat, nama rekod lain): draf menunggunya, walaupun dalam mod rawak, kecuali ia sudah diisi awal; `field:` menyimpan jawapannya |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawl: jatuhan dadu yang dilog, laluan (sentiasa bersambung), jarak, laluan tersembunyi (lihat di bawah) |

Langkah map menerima lebih banyak lagi, untuk prosedur jatuhan dadu daripada buku:

| Kunci | Fungsi |
|---|---|
| `regions: terrain` | entiti ini juga dijatuhkan; setiap tempat menyertai yang terdekat (`region`-nya) |
| `hidden: 6`, `conditional: 5` | satu d6 bagi setiap laluan: sama dengan atau melebihi nombor itu, laluan tersembunyi atau bersyarat (laluan tersembunyi tidak dipaparkan pada peta pemain) |
| `describe: [path-feature, path-condition]` | jadual yang dibaling untuk setiap laluan, disimpan sebagai `details`-nya |
| `entrance: true`, `exit: true` | tempat yang paling hampir dengan tepi ialah pintu masuk; selebihnya dinomborkan dari situ mengikut laluan (`map.n`), laluan menghala menjauhinya, dan pintu keluar ialah tempat yang jauh berhampiran tepi, bernombor terakhir |
| `number: "{@dungeon_name}, room {@n}"` | menamakan semula tempat yang bernombor (kunci draf mereka mengikut: `room-1` ialah bilik 1) |

Jadual jatuhan dadu boleh menamakan jadual seterusnya dalam data entrinya, supaya prosedur itu dibaca seperti dalam buku: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, kemudian `table: "{@drop.what}"`. Medan senarai yang belum ditetapkan (conditions, lists, tags) dibaca sebagai senarai kosong, jadi `'deprived' in @who.conditions` berfungsi dari awal.

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

Chargen dengan `advances:` mengubah rekod yang sedia ada dan bukannya mencipta rekod baharu: itulah prosedur naik tahap sistem.

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

- **Satu rekod:** penjana dengan `creates: npc` membina rekod itu seperti penciptaan watak membina watak (`apply`, `add`, `name`, `field:`); langkah `entity`-nya menambah rekod di sisinya, dan pautan `to: character` menunjuk kepadanya.
- **Menjalankan:** `gen run` dan `char new` membuat draf (`#g7`, `#c3`) dan tidak menulis apa-apa. `stop:` menamatkannya tanpa draf: di bawah `if:` yang membaca pilihan kempen, petunjuknya menghala ke pilihan (`didact session zero`); jika tidak, kata-katanya sendiri menyatakan apa yang perlu dibuat sebaliknya.
- **Menentukan:** `--prefill '{…}'` menentukan perkara lebih awal, mengikut nama yang diikat oleh sesuatu langkah (`as:`): satu nilai menjawab setiap kemunculan, senarai menjawab satu kemunculan bagi setiap item (senarai untuk `choose` dengan `count` ialah keseluruhan pilihan). Nilai `let` juga boleh diisi lebih awal (`{"hp": 6}`), dan nama, `ask` atau `let` menyimpan sebarang teks tepat seperti yang diberikan. Nilai untuk pemilihan daripada pilihan yang diketahui (`choose`, entri jadual) ialah pilihan yang dinamakannya, sama ada seperti yang ditulis atau dengan huruf besar/kecil yang berlainan, melalui `id` entrinya, atau melalui balingan yang jatuh padanya (`{"group": 3}`), dan ia membawa bersama data entri itu; nilai yang hampir dengan sesuatu pilihan tetapi bukan mana-mana daripadanya ditolak dengan menamakan pilihan yang terdekat, dan nilai lain ialah jawapan sendiri, tanpa data. `--auto` (atau `char new --mode random`) membiarkan dadu menentukan selebihnya. Jika tidak, draf menunggu pada setiap pilihan.
- **Menerangkan:** setiap pilihan yang ditawarkan menyatakan maksudnya, untuk pemain yang memilih: `note:` entri jadual atau `about:` jadualnya, jika tiada, entri kompendium yang dinamakannya (`id` dalam datanya), atau entri kompendium yang menjadi pilihan itu sendiri (pilihan antara ID kompendium menunjukkan nama setiap satu): `tagline` dan `summary`-nya, `description` atau `effect`-nya, jika tiada, perenggan pertama teksnya.
- **Kembali:** `char back` (atau `gen back`) menarik balik jawapan, balingan atau suntingan terakhir, jadi draf bertanya soalan itu sekali lagi; balingan yang dibuatnya ditanda sebagai dibuat asal.
- **Menyambung:** draf yang disambung memainkan semula jejaknya: setiap nilai yang dibaling atau dipilih, setiap satu digunakan sekali dan mengikut susunan (termasuk jatuhan dadu peta), jadi tiada yang dibaling dua kali dan tiada yang sudah ditentukan berubah.
- **Menulis:** `commit` menulis rekod, disemak berdasarkan helaiannya.
- **Memajukan:** draf `advances:` bermula daripada salinan rekod (dengan nilai lalai helaiannya), langkah-langkahnya membaca rekod itu sebagai `@who` dan nilai draf sebagai `@character.*`, dan `commit` hanya menulis apa yang berubah, disemak seperti `set`; rekod daripada langkah `entity`-nya (jalan cerita sesuatu ikatan baharu) dicipta di sisinya: pautan `to: character` menunjuk kepada rekod itu, dan medan yang menamakan sesuatu kunci menyimpan ID rekod bagi kunci itu, sama seperti semasa watak dicipta (`apply: {blood: "@pool"}`). `stop:` menyatakan sebab ia belum boleh (XP belum cukup), dan tiada draf dibuat. Sistem yang perkembangannya hanya satu peraturan sebaliknya menamakan peraturan itu dalam chargen-nya: `advance: {rule: grow}`.
- **Mod:** `modes: [guided]` mengekalkan prosedur langkah demi langkah: `--mode random` ditolak.

## Kompendium, rujukan dan glosari

- **Entri kompendium** ditulis seperti `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Nilai `"roll 2d8"` dibaling apabila entri itu dijelmakan. Jalankan `didact spawn troll`, atau bawa entri sesuatu pek ke dalam dunia dengan `didact compendium import <pack>` (`--type loc`, dan `--tag coast` untuk entri yang mempunyai setiap tag yang diberi).
- **Untuk beberapa sistem:** kunci di peringkat teratas pergi ke tempat `set` meletakkannya: ke blok sistem apabila helaiannya mempunyai medan itu, jika tidak ke `fields`. Entri yang ditulis oleh sesuatu latar untuk lebih daripada satu sistem memberikan nombor setiap sistem dalam bloknya sendiri (`mechanics: {my-system: {hp: 12}}`): `pack validate` menyemak setiap blok berbanding helaian sistemnya apabila sistem itu dipasang, dan mencatat kunci di peringkat teratas yang dimiliki oleh helaian itu dan juga helaian core. Apa yang dikatakan oleh blok kekal: di sebelah `mechanics: {my-system: {role: tactician}}`, `role: innkeeper` di peringkat teratas ialah medan core, seperti apa sahaja di bawah `fields:`. Blok yang menamakan pek yang sedang disahkan disemak berdasarkan pek itu seperti yang ada dalam foldernya.
- **Bahagian rujukan** diletakkan dalam `reference/*.md`, dengan front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` mencarinya; frasa berpetikan yang tiada di situ dicuba mengikut perkataannya.
- **Glosari** ialah `glossary.yaml`: `term: definition`, atau senarai `{term, definition, aliases, see}`. `didact define <term>` membacanya.

## Ujian: `tests/`

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

## Berkongsi dan membuang pek

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Pek yang mengisytiharkan `redistributable: false` tidak boleh dieksport.
- **core** ialah sebahagian daripada Didact dan sentiasa aktif: setiap sistem dibina di atasnya, jadi ia tidak boleh dinyahdayakan atau dinyahpasang.
- Pek lain yang disertakan bersama Didact ialah fail `.didactpack` dalam folder `packs/`-nya. `pack list` menunjukkannya sehingga dipasang, dan memasang salah satunya turut membawa pek yang diperlukannya yang juga disertakan.
- `pack update` mencari versi lebih baharu dalam folder `packs/` Didact dan di GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` menamakan tempat lain, atau kosong supaya tidak mencari). Versi baharu dipasang di sebelah versi lama: kempen mengekalkan versi masing-masing sehingga `didact campaign upgrade`.
- Hanya satu sistem permainan digunakan pada satu masa: sistem dunia yang terbuka. Dunia mengekalkan sistem yang digunakan semasa ia dicipta (`didact world new <id> --system <pack>`; dunia yang dicipta tanpa sistem mengambil sistem pertama yang diberikan kepadanya, melalui `pack enable` atau `world set system=`), kempennya memainkan sistem itu, dan pek yang memerlukan sistem lain (latar yang ditulis untuknya) tidak boleh ditambah: sistem lain dimainkan dalam dunianya sendiri.
- `uninstall` menolak selagi ada dunia atau kempen yang menggunakan satu-satunya salinan pek itu (`--force` tetap membuangnya). Ia tidak boleh dibuat asal: pasang semula .didactpack-nya.

## Daripada buku peraturan kepada pek: senarai semak

Teliti mekanik buku mengikut susunan ini. Setiap satu dipetakan kepada salah satu perkara di atas:

1. **Resolusi:** bagaimana balingan berjaya (semakan: `success`, `bands`, `auto`).
2. **Dadu:** dadu luar biasa, simbol, tingkat (`dice.yaml`, dadu bernama, rantai).
3. **Helaian:** atribut, nombor terbitan (`schemas/`, medan terbitan).
4. **Sumber:** HP, tuah, momentum (medan resource dan counter; langkah `set`).
5. **Keadaan:** status dan kesannya (medan `conditions`; langkah `if`).
6. **Pertarungan:** serangan, kerosakan, inisiatif (tindakan; `bag`/`deck` untuk susunan giliran).
7. **Prosedur:** penerokaan, perjalanan, masa rehat (prosedur dengan soalan panduan).
8. **Jadual:** setiap jadual rawak (`tables/`; `pack import` untuk jadual Markdown).
9. **Bestiari:** raksasa dan NPC (`compendium/`).
10. **Barang:** kelengkapan, jampi, relik (`compendium/`, medan slots).
11. **Panduan GM:** prinsip dan nasihat (`GUIDE.md`, `reference/`, `guidance:` pada jenis).
12. **Penciptaan watak:** cara mencipta watak (prosedur `chargen/`, atau `roll:` pada setiap medan).

Petik halaman dengan `source:` di mana-mana, supaya jurang kelihatan. Tambah ujian smoke-play yang mencipta watak, membaling semakan, bertarung dan menjalankan prosedur.
