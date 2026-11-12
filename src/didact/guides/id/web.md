<!-- translated from 5a088227a31a -->
# Aplikasi peramban

`didact serve` membuka pustaka Anda di peramban web: jelajahi dan edit entri, lihat hubungan antarentri dalam graf, baca jurnal, jalankan aturan dan tabel, dan gunakan setiap perintah lewat formulir.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Aplikasi ini berjalan luring: fon dan ikonnya disertakan bersama Didact.

**Mode demo.** `--demo` menyajikan kampanye contoh (`didact sample`: sebuah lembah sungai, satu karakter pemain, orang-orang dengan catatan GM, tempat dan jalur, sebuah misi, sebuah jam, dan sesi yang sedang berlangsung dengan pertarungan) dari pustakanya sendiri, di samping folder cache Didact. Semua paket yang disertakan dengan Didact terpasang di sana. Kampanye ini dibangun ulang setiap kali `--demo` dijalankan, jadi coba apa saja: pustaka Anda sendiri tidak tersentuh.

## Opsi

| Opsi | Bawaan | Fungsinya |
|---|---|---|
| `--port <n>` | 8765 | port yang didengarkan |
| `--host <address>` | 127.0.0.1 | alamat yang didengarkan: hanya mesin ini |
| `--open` | mati | membuka aplikasi di tab peramban |
| `--gm` | mati | memulai dengan tampilan GM aktif |
| `--demo` | mati | menyajikan kampanye contoh baru, bukan pustaka Anda |

Opsi global `--home`, `--world`, dan `--campaign` berlaku untuk semua yang dilakukan aplikasi. Membuka dunia atau kampanye lain di halaman Pustaka akan beralih ke sana, seperti `didact world use` dan `didact campaign open`, dan Tutup menutup kampanye yang terbuka (`didact campaign close`).

## Isinya

- **Ikhtisar:** pengarahan (dunia, kampanye, sesi, adegan, kelompok, apa yang jatuh tempo), aksi cepat (lempar dadu, tanya orakel dengan peluang yang dikenalnya, catat peristiwa, mulai atau akhiri sesi, entri baru), dan perubahan terbaru.
- **Status:** keadaan permainan dalam sekilas: sesi dan adegan, waktu dan pengingat yang akan datang, angka setiap anggota kelompok dan barang bawaannya, pertarungan (giliran siapa, kondisi), misi dan pelacak yang masih terbuka, serta lokasi kelompok dan jalan keluarnya. Angkanya bisa diubah langsung di sana: − dan + pada stat, tambah satu pada pelacak, gunakan atau buang barang, tambahkan barang, selesaikan misi, majukan waktu (sebuah angka, dan satuan yang dikenal kalender: jam, giliran jaga, hari, …), setel pengingat (sekali, atau berkala), dan batalkan pengingat.
- **Entri:** setiap entri, dikelompokkan menurut tipe, dengan kotak filter dan pilihan semua, dunia, atau kampanye. Halaman sebuah entri menampilkan lembar, deskripsi, detail, kolom, isi, tautan dua arah, kronik, dan riwayatnya, dengan formulir untuk mengubah masing-masing, serta untuk mengarsipkan atau menghapusnya. Karakter yang sistemnya memiliki naik level punya tombol Level up (`char advance`): draf yang menampilkan apa yang berubah, sebelum dan sesudahnya, sampai diterapkan.
- **Draf:** pembuatan karakter dan generator, selangkah demi selangkah. Buat karakter (langkah demi langkah atau acak, dengan memilih jenisnya jika sistem memiliki beberapa: karakter pemain, orang sewaan, …) dan Hasilkan… ada di halaman Entri; draf yang menunggu dicantumkan di sana dan di Ikhtisar. Halaman sebuah draf menampilkan isinya sejauh ini (entitas dan kolomnya, peta yang digambar generator, lemparan, pertanyaan dari buku) dan pertanyaan yang sedang ditunggunya. Setiap pilihan berupa tombol yang menjelaskan artinya jika paketnya menjelaskannya (apa yang diberikan sebuah latar belakang, apa yang dilakukan sebuah bakat); memilih beberapa berarti mencentang kotak untuk masing-masing; skor yang dibeli dengan anggaran berupa angka yang menghitung poinnya selagi Anda mengubahnya; nama atau jawaban terbuka lain bisa diketik; dan Biar dadu yang menentukan melempar untuk pilihan itu saja (`char roll c3 --one`). Kembali membatalkan langkah terakhir, sehingga pertanyaannya muncul lagi (`char back c3`: lemparan yang dibuatnya ditandai diurungkan, dan Urungkan mengembalikan langkah itu). Lalu Lempar sisanya, Edit, Buang… (dengan konfirmasi lebih dulu), dan Terapkan, yang membuka entri karakter baru, atau mencantumkan apa yang dibuat generator. Draf generator milik GM: tampilan pemain hanya menunjukkan bahwa draf itu ada.
- **Graf:** entri sebagai simpul dan tautan sebagai sisi. Seret simpul, seret latar untuk menggeser, zoom dengan roda gulir; arahkan kursor untuk menyorot tetangga sebuah entri; klik untuk membukanya. Tombol Graf di halaman entri hanya menampilkan lingkungan sekitarnya.
  - **Peta** (sakelar di atas graf, atau Buka peta di Status): tempat yang diketahui kelompok, jalur di antaranya (berlabel road, trail, …), wilayah tempat masing-masing berada (garis putus-putus), dan lokasi kelompok. Jalur ke tempat yang belum ditemukan mengarah ke "?"; tampilan GM menampilkan setiap tempat.
- **Jurnal:** sesi-sesi, masing-masing bisa dibuka ke adegan, peristiwa, dan lemparannya. Setiap peristiwa punya Edit dan Hapus (arahkan kursor ke atasnya), yang membuka formulir `beat edit` dan `beat rm`.
- **Referensi:** cari semuanya (hasil muncul saat Anda mengetik), jalankan aturan dari paket yang aktif lewat formulir, lempar tabelnya, dan baca teks aturan, glosarium, dan panduannya.
- **Pustaka:** dunia dan kampanye (buka, tutup, buat, hapus), paket (masing-masing dengan keterangan apa itu; aktifkan, nonaktifkan, pasang, copot; paket yang disertakan bersama Didact punya tombol Pasang), riwayat (Urungkan, Ulangi, Lompat kembali, Hapus), titik simpan (mundur, hapus), dan cadangan (cadangkan sekarang, pulihkan, hapus, simpan beberapa yang terbaru; cadangan yang dibuat saat sesi berakhir ditandai otomatis). Jika tidak ada kampanye yang terbuka, Ikhtisar mencantumkan kampanye dunia itu agar Anda bisa membuka salah satunya.
  - Menghapus dunia atau kampanye meminta konfirmasi lebih dulu, dan Urungkan mengembalikan semuanya.
  - Lompat kembali (di samping setiap perubahan) membatalkan semua yang terjadi setelah perubahan itu (`didact undo --to e40`): halamannya lebih dulu mencantumkan apa yang akan hilang. Setiap perubahan diurungkan dan setiap lemparan ditandai diurungkan, bukan dihapus: Ulangi, atau lompat kembali ke perubahan yang lebih baru, mengembalikannya. Tampilkan perubahan yang lebih lama mencantumkan lebih banyak riwayat.
  - Paket core selalu aktif. Hanya satu sistem permainan yang dipakai dalam satu waktu: sistem milik dunia yang terbuka, yang dipertahankannya untuk selamanya (dipilih saat dunia dibuat). Sistem lain dimainkan di dunianya sendiri: barisnya membuka dunia yang memainkannya, atau membuat dunia baru. Mencopot paket tidak bisa diurungkan: pasang lagi .didactpack-nya.
  - Menghapus riwayat lebih dulu menampilkan dengan tepat apa yang hilang dan apa yang berhenti bekerja, dengan tombol untuk mencadangkan lebih dulu. Tindakan ini tidak bisa diurungkan, begitu pula menghapus cadangan.
  - Mulai dari awal: **Setel ulang…** mengosongkan pustaka, seolah Didact baru dipasang, dan penomoran kembali dimulai dari #e1. Halamannya lebih dulu menampilkan apa yang hilang. Pustaka dicadangkan lebih dulu, dan cadangan tetap ada (paket yang terpasang juga, kecuali Anda mencentang kotaknya).
  - Memulihkan cadangan lebih dulu menampilkan isinya berdampingan dengan pustaka saat ini. Pustaka apa adanya dicadangkan lebih dulu: Urungkan tidak bisa membatalkan pemulihan, tetapi memulihkan cadangan itu bisa.
- **Perintah:** setiap perintah sebagai formulir, dan kotak yang menerima satu baris perintah utuh. Setiap kotak menerima apa yang diterima argumennya: angka, ID atau peristiwa (`e12`) sesuai polanya, jumlah waktu permainan sebagai angka dan satuan, serta daftar untuk memilih entri, draf, paket, titik simpan, orakel, tabel, dan aturan yang ada di sini.
- **Pengaturan:** opsi kampanye (varian dan aturan opsional sistemnya, yang diikuti aturan, pembuatan karakter, dan generator; masing-masing menjelaskan fungsinya: aturan opsional menjelaskan apa yang berubah jika diaktifkan, pilihan menjelaskan arti setiap nilainya, dan nilai bawaan yang ditetapkan opsi lain menyebutkan opsi yang mana), bahasa aplikasi, tesaurus (bahasa yang dipakai pencarian untuk sinonim: unduh satu, dengan bilah kemajuan, beralih di antara yang sudah diunduh, hapus satu), dan dokumentasi kode.
  - Aplikasi, panduannya, dan yang ditampilkan perintah di dalamnya tersedia dalam 24 bahasa. Tanpa pilihan, aplikasi mengikuti bahasa peramban. Baris perintah dan LLM yang memakainya tetap berbahasa Inggris: bahasa yang dipilih di sini hanya untuk aplikasi.
  - Tombol kode di bilah atas membuka dokumentasi API kode. Dokumentasi ini dibuat dari kode saat pertama kali dibuka, dan dibuat ulang setiap kali kode berubah (`didact docs build`).

Setiap perubahan menjalankan perintah `didact` sungguhan, sehingga diperiksa, dicatat, dan bisa diurungkan persis seperti di baris perintah. Aplikasi menampilkan perintah yang dijalankannya setiap kali (`didact set sweeney hp-=2`), dengan tombol Urungkan jika ada yang bisa dibatalkan.

Sebuah kotak hanya menerima apa yang diterima perintahnya. ID (milik dunia atau kampanye) dan tipe entri menerima huruf kecil, angka, dan tanda hubung: spasi menjadi tanda hubung dan huruf kapital menjadi huruf kecil saat Anda mengetik. Nama kolom tidak menerima spasi (spasi menjadi garis bawah), nama detail berupa satu kata, dan kotak angka menerima angka. Apa yang diterima sebuah kotak tertulis di bawahnya, dan perintahnya tetap memeriksanya lagi.

Menyimpan tidak pernah menimpa perubahan yang belum Anda lihat. Jika entri berubah setelah halaman menampilkannya (misalnya LLM mengubahnya dari baris perintah, atau tab lain), penyimpanan ditolak dan menunjukkan isinya sekarang. Deskripsi yang sedang Anda edit tetap di editor, di samping versi baru, untuk digabungkan dan disimpan lagi. − dan + selalu berhasil: keduanya saling menjumlah.

## Tampilan pemain dan tampilan GM

Aplikasi menampilkan apa yang diketahui pemain, seperti `didact show`: entri rahasia, bagian `## Secrets`, kolom rahasia, dan detail khusus GM tidak ditampilkan. Tombol **GM** di bilah atas mengaktifkan tampilan GM, dan sebuah spanduk memberitahukannya ("Tampilan GM: rahasia ditampilkan"). Peramban mengingat pilihan itu.

Dalam tampilan pemain:
- deskripsi yang berisi baris khusus GM tidak bisa diedit (menyimpannya akan menghilangkan baris itu): aktifkan tampilan GM lebih dulu;
- detail GM atau kolom rahasia yang tidak ditampilkan halaman tidak bisa ditimpa, meskipun catatan baru untuk GM bisa ditambahkan;
- riwayat menyebut perintah dan entri yang diketahui pemain (`set · Freya`), tidak pernah nilainya, dan Urungkan menyebut perubahan mana yang dibatalkannya, bukan isinya.

## Keamanan

Aplikasi ini bisa mengubah pustaka Anda, jadi secara bawaan hanya mendengarkan mesin ini.

- `--host` dengan alamat lain membuat mesin lain bisa menjangkaunya, dan Didact memperingatkan hal itu. Gunakan hanya di jaringan yang Anda percaya.
- Aplikasi hanya menjawab permintaan yang ditujukan kepadanya (alamatnya sendiri, `localhost`, `127.0.0.1`, atau `[::1]`, dengan port-nya). Ini mencegah situs web lain menjangkaunya lewat trik DNS.
- Setiap perubahan memerlukan formulir dari aplikasi itu sendiri: token rahasia di setiap formulir harus cocok dengan cookie yang tidak bisa dibaca atau dikirim situs lain.
- Tidak ada login. Siapa pun yang bisa memakai peramban komputer ini bisa memakai aplikasinya.
