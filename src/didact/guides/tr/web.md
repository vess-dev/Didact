<!-- translated from 5a088227a31a -->
# Tarayıcı uygulaması

`didact serve` kütüphanenizi bir web tarayıcısında açar: kayıtları keşfedin ve düzenleyin, birbirine nasıl bağlandıklarını bir çizgede görün, günlüğü okuyun, kuralları ve tabloları çalıştırın, her komutu bir formdan kullanın.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Çevrimdışı çalışır: yazı tipleri ve simgeler Didact ile birlikte gelir.

**Demo modu.** `--demo`, örnek kampanyayı (`didact sample`: bir ırmak vadisi, bir oyuncu karakteri, GM notları olan kişiler, yerler ve yollar, bir görev, bir saat ve bir çatışmayla süren bir oturum) Didact'ın önbellek klasörünün yanındaki kendine ait bir kütüphaneden sunar. Didact ile gelen tüm paketler orada kuruludur. `--demo` her başladığında sıfırdan kurulur, yani her şeyi deneyin: kendi kütüphanenize dokunulmaz.

## Seçenekler

| Seçenek | Varsayılan | Ne yapar |
|---|---|---|
| `--port <n>` | 8765 | dinlenecek port |
| `--host <address>` | 127.0.0.1 | dinlenecek adres: yalnızca bu makine |
| `--open` | kapalı | uygulamayı bir tarayıcı sekmesinde açar |
| `--gm` | kapalı | GM görünümü açık başlar |
| `--demo` | kapalı | kütüphaneniz yerine sıfırdan bir örnek kampanya sunar |

Genel `--home`, `--world` ve `--campaign` seçenekleri uygulamanın yaptığı her şeye uygulanır. Uygulamanın Kütüphane sayfasında başka bir dünya ya da kampanya açmak, `didact world use` ve `didact campaign open` gibi ona geçer; Kapat ise açık kampanyayı kenara koyar (`didact campaign close`).

## İçinde neler var

- **Genel bakış:** özet (dünya, kampanya, oturum, sahne, grup, sırası gelenler), hızlı eylemler (zar at, kâhine bildiği olasılıklarla sor, bir olay yaz, oturum başlat ya da bitir, yeni kayıt) ve son değişiklikler.
- **Durum:** işlerin ne durumda olduğu, bir bakışta: oturum ve sahne, zaman ve yaklaşan hatırlatıcılar, grubun her üyesinin sayıları ve taşıdıkları, çatışma (kimin sırası, durumlar), açık görevler ve sayaçlar, grubun nerede olduğu ve oradan çıkış yolları. Sayılar orada hemen değiştirilebilir: bir değerde − ve +, bir sayacı işaretleme, bir eşyayı kullanma ya da bırakma, eşya ekleme, bir görevi bitirme, zamanı ilerletme (bir sayı ve takvimin bildiği bir birim: saat, nöbet, gün, …), bir hatırlatıcı kurma (bir kez ya da belli aralıklarla) ve birini iptal etme.
- **Kayıtlar:** türe göre gruplanmış tüm kayıtlar; bir süzgeç kutusu ve tümü, dünya ya da kampanya çipleriyle. Bir kaydın sayfası karakter sayfasını, açıklamasını, ayrıntılarını, alanlarını, içindekileri, iki yönlü bağlantılarını, kroniğini ve geçmişini gösterir; her birini değiştirmek, kaydı arşivlemek ya da silmek için formlar sunar. Sisteminde seviye atlama olan bir karakterin Level up düğmesi vardır (`char advance`): onaylanana kadar neyin değiştiğini, öncesi ve sonrasıyla gösteren bir taslak.
- **Taslaklar:** karakter oluşturma ve üreteçler, adım adım. Karakter oluştur (adım adım ya da rastgele, sistemde birden çok tür olduğunda hangisi olacağını seçerek: oyuncu karakteri, paralı yardımcı, …) ve Üret… Kayıtlar sayfalarındadır; bekleyen taslaklar orada ve Genel bakış'ta listelenir. Bir taslağın sayfası şimdiye kadar tuttuklarını (varlıkları ve alanları, bir üretecin çizdiği harita, atışlar, kitabın yönlendirmeleri) ve beklediği soruyu gösterir. Her seçenek, paket bunu söylüyorsa ne anlama geldiğini de gösteren bir düğmedir (bir geçmişin ne kazandırdığı, bir yeteneğin ne yaptığı); birkaç seçim yapılacaksa her biri için işaretlenecek bir kutu vardır; bir bütçeyle satın alınan değerler, siz değiştirdikçe puanları sayan sayılardır; bir ad ya da başka açık bir yanıt yazılabilir; Zarlar karar versin de yalnızca o soru için zar atar (`char roll c3 --one`). Geri son adımı geri alır, böylece onun sorusu yeniden gelir (`char back c3`: adımın yaptığı atışlar geri alındı olarak işaretlenir ve Geri al adımı geri getirir). Sonra Kalanı zara bırak, Düzenle, Çöpe at… (önce sorar) ve Onayla gelir; Onayla yeni karakterin kaydını açar ya da üretecin yaptıklarını listeler. Bir üretecin taslağı GM'indir: oyuncu görünümü yalnızca var olduğunu gösterir.
- **Çizge:** düğüm olarak kayıtlar, kenar olarak bağlantılar. Düğümleri sürükleyin, kaydırmak için arka planı sürükleyin, tekerlekle yakınlaşın; bir kaydın komşularını aydınlatmak için üzerine gelin; açmak için tıklayın. Bir kaydın sayfasındaki Çizge düğmesi yalnızca onun çevresini gösterir.
  - **Harita** (çizgenin üstündeki anahtar ya da Durum'daki Haritayı aç): grubun bildiği yerler, aralarındaki yollar (road, trail, … diye etiketli), her birinin bulunduğu bölge (kesikli) ve grubun yeri. Henüz bulunmamış bir yere giden yol bir "?"a çıkar; GM görünümü her yeri gösterir.
- **Günlük:** oturumlar; her biri sahnelerine, olaylarına ve atışlarına açılır. Her olayın Düzenle ve Kaldır düğmeleri vardır (üzerine gelin); bunlar `beat edit` ve `beat rm` formlarını açar.
- **Başvuru:** her yerde arayın (sonuçlar siz yazarken çıkar), etkin paketlerin kurallarını formlardan çalıştırın, tablolarında zar atın, kural metinlerini, sözlükçelerini ve kılavuzlarını okuyun.
- **Kütüphane:** dünyalar ve kampanyalar (aç, kapat, oluştur, sil), paketler (her biri ne olduğuyla birlikte; etkinleştir, devre dışı bırak, kur, kaldır; Didact ile gelen paketlerin bir Kur düğmesi vardır), geçmiş (Geri al, Yinele, Geri atla, Temizle), kayıt noktaları (geri sar, kaldır) ve yedekler (şimdi yedekle, geri yükle, sil, en yeni birkaçını sakla; bir oturum bittiğinde alınanlar auto diye işaretlidir). Açık kampanya yokken Genel bakış, birini açabilmeniz için dünyanın kampanyalarını listeler.
  - Bir dünyayı ya da kampanyayı silmek önce sorar ve Geri al hepsini geri getirir.
  - Geri atla (her değişikliğin yanında) o değişiklikten sonraki her şeyi geri alır (`didact undo --to e40`): sayfası önce neyin gideceğini listeler. Her değişiklik geri alınır ve her atış geri alındı olarak işaretlenir, silinmez: Yinele ya da daha sonraki bir değişikliğe geri atlamak onları geri getirir. Daha eski değişiklikleri göster, geçmişin daha fazlasını listeler.
  - core paketi her zaman açıktır. Aynı anda tek bir oyun sistemi kullanımdadır: açık dünyanınki; dünya onu kalıcı olarak korur (dünya oluşturulurken seçilir). Başka bir sistem kendi dünyasında oynanır: onun satırı, o sistemle oynanan bir dünyayı açar ya da yeni bir dünya oluşturur. Bir paketi kaldırmak geri alınamaz: .didactpack dosyasını yeniden kurun.
  - Geçmişi temizlemek önce tam olarak neyin gideceğini ve neyin çalışmaz olacağını gösterir; önce yedeklemek için bir düğme de sunar. Geri alınamaz; bir yedeği silmek de öyle.
  - Baştan başlamak: **Sıfırla…** kütüphaneyi boşaltır, Didact yeni kurulmuş gibi olur ve numaralandırma yeniden #e1'den başlar. Sayfası önce neyin gideceğini gösterir. Kütüphane önce yedeklenir ve yedekler kalır (kutuyu işaretlemezseniz kurulu paketler de).
  - Bir yedeği geri yüklemek önce içinde ne olduğunu kütüphanenin şimdiki hâlinin yanında gösterir. Kütüphanenin önceki hâli önce yedeklenir: Geri al bir geri yüklemeyi geri alamaz, ama o yedeği geri yüklemek alabilir.
- **Komutlar:** form olarak her komut ve tam bir komut satırını alan bir kutu. Her kutu argümanının aldığını alır: bir sayı, desenine uyan bir kimlik ya da olay (`e12`), sayı ve birim olarak bir oyun zamanı miktarı ve buradaki kayıtlar, taslaklar, paketler, kayıt noktaları, kâhinler, tablolar ve kurallar arasından seçim yapılacak bir liste.
- **Ayarlar:** kampanyanın seçenekleri (kurallarının, karakter oluşturmanın ve üreteçlerin izlediği, sisteminin varyantları ve isteğe bağlı kuralları; her biri ne yaptığını söyler: isteğe bağlı bir kural açılınca neyin değiştiğini, bir seçim her değerinin ne anlama geldiğini, başka bir seçeneğin belirlediği bir varsayılan da onu hangi seçeneğin belirlediğini), uygulamanın dili, eş anlamlılar sözlüğü (aramaların eş anlamlılar için kullandığı dil: bir ilerleme çubuğuyla indirin, indirilenler arasında geçiş yapın, birini kaldırın) ve kodun belgeleri.
  - Uygulama, kılavuzları ve komutların uygulamada gösterdikleri 24 dilde sunulur. Bir seçim yapılmazsa uygulama tarayıcının dilini izler. Komut satırı ve onu kullanan dil modelleri İngilizce kalır: burada seçilen dil yalnızca uygulamanın dilidir.
  - Başlık çubuğundaki kod düğmesi kodun API belgelerini açar. Belgeler ilk seferde koddan oluşturulur, kod her değiştiğinde yeniden oluşturulur (`didact docs build`).

Her değişiklik gerçek bir `didact` komutu çalıştırır; böylece tıpkı komut satırındaki gibi denetlenir, günlüğe yazılır ve geri alınabilir. Uygulama her seferinde çalıştırdığı komutu gösterir (`didact set sweeney hp-=2`); geri alınacak bir şey varsa bir Geri al düğmesiyle.

Bir kutu yalnızca komutunun aldığını alır. Bir kimlik (bir dünyanın ya da bir kampanyanın) ve bir kayıt türü küçük harf, rakam ve tire alır: siz yazarken boşluklar tireye, büyük harfler küçük harfe dönüşür. Bir alanın adı boşluk almaz (boşluklar alt çizgi olur), bir ayrıntının adı tek sözcüktür, sayı kutuları da sayı alır. Bir kutunun ne aldığı altında yazar ve komut yine de ayrıca denetler.

Kaydetmek, görmediğiniz bir değişikliğin asla üzerine yazmaz. Kayıt, sayfa onu gösterdikten sonra değiştiyse (örneğin bir LLM onu komut satırından değiştirdiyse ya da başka bir sekme değiştirdiyse) kaydetme reddedilir ve şimdi orada ne olduğu söylenir. Düzenlemekte olduğunuz açıklama, birleştirip yeniden kaydetmeniz için yeni sürümün yanında düzenleyicide kalır. − ve + her zaman geçer: toplanırlar.

## Oyuncu görünümü ve GM görünümü

Uygulama, `didact show` gibi, oyuncuların bildiklerini gösterir: gizli kayıtlar, `## Secrets` bölümleri, gizli alanlar ve yalnızca GM'e ait ayrıntılar dışarıda kalır. Başlık çubuğundaki **GM** düğmesi GM görünümünü açar ve bir şerit bunu belirtir ("GM görünümü: sürprizler görünüyor"). Tarayıcı seçimi hatırlar.

Oyuncu görünümünde:
- yalnızca GM'e ait satırlar içeren bir açıklama düzenlenemez (kaydetmek onları kaybettirir): önce GM görünümünü açın;
- sayfanın göstermediği bir GM ayrıntısının ya da gizli alanın üzerine yazılamaz, ama GM için yeni bir not eklenebilir;
- geçmiş, komutu ve oyuncuların bildiği kayıtları adlandırır (`set · Freya`), değerleri asla göstermez; Geri al da hangi değişikliği geri aldığını söyler, ne olduğunu değil.

## Güvenlik

Uygulama kütüphanenizi değiştirebilir, bu yüzden varsayılan olarak yalnızca bu makineyi dinler.

- Başka bir adresle `--host`, başka makinelerin ona erişmesine izin verir ve Didact bu konuda uyarır. Yalnızca güvendiğiniz bir ağda kullanın.
- Yalnızca kendisine yönelik isteklere yanıt verir (kendi adresi, `localhost`, `127.0.0.1` ya da `[::1]`, kendi portuyla). Bu, başka web sitelerinin DNS hileleriyle ona ulaşmasını engeller.
- Her değişiklik uygulamanın kendi formunu gerektirir: her formdaki gizli bir belirteç, başka sitelerin okuyamadığı ve gönderemediği bir çerezle eşleşmelidir.
- Oturum açma yoktur. Bu bilgisayarın tarayıcısını kullanabilen herkes uygulamayı kullanabilir.
