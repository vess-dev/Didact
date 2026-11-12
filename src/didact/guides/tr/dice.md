<!-- translated from a81883b64f94 -->
# Zarlar

Her zarı Didact ile atın ve asla sonuç uydurmayın. Her atış bir kimlik alır (`#r12`), günlüğe yazılır ve yeniden oynatılabilir.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**İfadeyi tırnak içine alın**, tercihen tek tırnakla: `>`, `<`, `!`, `(`, `{`, `#` ve boşlukların hepsi kabukta bir anlam taşır. Tırnaksız `6d10>=8f1`, `6d10` atar ve `=8f1` adında bir dosya yazar.

## Sonucu okumak

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| İşaret | Anlamı |
|---|---|
| `(2)` | elendi |
| `6!` | patladı: bu yüzden bir zar daha eklendi |
| `1→4` | yeniden atıldı ya da sınırlandı: 1'den 4'e |
| `6+6+2` | biriken zar: atışları toplandı |
| `6-1` | delen zar: bir eksik sayılır |
| `9✓` / `1✗` | bir başarı / bir başarısızlık |
| `purr:3` | bir paket etkisinin eklediği zar |
| `@STR(12)` | bir değişken ve değeri |
| `([1 2])[8 8 8]` | sayıyı belirlemek için atılan zarlar, sonra havuz |
| `(doubles, max)` | kurallar için bayraklar: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact okuduğu kanonik biçimi geri yazar (`4d6k3` → `4d6kh3`), böylece farklı bir okuma asla gözden kaçmaz.

## Gösterim

| Ne | Yazım | Örnek |
|---|---|---|
| Zarlar | `NdX`, `d%` (d100), `dF` (Fate), `d66` (onlar ve birler) | `3d6`, `4dF` |
| Özel ve paket zarları | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Tutma, eleme | `khN` (ya da `kN`), `klN`, `dlN` (ya da `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Patlama | en yüksek yüzde ya da bir koşulda `!`; `!!` biriktirir, `!p` deler, `!o` bir kez patlar | `d6!`, `5d10!>=9` |
| Yeniden atma | `r` koşulu tutturmayana kadar (varsayılan: en düşük yüz), `ro` bir kez | `2d6r1`, `d20ro<3` |
| Benzersiz | `u` tekrarları yeniden atar, `uo` bir kez | `4d6u` |
| Sınırlama | `minN`, `maxN` | `4d6min2` |
| Başarılar, başarısızlıklar | zarların hemen ardından bir koşul; başarısızlıklar için `f` | `6d10>=8f1`, `12d6>=5` |
| Çift, tek | çift ya da tek zarları sayar | `4d6even` |
| Kritikler | `cs`, `cf` (+ koşul) kritikleri işaretler; toplam değişmez | `d20cs>=19` |
| Setler | `mt` eşleşen setleri sayar (`mt3`: 3+ setler) | `10d10mt` |
| Fark | `ms`: toplam − N; `<=`/`<` ile: N − toplam | `d20ms15`, `d20ms<=@DEX` |
| Sıralama | `sa` (ya da `s`), `sd` | `5d6sd` |
| Gruplar | `{a, b}` + tutma/eleme/başarılar | `{d8, d6}kh1` |
| Matematik | `+ - * / // %`, parantezler | `(1d6+2)*2`, `3d6*10` |
| Karşılaştırmalar | `== <> < <= > >=`, boşluklarla | `2d6 >= 8` |
| Değişkenler | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Atılan sayılar | `(expr)dX` | `(2d4)d8` |
| Fonksiyonlar | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Zar basamakları | `step(die, n)`; `step.extended(…)` daha uzun d3–d30 zincirinde ilerler | `step(d6, 1)` → bir d8 |
| Etiketler | `tag:expr` bir parçayı adlandırır; `expr[label]` onu etiketler | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Tekrar | `N#expr` N kez ayrı ayrı atar | `6#4d6dl1` |
| Paket makroları | `pack.name(args)` | `hack.attack(d8, d6)` |

**Boşluklar önemlidir:** `2d6>=8` 8 ya da üstü gelen zarları sayar (d6'da hep 0), `2d6 >= 8` ise toplamı karşılaştırır. Bir başarı koşulu tutturulamayacaksa Didact uyarır.

**Sıra:** değiştiriciler nasıl yazılırsa yazılsın hep bu sırayla uygulanır: min/max → patlama → yeniden atma → benzersiz → tutma → eleme → başarılar ve başarısızlıklar → kritikler → setler → fark → sıralama.

## Değişkenler

- `--as <record>` kaydın sayısal alanlarını kullanıma açar: `@hp`, `@STR`, `@stats.str` ve mechanics bloğundaki `@<field>`.
- `--var DEX=12` bir değişken tanımlar ve tekrarlanabilir.
- `@sweeney.hp` başka bir kaydın alanını okur; kimlikler için `@{npc:tom.hp}` kullanın.
- Değişkenlerden hesaplanan zar sayısı atılmış gibi gösterilir: level 2 iken `(@level)d6` günlüğe `2d6 → [3 4] = 7` olarak geçer ve atışın JSON'u ifadeyi ve değişkenleri saklar. Atılan bir sayı kendi zarlarını gösterir: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Gerçek zarlar, geri alma, yeniden oynatma, olasılıklar

- `--got 6,3,4` gerçek zarların yüzlerini atıldıkları sırayla kaydeder. Patlamalar ve yeniden atmalar sıradaki yüzü alır.
- `didact report 'the tower falls' --of 'the tower'` burada atılmamış bir sonucu kaydeder: çekilen bir kart, bir blok kulesi, bir yazı tura. Bir atış numarası alır ve atış kaydına girer; bir oturum sırasında ayrıca bir sonuç olayıdır. `replay` onu atlar.
- `didact rolls` son atışları listeler.
- `didact undo --event r12 --reason "…"` bir atışı geri alınmış olarak işaretler. Atış günlükte kalır ve atış numaraları asla geriye sarılmaz.
- `didact replay` günlükteki her atışı yeniden çalıştırır ve her birinin birebir aynı çıktığını denetler. Her atış kendi tohumlu akışından çeker, bu yüzden bir atış asla diğerini kaydırmaz.
- `didact odds '2d6 >= 8'` kesin olasılıkları verir (icepool ile), kesin hesap yapılamıyorsa bir simülasyon.
- `--seed <text>` sabit bir akıştan çeker: aynı tohum aynı zarları verir.

## Lehçe notları

- `r` tekrar tekrar yeniden atar (Roll20). Foundry'nin `r`'si bir kez yeniden atar; Didact bunu `ro` diye yazar.
- `cs` ve `cf`, Roll20'deki gibi yalnızca kritikleri işaretler. Foundry'de başarıları sayarlar; burada bu bir koşuldur (`>=19`).
- Zarların hemen ardından gelen `d` en düşüğü ele demektir: `4d6d1`, `4d6dl1` ile aynıdır.
- `!=` kullanılamaz. 6'da patlamak için `!6`, "eşit değil" için `<>` yazın.
