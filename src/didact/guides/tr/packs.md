<!-- translated from b1dfa1159ff4 -->
# Paketler

Paket; YAML dosyaları ve isteğe bağlı bir Python eklentisi olarak yazılmış bir oyun sistemi, kâhin, dünya ayarı, macera ya da ektir. Bu kılavuz bir paketin nasıl yazılacağını gösterir: bir kural kitabını pakete dönüştürmek ya da kendi içeriğinizi eklemek.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Bir paket kütüphanenizdekilerden de yapılabilir. `didact pack new my-brew --from-overlay my-system` bir sistem için ev yapımı içeriğinizi (`compendium add`, `--scope system` ile tutulan kayıtlar, lore) bir eke dönüştürür; `didact world export --as setting` ise bir dünyayı bir evren paketine dönüştürür: kişileri, yerleri ve lore’u derleme girdileri ve paket lore’u olarak, `compendium import` ile başka bir dünyaya getirilir. İkisi de `--secrets` verilmedikçe sırları ve GM notlarını dışarıda bırakır ve lisansını belirleyene kadar hiçbiri paylaşılabilir olarak işaretlenmez.

## Düzen

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

Bir dosya tek bir öğe, bir öğe listesi ya da `---` ile ayrılmış birkaç öğe tutar. Her öğe kimliğini kendi türünün anahtarıyla belirtir: `table: weather`, `check: save`, `type: pc` ya da derleme girdileri için `id: troll`. Öğelere `pack.id` (`my-system.save`) ile, ya da onu yalnızca bir etkin paket içeriyorsa çıplak kimliğiyle başvurun.

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

Bir hack, temelini `extends` içinde belirtir ve yalnızca farklı olanı tutar:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Aynı kimliğe sahip öğesi, türü ne olursa olsun (bir tablo, bir kural, bir derleme girdisi, bir başvuru bölümü, bir sözlükçe terimi) temelin öğesinin yerini alır. Hack'in `settings` değerleri temelinkilerin üzerine anahtar anahtar uygulanır: hack'in ayarladığı bir anahtar, temeldeki değerin bütünüyle yerini alır (`names` tabloları temelinkilerin yerine geçer) ve temelin kuralları da hack'in değerlerini okur. `hides`, geriye kalanlardan hack'in işine yaramayanları çıkarır: `*` herhangi bir karakter dizisiyle eşleşir, bir kimlikle eşleşen son kalıp belirleyicidir ve `!` ile başlayan bir kalıp öğeyi korur. Hack'in yerine koyduğu şey asla gizlenmez. Türler şunlardır: `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` ve `term`. `didact pack validate`, hiçbir şeyle eşleşmeyen bir kalıp için uyarır.

## İfadeler

Her koşul ve formül zar dilini (`didact guide dice`) kullanır; ayrıca:
- **Değerler:** `@name` bir değer okur: `@roll`, `@who.STR`, `@settings.x`. `$name` önce bir parametrenin metnini yapıştırır, böylece `@who.$attr`, `@who.STR` olur. Serbest metinli bir parametreyi tırnak içinde (`'$name'`) değil, `@name` olarak okuyun: metnindeki bir kesme işareti tırnağı kapatır (`pack validate` uyarır).
- **Mantık:** `and`, `or`, `not` ve `in` (`'deprived' in @who.conditions`).
- **Sabitler:** metin (`'travel'`) ve `true`/`false`.
- **Fonksiyonlar:** `if(cond, a, b)` yalnızca seçtiği dalı atar. `default(@thread.flashpoint, 0)` değerin kendisidir, ayarlanmamışsa yedek değerdir. `sum`, `count` (`count(@roll.dice, 6)` altıları sayar), `min`, `max`, `any` ve `all` liste alır.

## Karakter sayfaları: `schemas/`

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

| Tür | Tuttuğu | Seçenekler |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | düz bir değer | min, max; enum için `values` |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` değerdir, `@hp.max` üst sınır | range; min; max ya da max_field; die |
| `counter` | bir sayı | min, max, thresholds, occupies (bir slots alanı) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | eşyalar (`Rope` ya da `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | adının söylediği | `to` (refs için), `allowed` |
| `derived` | hesaplanır, asla saklanmaz | expr |

Her alan ayrıca `label`, `help`, `default`, `required` ve `roll` alır: `new pc Hero --fill` ya da `"roll"` değeri onu günlük üzerinden atar. `core` paketinin türleri sistemden bağımsız düzyazıyı `fields` içinde tutar. Bir sistemin türleri sayılarını `mechanics.<system>` içinde tutar. `set hero hp-=2` alanı bulur, sınırlar ve taşmayı bildirir. `+=` bir listeye ekler: bir `list` (`slots` gibi) yeniden eklenen bir değeri de tutar, `tags`, `conditions` ve `refs` onu yalnızca bir kez tutar, `-=` ise tüm kopyalarını çıkarır.

**Kancalar** bir değer bir çizgiyi geçtiğinde ne olacağını söyler. Her değişiklikte (`set`, `inv`, bir kuralın `set` adımı) tetiklenirler, ama yalnızca çizgi geçildiğinde: 3 → 0 tetikler, 0 → 0 tetiklemez. `--force` düzenlemeleri onları atlar.

| Kanca | Ne zaman tetiklenir |
|---|---|
| `on_zero` | bir sayı ya da `{value}` 0'a ulaştığında |
| `on_full` (slots'ta `when_full`) | maksimumuna, boyutuna ya da kapasitesine ulaştığında |
| `thresholds: {10: …, 20: …}` (sayaçlar) | her işareti geçtiğinde |

Bir eylem metin (LLM için bir not), aynı kayıtta `{set: {hp: 0}}` ya da `{condition: paralyzed}`, `{trigger: death}` (o kuralı `who` = kayıt ile çalıştırır) ya da bunların bir listesidir.

**Envanter** (`didact inv …`) karakter sayfasının `slots` alanında çalışır:
- **Yer:** eşyalar `size` × `count` kadar yer kaplar; alanı `occupies` ile kaplayan sayaçlar da değerleri kadar. `capacity` aşılırsa `--force` olmadan reddedilir.
- **Gruplar:** `groups: {backpack: 6, body: 4}` her gruba kendi yerini, ayrıca kendi sütunlarını ve toplamlarını verir: `@inventory.body.armor` yalnızca giyilen ya da elde tutulan şeylerdir, `@inventory.body.free` ise grubun kalan yeridir.
- **Kullanımlar:** `uses: 3`, `inv use` ile geri sayar. `uses: d8` bir kullanım zarıdır: 1–2 onu bir basamak düşürür. Tükenen eşya, `recharge` ya da `keep: true` yoksa gider. Aynı adlı birkaç eşyadan ad ilkini gösterir; bir kullanım harcanırken (`inv use`, bir kuralın `use:` adımı, `set …uses-=1`) kullanımı kalan ilkini.
- **Bir eşyanın kendi anahtarları:** `didact set freya inventory.sword.damage=d10` (bir kuralın `set: who.inventory.$item.damage` adımı da) bunlardan birini değiştirir, eşya `inv` komutlarındaki gibi, adının bir parçasıyla ya da tamamıyla, boşluklar ve noktalar dahil adlandırılır (`'inventory.12.7mm pistol.damage=d10'`, kabuk için tırnak içinde); `uses` ve `charges` bir `uses` alanı gibi sayar (`charges+=2` üst sınırda durur) ve yer, `inv add` ile olduğu gibi denetlenir. Bir kural böyle bir anahtarı `@{who.inventory.$item.damage}` olarak okur (kullanım zarını zarı olarak, kullanımları sayıları olarak); orada olmayan bir eşya ya da anahtar yok olarak okunur, böylece `default(…)` yedek değerini verir.
- **Derleme:** `item` türündeki (ya da weapon, armor, relic, …, ya da paketin bunlardan birini `extends` ile genişleten kendi türündeki) girdiler ayrıntılarını `inv add`'e ödünç verir; kimlikle, adla ya da bir diğer adla bulunurlar (ikisi aynı diğer adı paylaşıyorsa istediğinizi `pack.id` olarak belirtin); `:` dahil başka her ad eşyanın kendi adıdır.

## Tablolar: `tables/`

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

Başka biçimler:
- **Ağırlıklı listeler:** liste olarak `entries`, her girdide `weight:`.
- **Sütunlar:** `columns: [a, b]` bir satırın her sütununu ayrı atar. Düz bir girdi (liste değil) her sütunu doldurur, yani bir kelime listesi üzerinde `columns: [first, second]` "bu listede iki kez at" demektir. `labels: false` sütun adlarını sonuçtan çıkarır ("Abandon · Advantage"). `read: "It's a {first} {second} with {third} {fourth} inside."` sütunları bir cümle olarak okur.
- **Başvuru tabloları:** `lookup: hp_lost` ya da 2 boyutlu bir çizelge için `[odds, chaos]`.
- **Tekrarlar:** "iki kez at" için `duplicates: reroll | keep | make_it_worse`.
- **İki adım:** başka bir tabloda atan bir girdi (metin yerine `{table: lightning}` ya da metinden sonra `then:`) o atışın verisini de beraberinde getirir: bu girdiyi zarla elde eden bir kural ya da taslak ikisini de okur, önce girdinin kendi anahtarlarını, sonra ardından atılan ilk tablonunkileri. Bir `--prefill`, daha aşağıdaki bir girdiyi her derinlikte adlandırabilir (`Ring of the Hunt`), yol üzerindeki her girdinin verileriyle birlikte: aynı adlı iki girdiden yakın olanı (sonra ilki) kastedilir, devam eden bir girdi oradan atmayı sürdürür, bunlardan birine yakın olup hiçbiri olmayan bir ad ise reddedilir ve en yakını söylenir. Rehberli bir taslak, girdileri ne olduklarını söylediğinde ilk adımı sunar (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): birini seçmek, ona denk gelen bir atış gibi sonraki tabloya atar.
- **İki yönlü okuma:** bir d66 tablosunda `both_ways: true` öteki okumayı ekler: 31, 13'ü de verir ve okuyan seçer.
- **Bir girdinin anlamı:** `about: "Knows: {skills}. Also known as: {aka}."` her girdinin verisini yerine koyarak (bir liste `a, b` diye okunur; `{text}` girdinin kendisidir) bir seçim o girdiyi sunduğunda ne kazandırdığını söyler; bir girdinin kendi `note:` alanı ise bunu onun yerine söyler. İkisi de yoksa, verisindeki `id` bir derleme girdisini adlandıran bir girdiyi o derleme girdisi tanımlar.
- **Desteler ve torbalar:** `cards` ile (ya da `standard: true`) `deck: tarot`; `tokens` ile `bag: initiative`.

Doğrulama, zarların atabileceği her sonucun bir girdiye düştüğünü denetler.

## Kurallar: `rules/`

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

Eylemler ve prosedürler adım listeleridir; tetikleyiciler de `when:` koruması olan adımlardır. Adımlar şunlardır:

| Adım | Ne yapar |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | günlüğe yazılan bir atış; `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>` bağlar; bir `{…}` her metinde olduğu gibi önce doldurulur, böylece bir değerin metin olarak tuttuğu zarlar atılır (`{@{who.inventory.$item.damage}}`) ve günlük onları gösterir: zar olmayan bir değer reddedilir, böyle bir metinle hiçbir şey atmayan `roll: "@die"` de; bir atış kümesi (`{d8, d6}kh1`) küme olarak kalır |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | değer hesaplar; `set`'in `value`'su gibi, `{…}` içeren metin bir şablondur, çıplak bir kelime metindir; doldurulan her metinde `{{` ve `}}` süslü parantezin kendisini yazar |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (ya da `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | bir kaydı değiştirir: doğrulanır, sınırlanır, geri alınabilir; `set: who.$attr` bir parametrenin belirttiği alanı, `set: who.inventory.$item.damage` ise kaydın taşıdığı bir eşyanın bir anahtarını ayarlar (Envanter bölümüne bakın); `-=` bir listeden bir değer çıkarır ve listenin içermediği bir değer hiçbir şeyi değiştirmez (bir not bunu söyler; listenin asla içeremeyeceği bir değer reddedilir); `unset:` bir alanı `set --unset` gibi kaldırır |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | bir kayda bir eşya verir ya da ondan bir eşya alır, tıpkı `inv add` ve `inv drop` gibi: ayrıntıları derlemeden gelir, adının benzersiz bir parçası yeter, yer ve alanın kancaları denetlenir |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | taşınan bir eşyayı `inv use` gibi kullanır: kullanımlar ya da yükler geri sayar, kullanım zarı atılır ve 1–2'de bir basamak düşer, tükenen eşya yeniden dolmuyor ya da saklanmıyorsa gider; o adlı birkaç eşyadan kullanımı kalan ilki; `@torch.out` (son kullanımı gitti), `@torch.gone` (ondan hiçbir şey kalmadı), `@torch.left`, `@torch.die` ve `@torch.rolled` değerlerini bağlar (`as:` varsayılan olarak `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | hemen bir kayıt oluşturur; kayıt bir taslağın `entity` adımındaki gibi (aşağıda) tanımlanır ve sayfasına göre denetlenir; `as:` (yoksa `key` değeri, o da yoksa türü) onu bir kayıt olarak bağlar, bir `ref` parametresi gibi okunur ve ayarlanır (`pool: "@bleeding"`, `@bleeding.name`) ve bu ad hiçbir zaman bir parametrenin adı olamaz; `key:` yoksa hiçbir alan anahtar sayılmaz (`kind: track` yazıldığı gibi kalır); burada o türde ve o adda bir kayıt zaten varsa olduğu gibi alınır, böylece yeniden çalıştırılan bir kural yeni bir şey oluşturmaz |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | bir kontrol çalıştırır ve sonucunu bağlar |
| `do: other-action`, `with: {…}`, `as: trip` | başka bir kural çalıştırır; `@trip` onun sonucu, `@trip.<name>` ise onun bağladığıdır (`let: {found: 2}` için `@trip.found`, `roll: d6`, `as: luck` için `@trip.luck`); `as:` varsayılan olarak onun kimliğidir |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | günlüğe yazılan bir tablo atışı; metni ve girdinin `data`'sını (`@scar.<key>`, bir eşlemenin anahtarlarını da yollarıyla: `@scar.cost.hp`), ardından attığı herhangi bir tablonun verisiyle birlikte bağlar; bir eşya listesi (`[Rope, {name: Laser, damage: d8}]`) eşyaların adları olarak okunur (`count(@scar.gear)`, `'Laser' in @scar.gear`), bir adıma olduğu gibi verildiğinde ise (`apply: "@scar.gear"`) eşyaların kendisidir; başka eşlemelerden oluşan bir listeyi yalnızca bir adım okur |
| `table: "setting-{@drop.difficulty}-terrain"` | hesaplanan bir tablo: `{…}` ve `$param` doldurulur |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | liste olarak birkaç sonuç (`distinct` tekrarları yeniden atar) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | dallanma |
| `repeat: "@count"`, `as: i`, `steps: […]` | bir döngü: adımları o kadar kez çalıştırır, `@i` 1'den başlayarak sayar |
| `for: pcs` (ya da `party`), `as: member`, `steps: […]` | adımları her oyuncu karakteri (ya da grup üyesi) için bir kez, `@member` olarak çalıştırır: `entity:` adımının bağladığı gibi bir kayıt (`@member.name`, `set: member.fatigue`); `as:` asla bir parametrenin adını almaz, böylece kuralın kendi `who` parametresi olduğu gibi kalır |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | LLM için çıktı |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (ya da `every: 1 day`) | oyun zamanı geçtikçe vadesi gelen bir hatırlatıcı, `didact remind` ile kurulanlar gibi |
| `reroll: roll`, `keep_if: "@face == 6"` | bir atışın bazı zarlarını yeniden atar (zorlama mekanikleri) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | bir liste değerinde atar (bir kâhinin listeleri): girdiyi, `@who.choose` (boş bir satır) ve `@who.empty` bağlar |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | bir sayacın azalan havuzunu `track roll` gibi atar (1-3 gelen zarlar düşer; `drop` zarları önce düşer, `extra` zarları birlikte atılır) ya da yalnızca zar düşürür (`mode: drop`: zorlama, işaretleme); ardından bağlı evreler ve havuzun olayı gelir; `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` bağlar |

Bir kontrolün sonucu onu çalıştıran kural tarafından okunabilir (`check: … as: answer`, `@answer` verir), bayrakları da öyle: `'random-event' in @answer.flags`. `with:` değerleri `@` içeriyorsa hesaplanır, `$param` ya da `{…}` içeriyorsa doldurulur ("Does $npc flee?"), yoksa yazıldığı gibi aktarılır. `oracle` parametresi olan bir kural, kampanya kâhininin durum kaydını söylenmeden alır. `to: monster` içeren bir `ref` parametresi o türde bir kayıt alır: başka bir kaydın da taşıdığı bir ad (bir düşmanın, kartının adını taşıyan havuzu gibi) o türdeki kaydı gösterir.

Tetikleyiciler olayları gerçekleştiğinde kendiliğinden çalışır, ama yalnızca `when:` koşulları tutuyorsa:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Her kural (üreteçler ve karakter oluşturma dahil) `@system` (dünyada oynanan sistemin kimliği; böylece iki sistem için yazılmış bir evren onları ayırt edebilir), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` ve `@time.is_night` okuyabilir; ayları olan bir takvimde `@time.month`, `@time.month_name`, `@time.day_of_month` ve `@time.year` da okunabilir; bir çatışma sürerken `@combat.round` ve `@combat.fighters` (çatışmadakilerin kimlikleri) de okunabilir. Bir zaman tetikleyicisi ayrıca az önce ilerletilen saniyeleri, `@time.passed`'i okuyabilir; bir `combat_start` ya da `combat_end` tetikleyicisi başlayan ya da biten çatışmayı okur (`combat start` ve `combat end` onları çalıştırır; bir dövüşçünün ayrılması çatışmayı bitirmez); bir tetikleyicinin çalıştırdığı kural da tetikleyicinin okuduklarını okur. Zorunlu parametreleri olan bir tetikleyiciyi yalnızca `didact do` ya da bir alan kancası (`who` = kayıt) çalıştırır. `on: manual` tetikleyicileri yalnızca çağrıldıklarında çalışır. `for: pcs` (ya da `party`) bir tetikleyiciyi her oyuncu karakteri (ya da grup üyesi) için bir kez, `who` olarak çalıştırır: örneğin her oturumdan sonra deneyim vermek için. Başarısız olan bir tetikleyici, onu tetikleyen komutu durdurur; hangi tetikleyici olduğunu ve onsuz nasıl devam edileceğini söyler (`didact override add trigger <id> --data '{"on": "manual"}'`).

Takvim bir paketin `settings` kısmındadır: bir evren paketinin takvimi sistemin takvimine üstün gelir, bir dünyanın kendi takvimi (`world.yaml` dosyasındaki `calendar:`) ise ikisine de:

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

`leap: 4` bir ayı her 4. yılda bir gün uzatır, `leap: [4, 100, 400]` ise her 4. yılda, ama her 100. yılda değil, yine de her 400. yılda: her sayı bir öncekini geçersiz kılar. `weekday` başlangıcın haftanın hangi günü olduğunu söyler (yoksa haftanın ilk günüdür), `year` ise bir tarihin yılını nasıl yazdığıdır, hem Didact'ın gösterdiği hem de okuduğu tarihlerde (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` üçünü de denetler. Bir kampanya takvimin başka bir tarihinde, başlangıcından önce ya da sonra başlayabilir: `didact campaign new <id> --date '4 July 1902'` ya da ilk oturumuna kadar `didact time set '<date>'`. Tarihten önce yazılan haftanın günü denetlenir: tarih belirler ve başka bir güne denk geliyorsa bir not bunu söyler.

Seçenekler, her kampanyanın sıfırıncı oturumda seçtiği sistem varyantları ve isteğe bağlı kurallardır:

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

`didact campaign profile lethality=deadly supplies=on` onları kaydeder (ya da web uygulamasının Ayarlar sayfası). Kurallar, karakter oluşturma ve üreteçler onları okur (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): bir yanıt, başka bir seçeneğin gerektirdiğinin önüne geçer; o da varsayılanın önüne geçer. Bir seçeneğin gerektirdikleri sonuna kadar izlenir (ölümcüllüğü belirleyen bir tarz, o ölümcüllüğün gerektirdiklerini de belirler) ve iki gerektirme çakışırsa daha yakın olanı ağır basar. Özet, varsayılanından farklı olanları anlamlarıyla birlikte listeler; böylece oyun yöneticisi kuralların yapamadığını uygular. Bunlarla çalışamayan bir üreteç `stop:` ile ve nedeniyle durur, taslak oluşturulmaz.

## Kâhinler: `oracles/`

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

- **Sormak:** `didact ask '…' --odds likely`, `ask` kontrolünü çalıştırır. Yanıt onun sonucudur (bir bant); bayrakları da onunla gelir.
- **Durum:** kontrolün `oracle` olarak aldığı bir kayıtta yaşar. Bir kontrol onu `set: oracle.chaos += 1` ile değiştirir.
- **Listeler:** `lists: {names: […], method: sections, most: 3}` o kayıtta ağırlıklı listeler tutar. `didact lists add|drop|roll|show` onları yönetir, kurallar da `pick` ile onlarda atar. `sections` önce beş satırlık bir bölüm için, sonra onun içinde bir satır için atar (boş satır seçin demektir); `uniform` her satıra aynı şansı verir.
- **Kontrol için fazlası:** `didact ask '…' --with as_rule=true` kâhinin kontrolüne ek parametreler aktarır.
- **Günlük:** her yanıt numaralanır (`#o12`) ve günlüğe yazılır; `didact interpret o12 '…'` ne anlama geldiğini saklar. core paketinin `yes-no` kâhini yedek seçenektir.

## Üreteçler ve karakter oluşturma: `generators/`, `chargen/`

İkisi de bir **taslak** kuran prosedürlerdir. Her kural adımını (`roll`, `table`, `if`, `let`, `prompt`, …) ve ayrıca şunları kullanırlar:

| Adım | Ne yapar |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | taslağa bir kayıt ekler (anahtarlar `poi-1`, `poi-2`, …); paketin yazdığı bir anahtarı (`key:` ya da bir `as:` adı) adlandıran bir alan ya da bağlantı, onaylanınca o kaydın kimliği olur; bu yüzden hiçbir alanın metin olarak taşımadığı anahtarlar seçin (ikisi de olmayan bir varlığın değiştirilecek anahtarı yoktur); `from: "@relic.id"` kaydı bir derleme girdisinden başlatır (girdinin türü, adı ve alanlarıyla) |
| `choose: {from: [a, b], as: x}` (ya da `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | bir seçim; yönlendirmeli modda taslak `choose` bekler; `exclude` önceki seçimleri dışlar (zarla gelen biri yeniden atılır); `records:` buradaki o türden kayıtları kimlikleriyle seçeneklere ekler (oyun sırasında oluşturulanları); `answer:`, değeri seçeneklerden biriyse seçimi sormadan yapar (karakterin kendi yolu) |
| `choose_or_roll: {table: backgrounds, as: background}` | zarların yapabileceği bir seçim; seçilen girdinin verisi `@background.gear` olur |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | karaktere zar atar |
| `swap: {among: [STR, DEX, WIL], optional: true}` | iki değeri takas eder ya da olduğu gibi bırakır |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | sabit bir diziyi dağıtır |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | bir bütçe içinde değer satın alır (`default: random` rastgele modda bütçeyi rastgele harcar) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | bir liste envantere gider; bir eşleme alanları ayarlar (listeler toplanır) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | karakterin (ya da taslaktaki bir varlığın) bir alanına ekler: sayılar toplanır, diğer her şey bir listeye katılır; eklenecek bir şey olmaması sorun değildir |
| `remove: {field: talents, value: "@old"}` | bir liste alanından bir şey çıkarır (değiştirilen bir yetenek, sonuçlanan bir bağ); çıkarılacak bir şey olmaması sorun değildir |
| `roll_tables: [physique, vice]` | tablolarda atıp `traits`'e yazar; bir girdinin `data.gear`'ı envantere gider, `data.add: {gold: 20}` alanlara ekler |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | ad; atılacak bir şey yoksa `name: {prompt: …}` rastgele modda bile bir ad bekler |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | her yanıtın geçerli olduğu bir soru (bir amaç, başka bir kaydın adı): önceden doldurulmadıysa taslak, rastgele modda bile onu bekler; `field:` yanıtı saklar |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | bir pointcrawl: günlüğe yazılan bir zar bırakma, yollar (hep bağlantılı), mesafeler, gizli yollar (aşağıya bakın) |

Map adımı, kitaptaki zar bırakma prosedürleri için daha fazlasını alır:

| Anahtar | Ne yapar |
|---|---|
| `regions: terrain` | bu varlıklar da bırakılır; her yer en yakınına katılır (onun `region`'ı) |
| `hidden: 6`, `conditional: 5` | her yol için bir d6: o sayı ya da üstü gizli ya da koşullu bir yol demektir (gizli yollar oyuncuların haritasında görünmez) |
| `describe: [path-feature, path-condition]` | her yol için atılan tablolar, onun `details`'i olarak saklanır |
| `entrance: true`, `exit: true` | kenara en yakın yer giriştir; diğerleri yollar boyunca ondan başlayarak numaralanır (`map.n`), yollar ondan uzağa gider ve çıkış, bir kenara yakın uzak bir yerdir, en son numaralanır |
| `number: "{@dungeon_name}, room {@n}"` | numaralı yerleri yeniden adlandırır (taslak anahtarları da uyar: `room-1` 1. odadır) |

Bir zar bırakma tablosu, girdilerinin verisinde sıradaki tabloları adlandırabilir; böylece prosedür kitaptaki gibi okunur: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, sonra `table: "{@drop.what}"`. Ayarlanmamış liste alanları (conditions, lists, tags) boş liste olarak okunur, bu yüzden `'deprived' in @who.conditions` baştan çalışır.

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

`advances:` içeren bir chargen, kayıt oluşturmak yerine var olan bir kaydı değiştirir: sistemin seviye atlaması budur.

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

- **Tek kayıt:** `creates: npc` içeren bir üreteç, o kaydı karakter oluşturmanın bir karakteri kurduğu gibi kurar (`apply`, `add`, `name`, `field:`); `entity` adımları yanına kayıtlar ekler ve bir `to: character` bağlantısı ona işaret eder.
- **Çalıştırmak:** `gen run` ve `char new` bir taslak yapar (`#g7`, `#c3`) ve hiçbir şey yazmaz. Bir `stop:` çalıştırmayı taslak oluşturmadan bitirir: bir kampanya seçeneğini okuyan bir `if:` altında ipucu seçeneklere yönlendirir (`didact session zero`); aksi hâlde kendi sözleri bunun yerine ne yapılacağını söyler.
- **Karar vermek:** `--prefill '{…}'` bazı şeylere önceden, bir adımın bağladığı adla (`as:`) karar verir: tek bir değer her geçişi yanıtlar, bir liste her geçişe bir tane (`count` içeren bir `choose` için liste seçimin tamamıdır). `let` değerleri de önceden doldurulabilir (`{"hp": 6}`); bir ad, bir `ask` ya da bir `let` ise her türlü metni verildiği gibi saklar. Bilinen seçenekler arasındaki bir seçim (bir `choose`, bir tablonun girdisi) için verilen değer, adlandırdığı seçenek sayılır ve o girdinin verisini getirir; seçenek yazıldığı gibi ya da farklı büyük/küçük harfle, girdisinin `id`'siyle ya da ona düşen bir atışla (`{"group": 3}`) adlandırılabilir. Bir seçeneğe yakın olup hiçbirine uymayan bir değer, en yakını belirtilerek reddedilir; diğer her değer ise veri getirmeyen serbest bir yanıttır. `--auto` (ya da `char new --mode random`) gerisine zarların karar vermesini sağlar. Aksi hâlde taslak her seçimde bekler.
- **Tanımlamak:** bir seçim, seçecek oyuncu için her seçeneğin ne anlama geldiğini söyler: bir tablo girdisinin `note:` alanı ya da tablosunun `about:` alanı; yoksa girdinin adlandırdığı derleme girdisi (verisindeki `id`) ya da seçeneğin kendisi olan derleme girdisi (derleme kimlikleri arasında bir seçim her birinin adını gösterir): bu girdinin `tagline` ve `summary` alanları, `description` ya da `effect` alanı, o da yoksa metninin ilk paragrafı.
- **Geri gitmek:** `char back` (ya da `gen back`) son yanıtı, atışı ya da düzenlemeyi geri alır, böylece taslak o soruyu yeniden sorar; yaptığı atışlar geri alındı olarak işaretlenir.
- **Sürdürmek:** sürdürülen bir taslak izini yeniden oynatır: atılan ya da seçilen her değer, her biri bir kez ve sırayla (haritanın zar bırakması da); böylece hiçbir şey iki kez atılmaz ve önceden karar verilen hiçbir şey değişmez.
- **Yazmak:** `commit` kayıtları yazar, karakter sayfalarına göre denetleyerek.
- **İlerletmek:** bir `advances:` taslağı kaydın bir kopyasından (karakter sayfasının varsayılanlarıyla) başlar; adımları kaydı `@who`, taslağın değerlerini `@character.*` olarak okur ve `commit` yalnızca değişenleri, `set` gibi denetleyerek yazar; `entity` adımlarından gelen kayıtlar (yeni bir bağın olay örgüsü) onun yanında oluşturulur: bir `to: character` bağlantısı kayda işaret eder ve bir anahtarı adlandıran alan, karakter oluşturulurken olduğu gibi o kaydın kimliğini tutar (`apply: {blood: "@pool"}`). Bir `stop:` bunun neden henüz olamayacağını söyler (yeterli XP yok) ve taslak oluşturulmaz. Gelişimi tek bir kuraldan ibaret olan bir sistem bunun yerine o kuralı chargen'inde belirtir: `advance: {rule: grow}`.
- **Modlar:** `modes: [guided]` bir prosedürün adım adım ilerlemesini sağlar: `--mode random` reddedilir.

## Derleme, başvuru ve sözlükçe

- **Derleme girdileri** `new --data` gibi yazılır: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. `"roll 2d8"` değeri, girdi ortaya çıkarıldığında atılır. `didact spawn troll` çalıştırın ya da bir paketin girdilerini `didact compendium import <pack>` ile dünyaya getirin (`--type loc` ve verilen her etikete sahip olanlar için `--tag coast`).
- **Birden çok sistem için:** en üst düzeydeki bir anahtar `set`'in koyduğu yere gider: sistemin sayfasında o alan varsa sistemin bloğuna, yoksa `fields` içine. Bir evrenin birden fazla sistem için yazdığı bir girdi, her sistemin sayılarını kendi bloğunda verir (`mechanics: {my-system: {hp: 12}}`): `pack validate`, sistem kuruluysa her bloğu o sistemin sayfasına göre denetler ve hem o sayfada hem de core'un sayfasında bulunan en üst düzey bir anahtarı not eder. Bir bloğun söylediği geçerlidir: `mechanics: {my-system: {role: tactician}}` yanında en üst düzeydeki `role: innkeeper`, `fields:` altındaki her şey gibi core'un alanıdır. Doğrulanan paketi adlandıran bir blok, o paketin klasöründeki hâline göre denetlenir.
- **Başvuru bölümleri** ön bilgiyle (`id`, `title`, `tags`, `page`, `mechanics: [save]`) `reference/*.md` içine gider. `didact rules lookup <topic>` onları bulur; orada olmayan tırnak içindeki bir ifade, sözcükleriyle denenir.
- **Sözlükçe** `glossary.yaml` dosyasıdır: `term: definition` ya da `{term, definition, aliases, see}` listesi. `didact define <term>` onu okur.

## Testler: `tests/`

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

## Paketleri paylaşmak ve kaldırmak

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- `redistributable: false` bildiren bir paket dışa aktarılamaz.
- **core** Didact'ın parçasıdır ve her zaman açıktır: her sistem onun üzerine kurulur, bu yüzden devre dışı bırakılamaz ya da kaldırılamaz.
- Didact ile gelen diğer paketler, onun `packs/` klasöründeki `.didactpack` dosyalarıdır. `pack list` kurulana kadar onları gösterir ve birini kurmak, gerektirdiği ve Didact ile gelen paketleri de getirir.
- `pack update` daha yeni sürümleri Didact'ın `packs/` klasöründe ve GitHub'da (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` başka bir yeri belirtir, boşsa hiç bakılmaz) arar. Yeni sürüm eskisinin yanına kurulur: kampanyalar `didact campaign upgrade` yapılana kadar kendi sürümlerini korur.
- Aynı anda tek bir oyun sistemi kullanımdadır: açık dünyanınki. Bir dünya, oluşturulurken seçilen sistemi korur (`didact world new <id> --system <pack>`; sistemsiz oluşturulan bir dünya, `pack enable` ya da `world set system=` ile kendisine verilen ilk sistemi alır), kampanyaları o sistemle oynanır ve başka bir sistem gerektiren bir paket (onun için yazılmış bir evren) eklenemez: başka bir sistem kendi dünyasında oynanır.
- `uninstall`, bir dünya ya da kampanya paketin tek kopyasını kullanırken reddeder (`--force` yine de kaldırır). Geri alınamaz: .didactpack dosyasını yeniden kurun.

## Kural kitabından pakete: kontrol listesi

Kitabın mekaniklerini bu sırayla gözden geçirin. Her biri yukarıdaki bir şeye karşılık gelir:

1. **Çözümleme:** bir atış nasıl başarılı olur (bir kontrol: `success`, `bands`, `auto`).
2. **Zarlar:** alışılmadık zarlar, semboller, basamaklar (`dice.yaml`, adlı zarlar, zincirler).
3. **Karakter sayfası:** nitelikler, türetilen sayılar (`schemas/`, derived alanlar).
4. **Kaynaklar:** HP, şans, ivme (resource ve counter alanları; `set` adımları).
5. **Durumlar:** durumlar ve etkileri (`conditions` alanları; `if` adımları).
6. **Çatışma:** saldırılar, hasar, inisiyatif (eylemler; sıra için `bag`/`deck`).
7. **Prosedürler:** keşif, yolculuk, boş zaman (yönlendirmeli prosedürler).
8. **Tablolar:** her rastgele tablo (`tables/`; Markdown tabloları için `pack import`).
9. **Canavarlar:** canavarlar ve OYK'ler (`compendium/`).
10. **Eşyalar:** teçhizat, büyüler, kalıntılar (`compendium/`, slots alanları).
11. **GM rehberliği:** ilkeler ve öğütler (`GUIDE.md`, `reference/`, türlerde `guidance:`).
12. **Karakter oluşturma:** karakter nasıl yapılır (bir `chargen/` prosedürü ya da her alanda `roll:`).

Eksikler ortaya çıksın diye sayfaları her yerde `source:` ile belirtin. Bir karakter yapan, bir kontrol atan, dövüşen ve bir prosedür çalıştıran bir smoke-play testi ekleyin.
