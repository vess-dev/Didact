<!-- translated from bef7b2c650cb -->
# Memainkan sesi

Cara permainan berjalan melalui Didact: LLM menceritakan, dan Didact menyimpan setiap fakta, balingan dan perubahan.

## Sebelum sesi pertama

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Dunia mengekalkan sistem yang digunakan semasa ia dicipta, dan kempennya memainkan sistem itu: sistem lain dimainkan dalam dunianya sendiri. `didact campaign close` menutup kempen (dunianya kekal terbuka), dan `didact campaign open <id>` menyambungnya dari tempat ia ditinggalkan, termasuk sesinya.

`didact world delete <id>` dan `didact campaign delete <id>` memadam satu dunia atau kempen, dengan pratonton dahulu; `--yes` memadamnya, dan `didact undo` mengembalikan semuanya.

`session zero` menyenaraikan soalan yang perlu dipersetujui dengan pemain. Soalan daripada pek didahulukan. Pilihan sistem (varian dan peraturan pilihannya) termasuk di antaranya: peraturannya mengikut jawapan, dan ringkasan menyatakan maksud setiap pilihan yang diubah. Setiap taklimat membawa jawapannya.

## Satu sesi

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Giliran:** setiap mesej pemain membuka satu giliran (hook Claude Code memanggil `didact capture`, dan klien lain menggunakan `turn begin`). `didact undo --turn` membatalkan semua yang dilakukan untuk mesej itu: perubahan, peristiwa dan balingan. Transkrip tetap menyimpannya.
- **Lompat balik:** `didact undo --to e40` menarik balik semua yang berlaku selepas #e40, bermula daripada yang terbaharu (`--dry-run` menyenaraikannya): setiap perubahan dibuat asal dan setiap balingan ditanda sebagai dibuat asal. Tiada apa-apa yang dipadam: `redo`, atau lompat balik ke perubahan yang lebih kemudian, mengembalikannya.
- **Masa:** `didact time advance 1 watch` menghabiskan pemasa, menimbulkan peringatan dan menjalankan pencetus masa. `didact remind --list` menunjukkan peringatan yang akan datang, dan `didact remind --cancel 2` membatalkan satu. Kempen bermula pada permulaan kalendar, atau pada tarikh yang diberikan oleh `campaign new --date '4 July 1902'`, dan `didact time set '<date>'` mengubahnya sehingga sesi pertama.
- **Tempat:** `didact visit <place>` memindahkan kumpulan dan menandakan tempat itu sudah dilawati. `didact map` menunjukkan apa yang diketahui kumpulan, dan jalan keluar yang belum diterokai ditandakan `?`.
- **Pertarungan:** `didact combat start --party troll`, kemudian `combat next`, `combat hit freya troll weapon=d8` dan `combat end`. Petarung boleh datang dan pergi di tengah pertarungan: `didact combat join wolf-2` (dalam mod individu mereka membaling inisiatif) dan `didact combat leave troll --why fled`. Tiada giliran sesiapa yang dilangkau.
- **Barang:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (atau ke dalam peti, atau ke sesuatu tempat); `didact where rope` mencarinya. `inv add` menemui barang kompendium mengikut ID, nama atau alias.
- **Nota anda:** `didact about sweeney plan='…' doing='…' where='…'` menyimpan apa yang telah anda putuskan tentang sesiapa atau apa-apa sahaja. Pemain hanya nampak `looks`. `didact log … --about sweeney` meletakkan peristiwa pada rekod mereka (`--secret` jika pemain tidak nampak). `didact guide details` menerangkan lebih lanjut.
- **Dunia terus bergerak:** `didact faction turn`, serta jam: `didact track new 'The flood' --size 6`. Arahan yang hanya menerima satu jenis rekod mengambil nama yang turut dimiliki rekod lain sebagai jenis itu: `didact track roll draugr` membaling kumpulan dadu yang dinamakan sempena musuh (begitu juga `track tick` sesuatu penjejak, `quest done` sesuatu misi dan `visit` sesuatu tempat).

## Peramal, penjana dan watak

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

Tiada apa-apa yang dihasilkan oleh penjana atau penciptaan watak ditulis sehingga `commit`. Terangkan kehendak pemain dalam `--prefill`, dan prosedurnya mengisi selebihnya. Sesuatu soalan menyenaraikan maksud setiap pilihan apabila pek menyatakannya (`- Cutpurse: …`): beritahu pemain, supaya mereka memilih dengan mengetahui apa yang akan mereka dapat.

## Rahsia

Paparan selamat untuk pemain secara lalai: `show`, `find`, `sheet`, `map`, `brief`. Ia meninggalkan:
- rekod rahsia (`knowledge: secret`);
- bahagian `## Secrets` dan `## GM notes`;
- medan `secret: true`.

`--gm` menunjukkan semuanya. Apabila pemain mengetahui sesuatu:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` menulis apa yang diketahui pemain sebagai laman web kecil untuk dikongsi atau dibaca pada telefon: kumpulan, satu halaman bagi setiap rekod, jurnal dan peta. Ia sentiasa selamat untuk pemain, dan mengeksport semula ke folder itu akan mengemas kininya. `didact export --as lonelog` menulis jurnal dalam notasi Lonelog (`@ ? d: -> =>`, adegan sebagai `S1`, tag seperti `[N:Sweeney]`), juga selamat untuk pemain.

## Lore: apa yang timbul apabila sesuatu disebut

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Apa yang dikira:** setiap NPC, tempat, barang dan puak ialah kad yang dikunci dengan nama dan aliasnya. Entri lore mempunyai `keys`, dan keputusan peraturan timbul melalui peraturannya. Padanan dibuat pada perkataan penuh, dan bentuk jamak turut dikira ("wolves" sepadan dengan `wolf`).
- **Bila lore timbul:** hook Claude Code mengimbas setiap mesej pemain. `log`, `scene new` dan `show` juga membawa lore yang baru dicetuskan, dan satu entri tidak diulang untuk beberapa giliran.
- **Menala entri:** `--secondary` dengan `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (dalam giliran atau adegan), `--constant` (sentiasa dalam taklimat) dan `--no-recurse`.
- **Skop:** entri masuk ke kempen melainkan `--scope` menyebut world, system atau global. Imbasan hanya melihat kempen ini, dunianya, sistemnya dan global, tidak sekali-kali dunia lain. Entri yang lebih sempit dengan ID yang sama membayangi entri yang lebih luas.
- **Lorebook alat lain:** `didact lore import <file>` membaca World Info SillyTavern (termasuk KoboldAI), lorebook kad watak dan `.lorebook` NovelAI; `didact lore export --to <file>` menulis World Info. Kunci, logik, keutamaan, kebarangkalian, kumpulan dan pemasaan dibawa bersama.

## Mengubah cerita

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` mengubah fakta tetapi menyimpan nilai lamanya. Ia juga menandakan ringkasan yang menyebut Sweeney sebagai lapuk, dan `audit` menyenaraikannya.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` merekodkan keputusan peraturan. Keputusan itu kemudian muncul dalam `rules lookup` dan apabila peraturan itu dijalankan.
- `didact name npc` membaling nama baharu, tidak sekali-kali nama yang sudah digunakan oleh dunia. Sebelum anda mereka nama, semak dengan `didact names check <name>`. `didact names forget <name>` membebaskan nama itu semula.

## Pengemasan

- `didact history --clear` menunjukkan apa yang akan dibuang jika sejarah lama dikosongkan; `--yes` membuangnya buat selama-lamanya, termasuk rekod yang telah dipadam, dan buat asal, `diff`, `rewind` serta titik simpan yang lebih lama tidak lagi dapat mencapainya (`--before e120` menyimpan event itu dan yang selepasnya, `--rolls` turut membuang rekod dadu). Jalankan `didact snapshot` dahulu.
- `didact save --remove 'before the dragon'` mengalih keluar titik simpan; `didact undo` mengembalikannya.
- `didact transcript 3 --clear` memadam transkrip sesi 3 (`--clear --all`: transkrip setiap sesi). `didact undo` mengembalikannya, dan teksnya kekal dalam sejarah sehingga `history --clear`.
- `didact compendium remove <entry>` memadam entri yang anda tambah; rekod yang dijana daripadanya kekal.
- `didact snapshot --keep 3` memadam semua sandaran kecuali tiga yang terbaharu, dan `didact snapshot --remove <name>` memadam satu. Kedua-duanya tidak boleh dibuat asal.
- `didact session end` membuat sandaran pustaka dengan sendirinya (`snapshot-<time>-auto.zip`), dengan menyimpan lima yang terbaharu; `didact snapshot --list` menandakannya.
- `didact reset` menunjukkan apa yang akan hilang jika pustaka dikosongkan; `--yes` menjadikannya seperti baru dipasang: setiap dunia, kempen dan rekod, sejarah dan indeks carian hilang, dan perubahan seterusnya kembali menjadi #e1. Pustaka disandarkan dahulu (`…-before-reset.zip`), dan sandaran kekal, begitu juga pek yang dipasang melainkan dengan `--packs`. Untuk mencuba Didact pada kempen yang siap sedia, `didact sample` membina kempen contoh ke dalam pustaka kosong (`--home` memberinya folder sendiri), dan `didact serve --demo` menyajikannya dalam keadaan baharu.
- `didact snapshot --restore <name>` menunjukkan kandungan sesuatu sandaran di sebelah pustaka sekarang; `--yes` membuat sandaran pustaka seadanya (`…-before-restore.zip`), kemudian meletakkan sandaran itu sebagai gantinya. Nombor event dan balingan diteruskan. Buat asal tidak dapat membatalkan pemulihan: memulihkan sandaran keselamatan itu boleh.
