<!-- translated from 7fe144069f94 -->
# Szczegóły, kronika i miejsca pobytu

Notatki MG, które pilnują spójności gry: jak coś wygląda i czego chce, co robi i co planuje dalej, co mu się przydarzyło i gdzie wszystko jest.

## Szczegóły

Krótkie, nazwane notatki przy dowolnym wpisie: osobie, przedmiocie, miejscu, frakcji.

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

- **Nazwy.** Proponowane zależą od rodzaju wpisu, a zadziała każda jednowyrazowa nazwa:
  - osoby: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - przedmioty: looks, history, where, powers, secret, thoughts;
  - miejsca: looks, state, history, secret, thoughts;
  - grupy: wants, plan, state, history, secret, thoughts.

  Pakiet może proponować własne dla każdego typu (`details: [mood, grudge]` w schemacie).
- **Kto co widzi.** Gracze widzą tylko `looks`: `show` i `find` pomijają resztę, a `--gm` pokazuje wszystko. Gdy gracze poznają któryś szczegół, `didact reveal sweeney plan` przenosi go do tekstu wpisu, pod `## Revealed`.
- **`thoughts`** są twoje: dlaczego to stworzyłeś, dokąd może prowadzić, co wykorzystać później.
- **Dbaj o aktualność.** Nie musisz notować wszystkiego. Ale gdy coś postanowisz (plan, urazę, dokąd ktoś poszedł), zapisz to, żeby następna scena czy następna sesja pozostała temu wierna.

## Kronika: co się komu przydarzyło

Wydarzenie w dzienniku może wskazywać wpisy, których dotyczy. Pojawia się wtedy przy każdym z nich.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` i `about` wyświetlają kronikę wpisu: co zrobił i co jemu zrobiono.
- **Tajne wydarzenia** dzieją się poza wzrokiem graczy. Pojawiają się tylko w widokach MG (`session show --gm`, `about`, `brief --gm`) i nigdy w `export --as story`.
- Używaj `--about` przy wszystkim, co kogoś lub coś zmienia: zdradzie, długu, śmierci, podarunku, złamanej obietnicy.
- **Poprawianie wydarzenia:** `didact beat edit S1.4 --about tom` umieszcza je w kronice Toma (albo `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), a `didact beat rm S1.4` je usuwa. Identyfikatory są w `session show`, a oba polecenia można cofnąć.
- **Gdy zmieniają się identyfikatory:** `merge` lub nowy slug przenosi ze sobą każde odwołanie: powiązania, szczegóły, wpisy, których dotyczą wydarzenia, drużynę, walkę i położenie drużyny. Wpis usunięty przez `rm` opuszcza też drużynę i walkę. `merge` między typami zachowuje to, na co karta pozostającego wpisu ma pole, i mówi, co pomija.

## Miejsca pobytu: gdzie co jest

Przedmioty trafiają do ekwipunków, a mieć je może wszystko: postać, miejsce, skrzynia.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Podczas sesji przeniesienie przedmiotu zapisuje wydarzenie dotyczące dającego i otrzymującego („Sword: Freya → Chest”). Ich kroniki mówią potem, gdzie co trafiło.
- **Osoby i potwory** są w miejscach gośćmi, a nie ich zawartością: gdzie są, zapisuj w ich szczególe `where`.

## W scenach i walkach

- **`combat status --gm`** pokazuje `where`, `doing` i `plan` każdego walczącego. Aktualizuj je w miarę rozwoju walki: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (odprawa, od której zaczyna się sesja) wymienia to, co jest w grze (miejsce, walczących, tych, których dotyczą wydarzenia tej sceny, i drużynę), wraz z where, doing, plan i state. Wymienia też ostatnie wydarzenia poza kadrem.
