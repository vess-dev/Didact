<!-- translated from 7fe144069f94 -->
# Detail, kronik, dan lokasi

Catatan GM yang menjaga permainan tetap konsisten: seperti apa rupa sesuatu dan apa yang diinginkannya, apa yang sedang dilakukannya dan rencananya berikutnya, apa yang terjadi padanya, dan di mana semuanya berada.

## Detail

Catatan singkat bernama pada entri apa pun: orang, barang, tempat, faksi.

```
didact about sweeney looks='tall, one eye clouded' personality='jovial, greedy'
didact about sweeney wants='buy back the mill' plan='sell the route to the raiders'
didact about sweeney doing='whittling by the fire' where='the back room of the inn'
didact about item:old-sword history='forged for the last king' powers='cuts through wards'
didact about loc:the-ford state='flooded' secret='a drowned shrine under the stones'
didact about sweeney thoughts='built to foreshadow the betrayal; pay it off at the ford'
didact about sweeney                  # the notes, what's still open, chronicle, whereabouts
didact about sweeney --clear doing    # or doing='' 
```

- **Nama.** Nama yang disarankan bergantung pada jenis entrinya, dan nama satu kata apa pun bisa dipakai:
  - orang: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - barang: looks, history, where, powers, secret, thoughts;
  - tempat: looks, state, history, secret, thoughts;
  - faksi: wants, plan, state, history, secret, thoughts.

  Paket bisa menyarankan namanya sendiri per tipe (`details: [mood, grudge]` dalam skema).
- **Siapa melihat apa.** Pemain hanya melihat `looks`: `show` dan `find` tidak menampilkan sisanya, dan `--gm` menampilkan semuanya. Saat pemain mengetahui salah satunya, `didact reveal sweeney plan` memindahkannya ke teks entri di bawah `## Revealed`.
- **`thoughts`** milik Anda: mengapa Anda membuatnya, ke mana arahnya, apa yang perlu dituntaskan nanti.
- **Jaga tetap terbaru.** Anda tidak perlu mencatat semuanya. Tetapi saat Anda memutuskan sesuatu (rencana, dendam, ke mana seseorang pergi), tuliskan, supaya adegan berikutnya, atau sesi berikutnya, tetap setia padanya.

## Kronik: apa yang terjadi pada siapa

Peristiwa jurnal bisa menyebut entri yang terkait dengannya. Peristiwa itu lalu muncul di setiap entri tersebut.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` dan `about` mencantumkan kronik sebuah entri: apa yang dilakukannya, dan apa yang dilakukan terhadapnya.
- **Peristiwa rahasia** terjadi di luar pengetahuan pemain. Peristiwa ini hanya muncul di tampilan GM (`session show --gm`, `about`, `brief --gm`), dan tidak pernah di `export --as story`.
- Gunakan `--about` untuk apa pun yang mengubah seseorang atau sesuatu: pengkhianatan, utang, kematian, hadiah, janji yang diingkari.
- **Memperbaiki peristiwa:** `didact beat edit S1.4 --about tom` menaruhnya di kronik Tom (atau `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), dan `didact beat rm S1.4` menghapusnya. ID-nya ada di `session show`, dan keduanya bisa diurungkan.
- **Saat ID berubah:** `merge` atau slug baru membawa setiap rujukan bersamanya: tautan, detail, entri yang menjadi subjek peristiwa, kelompok, pertarungan, dan lokasi kelompok. Saat entri dihapus dengan `rm`, entri itu juga keluar dari kelompok atau pertarungan mana pun. `merge` lintas tipe menyimpan apa yang punya kolom di lembar entri yang bertahan, dan menyebut apa yang ditinggalkannya.

## Lokasi: di mana segala sesuatu berada

Barang tersimpan di inventaris, dan apa pun bisa menyimpannya: karakter, tempat, peti.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Selama sesi, memindahkan barang mencatat peristiwa tentang pemberi dan penerimanya ("Sword: Freya → Chest"). Kronik mereka lalu menunjukkan ke mana barang-barang pergi.
- **Orang dan monster** adalah pengunjung sebuah tempat, bukan isinya: catat lokasi mereka di detail `where`.

## Dalam adegan dan pertarungan

- **`combat status --gm`** menampilkan `where`, `doing`, dan `plan` setiap petarung. Perbarui seiring jalannya pertarungan: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (pengarahan pembuka sesi) mencantumkan apa saja yang sedang berperan (tempatnya, para petarung, siapa pun yang menjadi subjek peristiwa adegan ini, dan kelompok) beserta where, doing, plan, dan state. Pengarahan ini juga mencantumkan peristiwa terbaru di luar layar.
