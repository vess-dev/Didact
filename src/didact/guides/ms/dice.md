<!-- translated from a81883b64f94 -->
# Dadu

Baling setiap dadu melalui Didact, dan jangan sekali-kali mereka-reka hasilnya. Setiap balingan mendapat ID (`#r12`), masuk ke dalam log, dan boleh dimainkan semula.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Letakkan ungkapan dalam tanda petik**, sebaiknya petik tunggal: `>`, `<`, `!`, `(`, `{`, `#` dan ruang semuanya bermakna bagi shell. Tanpa petik, `6d10>=8f1` membaling `6d10` dan menulis fail bernama `=8f1`.

## Membaca hasil

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Tanda | Maksud |
|---|---|
| `(2)` | dibuang |
| `6!` | meletup: dadu seterusnya ditambah kerananya |
| `1→4` | dibaling semula atau diapit daripada 1 kepada 4 |
| `6+6+2` | dadu bertimbun (compounding): balingannya dijumlahkan |
| `6-1` | dadu menembusi (penetrating): nilainya dikira kurang satu |
| `9✓` / `1✗` | kejayaan / kegagalan |
| `purr:3` | dadu yang ditambah oleh kesan pek |
| `@STR(12)` | pemboleh ubah dan nilainya |
| `([1 2])[8 8 8]` | dadu yang dibaling untuk bilangannya, kemudian longgokannya |
| `(doubles, max)` | penanda untuk peraturan: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact memaparkan semula bentuk kanonik yang dibacanya (`4d6k3` → `4d6kh3`), jadi bacaan yang berbeza tidak akan terlepas pandang.

## Tatatanda

| Apa | Tulis | Contoh |
|---|---|---|
| Dadu | `NdX`, `d%` (d100), `dF` (Fate), `d66` (puluh dan sa) | `3d6`, `4dF` |
| Dadu tersuai dan dadu pek | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Simpan, buang | `khN` (atau `kN`), `klN`, `dlN` (atau `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Meletup | `!` pada muka tertinggi, atau satu syarat; `!!` bertimbun, `!p` menembusi, `!o` meletup sekali | `d6!`, `5d10!>=9` |
| Baling semula | `r` sehingga tidak memenuhi syarat (lalai: muka terendah), `ro` sekali | `2d6r1`, `d20ro<3` |
| Unik | `u` membaling semula pendua, `uo` sekali | `4d6u` |
| Apit | `minN`, `maxN` | `4d6min2` |
| Kejayaan, kegagalan | syarat sejurus selepas dadu; `f` untuk kegagalan | `6d10>=8f1`, `12d6>=5` |
| Genap, ganjil | kira dadu genap atau ganjil | `4d6even` |
| Kritikal | `cs`, `cf` (+ syarat) menandakan kritikal; jumlahnya tidak berubah | `d20cs>=19` |
| Set | `mt` mengira set nombor sepadan (`mt3`: set 3+) | `10d10mt` |
| Margin | `ms`: jumlah − N; dengan `<=`/`<`: N − jumlah | `d20ms15`, `d20ms<=@DEX` |
| Isih | `sa` (atau `s`), `sd` | `5d6sd` |
| Kumpulan dadu | `{a, b}` + simpan/buang/kejayaan | `{d8, d6}kh1` |
| Matematik | `+ - * / // %`, kurungan | `(1d6+2)*2`, `3d6*10` |
| Perbandingan | `== <> < <= > >=`, dengan ruang | `2d6 >= 8` |
| Pemboleh ubah | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Bilangan yang dibaling | `(expr)dX` | `(2d4)d8` |
| Fungsi | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Tingkat dadu | `step(die, n)`; `step.extended(…)` menyusuri rantai d3–d30 yang lebih panjang | `step(d6, 1)` → d8 |
| Tag, label | `tag:expr` menamakan satu bahagian; `expr[label]` melabelkannya | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Ulang | `N#expr` membaling N kali secara berasingan | `6#4d6dl1` |
| Makro pek | `pack.name(args)` | `hack.attack(d8, d6)` |

**Ruang itu penting:** `2d6>=8` mengira dadu yang menunjukkan 8 atau lebih (sentiasa 0 pada d6), manakala `2d6 >= 8` membandingkan jumlahnya. Didact memberi amaran apabila syarat kejayaan tidak mungkin dipenuhi.

**Susunan:** pengubah sentiasa dikenakan mengikut susunan ini, walau bagaimana pun ia ditulis: min/max → meletup → baling semula → unik → simpan → buang → kejayaan dan kegagalan → kritikal → set → margin → isih.

## Pemboleh ubah

- `--as <record>` menyediakan medan berangka rekod itu: `@hp`, `@STR`, `@stats.str`, dan `@<field>` daripada blok mekaniknya.
- `--var DEX=12` menetapkan satu pemboleh ubah, dan boleh diulang.
- `@sweeney.hp` membaca medan rekod lain; gunakan `@{npc:tom.hp}` untuk ID.
- Bilangan dadu yang dikira daripada pemboleh ubah dipaparkan seperti dibaling: `(@level)d6` dengan level 2 dilog sebagai `2d6 → [3 4] = 7`, dan JSON balingan itu menyimpan ungkapan dan pemboleh ubahnya. Bilangan yang dibaling menunjukkan dadunya sendiri: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dadu fizikal, buat asal, main semula, peluang

- `--got 6,3,4` merekodkan muka dadu sebenar, mengikut susunan ia dibaling. Letupan dan balingan semula mengambil muka seterusnya.
- `didact report 'the tower falls' --of 'the tower'` merekodkan hasil yang tidak dibaling di sini: kad yang dicabut, menara blok, syiling. Ia mendapat nombor balingan dan masuk ke log balingan, dan semasa sesi ia juga peristiwa hasil. `replay` melangkauinya.
- `didact rolls` menyenaraikan balingan terkini.
- `didact undo --event r12 --reason "…"` menandakan balingan sebagai dibuat asal. Ia kekal dalam log, dan nombor balingan tidak pernah berundur.
- `didact replay` menjalankan semula setiap balingan yang dilog dan menyemak bahawa setiap satu menghasilkan semula dengan tepat. Setiap balingan mengambil daripada alirannya sendiri yang bersemai (seeded), jadi satu balingan tidak pernah menganjakkan balingan lain.
- `didact odds '2d6 >= 8'` memberikan kebarangkalian tepat (melalui icepool), atau simulasi apabila pengiraan tepat tidak tersedia.
- `--seed <text>` mengambil daripada aliran tetap: semaian yang sama memberikan dadu yang sama.

## Nota dialek

- `r` membaling semula berulang kali (Roll20). `r` dalam Foundry membaling semula sekali, yang ditulis `ro` dalam Didact.
- `cs` dan `cf` hanya menandakan kritikal, seperti dalam Roll20. Dalam Foundry ia mengira kejayaan; di sini itu ialah syarat (`>=19`).
- `d` sejurus selepas dadu bermaksud buang yang terendah: `4d6d1` sama dengan `4d6dl1`.
- `!=` tidak dibenarkan. Tulis `!6` untuk meletup pada 6, atau `<>` untuk "tidak sama dengan".
