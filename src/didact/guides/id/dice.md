<!-- translated from a81883b64f94 -->
# Dadu

Lempar setiap dadu lewat Didact, dan jangan pernah mengarang hasilnya. Setiap lemparan mendapat ID (`#r12`), masuk ke log, dan bisa diputar ulang.

```
didact roll 4d6kh3                          #r12 4d6kh3 → [6 5 3 (2)] = 14
didact roll 'd20 <= @STR' --as freya        #r13 1d20 <= @STR → [7] <= @STR(12) = true
didact roll '6d10>=8f1'                     #r14 6d10>=8f1 → [9✓ 8✓ 3 1✗ 10✓ 4] = 2 successes
didact roll '{d8, d6}kh1' --reason "Freya attacks with two daggers"
```

**Beri tanda kutip pada ekspresi**, sebaiknya kutip tunggal: `>`, `<`, `!`, `(`, `{`, `#`, dan spasi semuanya punya arti bagi shell. Tanpa kutip, `6d10>=8f1` melempar `6d10` dan menulis berkas bernama `=8f1`.

## Membaca hasil

`#r12 4d6kh3 → [6 5 3 (2)] = 14 (doubles) — reason`

| Tanda | Arti |
|---|---|
| `(2)` | dibuang |
| `6!` | meledak: dadu berikutnya ditambahkan karenanya |
| `1→4` | dilempar ulang atau dibatasi dari 1 menjadi 4 |
| `6+6+2` | dadu bertumpuk (compounding): lemparannya dijumlahkan |
| `6-1` | dadu menembus (penetrating): nilainya dihitung kurang satu |
| `9✓` / `1✗` | sukses / gagal |
| `purr:3` | dadu yang ditambahkan oleh efek paket |
| `@STR(12)` | variabel dan nilainya |
| `([1 2])[8 8 8]` | dadu yang dilempar untuk jumlahnya, lalu kumpulannya |
| `(doubles, max)` | penanda untuk aturan: `doubles`, `all-same`, `max`, `min`, `exploded`, `rerolled`, `crit`, `fumble`, `capped` |

Didact menampilkan kembali bentuk kanonis yang dibacanya (`4d6k3` → `4d6kh3`), jadi pembacaan yang berbeda tidak akan luput dari perhatian.

## Notasi

| Apa | Tulis | Contoh |
|---|---|---|
| Dadu | `NdX`, `d%` (d100), `dF` (Fate), `d66` (puluhan dan satuan) | `3d6`, `4dF` |
| Dadu khusus dan dadu paket | `d{faces}`, `d[name]` | `d{0,0,1,1,2,3}`, `2d[boost]` |
| Simpan, buang | `khN` (atau `kN`), `klN`, `dlN` (atau `dN`), `dhN` | `4d6kh3`, `2d20kl1` |
| Meledak | `!` pada sisi tertinggi, atau sebuah kondisi; `!!` bertumpuk, `!p` menembus, `!o` meledak sekali | `d6!`, `5d10!>=9` |
| Lempar ulang | `r` sampai tidak memenuhi kondisi (bawaan: sisi terendah), `ro` sekali | `2d6r1`, `d20ro<3` |
| Unik | `u` melempar ulang duplikat, `uo` sekali | `4d6u` |
| Batasi | `minN`, `maxN` | `4d6min2` |
| Sukses, gagal | kondisi langsung setelah dadu; `f` untuk gagal | `6d10>=8f1`, `12d6>=5` |
| Genap, ganjil | hitung dadu genap atau ganjil | `4d6even` |
| Kritis | `cs`, `cf` (+ kondisi) menandai kritis; totalnya tidak berubah | `d20cs>=19` |
| Set | `mt` menghitung set angka kembar (`mt3`: set berisi 3+) | `10d10mt` |
| Selisih | `ms`: total − N; dengan `<=`/`<`: N − total | `d20ms15`, `d20ms<=@DEX` |
| Urutkan | `sa` (atau `s`), `sd` | `5d6sd` |
| Grup | `{a, b}` + simpan/buang/sukses | `{d8, d6}kh1` |
| Matematika | `+ - * / // %`, tanda kurung | `(1d6+2)*2`, `3d6*10` |
| Perbandingan | `== <> < <= > >=`, dengan spasi | `2d6 >= 8` |
| Variabel | `@name`, `@record.field`, `@{npc:tom.hp}` | `d20 <= @STR`, `(@level)d6` |
| Jumlah hasil lemparan | `(expr)dX` | `(2d4)d8` |
| Fungsi | `min max abs floor ceil round`; `if(c, a, b)`; `default(@x, 0)` | `max(d6, d8)` |
| Tingkat dadu | `step(die, n)`; `step.extended(…)` menyusuri rantai d3–d30 yang lebih panjang | `step(d6, 1)` → d8 |
| Tag, label | `tag:expr` menamai sebuah bagian; `expr[label]` melabelinya | `hope:1d12 + fear:1d12`, `d8[fire]` |
| Ulangi | `N#expr` melempar N kali secara terpisah | `6#4d6dl1` |
| Makro paket | `pack.name(args)` | `hack.attack(d8, d6)` |

**Spasi itu penting:** `2d6>=8` menghitung dadu yang menunjukkan 8 atau lebih (selalu 0 pada d6), sedangkan `2d6 >= 8` membandingkan totalnya. Didact memperingatkan Anda saat kondisi sukses tidak mungkin terpenuhi.

**Urutan:** pengubah selalu diterapkan dalam urutan ini, bagaimanapun cara menulisnya: min/max → meledak → lempar ulang → unik → simpan → buang → sukses dan gagal → kritis → set → selisih → urutkan.

## Variabel

- `--as <record>` menyediakan kolom numerik entri tersebut: `@hp`, `@STR`, `@stats.str`, dan `@<field>` dari blok mekanikanya.
- `--var DEX=12` menetapkan satu variabel, dan bisa diulang.
- `@sweeney.hp` membaca kolom entri lain; gunakan `@{npc:tom.hp}` untuk ID.
- Jumlah dadu yang dihitung dari variabel ditampilkan seperti hasil lemparan: `(@level)d6` dengan level 2 dicatat sebagai `2d6 → [3 4] = 7`, dan JSON lemparannya menyimpan ekspresi dan variabelnya. Jumlah hasil lemparan menampilkan dadunya sendiri: `(2d4)d8 → ([1 4])[4 4 2 1 7]`.

## Dadu fisik, urungkan, putar ulang, peluang

- `--got 6,3,4` mencatat sisi dadu sungguhan, sesuai urutan lemparannya. Ledakan dan lempar ulang mengambil sisi berikutnya.
- `didact report 'the tower falls' --of 'the tower'` mencatat hasil yang tidak dilempar di sini: kartu yang ditarik, menara balok, koin. Hasil ini mendapat nomor lemparan dan masuk ke log lemparan, dan selama sesi juga menjadi peristiwa hasil. `replay` melewatinya.
- `didact rolls` mencantumkan lemparan terbaru.
- `didact undo --event r12 --reason "…"` menandai lemparan sebagai diurungkan. Lemparan itu tetap di log, dan nomor lemparan tidak pernah mundur.
- `didact replay` menjalankan ulang setiap lemparan yang tercatat dan memeriksa bahwa masing-masing menghasilkan hal yang persis sama. Setiap lemparan mengambil dari alirannya sendiri yang ber-seed, jadi satu lemparan tidak pernah menggeser lemparan lain.
- `didact odds '2d6 >= 8'` memberikan probabilitas pasti (lewat icepool), atau simulasi jika perhitungan pasti tidak tersedia.
- `--seed <text>` mengambil dari aliran tetap: seed yang sama memberikan dadu yang sama.

## Catatan dialek

- `r` melempar ulang berkali-kali (Roll20). `r` di Foundry melempar ulang sekali, yang di Didact ditulis `ro`.
- `cs` dan `cf` hanya menandai kritis, seperti di Roll20. Di Foundry keduanya menghitung sukses; di sini itu adalah kondisi (`>=19`).
- `d` langsung setelah dadu berarti buang terendah: `4d6d1` sama dengan `4d6dl1`.
- `!=` tidak diperbolehkan. Tulis `!6` untuk meledak pada 6, atau `<>` untuk "tidak sama dengan".
