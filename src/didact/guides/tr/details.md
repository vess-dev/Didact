<!-- translated from 7fe144069f94 -->
# Ayrıntılar, kronik ve konumlar

Oyunu tutarlı tutan GM notları: şeylerin neye benzediği ve ne istediği, ne yaptıkları ve sırada ne planladıkları, başlarına ne geldiği ve her şeyin nerede olduğu.

## Ayrıntılar

Herhangi bir kayda eklenen kısa, adlı notlar: bir kişi, bir eşya, bir yer, bir hizip.

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

- **Adlar.** Önerilenler kaydın türüne göre değişir; tek kelimelik her ad kullanılabilir:
  - kişiler: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - eşyalar: looks, history, where, powers, secret, thoughts;
  - yerler: looks, state, history, secret, thoughts;
  - gruplar: wants, plan, state, history, secret, thoughts.

  Bir paket her tür için kendi adlarını önerebilir (bir şemada `details: [mood, grudge]`).
- **Kim neyi görür.** Oyuncular yalnızca `looks` notunu görür: `show` ve `find` gerisini dışarıda bırakır, `--gm` her şeyi gösterir. Oyuncular birini öğrendiğinde `didact reveal sweeney plan` onu kaydın metnine, `## Revealed` altına taşır.
- **`thoughts`** sizindir: onu neden yarattığınız, nereye varabileceği, ileride neyin karşılığını vereceğiniz.
- **Güncel tutun.** Her şeyi not etmeniz gerekmez. Ama bir şeye karar verdiğinizde (bir plan, bir kin, birinin nereye gittiği) yazın; böylece sonraki sahne ya da sonraki oturum ona sadık kalır.

## Kronik: kimin başına ne geldi

Bir günlük olayı ilgili olduğu kayıtları adlandırabilir. O zaman her birinde görünür.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` ve `about` bir kaydın kroniğini listeler: onun ne yaptığını ve ona ne yapıldığını.
- **Gizli olaylar** oyuncuların görmediği yerde olur. Yalnızca GM görünümlerinde (`session show --gm`, `about`, `brief --gm`) çıkar, `export --as story` çıktısında asla çıkmaz.
- Birini ya da bir şeyi değiştiren her şey için `--about` kullanın: bir ihanet, bir borç, bir ölüm, bir hediye, tutulmayan bir söz.
- **Bir olayı düzeltmek:** `didact beat edit S1.4 --about tom` olayı Tom'un kroniğine koyar (ya da `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), `didact beat rm S1.4` ise kaldırır. Kimlikler `session show` çıktısındadır ve ikisi de geri alınabilir.
- **Kimlikler değiştiğinde:** bir `merge` ya da yeni bir slug her başvuruyu beraberinde taşır: bağlantılar, ayrıntılar, olayların ilgili olduğu kayıtlar, grup, çatışma ve grubun konumu. Bir kayıt `rm` ile silindiğinde bulunduğu gruptan ya da çatışmadan da çıkar. Türler arası bir `merge`, kalan kaydın sayfasında alanı olanları tutar ve neyi dışarıda bıraktığını söyler.

## Konumlar: şeyler nerede

Eşyalar envanterlerde durur ve her şey onları tutabilir: bir karakter, bir yer, bir sandık.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Oturum sırasında bir eşyayı taşımak, veren ve alan hakkında bir olay kaydeder ("Sword: Freya → Chest"). Böylece kronikleri şeylerin nereye gittiğini söyler.
- **Kişiler ve canavarlar** yerlerin içeriği değil, ziyaretçileridir: nerede olduklarını `where` ayrıntılarında tutun.

## Sahnelerde ve çatışmalarda

- **`combat status --gm`** her dövüşçünün `where`, `doing` ve `plan` notlarını gösterir. Çatışma ilerledikçe onları güncelleyin: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (oturumun başında gelen özet) oyundakileri (yer, dövüşçüler, bu sahnenin olaylarının ilgili olduğu herkes ve grup) where, doing, plan ve state ile listeler. Ekran dışındaki son olayları da listeler.
