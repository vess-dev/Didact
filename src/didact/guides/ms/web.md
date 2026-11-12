<!-- translated from 5a088227a31a -->
# Aplikasi pelayar

`didact serve` membuka pustaka anda dalam pelayar web: terokai dan sunting rekod, lihat pautan antara rekod dalam graf, baca jurnal, jalankan peraturan dan jadual, dan gunakan setiap arahan melalui borang.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Ia berfungsi di luar talian: fon dan ikonnya disertakan bersama Didact.

**Mod demo.** `--demo` menyajikan kempen contoh (`didact sample`: sebuah lembah sungai, satu watak pemain, orang dengan nota GM, tempat dan laluan, satu misi, satu jam, dan sesi yang sedang berjalan dengan pertarungan) daripada pustakanya sendiri, di sebelah folder cache Didact. Semua pek yang disertakan bersama Didact dipasang di sana. Ia dibina semula setiap kali `--demo` dimulakan, jadi cubalah apa-apa sahaja: pustaka anda sendiri tidak disentuh.

## Pilihan

| Pilihan | Lalai | Fungsinya |
|---|---|---|
| `--port <n>` | 8765 | port yang didengari |
| `--host <address>` | 127.0.0.1 | alamat yang didengari: mesin ini sahaja |
| `--open` | mati | membuka aplikasi dalam tab pelayar |
| `--gm` | mati | bermula dengan paparan GM dihidupkan |
| `--demo` | mati | menyajikan kempen contoh baharu, bukan pustaka anda |

Pilihan global `--home`, `--world` dan `--campaign` terpakai pada semua yang dilakukan aplikasi. Membuka dunia atau kempen lain di halaman Pustaka akan bertukar kepadanya, seperti `didact world use` dan `didact campaign open`, dan Tutup menutup kempen yang terbuka (`didact campaign close`).

## Kandungannya

- **Gambaran keseluruhan:** taklimat (dunia, kempen, sesi, adegan, kumpulan, apa yang perlu diuruskan), tindakan pantas (baling dadu, tanya peramal dengan peluang yang diketahuinya, catat peristiwa, mula atau tamatkan sesi, rekod baharu) dan perubahan terkini.
- **Status:** keadaan permainan sepintas lalu: sesi dan adegan, masa dan peringatan yang akan datang, nombor setiap ahli kumpulan dan apa yang dibawanya, pertarungan (giliran siapa, keadaan), misi dan penjejak yang masih terbuka, serta lokasi kumpulan dan jalan keluarnya. Nombornya boleh diubah terus di situ: − dan + pada stat, tambah satu pada penjejak, guna atau buang barang, tambah barang, selesaikan misi, majukan masa (nombor, dan unit yang diketahui kalendar: jam, syif jaga, hari, …), tetapkan peringatan (sekali, atau berkala) dan batalkan satu.
- **Rekod:** setiap rekod, dikumpulkan mengikut jenis, dengan kotak penapis dan pilihan semua, dunia atau kempen. Halaman sesebuah rekod menunjukkan helaian, penerangan, butiran, medan, kandungan, pautan dua hala, kronikel dan sejarahnya, dengan borang untuk menukar setiap satu, serta untuk mengarkibkan atau memadamnya. Watak yang sistemnya mempunyai naik tahap mempunyai butang Level up (`char advance`): draf yang menunjukkan apa yang berubah, sebelum dan selepas, sehingga ia disahkan.
- **Draf:** penciptaan watak dan penjana, satu langkah pada satu masa. Cipta watak (langkah demi langkah atau secara rawak, dengan memilih jenisnya apabila sistem mempunyai beberapa: watak pemain, orang upahan, …) dan Jana… terdapat di halaman Rekod; draf yang menunggu disenaraikan di situ dan dalam Gambaran keseluruhan. Halaman sesebuah draf menunjukkan kandungannya setakat ini (entiti dan medannya, peta yang dilukis penjana, balingan, soalan panduan buku) dan soalan yang sedang ditunggunya. Setiap pilihan ialah butang yang menyatakan maksudnya apabila pek menyatakannya (apa yang diberikan oleh sesuatu latar belakang, apa yang dilakukan oleh sesuatu bakat); memilih beberapa ialah kotak untuk ditanda bagi setiap satu; skor yang dibeli dengan bajet ialah nombor yang mengira mata semasa anda mengubahnya; nama atau jawapan terbuka lain boleh ditaip; dan Biar dadu yang menentukan membaling untuk pilihan itu sahaja (`char roll c3 --one`). Kembali menarik balik langkah terakhir, jadi soalannya muncul semula (`char back c3`: balingan yang dibuatnya ditanda sebagai dibuat asal, dan Buat asal mengembalikan langkah itu). Kemudian Baling selebihnya, Sunting, Buang… (ia bertanya dahulu) dan Sahkan, yang membuka rekod watak baharu, atau menyenaraikan apa yang dijana oleh penjana. Draf penjana ialah milik GM: paparan pemain hanya menunjukkan bahawa ia wujud.
- **Graf:** rekod sebagai nod dan pautan sebagai sisi. Seret nod, seret latar belakang untuk mengalih, zum dengan roda tetikus; halakan tetikus untuk menyerlahkan jiran sesebuah rekod; klik untuk membukanya. Butang Graf di halaman rekod hanya menunjukkan kawasan sekitarnya.
  - **Peta** (suis di atas graf, atau Buka peta di Status): tempat yang diketahui kumpulan, laluan di antaranya (berlabel road, trail, …), wilayah tempat setiap satunya terletak (garis putus-putus), dan lokasi kumpulan. Laluan ke tempat yang belum ditemui membawa ke "?"; paparan GM menunjukkan setiap tempat.
- **Jurnal:** sesi-sesi, setiap satu boleh dibuka kepada adegan, peristiwa dan balingannya. Setiap peristiwa mempunyai Sunting dan Alih keluar (halakan tetikus padanya), yang membuka borang `beat edit` dan `beat rm`.
- **Rujukan:** cari semua (hasil muncul semasa anda menaip), jalankan peraturan daripada pek yang didayakan melalui borang, baling jadualnya, dan baca teks peraturan, glosari dan panduannya.
- **Pustaka:** dunia dan kempen (buka, tutup, cipta, padam), pek (setiap satu dengan keterangan tentangnya; dayakan, nyahdayakan, pasang, nyahpasang; pek yang disertakan bersama Didact mempunyai butang Pasang), sejarah (Buat asal, Buat semula, Lompat balik, Kosongkan), titik simpan (undur, alih keluar) dan sandaran (buat sandaran sekarang, pulihkan, padam, simpan beberapa yang terbaharu; sandaran yang dibuat apabila sesi tamat ditandakan auto). Apabila tiada kempen yang terbuka, Gambaran keseluruhan menyenaraikan kempen dunia itu supaya anda boleh membuka satu.
  - Memadam dunia atau kempen akan bertanya dahulu, dan Buat asal mengembalikan semuanya.
  - Lompat balik (di sebelah setiap perubahan) menarik balik semua yang berlaku selepas perubahan itu (`didact undo --to e40`): halamannya menyenaraikan apa yang akan dibuang dahulu. Setiap perubahan dibuat asal dan setiap balingan ditanda sebagai dibuat asal, bukan dipadam: Buat semula, atau lompat balik ke perubahan yang lebih kemudian, mengembalikannya. Tunjukkan perubahan yang lebih lama menyenaraikan lebih banyak sejarah.
  - Pek core sentiasa aktif. Hanya satu sistem permainan digunakan pada satu masa: sistem dunia yang terbuka, yang dikekalkannya buat selama-lamanya (dipilih semasa dunia dicipta). Sistem lain dimainkan dalam dunianya sendiri: barisnya membuka dunia yang memainkannya, atau mencipta dunia baharu. Menyahpasang pek tidak boleh dibuat asal: pasang semula .didactpack-nya.
  - Mengosongkan sejarah terlebih dahulu menunjukkan dengan tepat apa yang hilang dan apa yang berhenti berfungsi, dengan butang untuk membuat sandaran dahulu. Ia tidak boleh dibuat asal, begitu juga memadam sandaran.
  - Mula semula: **Tetapkan semula…** mengosongkan pustaka, seolah-olah Didact baru dipasang, dan penomboran bermula semula pada #e1. Halamannya menunjukkan apa yang hilang dahulu. Pustaka disandarkan dahulu, dan sandaran kekal (pek yang dipasang juga, melainkan anda menanda kotaknya).
  - Memulihkan sandaran terlebih dahulu menunjukkan kandungannya di sebelah pustaka sekarang. Pustaka seadanya disandarkan dahulu: Buat asal tidak dapat membatalkan pemulihan, tetapi memulihkan sandaran itu boleh.
- **Arahan:** setiap arahan sebagai borang, dan kotak yang menerima satu baris arahan penuh. Setiap kotak menerima apa yang diterima oleh argumennya: nombor, ID atau peristiwa (`e12`) mengikut coraknya, jumlah masa permainan sebagai nombor dan unit, dan senarai untuk memilih rekod, draf, pek, titik simpan, peramal, jadual dan peraturan di sini.
- **Tetapan:** pilihan kempen (varian dan peraturan pilihan sistemnya, yang diikuti oleh peraturan, penciptaan watak dan penjana; setiap satu menyatakan fungsinya: peraturan pilihan menyatakan apa yang berubah apabila ia dihidupkan, pilihan berbilang nilai menyatakan maksud setiap nilainya, dan nilai lalai yang ditetapkan oleh pilihan lain menyatakan pilihan yang mana), bahasa aplikasi, tesaurus (bahasa yang digunakan carian untuk sinonim: muat turun satu, dengan bar kemajuan, tukar antara yang telah dimuat turun, alih keluar satu) dan dokumentasi kod.
  - Aplikasi, panduannya dan apa yang ditunjukkan oleh arahan di dalamnya tersedia dalam 24 bahasa. Tanpa pilihan, aplikasi mengikut bahasa pelayar. Baris arahan dan LLM yang menggunakannya kekal dalam bahasa Inggeris: bahasa yang dipilih di sini hanya untuk aplikasi.
  - Butang kod di bar pengepala membuka dokumentasi API kod. Ia dibina daripada kod pada kali pertama, dan dibina semula setiap kali kod berubah (`didact docs build`).

Setiap perubahan menjalankan arahan `didact` yang sebenar, jadi ia disemak, dilog dan boleh dibuat asal tepat seperti di baris arahan. Aplikasi menunjukkan arahan yang dijalankannya setiap kali (`didact set sweeney hp-=2`), dengan butang Buat asal apabila ada sesuatu untuk dibatalkan.

Sesuatu kotak hanya menerima apa yang diterima oleh arahannya. ID (milik dunia atau kempen) dan jenis rekod menerima huruf kecil, digit dan sempang: ruang menjadi sempang dan huruf besar menjadi huruf kecil semasa anda menaip. Nama medan tidak menerima ruang (ruang menjadi garis bawah), nama butiran ialah satu perkataan, dan kotak nombor menerima nombor. Apa yang diterima oleh sesuatu kotak ditulis di bawahnya, dan arahan tetap menyemaknya semula.

Menyimpan tidak sekali-kali menulis ganti perubahan yang belum anda lihat. Jika rekod berubah selepas halaman memaparkannya (contohnya LLM mengubahnya dari baris arahan, atau tab lain), simpanan ditolak dan memberitahu apa yang ada sekarang. Penerangan yang sedang anda sunting kekal dalam editor, di sebelah versi baharu, untuk digabungkan dan disimpan semula. − dan + sentiasa berjaya: ia dijumlahkan.

## Paparan pemain dan paparan GM

Aplikasi menunjukkan apa yang diketahui pemain, seperti `didact show`: rekod rahsia, bahagian `## Secrets`, medan rahsia dan butiran khas GM tidak dipaparkan. Butang **GM** di bar pengepala menghidupkan paparan GM, dan sepanduk memberitahunya ("Paparan GM: rahsia dipaparkan"). Pelayar mengingati pilihan itu.

Dalam paparan pemain:
- penerangan yang mengandungi baris khas GM tidak boleh disunting (menyimpannya akan menghilangkan baris itu): hidupkan paparan GM dahulu;
- butiran GM atau medan rahsia yang tidak dipaparkan halaman tidak boleh ditulis ganti, walaupun nota baharu untuk GM boleh ditambah;
- sejarah menamakan arahan dan rekod yang diketahui pemain (`set · Freya`), tidak sekali-kali nilainya, dan Buat asal menyatakan perubahan mana yang dibatalkannya, bukan apa isinya.

## Keselamatan

Aplikasi ini boleh mengubah pustaka anda, jadi secara lalai ia hanya mendengar mesin ini.

- `--host` dengan alamat lain membolehkan mesin lain mencapainya, dan Didact memberi amaran tentangnya. Gunakan hanya pada rangkaian yang anda percayai.
- Ia hanya menjawab permintaan yang ditujukan kepadanya (alamatnya sendiri, `localhost`, `127.0.0.1` atau `[::1]`, dengan port-nya). Ini menghalang laman web lain daripada mencapainya melalui helah DNS.
- Setiap perubahan memerlukan borang daripada aplikasi itu sendiri: token rahsia dalam setiap borang mesti sepadan dengan kuki yang tidak boleh dibaca atau dihantar oleh laman lain.
- Tiada log masuk. Sesiapa yang boleh menggunakan pelayar komputer ini boleh menggunakan aplikasi.
