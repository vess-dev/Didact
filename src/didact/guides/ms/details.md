<!-- translated from 7fe144069f94 -->
# Butiran, kronikel dan lokasi

Nota GM yang memastikan permainan kekal konsisten: rupa sesuatu dan apa yang dikehendakinya, apa yang sedang dilakukannya dan rancangannya seterusnya, apa yang berlaku kepadanya, dan di mana segala-galanya berada.

## Butiran

Nota ringkas bernama pada mana-mana rekod: orang, barang, tempat, puak.

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

- **Nama.** Nama yang dicadangkan bergantung pada jenis rekod, dan sebarang nama satu perkataan boleh digunakan:
  - orang: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - barang: looks, history, where, powers, secret, thoughts;
  - tempat: looks, state, history, secret, thoughts;
  - puak: wants, plan, state, history, secret, thoughts.

  Pek boleh mencadangkan namanya sendiri bagi setiap jenis (`details: [mood, grudge]` dalam skema).
- **Siapa nampak apa.** Pemain hanya nampak `looks`: `show` dan `find` meninggalkan yang lain, dan `--gm` menunjukkan semuanya. Apabila pemain mengetahui salah satunya, `didact reveal sweeney plan` memindahkannya ke dalam teks rekod di bawah `## Revealed`.
- **`thoughts`** adalah milik anda: sebab anda menciptanya, ke mana ia boleh membawa, apa yang perlu dilunaskan kemudian.
- **Pastikan sentiasa terkini.** Anda tidak perlu mencatat semuanya. Tetapi apabila anda memutuskan sesuatu (rancangan, dendam, ke mana seseorang pergi), tuliskannya, supaya adegan seterusnya, atau sesi seterusnya, kekal setia kepadanya.

## Kronikel: apa yang berlaku kepada siapa

Peristiwa jurnal boleh menamakan rekod yang berkaitan dengannya. Peristiwa itu kemudian dipaparkan pada setiap rekod tersebut.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` dan `about` menyenaraikan kronikel sesebuah rekod: apa yang dilakukannya, dan apa yang dilakukan terhadapnya.
- **Peristiwa rahsia** berlaku di luar pengetahuan pemain. Ia hanya muncul dalam paparan GM (`session show --gm`, `about`, `brief --gm`), dan tidak sekali-kali dalam `export --as story`.
- Gunakan `--about` untuk apa-apa sahaja yang mengubah seseorang atau sesuatu: pengkhianatan, hutang, kematian, hadiah, janji yang dimungkiri.
- **Membetulkan peristiwa:** `didact beat edit S1.4 --about tom` meletakkannya pada kronikel Tom (atau `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), dan `didact beat rm S1.4` mengalih keluarnya. ID-nya ada dalam `session show`, dan kedua-duanya boleh dibuat asal.
- **Apabila ID berubah:** `merge` atau slug baharu membawa setiap rujukan bersamanya: pautan, butiran, rekod yang menjadi subjek peristiwa, kumpulan, pertarungan dan lokasi kumpulan. Apabila rekod dipadam dengan `rm`, ia turut keluar daripada mana-mana kumpulan atau pertarungan. `merge` merentas jenis mengekalkan apa yang ada medannya pada helaian rekod yang kekal, dan menyatakan apa yang ditinggalkannya.

## Lokasi: di mana segala-galanya berada

Barang disimpan dalam inventori, dan apa-apa sahaja boleh menyimpannya: watak, tempat, peti.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Semasa sesi, memindahkan barang mencatat peristiwa tentang pemberi dan penerimanya ("Sword: Freya → Chest"). Kronikel mereka kemudian menunjukkan ke mana barang-barang itu pergi.
- **Orang dan raksasa** ialah pelawat sesuatu tempat, bukan kandungannya: simpan lokasi mereka dalam butiran `where`.

## Dalam adegan dan pertarungan

- **`combat status --gm`** menunjukkan `where`, `doing` dan `plan` setiap petarung. Kemas kininya mengikut perjalanan pertarungan: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (taklimat yang memulakan sesi) menyenaraikan apa yang sedang terlibat (tempat itu, para petarung, sesiapa yang menjadi subjek peristiwa adegan ini, dan kumpulan) berserta where, doing, plan dan state. Ia juga menyenaraikan peristiwa terkini di luar tabir.
