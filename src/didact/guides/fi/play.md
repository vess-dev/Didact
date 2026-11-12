<!-- translated from bef7b2c650cb -->
# Pelikerran pelaaminen

Miten peli kulkee Didactin kautta: LLM kertoo tarinaa, ja Didact pitää kirjaa jokaisesta tosiasiasta, heitosta ja muutoksesta.

## Ennen ensimmäistä pelikertaa

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Maailma pitää systeemin, jolla se luotiin, ja sen kampanjat pelataan sillä: toista systeemiä pelataan omassa maailmassaan. `didact campaign close` panee kampanjan syrjään (sen maailma jää auki), ja `didact campaign open <id>` jatkaa sitä siitä, mihin se jäi, pelikertoineen kaikkineen.

`didact world delete <id>` ja `didact campaign delete <id>` poistavat maailman tai kampanjan ja näyttävät ensin esikatselun; `--yes` poistaa, ja `didact undo` tuo kaiken takaisin.

`session zero` luettelee kysymykset, joista sovitaan pelaajan kanssa. Paketin omat tulevat ensin. Niiden joukossa ovat järjestelmän asetukset (sen muunnelmat ja valinnaiset säännöt): sen säännöt noudattavat vastauksia, ja katsaus kertoo, mitä kukin muutettu asetus tarkoittaa. Vastaukset ovat mukana jokaisessa katsauksessa.

## Pelikerta

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Vuorot:** jokainen pelaajan viesti avaa vuoron (Claude Code -koukku kutsuu `didact capture` -komentoa, ja muut asiakasohjelmat käyttävät `turn begin` -komentoa). `didact undo --turn` peruu kaiken, mitä viestin vuoksi tehtiin: muutokset, tapahtumat ja heitot. Transkriptio säilyttää sen.
- **Takaisin hyppääminen:** `didact undo --to e40` peruu kaiken kohdan #e40 jälkeen, uusin ensin (`--dry-run` luettelee sen): jokainen muutos kumotaan ja jokainen heitto merkitään kumotuksi. Mitään ei poisteta: `redo` tai myöhempään muutokseen hyppääminen tuo kaiken takaisin.
- **Aika:** `didact time advance 1 watch` kuluttaa ajastimet loppuun, nostaa esiin muistutukset ja suorittaa aikalaukaisimet. `didact remind --list` näyttää tulevat muistutukset, ja `didact remind --cancel 2` poistaa yhden. Kampanja alkaa kalenterin alusta tai päivämäärästä, jonka `campaign new --date '4 July 1902'` antaa, ja `didact time set '<date>'` muuttaa sitä ensimmäiseen pelikertaan asti.
- **Paikat:** `didact visit <place>` siirtää seurueen ja merkitsee paikan käydyksi. `didact map` näyttää, mitä seurue tietää, ja tutkimaton uloskäynti on `?`.
- **Taistelut:** `didact combat start --party troll`, sitten `combat next`, `combat hit freya troll weapon=d8` ja `combat end`. Taistelijoita tulee ja menee kesken taistelun: `didact combat join wolf-2` (yksilöllisessä tilassa ne heittävät aloitteen) ja `didact combat leave troll --why fled`. Keneltäkään ei jää vuoroa väliin.
- **Tavarat:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (tai arkkuun tai paikkaan); `didact where rope` löytää sen. `inv add` löytää kompendiumin esineen sen tunnisteen, nimen tai aliaksen perusteella.
- **Muistiinpanosi:** `didact about sweeney plan='…' doing='…' where='…'` säilyttää sen, mitä olet päättänyt kenestä tai mistä tahansa. Pelaajat näkevät vain `looks`-tiedon. `didact log … --about sweeney` lisää tapahtuman hänen merkintäänsä (`--secret`, jos pelaajat eivät näe sitä). Lisää kohdassa `didact guide details`.
- **Maailma kulkee eteenpäin:** `didact faction turn` sekä kellot: `didact track new 'The flood' --size 6`. Komento, joka ottaa vain yhdenlaisen merkinnän, tulkitsee muiden jakaman nimen sellaiseksi: `didact track roll draugr` heittää poolin, joka on nimetty vihollisen mukaan (samoin `track tick` laskurin, `quest done` tehtävän ja `visit` paikan).

## Oraakkelit, generaattorit ja hahmot

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

Mitään generaattorin tai hahmonluonnin tekemää ei kirjoiteta ennen `commit`-komentoa. Kuvaa `--prefill`-valitsimessa, mitä pelaaja haluaa, niin menettely täyttää aukot. Kysymys luettelee, mitä kukin vaihtoehto tarkoittaa, kun paketti sen kertoo (`- Cutpurse: …`): kerro se pelaajalle, jotta hän valitsee tietäen, mitä saa.

## Salaisuudet

Näkymät ovat oletuksena pelaajille turvallisia: `show`, `find`, `sheet`, `map`, `brief`. Ne jättävät pois:
- salaiset merkinnät (`knowledge: secret`);
- osiot `## Secrets` ja `## GM notes`;
- `secret: true` -kentät.

`--gm` näyttää kaiken. Kun pelaajat saavat jotain selville:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` kirjoittaa sen, mitä pelaajat tietävät, pieneksi verkkosivustoksi, jonka voi jakaa tai lukea puhelimella: seurue, oma sivu kullekin merkinnälle, päiväkirja ja kartta. Se on aina pelaajille turvallinen, ja uusi vienti samaan kansioon päivittää sen. `didact export --as lonelog` kirjoittaa päiväkirjan Lonelog-merkintätavalla (`@ ? d: -> =>`, kohtaukset muodossa `S1`, tunnisteet kuten `[N:Sweeney]`), sekin pelaajille turvallisena.

## Taustatiedot: mitä nousee esiin, kun jotain mainitaan

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Mikä lasketaan:** jokainen sivuhahmo, paikka, esine ja ryhmittymä on kortti, jonka avaimina ovat sen nimi ja aliakset. Taustatietokohdilla on `keys`, ja sääntötulkinnat nousevat esiin sääntönsä kautta. Vastaavuutta haetaan kokonaisista sanoista, ja monikot lasketaan (”wolves” vastaa avainta `wolf`).
- **Milloin taustatiedot nousevat esiin:** Claude Code -koukku käy läpi jokaisen pelaajan viestin. Myös `log`, `scene new` ja `show` tuovat mukanaan juuri lauenneet taustatiedot, eikä samaa kohtaa toisteta muutamaan vuoroon.
- **Kohdan hienosäätö:** `--secondary` yhdessä `--logic`-valitsimen kanssa, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (vuoroina tai kohtauksina), `--constant` (aina katsauksessa) ja `--no-recurse`.
- **Laajuudet:** kohdat menevät kampanjaan, ellei `--scope` sano world, system tai global. Haku näkee vain tämän kampanjan, sen maailman, sen systeemin ja globaalit kohdat, ei koskaan toista maailmaa. Suppeampi kohta samalla tunnisteella peittää laajemman.
- **Muiden työkalujen lorebookit:** `didact lore import <file>` lukee SillyTavernin World Infon (myös KoboldAI:n), hahmokortin lorebookin ja NovelAI:n `.lorebook`-tiedoston; `didact lore export --to <file>` kirjoittaa World Infoa. Avainsanat, logiikka, prioriteetti, todennäköisyys, ryhmät ja ajoitus siirtyvät mukana.

## Tarinan muuttaminen

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` muuttaa tosiasian mutta säilyttää vanhan arvon. Se myös merkitsee Sweeneyn mainitsevat yhteenvedot vanhentuneiksi, ja `audit` luettelee sen.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` kirjaa sääntötulkinnan. Se näkyy sitten `rules lookup` -haussa ja silloin, kun kyseinen sääntö suoritetaan.
- `didact name npc` arpoo uuden nimen, ei koskaan sellaista, jota maailma jo käyttää. Ennen kuin keksit nimen itse, tarkista se komennolla `didact names check <name>`. `didact names forget <name>` vapauttaa nimen taas.

## Ylläpito

- `didact history --clear` näyttää, mitä vanhan historian tyhjentäminen poistaisi; `--yes` poistaa sen lopullisesti, poistetut merkinnät mukaan lukien, eivätkä kumoaminen, `diff`, `rewind` ja vanhemmat tallennuspisteet enää ulotu siihen (`--before e120` säilyttää e120:n ja sitä myöhemmät, `--rolls` poistaa myös noppahistorian). Aja ensin `didact snapshot`.
- `didact save --remove 'before the dragon'` poistaa tallennuspisteen; `didact undo` tuo sen takaisin.
- `didact transcript 3 --clear` poistaa pelikerran 3 transkription (`--clear --all`: kaikkien pelikertojen). `didact undo` tuo sen takaisin, ja teksti säilyy historiassa `history --clear` -komentoon asti.
- `didact compendium remove <entry>` poistaa lisäämäsi kohdan; siitä luodut merkinnät säilyvät.
- `didact snapshot --keep 3` poistaa kaikki paitsi kolme uusinta varmuuskopiota, ja `didact snapshot --remove <name>` poistaa yhden. Kumpaakaan ei voi kumota.
- `didact session end` varmuuskopioi kirjaston itsestään (`snapshot-<time>-auto.zip`) ja säilyttää niistä viisi uusinta; `didact snapshot --list` merkitsee ne.
- `didact reset` näyttää, mitä kirjaston tyhjentäminen veisi; `--yes` tekee siitä kuin juuri asennetun: kaikki maailmat, kampanjat ja merkinnät, historia ja hakuindeksi poistuvat, ja seuraava muutos on taas #e1. Se varmuuskopioi kirjaston ensin (`…-before-reset.zip`), ja varmuuskopiot säilyvät, samoin asennetut paketit, ellei `--packs` ole annettu. Jos haluat sen sijaan kokeilla Didactia valmiilla kampanjalla, `didact sample` rakentaa esimerkkikampanjan tyhjään kirjastoon (`--home` antaa sille oman kansion), ja `didact serve --demo` tarjoilee sen aina uutena.
- `didact snapshot --restore <name>` näyttää, mitä varmuuskopio sisältää verrattuna nykyiseen kirjastoon; `--yes` varmuuskopioi kirjaston sellaisenaan (`…-before-restore.zip`) ja laittaa sitten varmuuskopion sen tilalle. Muutosten ja heittojen numerointi jatkuu. Kumoaminen ei voi perua palautusta: sen turvavarmuuskopion palauttaminen voi.
