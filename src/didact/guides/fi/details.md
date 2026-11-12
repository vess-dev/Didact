<!-- translated from 7fe144069f94 -->
# Yksityiskohdat, kronikka ja sijainnit

PJ:n muistiinpanot, jotka pitävät pelin johdonmukaisena: miltä asiat näyttävät ja mitä ne haluavat, mitä ne tekevät ja suunnittelevat seuraavaksi, mitä niille on tapahtunut ja missä kaikki on.

## Yksityiskohdat

Lyhyitä nimettyjä muistiinpanoja mihin tahansa merkintään: henkilöön, esineeseen, paikkaan, ryhmittymään.

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

- **Nimet.** Ehdotetut nimet riippuvat merkinnän lajista, ja mikä tahansa yksisanainen nimi käy:
  - henkilöt: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts;
  - esineet: looks, history, where, powers, secret, thoughts;
  - paikat: looks, state, history, secret, thoughts;
  - ryhmät: wants, plan, state, history, secret, thoughts.

  Paketti voi ehdottaa tyyppikohtaisesti omiaan (`details: [mood, grudge]` skeemassa).
- **Kuka näkee mitä.** Pelaajat näkevät vain `looks`-tiedon: `show` ja `find` jättävät loput pois, ja `--gm` näyttää kaiken. Kun pelaajat saavat jonkin tiedon selville, `didact reveal sweeney plan` siirtää sen merkinnän tekstiin otsikon `## Revealed` alle.
- **`thoughts`** ovat sinun: miksi teit sen, mihin se voi johtaa, mitä pitää lunastaa myöhemmin.
- **Pidä ne ajan tasalla.** Kaikkea ei tarvitse kirjata. Mutta kun päätät jotain (suunnitelman, kaunan, minne joku meni), kirjoita se ylös, jotta seuraava kohtaus tai seuraava pelikerta pysyy sille uskollisena.

## Kronikka: mitä kenellekin tapahtui

Päiväkirjan tapahtuma voi nimetä merkinnät, joita se koskee. Se näkyy silloin jokaisessa niistä.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` ja `about` luettelevat merkinnän kronikan: mitä se teki ja mitä sille tehtiin.
- **Salaiset tapahtumat** tapahtuvat pelaajien näkymättömissä. Ne näkyvät vain PJ-näkymissä (`session show --gm`, `about`, `brief --gm`), eivätkä koskaan `export --as story` -viennissä.
- Käytä `--about`-valitsinta kaikkeen, mikä muuttaa jotakuta tai jotakin: petokseen, velkaan, kuolemaan, lahjaan, rikottuun lupaukseen.
- **Tapahtuman korjaaminen:** `didact beat edit S1.4 --about tom` lisää sen Tomin kronikkaan (tai `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), ja `didact beat rm S1.4` poistaa sen. Tunnisteet näkyvät `session show` -komennossa, ja molemmat voi kumota.
- **Kun tunnisteet muuttuvat:** `merge` tai uusi slug vie jokaisen viittauksen mukanaan: linkit, yksityiskohdat, merkinnät, joita tapahtumat koskevat, seurueen, taistelun ja seurueen sijainnin. Kun merkintä poistetaan `rm`-komennolla, se lähtee myös seurueesta tai taistelusta. Tyyppien välinen `merge` säilyttää sen, mille jäävän merkinnän lomakkeessa on kenttä, ja kertoo, mitä se jättää pois.

## Sijainnit: missä asiat ovat

Esineet ovat inventaarioissa, ja mikä tahansa voi pitää niitä: hahmo, paikka, arkku.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Pelikerran aikana esineen siirtäminen kirjaa tapahtuman antajasta ja vastaanottajasta (”Sword: Freya → Chest”). Heidän kronikoistaan näkyy sitten, minne tavarat menivät.
- **Henkilöt ja hirviöt** ovat paikkojen vieraita, eivät niiden sisältöä: pidä kirjaa niiden olinpaikasta `where`-yksityiskohdassa.

## Kohtauksissa ja taisteluissa

- **`combat status --gm`** näyttää jokaisen taistelijan `where`-, `doing`- ja `plan`-tiedot. Päivitä niitä taistelun edetessä: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (katsaus, jolla pelikerta alkaa) luettelee, mikä on pelissä (paikka, taistelijat, kaikki, joita tämän kohtauksen tapahtumat koskevat, ja seurue), sekä niiden where-, doing-, plan- ja state-tiedot. Se luettelee myös viimeisimmät kulisseissa tapahtuneet tapahtumat.
