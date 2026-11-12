<!-- translated from 5a088227a31a -->
# Selainsovellus

`didact serve` avaa kirjastosi verkkoselaimessa: tutki ja muokkaa merkintöjä, katso graafista, miten ne linkittyvät, lue päiväkirjaa, suorita sääntöjä ja taulukoita ja käytä mitä tahansa komentoa lomakkeen kautta.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Se toimii ilman verkkoyhteyttä: fontit ja kuvakkeet tulevat Didactin mukana.

**Demotila.** `--demo` tarjoilee esimerkkikampanjan (`didact sample`: jokilaakso, pelaajahahmo, henkilöitä PJ:n muistiinpanoineen, paikkoja ja reittejä, tehtävä, kello ja käynnissä oleva pelikerta, jossa on taistelu) omasta kirjastostaan Didactin välimuistikansion vierestä. Siihen on asennettu kaikki Didactin mukana tulevat paketit. Se rakennetaan uudelleen joka kerta, kun `--demo` käynnistyy, joten kokeile mitä vain: oma kirjastosi pysyy koskemattomana.

## Valitsimet

| Valitsin | Oletus | Mitä se tekee |
|---|---|---|
| `--port <n>` | 8765 | portti, jota kuunnellaan |
| `--host <address>` | 127.0.0.1 | osoite, jota kuunnellaan: vain tämä kone |
| `--open` | pois | avaa sovelluksen selaimen välilehteen |
| `--gm` | pois | käynnistä PJ-näkymä päällä |
| `--demo` | pois | tarjoile uusi esimerkkikampanja kirjastosi sijaan |

Yleiset valitsimet `--home`, `--world` ja `--campaign` koskevat kaikkea, mitä sovellus tekee. Toisen maailman tai kampanjan avaaminen sovelluksen Kirjasto-sivulla vaihtaa siihen, kuten `didact world use` ja `didact campaign open` tekevät, ja Sulje panee avoimen kampanjan syrjään (`didact campaign close`).

## Mitä siinä on

- **Yleiskatsaus:** katsaus (maailma, kampanja, pelikerta, kohtaus, seurue, mitä on tulossa), pikatoiminnot (heitä noppia, kysy oraakkelilta sen tuntemin todennäköisyyksin, kirjaa tapahtuma, aloita tai päätä pelikerta, uusi merkintä) ja viimeisimmät muutokset.
- **Tilanne:** tilanne yhdellä silmäyksellä: pelikerta ja kohtaus, aika ja tulevat muistutukset, kunkin seurueen jäsenen luvut ja mitä hän kantaa, taistelu (kenen vuoro, tilat), avoimet tehtävät ja laskurit sekä seurueen sijainti ja reitit sieltä pois. Lukuja voi säätää suoraan siinä: − ja + arvon kohdalla, rastita laskuri, käytä tai pudota esine, lisää esine, merkitse tehtävä valmiiksi, siirrä aikaa eteenpäin (luku ja kalenterin tuntema yksikkö: tunnit, vartiot, päivät, …), aseta muistutus (kerran tai tietyin välein) ja peruuta muistutus.
- **Merkinnät:** kaikki merkinnät tyypeittäin ryhmiteltyinä, suodatinkentän sekä Kaikki-, Maailma- ja Kampanja-valintojen kera. Merkinnän sivu näyttää sen arvot, kuvauksen, yksityiskohdat, kentät, sisällön, linkit molempiin suuntiin, kronikan ja historian, ja lomakkeilla voi muuttaa jokaista niistä sekä arkistoida tai poistaa merkinnän. Hahmolla, jonka systeemissä on tasonnousu, on Level up -painike (`char advance`): luonnos, joka näyttää, mikä muuttuu, ennen ja jälkeen, kunnes se hyväksytään.
- **Luonnokset:** hahmonluonti ja generaattorit, vaihe kerrallaan. Luo hahmo (vaihe vaiheelta tai satunnaisesti, valiten lajin, kun systeemissä on useita: pelaajahahmo, palkkalainen, …) ja Generoi… löytyvät Merkinnät-sivuilta; odottavat luonnokset luetellaan siellä ja Yleiskatsauksessa. Luonnoksen sivu näyttää, mitä siinä on tähän mennessä (sen entiteetit ja niiden kentät, generaattorin piirtämä kartta, heitot, kirjan kehotteet), ja kysymyksen, johon se odottaa vastausta. Jokainen vaihtoehto on painike, joka kertoo, mitä se tarkoittaa, kun paketti sen kertoo (mitä tausta antaa, mitä kyky tekee); kun valitaan useita, kullakin on oma rastitettava ruutunsa; budjetilla ostettavat arvot ovat lukuja, jotka laskevat pisteet sitä mukaa kuin etenet; nimen tai muun vapaan vastauksen voi kirjoittaa; ja Anna noppien päättää heittää vain sen yhden (`char roll c3 --one`). Takaisin peruu viimeisimmän vaiheen, joten sen kysymys esitetään uudelleen (`char back c3`: vaiheen tekemät heitot merkitään kumotuiksi, ja Kumoa tuo vaiheen takaisin). Sitten Heitä loput, Muokkaa, Hylkää… (se kysyy ensin) ja Hyväksy, joka avaa uuden hahmon merkinnän tai luettelee, mitä generaattori teki. Generaattorin luonnos on PJ:n: pelaajanäkymä näyttää vain, että se on olemassa.
- **Kaavio:** merkinnät solmuina ja linkit kaarina. Vedä solmuja, vedä taustaa panoroidaksesi, zoomaa rullalla; vie osoitin merkinnän päälle korostaaksesi sen naapurit; napsauta avataksesi merkinnän. Merkinnän sivun Kaavio-painike näyttää vain sen lähiympäristön.
  - **Kartta** (graafin yläpuolella oleva kytkin tai Avaa kartta Tilanne-sivulla): seurueen tuntemat paikat, niiden väliset reitit (nimettyinä tie, polku, …), alue, jolla kukin sijaitsee (katkoviivalla), ja seurueen sijainti. Reitti paikkaan, jota ei ole vielä löydetty, johtaa ”?”-merkkiin; PJ-näkymä näyttää kaikki paikat.
- **Päiväkirja:** pelikerrat, joista kukin avautuu kohtauksikseen, tapahtumikseen ja heitoikseen. Jokaisella tapahtumalla on Muokkaa ja Poista (vie osoitin sen päälle), jotka avaavat `beat edit`- ja `beat rm` -lomakkeet.
- **Käsikirja:** hae kaikkialta (tulokset näkyvät kirjoittaessa), suorita käytössä olevien pakettien sääntöjä lomakkeilla, heitä niiden taulukoita ja lue niiden sääntötekstiä, sanastoa ja oppaita.
- **Kirjasto:** maailmat ja kampanjat (avaa, sulje, luo, poista), paketit (kukin kuvauksineen; ota käyttöön, poista käytöstä, asenna, poista asennus; Didactin mukana tulevilla paketeilla on Asenna-painike), historia (Kumoa, Tee uudelleen, Hyppää takaisin, Tyhjennä), tallennuspisteet (kelaa taaksepäin, poista) ja varmuuskopiot (varmuuskopioi nyt, palauta, poista, säilytä muutama uusin; pelikerran päättyessä tehdyt on merkitty sanalla auto). Kun mikään kampanja ei ole auki, Yleiskatsaus luettelee maailman kampanjat, jotta voit avata jonkin.
  - Maailman tai kampanjan poistaminen kysyy ensin, ja Kumoa tuo kaiken takaisin.
  - Hyppää takaisin (kunkin muutoksen vieressä) peruu kaiken kyseisen muutoksen jälkeen (`didact undo --to e40`): sen sivu luettelee ensin, mitä poistuu. Jokainen muutos kumotaan ja jokainen heitto merkitään kumotuksi, ei poisteta: Tee uudelleen tai myöhempään muutokseen hyppääminen tuo ne takaisin. Näytä vanhemmat muutokset näyttää historiaa pidemmälle.
  - Ydinpaketti on aina käytössä. Käytössä on kerrallaan vain yksi pelisysteemi: avoimen maailman, joka pitää sen lopullisesti (se valitaan maailmaa luotaessa). Toista systeemiä pelataan omassa maailmassaan: sen rivi avaa maailman, jossa sitä pelataan, tai luo uuden. Paketin asennuksen poistamista ei voi kumota: asenna sen .didactpack uudelleen.
  - Historian tyhjentäminen näyttää ensin tarkalleen, mitä poistuu ja mikä lakkaa toimimasta, sekä painikkeen, jolla voi ensin varmuuskopioida. Sitä ei voi kumota, eikä myöskään varmuuskopion poistamista.
  - Aloita alusta: **Nollaa…** tyhjentää kirjaston kuin Didact olisi juuri asennettu, ja numerointi alkaa taas kohdasta #e1. Sen sivu näyttää ensin, mitä poistuu. Kirjasto varmuuskopioidaan ensin, ja varmuuskopiot säilyvät (samoin asennetut paketit, ellet rastita ruutua).
  - Varmuuskopion palauttaminen näyttää ensin, mitä se sisältää verrattuna nykyiseen kirjastoon. Kirjasto sellaisenaan varmuuskopioidaan ensin: Kumoa ei voi perua palautusta, mutta sen varmuuskopion palauttaminen voi.
- **Komennot:** jokainen komento lomakkeena sekä kenttä, johon voi kirjoittaa kokonaisen komentorivin. Kukin kenttä ottaa sen, mitä sen argumentti ottaa: luvun, tunnuksen tai tapahtuman (`e12`) kaavansa mukaan, peliajan määrän lukuna ja yksikkönä sekä luettelon, josta valita täkäläiset merkinnät, luonnokset, paketit, tallennuspisteet, oraakkelit, taulukot ja säännöt.
- **Asetukset:** kampanjan asetukset (sen järjestelmän muunnelmat ja valinnaiset säännöt, joita säännöt, hahmonluonti ja generaattorit noudattavat; kukin kertoo, mitä se tekee: valinnainen sääntö sen, mitä sen käyttöön ottaminen muuttaa, vaihtoehdoista valittava asetus sen, mitä kukin sen arvoista tarkoittaa, ja oletus, jonka jokin toinen asetus määrää, kertoo mikä asetus), sovelluksen kieli, synonyymisanakirja (kieli, jolla haku etsii synonyymejä: lataa kieli, edistymispalkin kera, vaihda ladattujen välillä, poista kieli) ja koodin dokumentaatio.
  - Sovellus, sen oppaat ja se, mitä komennot näyttävät sovelluksessa, ovat saatavilla 24 kielellä. Jos kieltä ei ole valittu, sovellus seuraa selaimen kieltä. Komentorivi ja sitä käyttävät kielimallit pysyvät englanninkielisinä: tässä valittu kieli koskee vain sovellusta.
  - Yläpalkin koodipainike avaa koodin API-dokumentaation. Se rakennetaan koodista ensimmäisellä kerralla ja uudelleen aina, kun koodi muuttuu (`didact docs build`).

Jokainen muutos suorittaa oikean `didact`-komennon, joten se tarkistetaan, kirjataan ja voidaan kumota täsmälleen kuten komentorivillä. Sovellus näyttää joka kerta suorittamansa komennon (`didact set sweeney hp-=2`) sekä Kumoa-painikkeen, kun on jotain peruttavaa.

Kenttä ottaa vain sen, mitä sen komento ottaa. Tunnus (maailman tai kampanjan) ja merkintätyyppi ottavat pieniä kirjaimia, numeroita ja yhdysviivoja: välilyönneistä tulee yhdysviivoja ja isot kirjaimet muuttuvat pieniksi kirjoittaessasi. Merkinnän kentän nimeen ei käy välilyöntejä (niistä tulee alaviivoja), yksityiskohdan nimi on yksi sana, ja lukukenttiin käy vain lukuja. Mitä kenttä ottaa, lukee sen alla, ja komento tarkistaa sen joka tapauksessa uudelleen.

Tallentaminen ei koskaan korvaa muutosta, jota et ole nähnyt. Jos merkintä muuttui sen jälkeen, kun sivu näytti sen (vaikkapa LLM muutti sitä komentoriviltä tai toinen välilehti muutti sitä), tallennus hylätään ja näytetään, mitä siinä nyt on. Muokkaamasi kuvaus jää editoriin uuden version viereen, jotta voit yhdistää ja tallentaa uudelleen. − ja + menevät aina läpi: ne lasketaan yhteen.

## Pelaajanäkymä ja PJ-näkymä

Sovellus näyttää sen, mitä pelaajat tietävät, kuten `didact show`: salaiset merkinnät, `## Secrets`-osiot, salaiset kentät ja vain PJ:lle tarkoitetut yksityiskohdat jäävät pois. Yläpalkin **GM**-painike ottaa PJ-näkymän käyttöön, ja palkki kertoo sen (”PJ-näkymä: juonipaljastukset näkyvissä”). Selain muistaa valinnan.

Pelaajanäkymässä:
- kuvausta, jossa on vain PJ:lle tarkoitettuja rivejä, ei voi muokata (tallentaminen hävittäisi ne): ota ensin PJ-näkymä käyttöön;
- PJ:n yksityiskohtaa tai salaista kenttää, jota sivu ei näytä, ei voi kirjoittaa yli, mutta uuden muistiinpanon PJ:lle voi lisätä;
- historia nimeää komennon ja pelaajien tuntemat merkinnät (`set · Freya`), ei koskaan arvoja, ja Kumoa kertoo, minkä muutoksen se perui, ei sitä, mikä muutos oli.

## Turvallisuus

Sovellus voi muuttaa kirjastoasi, joten oletuksena se kuuntelee vain tätä konetta.

- `--host` toisella osoitteella päästää muut koneet siihen käsiksi, ja Didact varoittaa siitä. Käytä sitä vain verkossa, johon luotat.
- Se vastaa vain pyyntöihin, jotka on osoitettu sille itselleen (sen omaan osoitteeseen, `localhost`, `127.0.0.1` tai `[::1]`, sen portilla). Se estää muita sivustoja tavoittamasta sitä DNS-temppujen avulla.
- Jokainen muutos vaatii sovelluksen oman lomakkeen: jokaisen lomakkeen salaisen tunnisteen on vastattava evästettä, jota muut sivustot eivät voi lukea tai lähettää.
- Kirjautumista ei ole. Kuka tahansa, joka voi käyttää tämän tietokoneen selainta, voi käyttää sovellusta.
