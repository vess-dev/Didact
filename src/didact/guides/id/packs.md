<!-- translated from b1dfa1159ff4 -->
# Paket

Paket adalah sistem permainan, orakel, latar, petualangan, atau suplemen, yang ditulis sebagai berkas YAML plus plugin Python opsional. Panduan ini menunjukkan cara menulisnya: mengubah buku aturan menjadi paket, atau menambahkan konten buatan sendiri.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Paket juga bisa dibuat dari isi pustaka Anda. `didact pack new my-brew --from-overlay my-system` mengubah homebrew Anda untuk sebuah sistem (`compendium add`, entri yang disimpan dengan `--scope system`, lore) menjadi suplemen, dan `didact world export --as setting` mengubah dunia menjadi paket latar: orang, tempat, dan lorenya menjadi entri kompendium dan lore paket, yang dibawa ke dunia lain dengan `compendium import`. Keduanya tidak menyertakan rahasia dan catatan GM kecuali dengan `--secrets`, dan keduanya tidak ditandai dapat dibagikan sampai Anda mengatur lisensinya.

## Tata letak

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

Satu berkas berisi satu item, daftar item, atau beberapa item yang dipisahkan `---`. Setiap item menyebut ID-nya dengan kunci jenisnya: `table: weather`, `check: save`, `type: pc`, atau `id: troll` untuk entri kompendium. Rujuk item sebagai `pack.id` (`my-system.save`), atau dengan ID saja jika hanya satu paket aktif yang memilikinya.

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

Sebuah hack menyebut dasarnya di `extends` dan hanya berisi yang berbeda:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Item miliknya dengan ID yang sama menggantikan item dasar, apa pun jenisnya (tabel, aturan, entri kompendium, bagian rujukan, istilah glosarium). `settings` miliknya ditumpuk di atas milik dasar, kunci demi kunci: kunci yang ditetapkan hack menggantikan nilai dasar secara utuh (tabel `names`-nya menggantikan tabel nama dasar), dan aturan dasar juga membaca nilai milik hack. `hides` membuang sisanya yang tidak diperlukan hack: `*` cocok dengan deretan karakter apa pun, pola terakhir yang cocok dengan sebuah ID yang menentukan, dan pola yang diawali `!` mempertahankan item itu. Apa yang digantikan hack tidak pernah disembunyikan. Jenisnya adalah `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference`, dan `term`. `didact pack validate` memperingatkan pola yang tidak cocok dengan apa pun.

## Ekspresi

Setiap kondisi dan rumus memakai bahasa dadu (`didact guide dice`), ditambah:
- **Nilai:** `@name` membaca sebuah nilai: `@roll`, `@who.STR`, `@settings.x`. `$name` menempelkan teks sebuah parameter lebih dulu, jadi `@who.$attr` menjadi `@who.STR`. Baca parameter teks bebas sebagai `@name`, bukan dalam kutipan (`'$name'`): apostrof dalam teksnya akan menutup kutipan (`pack validate` memperingatkan).
- **Logika:** `and`, `or`, `not`, dan `in` (`'deprived' in @who.conditions`).
- **Literal:** teks (`'travel'`) dan `true`/`false`.
- **Fungsi:** `if(cond, a, b)` hanya melempar cabang yang diambilnya. `default(@thread.flashpoint, 0)` adalah nilainya, atau nilai cadangan jika belum ditetapkan. `sum`, `count` (`count(@roll.dice, 6)` menghitung angka enam), `min`, `max`, `any`, dan `all` menerima daftar.

## Lembar: `schemas/`

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

| Jenis | Berisi | Opsi |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | nilai biasa | min, max; `values` untuk enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` adalah nilainya, `@hp.max` batasnya | range; min; max atau max_field; die |
| `counter` | sebuah angka | min, max, thresholds, occupies (kolom slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | barang (`Rope` atau `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | sesuai namanya | `to` (untuk refs), `allowed` |
| `derived` | dihitung, tidak pernah disimpan | expr |

Setiap kolom juga menerima `label`, `help`, `default`, `required`, dan `roll`: `new pc Hero --fill`, atau nilai `"roll"`, melemparnya lewat log. Tipe dari paket `core` menyimpan prosa yang tidak terikat sistem di `fields`. Tipe milik sebuah sistem menyimpan angkanya di `mechanics.<system>`. `set hero hp-=2` menemukan kolomnya, membatasinya, dan melaporkan kelebihannya. `+=` menambahkan ke daftar: `list` (seperti `slots`) tetap menyimpan nilai yang ditambahkan lagi, `tags`, `conditions`, dan `refs` hanya menyimpannya sekali, dan `-=` membuang setiap salinannya.

**Hook** menentukan apa yang terjadi saat sebuah nilai melewati batas. Hook terpicu pada setiap perubahan (`set`, `inv`, langkah `set` dalam aturan), tetapi hanya saat batasnya dilewati: 3 → 0 memicu, 0 → 0 tidak. Suntingan dengan `--force` melewatinya.

| Hook | Terpicu saat |
|---|---|
| `on_zero` | angka atau `{value}` mencapai 0 |
| `on_full` (`when_full` pada slots) | mencapai max, size, atau capacity-nya |
| `thresholds: {10: …, 20: …}` (counter) | naik melewati setiap tanda |

Sebuah aksi berupa teks (catatan untuk LLM), `{set: {hp: 0}}` atau `{condition: paralyzed}` pada entri yang sama, `{trigger: death}` (menjalankan aturan itu dengan `who` = entri tersebut), atau daftar dari semua itu.

**Inventaris** (`didact inv …`) bekerja pada kolom `slots` di lembar:
- **Ruang:** barang memakan `size` × `count`-nya, dan counter yang `occupies` kolom itu memakan nilainya. Melewati `capacity` ditolak kecuali dengan `--force`.
- **Grup:** `groups: {backpack: 6, body: 4}` memberi setiap grup ruangnya sendiri, serta kolom dan totalnya sendiri: `@inventory.body.armor` hanyalah yang dikenakan atau dipegang, `@inventory.body.free` sisa ruangnya.
- **Pemakaian:** `uses: 3` berkurang dengan `inv use`. `uses: d8` adalah dadu pemakaian: 1–2 menurunkannya satu tingkat. Barang yang habis dipakai hilang kecuali punya `recharge` atau `keep: true`. Dari beberapa barang bernama sama, nama itu berarti yang pertama; untuk menghabiskan satu pemakaian (`inv use`, `use:` sebuah aturan, `set …uses-=1`), yang pertama yang masih punya sisa pemakaian.
- **Kunci milik barang:** `didact set freya inventory.sword.damage=d10` (begitu pula `set: who.inventory.$item.damage` dalam aturan) mengubah salah satunya, dengan barang disebut seperti cara `inv` menyebutnya, dengan sebagian namanya atau seluruhnya, spasi dan titik juga (`'inventory.12.7mm pistol.damage=d10'`, dikutip untuk shell); `uses` dan `charges` dihitung seperti kolom `uses` (`charges+=2` berhenti di maksimumnya), dan ruangnya diperiksa seperti `inv add` memeriksanya. Aturan membaca kunci seperti itu sebagai `@{who.inventory.$item.damage}` (dadu pemakaian sebagai dadunya, pemakaian sebagai jumlahnya); barang atau kunci yang tidak ada dibaca sebagai tidak ada, jadi `default(…)` memberi nilai cadangannya.
- **Kompendium:** entri bertipe `item` (atau weapon, armor, relic, …, atau tipe milik paket sendiri yang memperluas salah satunya dengan `extends`) meminjamkan detailnya ke `inv add`, ditemukan lewat ID, nama, atau alias (jika dua entri berbagi satu alias: sebut yang dimaksud sebagai `pack.id`); nama lain apa pun, termasuk `:`, adalah nama barang itu sendiri.

## Tabel: `tables/`

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
- **Daftar berbobot:** `entries` sebagai daftar, dengan `weight:` per entri.
- **Kolom:** `columns: [a, b]` melempar setiap kolom sebuah baris secara terpisah. Entri biasa (bukan daftar) mengisi setiap kolom, jadi `columns: [first, second]` pada daftar kata berarti "lempar dua kali pada daftar ini". `labels: false` menghilangkan nama kolom dari hasilnya ("Abandon · Advantage"). `read: "It's a {first} {second} with {third} {fourth} inside."` membaca kolom-kolomnya menjadi satu kalimat.
- **Tabel acuan:** `lookup: hp_lost`, atau `[odds, chaos]` untuk bagan 2-D.
- **Duplikat:** `duplicates: reroll | keep | make_it_worse` untuk "lempar dua kali".
- **Dua tahap:** entri yang melempar tabel lain (`{table: lightning}` sebagai gantinya, atau `then:` sesudahnya) ikut membawa data lemparan itu: aturan atau draf yang melemparnya membaca keduanya, kunci milik entri itu sendiri lebih dulu, lalu kunci milik tabel pertama yang dilempar sesudahnya. `--prefill` bisa menyebut entri yang lebih ke bawah, di kedalaman berapa pun (`Ring of the Hunt`), dengan data setiap entri di sepanjang jalan: dari dua yang bernama sama, yang dimaksud adalah yang lebih dekat (lalu yang pertama), entri yang berlanjut melempar terus dari sana, dan nama yang mirip dengan salah satunya tetapi bukan salah satunya ditolak, dengan menyebut yang terdekat. Draf terpandu menawarkan langkah pertama jika entrinya menyebut apa mereka (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): memilih salah satunya melempar tabel berikutnya, seperti lemparan yang jatuh padanya.
- **Dibaca dua arah:** `both_ways: true` pada tabel d66 menambahkan pembacaan sebaliknya: 31 juga memberi 13, dan pembaca yang memilih.
- **Arti sebuah entri:** `about: "Knows: {skills}. Also known as: {aka}."` diisi dengan data setiap entri (daftar dibaca `a, b`; `{text}` adalah entri itu sendiri) untuk menyebutkan apa yang diberikannya saat sebuah pilihan menawarkannya; `note:` milik entri itu sendiri menyebutkannya sebagai gantinya. Tanpa keduanya, entri yang datanya memiliki `id` yang menyebut sebuah entri kompendium dijelaskan oleh entri kompendium itu.
- **Dek dan kantong:** `deck: tarot` dengan `cards` (atau `standard: true`); `bag: initiative` dengan `tokens`.

Validasi memeriksa bahwa setiap hasil yang mungkin dari dadu jatuh pada sebuah entri.

## Aturan: `rules/`

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

Aksi dan prosedur adalah daftar langkah, dan pemicu adalah langkah dengan penjaga `when:`. Langkah-langkahnya:

| Langkah | Fungsi |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | lemparan yang dicatat; mengikat `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` diisi lebih dulu, seperti di teks mana pun, jadi dadu yang dipegang sebuah nilai sebagai teks dilempar (`{@{who.inventory.$item.damage}}`), dan catatan menampilkannya: nilai yang bukan dadu ditolak, begitu juga `roll: "@die"` dengan teks seperti itu, yang tidak melempar apa pun; himpunan lemparan (`{d8, d6}kh1`) tetap himpunan |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | menghitung nilai; seperti `value` pada `set`, teks `{…}` adalah templat dan kata tanpa tanda adalah teks; di teks apa pun yang diisi, `{{` dan `}}` menulis kurung kurawal itu sendiri |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (atau `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | mengubah entri: divalidasi, dibatasi, bisa diurungkan; `set: who.$attr` menetapkan kolom yang disebut oleh sebuah parameter, dan `set: who.inventory.$item.damage` kunci sebuah barang yang dibawanya (lihat Inventaris); `-=` mengambil sebuah nilai dari daftar, dan nilai yang tidak ada di dalamnya tidak mengubah apa pun (sebuah catatan menyebutkannya; nilai yang tidak mungkin pernah ada di dalamnya ditolak); `unset:` menghapus sebuah kolom, seperti `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | memberikan barang kepada sebuah entri atau mengambil barang darinya, seperti yang dilakukan `inv add` dan `inv drop`: detailnya diambil dari kompendium, bagian unik dari namanya sudah cukup, dan ruang serta hook kolomnya diperiksa |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | memakai barang yang dibawa seperti `inv use`: pemakaian atau muatan berkurang, dadu pemakaian dilempar dan turun satu tingkat pada 1–2, dan barang yang habis hilang kecuali terisi ulang atau disimpan; dari beberapa yang bernama sama, yang pertama yang masih punya sisa pemakaian; mengikat `@torch.out` (pemakaian terakhirnya sudah lewat), `@torch.gone` (tidak ada lagi yang tersisa), `@torch.left`, `@torch.die`, dan `@torch.rolled` (`as:` bawaannya `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | langsung membuat entri, yang dijelaskan seperti langkah `entity` pada draf (lihat di bawah) dan diperiksa terhadap lembarnya; `as:` (jika tidak ada, `key`-nya, jika tidak ada juga, tipenya) mengikatnya sebagai entri, yang dibaca dan ditetapkan seperti parameter `ref` (`pool: "@bleeding"`, `@bleeding.name`), dan tidak pernah berupa nama parameter; tanpa `key:` tidak ada kolom yang dianggap kunci (`kind: track` tetap seperti ditulis); entri bertipe dan bernama sama yang sudah ada di sini dipakai apa adanya, jadi aturan yang dijalankan lagi tidak membuat apa pun yang baru |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | menjalankan pemeriksaan dan mengikat hasilnya |
| `do: other-action`, `with: {…}`, `as: trip` | menjalankan aturan lain; `@trip` adalah hasilnya dan `@trip.<name>` apa yang diikatnya (`@trip.found` untuk `let: {found: 2}`-nya, `@trip.luck` untuk `roll: d6`, `as: luck`-nya); `as:` bawaannya ID aturan itu |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | lemparan tabel yang dicatat; mengikat teks dan `data` entrinya (`@scar.<key>`, dan kunci sebuah pemetaan lewat jalurnya: `@scar.cost.hp`), beserta data tabel mana pun yang dilempar berikutnya; daftar barang (`[Rope, {name: Laser, damage: d8}]`) dibaca sebagai nama-namanya (`count(@scar.gear)`, `'Laser' in @scar.gear`), dan bila diberikan ke sebuah langkah apa adanya (`apply: "@scar.gear"`) ia adalah barang-barang itu sendiri; daftar pemetaan lain hanya dibaca oleh sebuah langkah |
| `table: "setting-{@drop.difficulty}-terrain"` | tabel hasil perhitungan: `{…}` dan `$param` diisi |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | beberapa hasil sebagai daftar (`distinct` melempar ulang yang berulang) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | percabangan |
| `repeat: "@count"`, `as: i`, `steps: […]` | perulangan: menjalankan langkah-langkahnya sebanyak jumlah yang diberikan, dengan `@i` dihitung mulai dari 1 |
| `for: pcs` (atau `party`), `as: member`, `steps: […]` | menjalankan langkah-langkahnya sekali untuk setiap karakter pemain (atau anggota kelompok), sebagai `@member`: sebuah entri, seperti yang diikat oleh `entity:` (`@member.name`, `set: member.fatigue`); `as:` tidak pernah memakai nama parameter, jadi `who` milik aturan itu sendiri tetap utuh |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | keluaran untuk LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (atau `every: 1 day`) | pengingat yang jatuh tempo seiring berjalannya waktu permainan, seperti yang diatur oleh `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | melempar ulang sebagian dadu sebuah lemparan (mekanik push) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | melempar pada nilai daftar (daftar milik orakel): mengikat entrinya, `@who.choose` (baris kosong), dan `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | melempar pool yang menyusut milik sebuah pelacak seperti `track roll` (dadu yang menunjukkan 1-3 dibuang; dadu `drop` dibuang lebih dulu, dadu `extra` ikut dilempar) atau hanya membuang dadu (`mode: drop`: push, tick); fase yang tertaut dan peristiwa pool itu menyusul; mengikat `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Hasil sebuah pemeriksaan bisa dibaca oleh aturan yang menjalankannya (`check: … as: answer` memberi `@answer`), begitu pula penandanya: `'random-event' in @answer.flags`. Nilai `with:` dievaluasi jika berisi `@`, diisi jika berisi `$param` atau `{…}` ("Does $npc flee?"), dan diteruskan apa adanya jika tidak. Aturan dengan parameter `oracle` mendapat entri status orakel kampanye tanpa perlu diberi tahu. Parameter `ref` dengan `to: monster` mengambil entri bertipe itu: nama yang juga dimiliki entri lain (pool seorang musuh, dinamai seperti kartunya) berarti entri bertipe itu.

Pemicu berjalan sendiri saat event-nya terjadi, dan hanya jika `when:`-nya terpenuhi:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Aturan apa pun (termasuk generator dan pembuatan karakter) bisa membaca `@system` (ID sistem permainan yang dipakai dunia, agar latar yang ditulis untuk dua sistem bisa membedakan keduanya), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch`, dan `@time.is_night`, serta, jika kalendernya punya bulan, `@time.month`, `@time.month_name`, `@time.day_of_month`, dan `@time.year`; selama pertarungan berlangsung, `@combat.round` dan `@combat.fighters` (ID mereka yang ikut bertarung). Pemicu waktu juga bisa membaca `@time.passed`, jumlah detik yang baru saja dimajukan, pemicu `combat_start` atau `combat_end` membaca pertarungan yang dimulai atau berakhir (`combat start` dan `combat end` menjalankannya; petarung yang keluar tidak mengakhiri pertarungan), dan aturan yang dijalankan pemicu membaca apa yang dibaca pemicu itu. Pemicu dengan parameter wajib hanya dijalankan oleh `didact do` atau hook kolom (`who` = entri tersebut). Pemicu `on: manual` hanya berjalan saat dipanggil. `for: pcs` (atau `party`) menjalankan pemicu sekali untuk setiap karakter pemain (atau anggota kelompok), sebagai `who`: misalnya untuk pengalaman setelah setiap sesi. Pemicu yang gagal menghentikan perintah yang memicunya, dan menyebut pemicu mana itu serta cara melanjutkan tanpanya (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalender ada di `settings` sebuah paket: kalender paket latar mengalahkan kalender sistem, dan kalender milik dunia sendiri (`calendar:` di `world.yaml`-nya) mengalahkan keduanya:

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

`leap: 4` membuat sebuah bulan sehari lebih panjang setiap tahun ke-4, dan `leap: [4, 100, 400]` setiap tahun ke-4, tetapi tidak setiap tahun ke-100, namun tetap setiap tahun ke-400: setiap angka mengesampingkan angka sebelumnya. `weekday` menyebut hari dalam pekan untuk tanggal awal (jika tidak, hari pertama dalam pekan), dan `year` adalah cara sebuah tanggal menulis tahunnya, baik di tanggal yang ditampilkan Didact maupun di tanggal yang dibacanya (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` memeriksa ketiganya. Kampanye bisa dimulai pada tanggal lain dari kalender, sebelum awalnya atau sesudahnya: `didact campaign new <id> --date '4 July 1902'`, atau `didact time set '<date>'` sampai sesi pertamanya. Hari dalam pekan yang ditulis sebelum tanggal diperiksa: tanggal yang menentukan, dan sebuah catatan menyebutkannya jika jatuh pada hari lain.

Opsi adalah varian dan aturan opsional sistem, yang dipilih setiap kampanye pada sesi nol:

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

`didact campaign profile lethality=deadly supplies=on` menyimpannya (atau halaman Pengaturan di aplikasi web). Aturan, pembuatan karakter, dan generator membacanya (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): jawaban mengalahkan apa yang ditentukan opsi lain, dan itu mengalahkan nilai bawaan. Apa yang ditentukan sebuah opsi diikuti sampai tuntas (suasana yang menetapkan tingkat bahaya juga menetapkan apa yang ditentukan tingkat bahaya itu), dan dari dua ketentuan, yang lebih dekat yang menang. Ringkasan mencantumkan opsi yang berbeda dari nilai bawaannya beserta artinya, agar GM menerapkan apa yang tidak bisa dilakukan aturan. Generator yang tidak bisa berjalan dengan opsi itu berhenti lewat `stop:` beserta alasannya, dan tidak ada draf yang dibuat.

## Orakel: `oracles/`

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

- **Bertanya:** `didact ask '…' --odds likely` menjalankan pemeriksaan `ask`. Jawabannya adalah hasilnya (sebuah pita), dan penandanya ikut serta.
- **Status:** disimpan dalam entri yang diterima pemeriksaan sebagai `oracle`. Pemeriksaan mengubahnya dengan `set: oracle.chaos += 1`.
- **Daftar:** `lists: {names: […], method: sections, most: 3}` menyimpan daftar berbobot di entri itu. `didact lists add|drop|roll|show` mengelolanya, dan aturan melemparnya dengan `pick`. `sections` melempar untuk satu bagian berisi lima baris, lalu satu baris di dalamnya (baris kosong berarti pilih sendiri); `uniform` memberi setiap baris peluang yang sama.
- **Tambahan untuk pemeriksaan:** `didact ask '…' --with as_rule=true` meneruskan parameter tambahan ke pemeriksaan orakel.
- **Log:** setiap jawaban diberi nomor (`#o12`) dan dicatat, dan `didact interpret o12 '…'` menyimpan maknanya. Orakel `yes-no` dari paket core adalah cadangannya.

## Generator dan pembuatan karakter: `generators/`, `chargen/`

Keduanya adalah prosedur yang membangun **draf**. Keduanya memakai setiap langkah aturan (`roll`, `table`, `if`, `let`, `prompt`, …) ditambah langkah-langkah ini:

| Langkah | Fungsi |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | menambahkan entri ke draf (kunci `poi-1`, `poi-2`, …); kolom atau tautan yang menyebut kunci yang ditulis paket (`key:`, atau nama `as:`) menjadi ID entri itu saat diterapkan, jadi pilih kunci yang tidak dimuat kolom mana pun sebagai teks (entitas tanpa keduanya tidak punya kunci untuk ditukar); `from: "@relic.id"` memulainya dari entri kompendium (tipe, nama, dan kolomnya) |
| `choose: {from: [a, b], as: x}` (atau `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | sebuah pilihan; dalam mode terpandu draf menunggu `choose`; `exclude` mengecualikan pilihan sebelumnya (yang dilempar akan dilempar lagi); `records:` menambahkan entri bertipe itu yang ada di sini, berdasarkan ID (yang dibuat selama permainan); `answer:` menentukan pilihan tanpa bertanya jika nilainya salah satu opsi (jalur milik karakter itu sendiri) |
| `choose_or_roll: {table: backgrounds, as: background}` | pilihan yang bisa ditentukan dadu; data entri yang dipilih adalah `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | melempar ke dalam karakter |
| `swap: {among: [STR, DEX, WIL], optional: true}` | menukar dua skor, atau tetap |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | membagikan susunan angka tetap |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | membeli skor dalam batas anggaran (`default: random` membelanjakannya secara acak dalam mode acak) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | daftar masuk ke inventaris; pemetaan menetapkan kolom (daftar dijumlahkan) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | menambah ke kolom karakter (atau entitas dalam draf): angka dijumlahkan, selain itu digabung ke daftar; tidak ada yang ditambahkan pun tidak masalah |
| `remove: {field: talents, value: "@old"}` | membuang sesuatu dari kolom daftar (bakat yang ditukar, ikatan yang sudah tuntas); tidak ada yang dibuang pun tidak masalah |
| `roll_tables: [physique, vice]` | melempar tabel ke dalam `traits`; `data.gear` sebuah entri masuk ke inventaris dan `data.add: {gold: 20}` menambah ke kolom |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | namanya; `name: {prompt: …}` tanpa sumber untuk dilempar akan menunggu nama, bahkan dalam mode acak |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | pertanyaan yang boleh dijawab apa saja (tujuan, nama entri lain): draf menunggunya, bahkan dalam mode acak, kecuali sudah diisi di awal; `field:` menyimpan jawabannya |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawl: jatuhan dadu yang dicatat, jalur (selalu terhubung), jarak, jalur tersembunyi (lihat di bawah) |

Langkah map menerima lebih banyak lagi, untuk prosedur jatuhan dadu dari buku:

| Kunci | Fungsi |
|---|---|
| `regions: terrain` | entitas ini juga dijatuhkan; setiap tempat bergabung dengan yang terdekat (`region`-nya) |
| `hidden: 6`, `conditional: 5` | satu d6 per jalur: sama dengan atau di atas angka itu, jalurnya tersembunyi atau bersyarat (jalur tersembunyi tidak muncul di peta pemain) |
| `describe: [path-feature, path-condition]` | tabel yang dilempar untuk setiap jalur, disimpan sebagai `details`-nya |
| `entrance: true`, `exit: true` | tempat yang paling dekat ke tepi menjadi pintu masuk; sisanya dinomori dari situ mengikuti jalur (`map.n`), jalur mengarah menjauh darinya, dan pintu keluar adalah tempat jauh di dekat tepi, dengan nomor terakhir |
| `number: "{@dungeon_name}, room {@n}"` | mengganti nama tempat yang bernomor (kunci draf mereka mengikuti: `room-1` adalah ruang 1) |

Tabel jatuhan dadu bisa menyebut tabel berikutnya di data entrinya, sehingga prosedurnya terbaca seperti di buku: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, lalu `table: "{@drop.what}"`. Kolom daftar yang belum ditetapkan (conditions, lists, tags) terbaca sebagai daftar kosong, jadi `'deprived' in @who.conditions` langsung berfungsi sejak awal.

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

Chargen dengan `advances:` mengubah entri yang sudah ada alih-alih membuat yang baru: itulah prosedur naik level sistem.

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

- **Satu entri:** generator dengan `creates: npc` membangun entri itu seperti pembuatan karakter membangun karakter (`apply`, `add`, `name`, `field:`); langkah `entity`-nya menambahkan entri di sampingnya, dan tautan `to: character` menunjuk kepadanya.
- **Menjalankan:** `gen run` dan `char new` membuat draf (`#g7`, `#c3`) dan tidak menulis apa pun. `stop:` mengakhirinya tanpa membuat draf: di bawah `if:` yang membaca opsi kampanye, petunjuknya mengarah ke opsi (`didact session zero`); jika tidak, kata-katanya sendiri menyebut apa yang dilakukan sebagai gantinya.
- **Menentukan:** `--prefill '{…}'` menentukan hal-hal di muka, berdasarkan nama yang diikat sebuah langkah (`as:`): satu nilai menjawab setiap kemunculan, sebuah daftar menjawab satu kemunculan per item (daftar untuk `choose` dengan `count` adalah seluruh pilihannya). Nilai `let` juga bisa diisi di muka (`{"hp": 6}`), dan nama, `ask`, atau `let` menyimpan teks apa pun seperti yang diberikan. Nilai untuk pilihan di antara opsi yang sudah diketahui (sebuah `choose`, entri sebuah tabel) adalah opsi yang disebutnya, sesuai tulisannya atau dengan huruf besar-kecil yang berbeda, lewat `id` entrinya, atau lewat lemparan yang jatuh padanya (`{"group": 3}`), dan ikut membawa data entri itu; nilai yang mirip sebuah opsi tetapi tidak sama dengan opsi mana pun ditolak, dengan menyebutkan opsi yang paling mirip, dan nilai lain apa pun adalah jawaban bebas, tanpa data. `--auto` (atau `char new --mode random`) membiarkan dadu menentukan sisanya. Jika tidak, draf menunggu di setiap pilihan.
- **Menjelaskan:** sebuah pilihan menjelaskan arti setiap opsinya, untuk pemain yang memilih: `note:` milik entri tabel atau `about:` milik tabelnya, jika tidak ada maka entri kompendium yang disebutnya (`id` di datanya), atau entri kompendium yang merupakan opsi itu sendiri (pilihan di antara ID kompendium menampilkan nama masing-masing): `tagline` dan `summary`-nya, `description` atau `effect`-nya, jika tidak ada maka paragraf pertama teksnya.
- **Kembali:** `char back` (atau `gen back`) membatalkan jawaban, lemparan, atau suntingan terakhir, sehingga draf menanyakan pertanyaan itu lagi; lemparan yang dibuatnya ditandai diurungkan.
- **Melanjutkan:** draf yang dilanjutkan memutar ulang jejaknya: setiap nilai yang dilempar atau dipilih, masing-masing dipakai sekali dan berurutan (termasuk jatuhan dadu peta), jadi tidak ada yang dilempar dua kali dan tidak ada yang sudah ditentukan berubah.
- **Menulis:** `commit` menulis entrinya, diperiksa terhadap lembarnya.
- **Memajukan:** draf `advances:` dimulai dari salinan entri (dengan nilai bawaan lembarnya), langkah-langkahnya membaca entri itu sebagai `@who` dan nilai draf sebagai `@character.*`, dan `commit` hanya menulis apa yang berubah, diperiksa seperti `set`; entri dari langkah `entity`-nya (alur cerita sebuah ikatan baru) dibuat di sampingnya: tautan `to: character` menunjuk ke entri itu, dan kolom yang menyebut sebuah kunci berisi ID entri milik kunci itu, seperti saat karakter dibuat (`apply: {blood: "@pool"}`). `stop:` menyebutkan alasan mengapa belum bisa (XP belum cukup), dan tidak ada draf yang dibuat. Sistem yang perkembangannya hanya berupa satu aturan cukup menyebut aturan itu di chargen-nya: `advance: {rule: grow}`.
- **Mode:** `modes: [guided]` membuat prosedur tetap langkah demi langkah: `--mode random` ditolak.

## Kompendium, referensi, dan glosarium

- **Entri kompendium** ditulis seperti `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Nilai `"roll 2d8"` dilempar saat entri dimunculkan. Jalankan `didact spawn troll`, atau bawa entri sebuah paket ke dalam dunia dengan `didact compendium import <pack>` (`--type loc`, dan `--tag coast` untuk entri yang memiliki setiap tag yang diberikan).
- **Untuk beberapa sistem:** kunci di tingkat teratas masuk ke tempat `set` menaruhnya: ke blok sistem bila lembarnya punya kolom itu, jika tidak ke `fields`. Entri yang ditulis sebuah latar untuk lebih dari satu sistem memberikan angka tiap sistem di bloknya sendiri (`mechanics: {my-system: {hp: 12}}`): `pack validate` memeriksa setiap blok terhadap lembar sistemnya bila sistem itu terpasang, dan mencatat kunci di tingkat teratas yang dimiliki lembar itu sekaligus lembar core. Apa yang dikatakan blok tetap berlaku: di samping `mechanics: {my-system: {role: tactician}}`, `role: innkeeper` di tingkat teratas adalah kolom core, seperti semua yang ada di bawah `fields:`. Blok yang menyebut paket yang sedang divalidasi diperiksa terhadap paket itu sebagaimana adanya di foldernya.
- **Bagian referensi** ditaruh di `reference/*.md`, dengan front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` menemukannya; frasa bertanda kutip yang tidak ada di sana dicoba sebagai kata-katanya.
- **Glosarium** adalah `glossary.yaml`: `term: definition`, atau daftar `{term, definition, aliases, see}`. `didact define <term>` membacanya.

## Tes: `tests/`

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

## Membagikan dan menghapus paket

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Paket yang menyatakan `redistributable: false` tidak bisa diekspor.
- **core** adalah bagian dari Didact dan selalu aktif: setiap sistem dibangun di atasnya, jadi paket ini tidak bisa dinonaktifkan atau dicopot.
- Paket lain yang disertakan bersama Didact berupa berkas `.didactpack` di folder `packs/`-nya. `pack list` menampilkannya sampai dipasang, dan memasang salah satunya ikut membawa paket yang dibutuhkannya yang juga disertakan.
- `pack update` mencari versi yang lebih baru di folder `packs/` Didact dan di GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` menyebut tempat lain, atau kosong agar tidak mencari). Versi baru dipasang di samping versi lama: kampanye tetap memakai versinya sampai `didact campaign upgrade`.
- Hanya satu sistem permainan yang dipakai dalam satu waktu: sistem milik dunia yang terbuka. Dunia mempertahankan sistem yang dipakainya saat dibuat (`didact world new <id> --system <pack>`; dunia yang dibuat tanpa sistem memakai sistem pertama yang diberikan kepadanya, lewat `pack enable` atau `world set system=`), kampanyenya memainkan sistem itu, dan paket yang memerlukan sistem lain (latar yang ditulis untuknya) tidak dapat ditambahkan: sistem lain dimainkan di dunianya sendiri.
- `uninstall` menolak selama ada dunia atau kampanye yang memakai satu-satunya salinan paket itu (`--force` tetap menghapusnya). Ini tidak bisa diurungkan: pasang lagi .didactpack-nya.

## Dari buku aturan ke paket: daftar periksa

Telusuri mekanik buku dalam urutan ini. Masing-masing dipetakan ke salah satu hal di atas:

1. **Resolusi:** bagaimana sebuah lemparan berhasil (pemeriksaan: `success`, `bands`, `auto`).
2. **Dadu:** dadu tak biasa, simbol, tingkat (`dice.yaml`, dadu bernama, rantai).
3. **Lembar:** atribut, angka turunan (`schemas/`, kolom turunan).
4. **Sumber daya:** HP, keberuntungan, momentum (kolom resource dan counter; langkah `set`).
5. **Kondisi:** keadaan dan efeknya (kolom `conditions`; langkah `if`).
6. **Pertarungan:** serangan, kerusakan, inisiatif (aksi; `bag`/`deck` untuk urutan giliran).
7. **Prosedur:** eksplorasi, perjalanan, waktu senggang (prosedur dengan prompt).
8. **Tabel:** setiap tabel acak (`tables/`; `pack import` untuk tabel Markdown).
9. **Bestiari:** monster dan NPC (`compendium/`).
10. **Barang:** perlengkapan, mantra, relik (`compendium/`, kolom slots).
11. **Panduan GM:** prinsip dan saran (`GUIDE.md`, `reference/`, `guidance:` pada tipe).
12. **Pembuatan karakter:** cara membuat karakter (prosedur `chargen/`, atau `roll:` pada setiap kolom).

Kutip halaman dengan `source:` di mana-mana, agar celahnya terlihat. Tambahkan tes smoke-play yang membuat karakter, melempar pemeriksaan, bertarung, dan menjalankan prosedur.
