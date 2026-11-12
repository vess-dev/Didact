<!-- translated from b1dfa1159ff4 -->
# Paketit

Paketti on pelisysteemi, oraakkeli, pelimaailma, seikkailu tai lisäosa, kirjoitettuna YAML-tiedostoina sekä valinnaisena Python-liitännäisenä. Tämä opas näyttää, miten sellainen kirjoitetaan: sääntökirjasta paketiksi tai omaa sisältöä lisäten.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Paketin voi tehdä myös kirjastosi sisällöstä. `didact pack new my-brew --from-overlay my-system` tekee systeemin kotitekoisesta sisällöstäsi (`compendium add`, `--scope system` -merkinnät, taustatiedot) lisäosan, ja `didact world export --as setting` tekee maailmasta pelimaailmapaketin: sen henkilöt, paikat ja taustatiedot kompendiumin kohtina ja paketin taustatietoina, jotka tuodaan toiseen maailmaan `compendium import` -komennolla. Kumpikin jättää salaisuudet ja PJ:n muistiinpanot pois, ellei `--secrets`, eikä kumpaakaan merkitä jaettavaksi ennen kuin asetat sen lisenssin.

## Rakenne

```
my-hack/
  pack.yaml        id, name, kind, version, requires, extends, license, plugins, settings
  GUIDE.md         how to run it: an LLM reads this first
  dice.yaml        named dice, macros, dice chains
  schemas/         record types and their fields (sheets)
  tables/          random and lookup tables, decks, bags
  rules/           checks, actions, procedures, triggers
  compendium/      monsters, items, spells, backgrounds…
  reference/       the rules text, one short section per file (Markdown)
  glossary.yaml    terms and definitions
  tests/           examples `pack test` runs
  plugins/         Python, for what YAML can't express (off until trusted)
```

Tiedosto sisältää yhden kohteen, luettelon kohteita tai useita kohteita `---`-erottimin. Jokainen kohde ilmoittaa tunnisteensa lajinsa avaimella: `table: weather`, `check: save`, `type: pc` tai kompendiumin kohdille `id: troll`. Viittaa kohteisiin muodossa `pack.id` (`my-system.save`) tai pelkällä tunnisteella, kun se on vain yhdessä käytössä olevassa paketissa.

```yaml
# pack.yaml
id: my-hack
name: My Hack
kind: system                 # system | oracle | supplement | setting | adventure
version: 0.1.0
alias: hack                  # the name in expressions: hack.attack(d8, d8)
requires: {didact: ">=0.1", packs: [core]}
extends: []                  # for a hack: [my-system]; same-id items replace the base's
license: {spdx: CC-BY-SA-4.0, redistributable: true, attribution: "…"}
settings: {torch_uses: 3}    # rules read these as @settings.torch_uses
```

Hack nimeää pohjansa kohdassa `extends` ja sisältää vain sen, mikä eroaa:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Sen kohde, jolla on sama tunniste, korvaa pohjan kohteen lajista riippumatta (taulukko, sääntö, kompendiumin kohta, viiteosio, sanaston termi). Sen `settings`-arvot asettuvat pohjan arvojen päälle avain avaimelta: avain, jonka se asettaa, korvaa pohjan arvon kokonaan (sen `names`-taulukot tulevat pohjan nimitaulukoiden tilalle), ja pohjan säännötkin lukevat hackin arvot. `hides` jättää pois sen, mitä jää jäljelle ja mitä hack ei tarvitse: `*` vastaa mitä tahansa merkkijonoa, viimeinen tunnisteeseen osuva kuvio ratkaisee, ja `!`-merkillä alkava kuvio säilyttää kohteen. Sitä, minkä hack korvaa, ei koskaan piiloteta. Lajit ovat `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` ja `term`. `didact pack validate` varoittaa kuviosta, joka ei osu mihinkään.

## Lausekkeet

Jokainen ehto ja kaava käyttää noppakieltä (`didact guide dice`), ja lisäksi:
- **Arvot:** `@name` lukee arvon: `@roll`, `@who.STR`, `@settings.x`. `$name` liittää ensin parametrin tekstin, joten `@who.$attr` muuttuu muotoon `@who.STR`. Lue vapaata tekstiä oleva parametri muodossa `@name`, älä lainausmerkeissä (`'$name'`): sen tekstin heittomerkki päättäisi ne (`pack validate` varoittaa).
- **Logiikka:** `and`, `or`, `not` ja `in` (`'deprived' in @who.conditions`).
- **Literaalit:** teksti (`'travel'`) sekä `true`/`false`.
- **Funktiot:** `if(cond, a, b)` heittää vain valitsemansa haaran. `default(@thread.flashpoint, 0)` on arvo tai varavaihtoehto, kun arvoa ei ole asetettu. `sum`, `count` (`count(@roll.dice, 6)` laskee kuutoset), `min`, `max`, `any` ja `all` ottavat luetteloita.

## Lomakkeet: `schemas/`

```yaml
type: character
fields:
  STR: {kind: stat, range: [0, 18], roll: 3d6, on_zero: {trigger: death}}
  hp: {kind: resource, min: 0, roll: d6}
  armor: {kind: derived, expr: "min(3, sum(@inventory.armor))"}
  inventory: {kind: slots, capacity: 10, sizes: {petty: 0, normal: 1, bulky: 2},
              when_full: {set: {hp: 0}}}
  fatigue: {kind: counter, min: 0, occupies: inventory}
guidance: "3 HP is an average monster, 6 a hardy one, 10+ a serious threat."
---
type: pc
extends: character
```

| Laji | Sisältää | Valinnat |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | tavallisen arvon | min, max; enumille `values` |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` on arvo, `@hp.max` yläraja | range; min; max tai max_field; die |
| `counter` | luvun | min, max, thresholds, occupies (slots-kenttä) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | esineitä (`Rope` tai `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | nimensä mukaisesti | `to` (refs-kentille), `allowed` |
| `derived` | laskettu, ei koskaan tallenneta | expr |

Jokainen kenttä ottaa myös `label`, `help`, `default`, `required` ja `roll`: `new pc Hero --fill` tai arvo `"roll"` heittää sen lokin kautta. `core`-paketin tyypit sisältävät systeemistä riippumatonta tekstiä kentissä `fields`. Systeemin tyypit pitävät sen luvut kentässä `mechanics.<system>`. `set hero hp-=2` löytää kentän, rajaa arvon ja ilmoittaa mahdollisesta ylityksestä. `+=` lisää luetteloon: `list`-kenttä (kuten `slots`) säilyttää uudelleen lisätyn arvon, `tags`, `conditions` ja `refs` sisältävät sen vain kerran, ja `-=` poistaa sen kaikki kopiot.

**Koukut** kertovat, mitä tapahtuu, kun arvo ylittää rajan. Ne laukeavat jokaisessa muutoksessa (`set`, `inv`, säännön `set`-vaihe), mutta vain kun raja ylitetään: 3 → 0 laukaisee, 0 → 0 ei. `--force`-muokkaukset ohittavat ne.

| Koukku | Laukeaa, kun |
|---|---|
| `on_zero` | luku tai `{value}` saavuttaa 0:n |
| `on_full` (slots-kentillä `when_full`) | se saavuttaa maksiminsa, kokonsa tai kapasiteettinsa |
| `thresholds: {10: …, 20: …}` (laskurit) | se nousee kunkin rajan ohi |

Toiminto on tekstiä (muistiinpano LLM:lle), `{set: {hp: 0}}` tai `{condition: paralyzed}` samassa merkinnässä, `{trigger: death}` (suorittaa sen säännön, `who` = merkintä) tai luettelo näistä.

**Inventaario** (`didact inv …`) toimii arvojen `slots`-kentällä:
- **Tila:** esineet vievät tilaa `size` × `count`, ja laskurit, joilla on kenttään viittaava `occupies`, vievät arvonsa verran. `capacity`-rajan ylitys hylätään, ellei `--force` ole annettu.
- **Ryhmät:** `groups: {backpack: 6, body: 4}` antaa jokaiselle ryhmälle oman tilansa sekä omat sarakkeensa ja summansa: `@inventory.body.armor` on vain se, mikä on puettuna tai kädessä, `@inventory.body.free` ryhmän jäljellä oleva tila.
- **Käyttökerrat:** `uses: 3` laskee alaspäin `inv use` -komennolla. `uses: d8` on kulutusnoppa: 1–2 pienentää sitä portaalla. Loppuun käytetty esine katoaa, ellei sillä ole `recharge`- tai `keep: true` -määritystä. Useista samannimisistä esineistä nimi tarkoittaa ensimmäistä; käyttökertaa kulutettaessa (`inv use`, säännön `use:`, `set …uses-=1`) ensimmäistä, jolla on vielä käyttökertoja jäljellä.
- **Esineen omat avaimet:** `didact set freya inventory.sword.damage=d10` (myös säännön `set: who.inventory.$item.damage`) muuttaa yhtä niistä, ja esine nimetään kuten `inv`-komennossa, osalla nimestään tai koko nimellä, välilyönnit ja pisteet mukaan lukien (`'inventory.12.7mm pistol.damage=d10'`, lainausmerkeissä komentotulkkia varten); `uses` ja `charges` lasketaan kuten `uses`-kentässä (`charges+=2` pysähtyy maksimiinsa), ja tila tarkistetaan samoin kuin `inv add` -komennossa. Sääntö lukee yhden muodossa `@{who.inventory.$item.damage}` (kulutusnoppa noppanaan, käyttökerrat määränään); esine tai avain, jota ei ole, luetaan puuttuvaksi, joten `default(…)` antaa varaarvonsa.
- **Kompendium:** tyypin `item` (tai weapon, armor, relic, …, tai paketin oman tyypin, joka laajentaa jotakin niistä `extends`-määrityksellä) kohdat lainaavat tietonsa `inv add` -komennolle, ja ne löytyvät tunnisteen, nimen tai aliaksen perusteella (jos kahdella on sama: nimeä tarkoitettu muodossa `pack.id`); mikä tahansa muu nimi, `:` mukaan lukien, on esineen oma nimi.

## Taulukot: `tables/`

```yaml
table: weather
dice: d6                     # any expression: 2d6, d66, d100, d20 + @corruption
clamp: true                  # a total past the ends uses the first or last entry
entries:
  1-2: Clear
  3-4: {text: Rain, data: {travel: slow}}
  5: {text: Storm, then: [{table: lightning}]}
  6: {text: Two fronts, roll: 2}
refs: {noun: nouns}          # "{noun}" in a text rolls on table nouns; "{1d4}" rolls dice
source: "Core Rules p. 12"
```

Muita muotoja:
- **Painotetut luettelot:** `entries` luettelona, ja jokaisella kohdalla `weight:`.
- **Sarakkeet:** `columns: [a, b]` heittää rivin jokaisen sarakkeen erikseen. Tavallinen kohta (ei luettelo) täyttää jokaisen sarakkeen, joten `columns: [first, second]` sanaluettelon päällä tarkoittaa ”heitä tätä luetteloa kahdesti”. `labels: false` jättää sarakkeiden nimet pois tuloksesta (”Abandon · Advantage”). `read: "It's a {first} {second} with {third} {fourth} inside."` lukee sarakkeet lauseeksi.
- **Hakutaulukot:** `lookup: hp_lost` tai kaksiulotteiselle taulukolle `[odds, chaos]`.
- **Kaksoiskappaleet:** `duplicates: reroll | keep | make_it_worse` ”heitä kahdesti” -tuloksille.
- **Kaksi vaihetta:** kohta, joka heittää toisesta taulukosta (`{table: lightning}` tekstin sijaan tai `then:` sen jälkeen), tuo mukanaan sen heiton tiedot: sääntö tai luonnos, jonka heitto osuu siihen, lukee molemmat, ensin kohdan omat avaimet ja sitten ensimmäisen seuraavaksi heitetyn taulukon avaimet. `--prefill` voi nimetä kohdan alempaa, millä tahansa syvyydellä (`Ring of the Hunt`), jokaisen matkan varrella olevan kohdan tiedoin: kahdesta samannimisestä tarkoitetaan lähempää (sitten ensimmäistä), jatkuva kohta heittää siitä eteenpäin, ja jonkin niistä lähelle osuva mutta mikään niistä olematon hylätään, ja lähin nimetään. Ohjattu luonnos tarjoaa ensimmäisen vaiheen, kun sen kohdat kertovat, mitä ne ovat (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): yhden valitseminen heittää seuraavaa taulukkoa, kuten siihen osuva heitto.
- **Molempiin suuntiin luettava:** `both_ways: true` d66-taulukossa lisää toisen lukutavan: 31 antaa myös 13:n, ja lukija valitsee.
- **Mitä kohta tarkoittaa:** `about: "Knows: {skills}. Also known as: {aka}."` täyttää kunkin kohdan tiedot (luettelo luetaan `a, b`; `{text}` on itse kohta) kertoakseen, mitä kohta antaa, kun valinta tarjoaa sitä; kohdan oma `note:` kertoo sen sen sijaan. Jos kumpaakaan ei ole, kohta, jonka tiedoissa on kompendiumin kohtaa nimeävä `id`, kuvataan sillä kompendiumin kohdalla.
- **Pakat ja pussit:** `deck: tarot` ja `cards` (tai `standard: true`); `bag: initiative` ja `tokens`.

Validointi tarkistaa, että jokainen nopilla mahdollinen tulos osuu johonkin kohtaan.

## Säännöt: `rules/`

```yaml
check: save
params: {who: ref, attr: {enum: [STR, DEX, WIL]}}
prompt: State the risk before rolling.
before: [{table: chart, with: {odds: $odds}, as: cell}]   # optional: steps first (a `roll` step can replace `roll:`)
roll: d20                              # or several: {action: "d6 + @stat", challenge: 2d10}
success: "@roll <= @who.$attr"         # or bands: {strong: "@roll >= 10", weak: "@roll >= 7", miss: else}
auto: {1: success, 20: failure}        # natural rolls
flags: {crit: "count(@roll.dice, 6) >= 2"}
on: {failure: ["The risk comes true."]}
options:                               # the roll comes back pending: `didact resolve r12 push`
  push: {label: "Push", steps: [{reroll: roll, keep_if: "@face == 6"}]}
```

Toiminnot ja menettelyt ovat vaiheluetteloita, ja laukaisimet ovat vaiheita, joilla on `when:`-ehto. Vaiheet ovat:

| Vaihe | Tekee |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | kirjatun heiton; sitoo `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; `{…}` täytetään ensin, kuten missä tahansa tekstissä, joten arvon tekstinä pitämät nopat heitetään (`{@{who.inventory.$item.damage}}`), ja loki näyttää ne: arvo, joka ei ole noppia, hylätään, samoin `roll: "@die"` tällaisella tekstillä, joka ei heitä mitään; heittojen joukko (`{d8, d6}kh1`) pysyy sellaisena |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | laskee arvoja; kuten `set`-vaiheen `value`-arvossa, `{…}`-teksti on malli ja pelkkä sana on tekstiä; kaikessa täytettävässä tekstissä `{{` ja `}}` kirjoittavat itse sulkeen |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (tai `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | muuttaa merkintää: validoituna, rajattuna, kumottavissa; `set: who.$attr` asettaa kentän, jonka parametri nimeää, ja `set: who.inventory.$item.damage` sen kantaman esineen avaimen (ks. Inventaario); `-=` poistaa arvon luettelosta, ja arvo, jota luettelossa ei ole, ei muuta mitään (huomautus kertoo sen; arvo, jota siinä ei voisi koskaan olla, hylätään); `unset:` poistaa kentän kuten `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | antaa merkinnälle esineen tai ottaa siltä sellaisen, kuten `inv add` ja `inv drop` tekevät: tiedot tulevat kompendiumista, yksilöivä osa nimestä riittää, ja tila sekä kentän koukut tarkistetaan |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | käyttää kannettua esinettä kuten `inv use`: käyttökerrat tai lataukset laskevat, kulutusnoppa heitetään ja se pienenee portaalla tuloksella 1–2, ja loppuun käytetty esine katoaa, ellei se lataudu uudelleen tai sitä pidetä; useista samannimisistä ensimmäinen, jolla on käyttökertoja jäljellä; sitoo arvot `@torch.out` (sen viimeinen käyttökerta meni), `@torch.gone` (siitä ei ole mitään jäljellä), `@torch.left`, `@torch.die` ja `@torch.rolled` (`as:` on oletuksena `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | luo merkinnän heti, kuvattuna samoin kuin luonnoksen `entity`-vaiheessa (alla) ja tarkistettuna arvojaan vasten; `as:` (muuten sen `key`, muuten sen tyyppi) sitoo sen merkintänä, jota luetaan ja muutetaan kuten `ref`-parametria (`pool: "@bleeding"`, `@bleeding.name`), eikä se ole koskaan parametrin nimi; ilman `key:`-avainta mitään kenttää ei tulkita avaimeksi (`kind: track` pysyy kirjoitetun mukaisena); jos samantyyppinen ja samanniminen merkintä on jo täällä, se otetaan sellaisenaan, joten uudelleen suoritettu sääntö ei tee mitään uutta |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | suorittaa tarkistuksen ja sitoo sen tuloksen |
| `do: other-action`, `with: {…}`, `as: trip` | suorittaa toisen säännön; `@trip` on sen tulos ja `@trip.<name>` se, mitä se sitoi (`@trip.found` sen `let: {found: 2}` -määrityksestä, `@trip.luck` sen `roll: d6`, `as: luck` -heitosta); `as:` on oletuksena sen tunniste |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | kirjatun taulukkoheiton; sitoo tekstin ja kohdan `data`-tiedot (`@scar.<key>` ja avain–arvo-rakenteen avaimet polkuina: `@scar.cost.hp`) sekä niiden taulukoiden tiedot, joista se heittää seuraavaksi; esineluettelo (`[Rope, {name: Laser, damage: d8}]`) luetaan esineiden niminä (`count(@scar.gear)`, `'Laser' in @scar.gear`), ja vaiheelle sellaisenaan annettuna (`apply: "@scar.gear"`) se on itse esineet; muiden avain–arvo-rakenteiden luettelon voi lukea vain vaihe |
| `table: "setting-{@drop.difficulty}-terrain"` | lasketun taulukon: `{…}` ja `$param` täytetään |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | useita tuloksia luettelona (`distinct` heittää toistot uudelleen) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | haarautumisen |
| `repeat: "@count"`, `as: i`, `steps: […]` | silmukan: suorittaa vaiheet annetun määrän kertoja, ja `@i` laskee 1:stä ylöspäin |
| `for: pcs` (tai `party`), `as: member`, `steps: […]` | suorittaa vaiheet kerran jokaiselle pelaajahahmolle (tai seurueen jäsenelle), joka on silloin `@member`: merkintä, kuten se, jonka `entity:` sitoo (`@member.name`, `set: member.fatigue`); `as:` ei voi koskaan olla parametrin nimi, joten säännön oma `who` pysyy sen omana |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | tulosteen LLM:lle |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (tai `every: 1 day`) | muistutuksen, joka erääntyy peliajan kuluessa, kuten ne, jotka `didact remind` asettaa |
| `reroll: roll`, `keep_if: "@face == 6"` | heittää osan heiton nopista uudelleen (push-mekaniikat) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | heittää luetteloarvosta (oraakkelin luettelot): sitoo kohdan, `@who.choose` (tyhjä rivi) ja `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | heittää laskurin hupenevan noppapoolin kuten `track roll` (nopat, joissa on 1-3, poistuvat; `drop`-nopat pudotetaan ensin, `extra`-nopat heitetään mukana) tai vain pudottaa noppia (`mode: drop`: push, rasti); linkitetyn poolin vaiheet ja poolin tapahtuma seuraavat; sitoo `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Tarkistuksen tuloksen voi lukea sen suorittanut sääntö (`check: … as: answer` antaa `@answer`), samoin sen liput: `'random-event' in @answer.flags`. `with:`-arvot lasketaan, kun niissä on `@`, täytetään, kun niissä on `$param` tai `{…}` (”Does $npc flee?”), ja välitetään muuten sellaisenaan. Sääntö, jolla on `oracle`-parametri, saa kampanjan oraakkelin tilamerkinnän pyytämättä. `ref`-parametri, jolla on `to: monster`, ottaa sen tyyppisen merkinnän: nimi, jonka jokin toinen merkintä jakaa (vihollisen pooli, nimetty korttinsa mukaan), tarkoittaa sitä, joka on tätä tyyppiä.

Laukaisimet suoritetaan itsestään, kun niiden tilanne koittaa, ja vain jos niiden `when:` pätee:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Mikä tahansa sääntö (myös generaattori ja hahmonluonti) voi lukea `@system` (sen systeemin tunniste, jota maailmassa pelataan, jotta kahdelle systeemille kirjoitettu pelimaailma voi erottaa ne toisistaan), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` ja `@time.is_night` sekä, jos kalenterissa on kuukausia, `@time.month`, `@time.month_name`, `@time.day_of_month` ja `@time.year`; kun taistelu on käynnissä, `@combat.round` ja `@combat.fighters` (taistelussa mukana olevien tunnisteet). Aikalaukaisin voi lukea myös `@time.passed`, juuri kuluneet sekunnit, `combat_start`- tai `combat_end`-laukaisin lukee alkavan tai päättyvän taistelun (`combat start` ja `combat end` suorittavat ne; taistelijan poistuminen ei päätä taistelua), ja laukaisimen suorittama sääntö lukee sen, minkä laukaisinkin lukee. Laukaisimen, jolla on pakollisia parametreja, suorittaa vain `didact do` tai kentän koukku (`who` = merkintä). `on: manual` -laukaisimet suoritetaan vain kutsuttaessa. `for: pcs` (tai `party`) suorittaa laukaisimen kerran jokaiselle pelaajahahmolle (tai seurueen jäsenelle), joka on silloin `who`: esimerkiksi kokemuspisteet jokaisen pelikerran jälkeen. Epäonnistuva laukaisin pysäyttää komennon, joka laukaisi sen, ja kertoo, mikä laukaisin se oli ja miten jatkaa ilman sitä (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalenteri on paketin `settings`-asetuksissa: pelimaailmapaketin kalenteri voittaa systeemin kalenterin, ja maailman oma kalenteri (`calendar:` sen tiedostossa `world.yaml`) voittaa molemmat:

```yaml
settings:
  watches: [morning, afternoon, night]   # the day's watches
  calendar:
    week: [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
    months: [{name: January, days: 31}, {name: February, days: 28, leap: [4, 100, 400]}, …]
    start: {year: 1890, month: 3, day: 14, weekday: Friday}   # where a campaign opens
    year: "{year} AD"                     # how a date writes its year
    seasons: [{name: spring, month: 3, day: 20}, …]           # each from its first day
    holidays: [{name: Midsummer, month: 6, day: 24, text: "…"}]
```

`leap: 4` tekee kuukaudesta päivää pidemmän joka 4. vuosi, ja `leap: [4, 100, 400]` joka 4. vuosi, mutta ei joka 100. vuosi, mutta kuitenkin joka 400. vuosi: kukin luku kumoaa edellisen. `weekday` nimeää alun viikonpäivän (muuten se on viikon ensimmäinen päivä), ja `year` on se, miten päivämäärä kirjoittaa vuotensa, sekä Didactin näyttämissä että sen lukemissa päivämäärissä (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` tarkistaa kaikki kolme. Kampanja voi alkaa kalenterin toisesta päivämäärästä, ennen sen alkua tai sen jälkeen: `didact campaign new <id> --date '4 July 1902'` tai `didact time set '<date>'` ennen kampanjan ensimmäistä pelikertaa. Päivämäärän eteen kirjoitettu viikonpäivä tarkistetaan: päivämäärä ratkaisee, ja huomautus kertoo, jos se osuu toiselle päivälle.

Asetukset ovat järjestelmän muunnelmia ja valinnaisia sääntöjä, jotka kukin kampanja valitsee nollasessiossa:

```yaml
option: lethality                       # rules read it as @option.lethality
ask: How deadly should it be?           # session zero asks it (in place of Didact's own of that key)
choices: {gentle: "…", standard: "As the book has it.", deadly: "…"}   # each with what it means
default: standard
---
option: supplies                        # a flag: on or off (@option.supplies is true or false)
kind: flag
ask: Can the PCs run out of supplies?
help: Each PC has a 4d Supplies pool.
---
option: flavor
choices: {heroic: "…", grimdark: "…"}
implies: {grimdark: {lethality: deadly, supplies: true}}   # a choice that sets others (a flag's: on)
```

`didact campaign profile lethality=deadly supplies=on` tallentaa ne (tai verkkosovelluksen Asetukset-sivu). Säännöt, hahmonluonti ja generaattorit lukevat ne (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): vastaus menee sen edelle, mitä toinen asetus tuo mukanaan, ja se oletusarvon edelle. Sitä, mitä asetus tuo mukanaan, seurataan loppuun asti (tyylilaji, joka asettaa tappavuuden, asettaa myös sen, mitä kyseinen tappavuus tuo mukanaan), ja kahdesta seurauksesta lähempi menee edelle. Katsaus luettelee ne, jotka poikkeavat oletusarvostaan, merkityksineen, jotta pelinjohtaja soveltaa sen, mihin säännöt eivät pysty. Generaattori, joka ei voi toimia niiden alla, pysähtyy `stop:`-askeleeseen syineen, eikä luonnosta synny.

## Oraakkelit: `oracles/`

```yaml
oracle: chart
title: Chart oracle
ask: chart-question          # the check that answers; it may take question, odds and oracle
odds: [unlikely, 50-50, likely]
meaning: [actions, descriptions]   # tables for `didact meaning` (a word from each)
state: {chaos: {start: 5, min: 1, max: 9}}  # kept per campaign; rules read @oracle.chaos
lists: {names: [threads, characters], method: sections}   # weighted lists (`didact lists`)
prompt: Interpret the answer in the fiction.
```

- **Kysyminen:** `didact ask '…' --odds likely` suorittaa `ask`-tarkistuksen. Vastaus on sen tulos (vyöhyke), ja sen liput kulkevat mukana.
- **Tila:** se on merkinnässä, jonka tarkistus saa nimellä `oracle`. Tarkistus muuttaa sitä komennolla `set: oracle.chaos += 1`.
- **Luettelot:** `lists: {names: […], method: sections, most: 3}` säilyttää painotettuja luetteloita tuossa merkinnässä. `didact lists add|drop|roll|show` hallitsee niitä, ja säännöt heittävät niistä `pick`-vaiheella. `sections` heittää ensin viiden rivin osion, sitten rivin sen sisältä (tyhjä rivi tarkoittaa, että valitset itse); `uniform` antaa jokaiselle riville saman mahdollisuuden.
- **Lisää tarkistukselle:** `didact ask '…' --with as_rule=true` välittää oraakkelin tarkistukselle ylimääräisiä parametreja.
- **Loki:** jokainen vastaus numeroidaan (`#o12`) ja kirjataan, ja `didact interpret o12 '…'` säilyttää sen, mitä se tarkoitti. Ydinpaketin `yes-no`-oraakkeli on varavaihtoehto.

## Generaattorit ja hahmonluonti: `generators/`, `chargen/`

Molemmat ovat menettelyjä, jotka rakentavat **luonnoksen**. Ne käyttävät kaikkia sääntöjen vaiheita (`roll`, `table`, `if`, `let`, `prompt`, …) sekä näitä:

| Vaihe | Tekee |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | lisää luonnokseen merkinnän (avaimet `poi-1`, `poi-2`, …); kenttä tai linkki, joka nimeää paketin kirjoittaman avaimen (`key:` tai `as:`-nimi), muuttuu commit-vaiheessa kyseisen merkinnän tunnisteeksi, joten valitse avaimia, joita mikään kenttä ei sisällä tekstinä (entiteetillä, jolla ei ole kumpaakaan, ei ole vaihdettavaa avainta); `from: "@relic.id"` ottaa sen pohjaksi kompendiumin kohdan (sen tyypin, nimen ja kentät) |
| `choose: {from: [a, b], as: x}` (tai `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | valinnan; ohjatussa tilassa luonnos odottaa `choose`-komentoa; `exclude` sulkee pois aiemmat valinnat (heitetty heitetään uudelleen); `records:` lisää tähän sen tyypin merkinnät tunnisteen mukaan (pelissä tehdyt); `answer:` tekee valinnan kysymättä, kun sen arvo on yksi vaihtoehdoista (hahmon oma polku) |
| `choose_or_roll: {table: backgrounds, as: background}` | valinnan, jonka nopat voivat tehdä; valitun kohdan tiedot ovat `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | heittää arvot hahmoon |
| `swap: {among: [STR, DEX, WIL], optional: true}` | vaihda kaksi arvoa keskenään tai pidä ennallaan |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | jaa kiinteä arvosarja |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | osta arvoja budjetin puitteissa (`default: random` käyttää sen satunnaisesti satunnaistilassa) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | luettelo menee inventaarioon; avain–arvo-rakenne asettaa kenttiä (luettelot yhdistetään) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | lisää hahmon (tai luonnoksen entiteetin) kenttään: luvut lasketaan yhteen, kaikki muu liitetään luetteloon; jos lisättävää ei ole, se ei haittaa |
| `remove: {field: talents, value: "@old"}` | poistaa jotain luettelokentästä (vaihdettu kyky, ratkaistu side); jos poistettavaa ei ole, se ei haittaa |
| `roll_tables: [physique, vice]` | heittää taulukoista `traits`-kenttään; kohdan `data.gear` menee inventaarioon ja `data.add: {gold: 20}` lisää kenttiin |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | nimen; `name: {prompt: …}` ilman mitään, mistä heittää, odottaa nimeä satunnaistilassakin |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | kysymys, johon mikä tahansa vastaus käy (tavoite, toisen merkinnän nimi): luonnos odottaa sitä satunnaistilassakin, ellei se ole valmiiksi täytetty; `field:` tallentaa vastauksen |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | pointcrawlin: kirjattu noppien pudotus, reitit (aina yhtenäiset), etäisyydet, piilotetut reitit (ks. alla) |

Karttavaihe ottaa lisää avaimia kirjojen noppienpudotusmenettelyjä varten:

| Avain | Tekee |
|---|---|
| `regions: terrain` | myös nämä entiteetit pudotetaan; jokainen paikka liittyy lähimpään (sen `region`) |
| `hidden: 6`, `conditional: 5` | d6 reittiä kohti: luvun kohdalla tai yli piilotettu tai ehdollinen reitti (piilotetut reitit eivät näy pelaajien kartalla) |
| `describe: [path-feature, path-condition]` | kullekin reitille heitettävät taulukot, tallennettuina sen `details`-tietoihin |
| `entrance: true`, `exit: true` | reunaa lähin paikka on sisäänkäynti; muut numeroidaan siitä alkaen reittejä pitkin (`map.n`), reitit johtavat siitä poispäin, ja uloskäynti on kaukainen paikka lähellä reunaa, numeroituna viimeisenä |
| `number: "{@dungeon_name}, room {@n}"` | nimeää numeroidut paikat uudelleen (niiden luonnosavaimet seuraavat: `room-1` on huone 1) |

Noppienpudotustaulukko voi nimetä seuraavat taulukot kohtiensa tiedoissa, jolloin menettely etenee kuten kirjassa: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, sitten `table: "{@drop.what}"`. Asettamattomat luettelokentät (conditions, lists, tags) luetaan tyhjinä luetteloina, joten `'deprived' in @who.conditions` toimii alusta asti.

```yaml
chargen: pc
creates: pc
modes: [random, guided]
steps:
  - choose_or_roll: {table: backgrounds, as: background, field: background}
  - apply: "@background.gear"
  - roll: {each: [STR, DEX, WIL], dice: 3d6}
  - swap: {among: [STR, DEX, WIL], optional: true}
  - name: {from: "@background.names"}
```

Hahmonluonti, jossa on `advances:`, muuttaa merkintää uuden tekemisen sijaan: systeemin tasonnousu.

```yaml
chargen: level-up
advances: pc                   # `didact char advance <pc>`, or Level up on its page
params: {who: ref}
steps:
  - if: "@who.xp < @who.level + 1"
    then: [stop: "{@who.name} needs more XP"]
  - apply: {level: "{@who.level + 1}", xp: "{@who.xp - @who.level - 1}"}
  - choose: {table: paths, as: path, answer: "@who.path"}     # the character's own: not asked
  - choose: {from: "@path.talents", records: talent, as: talent, exclude: "@character.talents"}
  - add: {field: talents, value: "@talent"}
```

- **Yksi merkintä:** generaattori, jolla on `creates: npc`, rakentaa sen merkinnän niin kuin hahmonluonti rakentaa hahmon (`apply`, `add`, `name`, `field:`); sen `entity`-vaiheet lisäävät merkintöjä sen rinnalle, ja linkki `to: character` osoittaa siihen.
- **Suorittaminen:** `gen run` ja `char new` tekevät luonnoksen (`#g7`, `#c3`) eivätkä kirjoita mitään. `stop:` lopettaa sen ilman luonnosta: kampanjan valintaa lukevan `if:`-ehdon alla sen vihje ohjaa valintoihin (`didact session zero`); muuten sen omat sanat kertovat, mitä tehdä sen sijaan.
- **Päättäminen:** `--prefill '{…}'` päättää asioita etukäteen sen nimen perusteella, jonka vaihe sitoo (`as:`): yksittäinen arvo vastaa jokaiseen esiintymään, luettelo yhteen esiintymään kukin alkio (luettelo `choose`-vaiheelle, jolla on `count`, on koko valinta). Myös `let`-arvot voi esitäyttää (`{"hp": 6}`), ja nimi, `ask` tai `let` säilyttää minkä tahansa tekstin sellaisenaan. Kun valitaan tunnetuista vaihtoehdoista (`choose`, taulukon kohta), arvo on se vaihtoehto, jonka se nimeää kirjoitettuna samoin tai eri kirjainkoolla, kohdan `id`:n perusteella tai siihen osuvalla heitolla (`{"group": 3}`), ja se tuo mukanaan kohdan tiedot; arvo, joka on lähellä jotakin vaihtoehtoa mutta ei ole mikään niistä, hylätään ja lähin vaihtoehto mainitaan, ja mikä tahansa muu on oma vastaus ilman tietoja. `--auto` (tai `char new --mode random`) antaa noppien päättää loput. Muuten luonnos odottaa jokaisen valinnan kohdalla.
- **Kuvaaminen:** valinta kertoo valitsevalle pelaajalle, mitä kukin vaihtoehto tarkoittaa: taulukon kohdan `note:` tai sen taulukon `about:`, muuten kompendiumin kohta, jonka se nimeää (sen tietojen `id`), tai se, joka vaihtoehto itse on (kompendiumin tunnuksista tehtävä valinta näyttää kunkin nimen): sen `tagline` ja `summary`, sen `description` tai `effect`, muuten sen tekstin ensimmäinen kappale.
- **Palaaminen:** `char back` (tai `gen back`) peruu viimeisimmän vastauksen, heiton tai muokkauksen, joten luonnos kysyy saman kysymyksen uudelleen; sen tekemät heitot merkitään kumotuiksi.
- **Jatkaminen:** jatkettu luonnos toistaa polkunsa: jokaisen heitetyn tai valitun arvon, kunkin kerran ja järjestyksessä (myös kartan noppien pudotuksen), joten mitään ei heitetä kahdesti eikä mikään jo päätetty muutu.
- **Kirjoittaminen:** `commit` kirjoittaa merkinnät arvojaan vasten tarkistettuina.
- **Kehittäminen:** `advances:`-luonnos alkaa merkinnän kopiosta (lomakkeensa oletusarvoineen), sen vaiheet lukevat merkinnän nimellä `@who` ja luonnoksen arvot nimellä `@character.*`, ja `commit` kirjoittaa vain sen, mikä muuttui, tarkistettuna samoin kuin `set`; sen `entity`-vaiheiden tekemät merkinnät (uuden siteen juonenlanka) luodaan sen rinnalle: linkki `to: character` osoittaa merkintään, ja kenttä, joka nimeää avaimen, sisältää sitä vastaavan merkinnän tunnisteen, kuten hahmoa luotaessa (`apply: {blood: "@pool"}`). `stop:` kertoo, miksi ei vielä (XP ei riitä), eikä luonnosta synny. Systeemi, jonka kehittyminen on yksi ainoa sääntö, nimeää sen sen sijaan hahmonluonnissaan: `advance: {rule: grow}`.
- **Tilat:** `modes: [guided]` pitää menettelyn vaihe vaiheelta etenevänä: `--mode random` hylätään.

## Kompendium, käsikirja ja sanasto

- **Kompendiumin kohdat** kirjoitetaan kuten `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Arvo `"roll 2d8"` heitetään, kun kohta luodaan peliin. Aja `didact spawn troll` tai tuo paketin kohdat maailmaan komennolla `didact compendium import <pack>` (`--type loc` ja `--tag coast` niille, joilla on jokainen annettu tunniste).
- **Useammalle systeemille:** ylimmän tason avain menee sinne, minne `set` sen laittaa: systeemin lohkoon, kun sen lomakkeessa on se kenttä, muuten kenttään `fields`. Kohta, jonka pelimaailma kirjoittaa useammalle kuin yhdelle systeemille, antaa kunkin systeemin luvut tämän omassa lohkossa (`mechanics: {my-system: {hp: 12}}`): `pack validate` tarkistaa jokaisen lohkon kyseisen systeemin lomaketta vasten, kun systeemi on asennettu, ja huomauttaa ylimmän tason avaimesta, joka on sekä siinä lomakkeessa että core-paketin lomakkeessa. Se, mitä lohko sanoo, pätee: lohkon `mechanics: {my-system: {role: tactician}}` rinnalla ylimmän tason `role: innkeeper` on core-paketin kenttä, samoin kuin kaikki, mikä on `fields:`-kohdan alla. Lohko, joka nimeää validoitavan paketin, tarkistetaan sitä pakettia vasten sellaisena kuin se on kansiossaan.
- **Käsikirjan osiot** menevät tiedostoihin `reference/*.md`, alkutietoineen (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` löytää ne; lainausmerkeissä oleva ilmaus, jota ei löydy, kokeillaan sana sanalta.
- **Sanasto** on `glossary.yaml`: `term: definition` tai luettelo muotoa `{term, definition, aliases, see}`. `didact define <term>` lukee sitä.

## Testit: `tests/`

```yaml
test: weather-lands     # roll a table many times: every roll must land
table: weather
times: 50
---
test: fair-save         # exact odds
odds: "d20 <= 10"
chance: 0.5
---
test: every-table       # each of the pack's tables (a lookup table once per key)
table: all
---
test: play              # a smoke-play script: real commands in a scratch library
script:
  - world new t --system {pack} --seed smoke    # seeded: it plays the same every time
  - new pc Hero --fill
  - run: do save who=hero attr=STR
    expect: "→"                                  # text the step must print (or a list)
  - run: table list
    expect_not: my-system.spell-fire             # text it must not print (or a list)
  - run: table roll my-system.spell-fire
    fails: true                                  # it must fail (`expect` reads its error too)
```

## Pakettien jakaminen ja poistaminen

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Pakettia, joka ilmoittaa `redistributable: false`, ei voi viedä.
- **core** on osa Didactia ja aina käytössä: jokainen systeemi rakentuu sen päälle, joten sitä ei voi poistaa käytöstä eikä sen asennusta voi poistaa.
- Muut Didactin mukana tulevat paketit ovat `.didactpack`-tiedostoja sen `packs/`-kansiossa. `pack list` näyttää ne, kunnes ne on asennettu, ja yhden asentaminen tuo mukanaan sen tarvitsemat paketit, jos nekin tulevat Didactin mukana.
- `pack update` etsii uudempia versioita Didactin `packs/`-kansiosta ja GitHubista (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` nimeää toisen paikan, tai ei mitään, jolloin ei etsitä). Uusi versio asennetaan vanhan rinnalle: kampanjat pitävät omansa, kunnes ajetaan `didact campaign upgrade`.
- Käytössä on kerrallaan vain yksi pelisysteemi: avoimen maailman. Maailma pitää systeemin, jolla se luotiin (`didact world new <id> --system <pack>`; ilman systeemiä luotu maailma ottaa ensimmäisen, jonka se saa, komennolla `pack enable` tai `world set system=`), sen kampanjat pelataan sillä, eikä pakettia, joka tarvitsee toisen systeemin (sille kirjoitettu pelimaailma), voi lisätä: toista systeemiä pelataan omassa maailmassaan.
- `uninstall` kieltäytyy, kun jokin maailma tai kampanja käyttää paketin ainoaa kopiota (`--force` poistaa sen silti). Sitä ei voi kumota: asenna .didactpack uudelleen.

## Sääntökirjasta paketiksi: tarkistuslista

Käy kirjan mekaniikat läpi tässä järjestyksessä. Jokainen vastaa jotakin yllä olevaa:

1. **Ratkaisu:** miten heitto onnistuu (tarkistus: `success`, `bands`, `auto`).
2. **Nopat:** erikoisnopat, symbolit, portaat (`dice.yaml`, nimetyt nopat, ketjut).
3. **Lomake:** ominaisuudet, johdetut luvut (`schemas/`, johdetut kentät).
4. **Resurssit:** osumapisteet, onni, momentum (resurssi- ja laskurikentät; `set`-vaiheet).
5. **Tilat:** olotilat ja niiden vaikutukset (`conditions`-kentät; `if`-vaiheet).
6. **Taistelu:** hyökkäykset, vahinko, aloite (toiminnot; `bag`/`deck` vuorojärjestykseen).
7. **Menettelyt:** tutkiminen, matkustus, seikkailujen välinen aika (menettelyt kehotteineen).
8. **Taulukot:** jokainen satunnaistaulukko (`tables/`; `pack import` Markdown-taulukoille).
9. **Bestiaari:** hirviöt ja sivuhahmot (`compendium/`).
10. **Esineet:** varusteet, loitsut, reliikit (`compendium/`, slots-kentät).
11. **PJ:n ohjeet:** periaatteet ja neuvot (`GUIDE.md`, `reference/`, tyyppien `guidance:`).
12. **Hahmonluonti:** miten hahmo tehdään (`chargen/`-menettely tai `roll:` jokaisessa kentässä).

Merkitse sivut `source:`-kenttään kaikkialla, jotta aukot tulevat näkyviin. Lisää smoke-play-testi, joka tekee hahmon, heittää tarkistuksen, taistelee ja suorittaa menettelyn.
