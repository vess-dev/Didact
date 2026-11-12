<!-- translated from bef7b2c650cb -->
# Memainkan sesi

Cara permainan berjalan lewat Didact: LLM bernarasi, dan Didact menyimpan setiap fakta, lemparan, dan perubahan.

## Sebelum sesi pertama

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Dunia mempertahankan sistem yang dipakainya saat dibuat, dan kampanyenya memainkan sistem itu: sistem lain dimainkan di dunianya sendiri. `didact campaign close` menutup kampanye (dunianya tetap terbuka), dan `didact campaign open <id>` melanjutkannya dari titik terakhir, termasuk sesinya.

`didact world delete <id>` dan `didact campaign delete <id>` menghapus satu dunia atau kampanye, dengan pratinjau lebih dulu; `--yes` menghapusnya, dan `didact undo` mengembalikan semuanya.

`session zero` mencantumkan pertanyaan yang perlu disepakati dengan pemain. Pertanyaan dari paket muncul lebih dulu. Opsi sistem (varian dan aturan opsionalnya) termasuk di antaranya: aturannya mengikuti jawaban, dan ringkasan menyebutkan arti setiap opsi yang diubah. Setiap pengarahan memuat jawabannya.

## Sebuah sesi

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Giliran:** setiap pesan pemain membuka satu giliran (hook Claude Code memanggil `didact capture`, dan klien lain memakai `turn begin`). `didact undo --turn` membatalkan semua yang dilakukan untuk pesan itu: perubahan, peristiwa, dan lemparan. Transkrip tetap menyimpannya.
- **Lompat kembali:** `didact undo --to e40` membatalkan semua yang terjadi setelah #e40, mulai dari yang terbaru (`--dry-run` menampilkan daftarnya): setiap perubahan diurungkan dan setiap lemparan ditandai diurungkan. Tidak ada yang dihapus: `redo`, atau lompat kembali ke perubahan yang lebih baru, mengembalikannya.
- **Waktu:** `didact time advance 1 watch` menghabiskan timer, memunculkan pengingat, dan menjalankan pemicu waktu. `didact remind --list` menampilkan pengingat yang akan datang, dan `didact remind --cancel 2` membatalkan satu. Kampanye dimulai pada awal kalender, atau pada tanggal yang diberikan `campaign new --date '4 July 1902'`, dan `didact time set '<date>'` mengubahnya sampai sesi pertama.
- **Tempat:** `didact visit <place>` memindahkan kelompok dan menandai tempat itu sudah dikunjungi. `didact map` menampilkan apa yang diketahui kelompok, dan jalan keluar yang belum dijelajahi ditandai `?`.
- **Pertarungan:** `didact combat start --party troll`, lalu `combat next`, `combat hit freya troll weapon=d8`, dan `combat end`. Petarung bisa datang dan pergi di tengah pertarungan: `didact combat join wolf-2` (dalam mode individual mereka melempar inisiatif) dan `didact combat leave troll --why fled`. Tidak ada giliran yang terlewat.
- **Barang:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (atau ke dalam peti, atau ke sebuah tempat); `didact where rope` menemukannya. `inv add` menemukan barang kompendium lewat ID-nya, namanya, atau alias.
- **Catatan Anda:** `didact about sweeney plan='…' doing='…' where='…'` menyimpan apa yang sudah Anda putuskan tentang siapa pun atau apa pun. Pemain hanya melihat `looks`. `didact log … --about sweeney` menaruh peristiwa di entri mereka (`--secret` jika pemain tidak melihatnya). `didact guide details` menjelaskan lebih lanjut.
- **Dunia terus bergerak:** `didact faction turn`, plus jam: `didact track new 'The flood' --size 6`. Perintah yang hanya menerima satu jenis entri mengambil nama yang juga dimiliki entri lain sebagai jenis itu: `didact track roll draugr` melempar pool yang dinamai seperti musuh (begitu juga `track tick` sebuah pelacak, `quest done` sebuah misi, dan `visit` sebuah tempat).

## Orakel, generator, dan karakter

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

Tidak ada hasil generator atau pembuatan karakter yang ditulis sebelum `commit`. Jelaskan keinginan pemain di `--prefill`, dan prosedurnya mengisi sisanya. Sebuah pertanyaan mencantumkan arti setiap pilihan jika paketnya menyebutkannya (`- Cutpurse: …`): sampaikan kepada pemain, agar mereka memilih dengan mengetahui apa yang akan mereka dapatkan.

## Rahasia

Tampilan secara bawaan aman untuk pemain: `show`, `find`, `sheet`, `map`, `brief`. Tampilan ini tidak menyertakan:
- entri rahasia (`knowledge: secret`);
- bagian `## Secrets` dan `## GM notes`;
- kolom `secret: true`.

`--gm` menampilkan semuanya. Saat pemain mengetahui sesuatu:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` menulis apa yang diketahui pemain sebagai situs web kecil untuk dibagikan atau dibaca di ponsel: kelompok, satu halaman per entri, jurnal, dan peta. Hasilnya selalu aman untuk pemain, dan mengekspor lagi ke folder itu akan memperbaruinya. `didact export --as lonelog` menulis jurnal dalam notasi Lonelog (`@ ? d: -> =>`, adegan sebagai `S1`, tag seperti `[N:Sweeney]`), juga aman untuk pemain.

## Lore: apa yang muncul saat sesuatu disebut

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Apa yang dihitung:** setiap NPC, tempat, barang, dan faksi adalah kartu dengan kunci nama dan aliasnya. Entri lore punya `keys`, dan keputusan aturan muncul lewat aturannya. Pencocokan dilakukan pada kata utuh, dan bentuk jamak ikut dihitung ("wolves" cocok dengan `wolf`).
- **Kapan lore muncul:** hook Claude Code memindai setiap pesan pemain. `log`, `scene new`, dan `show` juga membawa lore yang baru terpicu, dan satu entri tidak diulang selama beberapa giliran.
- **Menyetel entri:** `--secondary` dengan `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (dalam giliran atau adegan), `--constant` (selalu ada di pengarahan), dan `--no-recurse`.
- **Cakupan:** entri masuk ke kampanye kecuali `--scope` menyebut world, system, atau global. Pemindaian hanya melihat kampanye ini, dunianya, sistemnya, dan global, tidak pernah dunia lain. Entri yang lebih sempit dengan ID yang sama menutupi entri yang lebih luas.
- **Lorebook dari alat lain:** `didact lore import <file>` membaca World Info SillyTavern (juga milik KoboldAI), lorebook kartu karakter, dan `.lorebook` NovelAI; `didact lore export --to <file>` menulis World Info. Kunci, logika, prioritas, probabilitas, grup, dan pengaturan waktu ikut dibawa.

## Mengubah cerita

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` mengubah faktanya tetapi menyimpan nilai lamanya. Perintah ini juga menandai ringkasan yang menyebut Sweeney sebagai usang, dan `audit` mencantumkannya.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` mencatat keputusan aturan. Keputusan itu lalu muncul di `rules lookup` dan saat aturan tersebut dijalankan.
- `didact name npc` melempar nama baru, tidak pernah nama yang sudah dipakai dunia. Sebelum mengarang nama, periksa dengan `didact names check <name>`. `didact names forget <name>` membebaskan nama itu lagi.

## Perawatan

- `didact history --clear` menampilkan apa yang akan dibuang jika riwayat lama dihapus; `--yes` membuangnya untuk selamanya, termasuk entri yang sudah dihapus, dan urungkan, `diff`, `rewind`, serta titik simpan yang lebih lama tidak bisa menjangkaunya lagi (`--before e120` menyimpan event itu dan yang sesudahnya, `--rolls` ikut membuang catatan dadu). Jalankan `didact snapshot` lebih dulu.
- `didact save --remove 'before the dragon'` menghapus titik simpan; `didact undo` mengembalikannya.
- `didact transcript 3 --clear` menghapus transkrip sesi 3 (`--clear --all`: transkrip semua sesi). `didact undo` mengembalikannya, dan teksnya tetap ada di riwayat sampai `history --clear`.
- `didact compendium remove <entry>` menghapus entri yang Anda tambahkan; entri yang dibuat darinya tetap ada.
- `didact snapshot --keep 3` menghapus semua cadangan kecuali tiga yang terbaru, dan `didact snapshot --remove <name>` menghapus satu. Keduanya tidak bisa diurungkan.
- `didact session end` mencadangkan pustaka dengan sendirinya (`snapshot-<time>-auto.zip`), dengan menyimpan lima yang terbaru; `didact snapshot --list` menandainya.
- `didact reset` menampilkan apa yang akan hilang jika pustaka dikosongkan; `--yes` membuatnya seperti baru dipasang: setiap dunia, kampanye, dan entri, riwayat, serta indeks pencarian hilang, dan perubahan berikutnya kembali menjadi #e1. Pustaka dicadangkan lebih dulu (`…-before-reset.zip`), dan cadangan tetap ada, begitu pula paket yang terpasang kecuali dengan `--packs`. Untuk mencoba Didact pada kampanye siap pakai, `didact sample` membangun kampanye contoh ke dalam pustaka kosong (`--home` memberinya folder sendiri), dan `didact serve --demo` menyajikannya dalam keadaan baru.
- `didact snapshot --restore <name>` menampilkan isi sebuah cadangan berdampingan dengan pustaka saat ini; `--yes` mencadangkan pustaka apa adanya (`…-before-restore.zip`), lalu menaruh cadangan itu sebagai gantinya. Nomor event dan lemparan berlanjut. Urungkan tidak bisa membatalkan pemulihan: memulihkan cadangan pengaman itu bisa.
