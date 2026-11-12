<!-- translated from bef7b2c650cb -->
# Bir oturum oynamak

Bir oyun Didact ile nasıl yürür: LLM anlatır, Didact her olguyu, atışı ve değişikliği saklar.

## İlk oturumdan önce

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Bir dünya, oluşturulurken seçilen sistemi korur ve kampanyaları o sistemle oynanır: başka bir sistem kendi dünyasında oynanır. `didact campaign close` bir kampanyayı kenara koyar (dünyası açık kalır), `didact campaign open <id>` ise onu oturumuyla birlikte kaldığı yerden sürdürür.

`didact world delete <id>` ve `didact campaign delete <id>` bir dünyayı ya da kampanyayı, önce ön izlemesini göstererek kaldırır; `--yes` siler, `didact undo` hepsini geri getirir.

`session zero` oyuncuyla netleştirilecek soruları listeler. Önce paketin kendi soruları gelir. Sistemin seçenekleri (varyantları ve isteğe bağlı kuralları) de bunlar arasındadır: kuralları yanıtları izler, özet de değiştirilen her seçeneğin ne anlama geldiğini söyler. Her özet yanıtları taşır.

## Bir oturum

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Turlar:** her oyuncu mesajı bir tur açar (Claude Code kancası `didact capture` çağırır, diğer istemciler `turn begin` kullanır). `didact undo --turn` o mesaj için yapılan her şeyi geri alır: değişiklikler, olaylar ve atışlar. Döküm onu saklar.
- **Geri atlama:** `didact undo --to e40`, #e40 sonrasındaki her şeyi en yenisi önce geri alır (`--dry-run` bunları listeler): her değişiklik geri alınır ve her atış geri alındı olarak işaretlenir. Hiçbir şey silinmez: `redo` ya da daha sonraki bir değişikliğe geri atlamak onu geri getirir.
- **Zaman:** `didact time advance 1 watch` zamanlayıcıları doldurur, hatırlatıcıları getirir ve zaman tetikleyicilerini çalıştırır. `didact remind --list` gelecek hatırlatıcıları gösterir, `didact remind --cancel 2` birini iptal eder. Bir kampanya takvimin başlangıcında ya da `campaign new --date '4 July 1902'` komutunun verdiği tarihte başlar, `didact time set '<date>'` ise ilk oturuma kadar onu değiştirir.
- **Yerler:** `didact visit <place>` grubu taşır ve yeri ziyaret edildi olarak işaretler. `didact map` grubun bildiklerini gösterir; keşfedilmemiş bir çıkış `?` olur.
- **Çatışmalar:** `didact combat start --party troll`, sonra `combat next`, `combat hit freya troll weapon=d8` ve `combat end`. Dövüşçüler çatışma sürerken gelip gidebilir: `didact combat join wolf-2` (bireysel modda inisiyatif atarlar) ve `didact combat leave troll --why fled`. Kimsenin sırası atlanmaz.
- **Eşyalar:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (ya da bir sandığa, ya da bir yere); `didact where rope` onu bulur. `inv add` bir derleme eşyasını kimliğiyle, adıyla ya da bir diğer adıyla bulur.
- **Notlarınız:** `didact about sweeney plan='…' doing='…' where='…'` biri ya da bir şey hakkında verdiğiniz kararları saklar. Oyuncular yalnızca `looks` notunu görür. `didact log … --about sweeney` bir olayı onun kaydına koyar (oyuncular görmüyorsa `--secret`). Fazlası `didact guide details` içinde.
- **Dünyanın yoluna devam etmesi:** `didact faction turn`, bir de saatler: `didact track new 'The flood' --size 6`. Tek bir tür kayıt alan bir komut, başkalarının da taşıdığı bir adı o türden sayar: `didact track roll draugr`, bir düşmanın adını taşıyan havuzu atar (`track tick` bir sayacı, `quest done` bir görevi ve `visit` bir yeri de öyle).

## Kâhinler, üreteçler ve karakterler

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

Bir üretecin ya da karakter oluşturmanın yaptığı hiçbir şey `commit` gelene kadar yazılmaz. Oyuncunun ne istediğini `--prefill` ile anlatın, boşlukları prosedür doldurur. Paket söylüyorsa bir soru her seçeneğin ne anlama geldiğini listeler (`- Cutpurse: …`): bunu oyuncuya söyleyin ki ne elde edeceğini bilerek seçsin.

## Sırlar

Görünümler varsayılan olarak oyuncular için güvenlidir: `show`, `find`, `sheet`, `map`, `brief`. Şunları dışarıda bırakırlar:
- gizli kayıtlar (`knowledge: secret`);
- `## Secrets` ve `## GM notes` bölümleri;
- `secret: true` alanları.

`--gm` her şeyi gösterir. Oyuncular bir şey öğrendiğinde:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` oyuncuların bildiklerini paylaşmak ya da telefonda okumak için küçük bir web sitesi olarak yazar: grup, her kayıt için bir sayfa, günlük ve harita. Her zaman oyuncular için güvenlidir; aynı klasöre yeniden dışa aktarmak onu günceller. `didact export --as lonelog` günlüğü Lonelog gösteriminde yazar (`@ ? d: -> =>`, sahneler `S1` olarak, `[N:Sweeney]` gibi etiketler); o da oyuncular için güvenlidir.

## Lore: bir şeyden söz edilince geri gelenler

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Neler sayılır:** her OYK, yer, eşya ve hizip, adı ve takma adlarıyla anahtarlanmış bir karttır. Lore girdilerinin `keys` alanı vardır; hakem kararları da kuralları üzerinden gelir. Eşleşme tam kelimeler üzerindedir ve çoğullar da sayılır ("wolves", `wolf` ile eşleşir).
- **Lore ne zaman gelir:** Claude Code kancası her oyuncu mesajını tarar. `log`, `scene new` ve `show` da yeni tetiklenen lore'u taşır; bir girdi birkaç tur boyunca tekrarlanmaz.
- **Bir girdiyi ayarlamak:** `--logic` ile `--secondary`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (tur ya da sahne olarak), `--constant` (hep özette) ve `--no-recurse`.
- **Kapsamlar:** girdiler, `--scope` world, system ya da global demedikçe kampanyaya gider. Bir tarama yalnızca bu kampanyayı, dünyasını, sistemini ve global'i görür, asla başka bir dünyayı görmez. Aynı kimliğe sahip daha dar bir girdi daha geniş olanı gölgeler.
- **Başka araçların lore kitapları:** `didact lore import <file>` SillyTavern World Info’yu (KoboldAI’ınkini de), bir karakter kartının lore kitabını ve NovelAI’ın `.lorebook` dosyasını okur; `didact lore export --to <file>` World Info yazar. Anahtarlar, mantık, öncelik, olasılık, gruplar ve zamanlama taşınır.

## Hikâyeyi değiştirmek

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` olguyu değiştirir ama eski değeri saklar. Ayrıca Sweeney'den söz eden özetleri eskimiş olarak işaretler ve `audit` bunu listeler.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` bir hakem kararı kaydeder. Karar sonra `rules lookup` içinde ve o kural çalıştığında çıkar.
- `didact name npc` yeni bir ad atar, asla dünyanın zaten kullandığı birini değil. Bir ad uydurmadan önce `didact names check <name>` ile denetleyin. `didact names forget <name>` bir adı yeniden serbest bırakır.

## Bakım

- `didact history --clear` eski geçmişi temizlemenin neyi atacağını gösterir; `--yes` silinmiş kayıtlar dahil onu kalıcı olarak atar ve geri alma, `diff`, `rewind` ve daha eski kayıt noktaları artık ona ulaşamaz (`--before e120` o olayı ve sonrakileri saklar, `--rolls` zar kaydını da atar). Önce `didact snapshot` çalıştırın.
- `didact save --remove 'before the dragon'` bir kayıt noktasını kaldırır; `didact undo` onu geri getirir.
- `didact transcript 3 --clear` 3. oturumun dökümünü siler (`--clear --all`: tüm oturumlarınkini). `didact undo` onu geri getirir ve metin `history --clear` yapılana kadar geçmişte kalır.
- `didact compendium remove <entry>` eklediğiniz bir girdiyi siler; ondan doğan kayıtlar kalır.
- `didact snapshot --keep 3` en yeni üçü dışındaki tüm yedekleri siler, `didact snapshot --remove <name>` birini siler. İkisi de geri alınamaz.
- `didact session end` kütüphaneyi kendiliğinden yedekler (`snapshot-<time>-auto.zip`) ve bunların en yeni beşini saklar; `didact snapshot --list` onları işaretler.
- `didact reset` kütüphaneyi boşaltmanın neyi götüreceğini gösterir; `--yes` onu yeni kurulmuş gibi yapar: her dünya, kampanya ve kayıt, geçmiş ve arama dizini gider, bir sonraki değişiklik yine #e1 olur. Önce kütüphaneyi yedekler (`…-before-reset.zip`); yedekler kalır, `--packs` verilmedikçe kurulu paketler de. Didact'ı bunun yerine hazır bir kampanyada denemek için `didact sample` örnek kampanyayı boş bir kütüphaneye kurar (`--home` ona kendi klasörünü verir), `didact serve --demo` da onu her seferinde sıfırdan sunar.
- `didact snapshot --restore <name>` bir yedeğin içinde ne olduğunu kütüphanenin şimdiki hâlinin yanında gösterir; `--yes` kütüphaneyi olduğu gibi yedekler (`…-before-restore.zip`), sonra yedeği onun yerine koyar. Olay ve atış numaraları kaldığı yerden sürer. Geri al bir geri yüklemeyi geri alamaz: o güvenlik yedeğini geri yüklemek alabilir.
