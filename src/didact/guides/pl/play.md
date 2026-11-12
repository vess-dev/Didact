<!-- translated from bef7b2c650cb -->
# Rozgrywanie sesji

Jak przebiega gra przez Didact: LLM prowadzi narrację, a Didact przechowuje każdy fakt, rzut i zmianę.

## Przed pierwszą sesją

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Świat zachowuje system, z którym go utworzono, a jego kampanie grają w tym systemie: w innym systemie gra się w osobnym świecie. `didact campaign close` odkłada kampanię (jej świat pozostaje otwarty), a `didact campaign open <id>` wznawia ją tam, gdzie została przerwana, razem z sesją i całą resztą.

`didact world delete <id>` i `didact campaign delete <id>` usuwają świat lub kampanię, najpierw pokazując podgląd; `--yes` usuwa, a `didact undo` przywraca wszystko.

`session zero` wyświetla pytania do ustalenia z graczem. Najpierw te z pakietu. Należą do nich opcje systemu (jego warianty i reguły opcjonalne): jego reguły idą za odpowiedziami, a podsumowanie mówi, co znaczy każda zmieniona opcja. Każda odprawa zawiera odpowiedzi.

## Sesja

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Tury:** każda wiadomość gracza otwiera turę (hook Claude Code wywołuje `didact capture`, a inni klienci używają `turn begin`). `didact undo --turn` cofa wszystko, co zrobiono w odpowiedzi na tę wiadomość: zmiany, wydarzenia i rzuty. Transkrypcja to zachowuje.
- **Powrót do zmiany:** `didact undo --to e40` wycofuje wszystko po #e40, od najnowszego (`--dry-run` to wypisuje): każda zmiana zostaje cofnięta, a każdy rzut oznaczony jako cofnięty. Nic nie jest usuwane: `redo` albo powrót do późniejszej zmiany to przywraca.
- **Czas:** `didact time advance 1 watch` odlicza timery, przywołuje przypomnienia i uruchamia wyzwalacze czasowe. `didact remind --list` pokazuje nadchodzące przypomnienia, a `didact remind --cancel 2` anuluje jedno. Kampania zaczyna się na początku kalendarza albo w dniu, który podaje `campaign new --date '4 July 1902'`, a `didact time set '<date>'` zmienia go do pierwszej sesji.
- **Miejsca:** `didact visit <place>` przenosi drużynę i oznacza miejsce jako odwiedzone. `didact map` pokazuje to, co zna drużyna, a niezbadane wyjście to `?`.
- **Walki:** `didact combat start --party troll`, potem `combat next`, `combat hit freya troll weapon=d8` i `combat end`. Walczący przychodzą i odchodzą w trakcie walki: `didact combat join wolf-2` (w trybie indywidualnym rzucają na inicjatywę) i `didact combat leave troll --why fled`. Niczyja tura nie przepada.
- **Rzeczy:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (albo do skrzyni, albo na miejsce); `didact where rope` ją odnajduje. `inv add` znajduje przedmiot z kompendium po jego identyfikatorze, nazwie lub aliasie.
- **Twoje notatki:** `didact about sweeney plan='…' doing='…' where='…'` przechowuje to, co postanowiłeś o kimkolwiek lub czymkolwiek. Gracze widzą tylko `looks`. `didact log … --about sweeney` umieszcza wydarzenie w jego wpisie (`--secret`, jeśli gracze go nie widzą). Więcej w `didact guide details`.
- **Świat idzie naprzód:** `didact faction turn` oraz zegary: `didact track new 'The flood' --size 6`. Polecenie przyjmujące tylko jeden rodzaj wpisu bierze nazwę, którą dzielą inne, jako ten rodzaj: `didact track roll draugr` rzuca pulą nazwaną od wroga (tak samo `track tick` licznik, `quest done` zadanie i `visit` miejsce).

## Wyrocznie, generatory i postacie

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

Nic, co tworzy generator lub tworzenie postaci, nie zostaje zapisane przed `commit`. Opisz w `--prefill`, czego chce gracz, a procedura uzupełni luki. Pytanie wymienia, co oznacza każda opcja, gdy podaje to pakiet (`- Cutpurse: …`): powiedz to graczowi, żeby wybierał, wiedząc, co dostaje.

## Sekrety

Widoki są domyślnie bezpieczne dla graczy: `show`, `find`, `sheet`, `map`, `brief`. Pomijają:
- tajne wpisy (`knowledge: secret`);
- sekcje `## Secrets` i `## GM notes`;
- pola `secret: true`.

`--gm` pokazuje wszystko. Gdy gracze czegoś się dowiedzą:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` zapisuje to, co wiedzą gracze, jako małą stronę internetową do udostępnienia albo czytania na telefonie: drużynę, stronę dla każdego wpisu, dziennik i mapę. Zawsze jest bezpieczna dla graczy, a ponowny eksport do tego folderu ją aktualizuje. `didact export --as lonelog` zapisuje dziennik w notacji Lonelog (`@ ? d: -> =>`, sceny jako `S1`, tagi w rodzaju `[N:Sweeney]`), również bezpieczny dla graczy.

## Wiedza: co wraca, gdy coś zostanie wspomniane

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Co się liczy:** każdy BN, miejsce, przedmiot i frakcja to karta, której kluczami są nazwa i aliasy. Hasła wiedzy mają `keys`, a rozstrzygnięcia pojawiają się przez swoją zasadę. Dopasowanie działa na całych słowach, a liczba mnoga też się liczy („wolves” pasuje do `wolf`).
- **Kiedy pojawia się wiedza:** hook Claude Code skanuje każdą wiadomość gracza. `log`, `scene new` i `show` też dołączają nowo wywołaną wiedzę, a hasło nie powtarza się przez kilka tur.
- **Dostrajanie hasła:** `--secondary` z `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (w turach lub scenach), `--constant` (zawsze w odprawie) i `--no-recurse`.
- **Zakresy:** hasła trafiają do kampanii, chyba że `--scope` wskazuje świat, system lub zakres globalny. Skan widzi tylko tę kampanię, jej świat, jej system i zakres globalny, nigdy inny świat. Węższe hasło o tym samym identyfikatorze przesłania szersze.
- **Lorebooki innych narzędzi:** `didact lore import <file>` czyta World Info z SillyTavern (także z KoboldAI), lorebook karty postaci i `.lorebook` z NovelAI; `didact lore export --to <file>` zapisuje World Info. Klucze, logika, priorytet, prawdopodobieństwo, grupy i czas są przenoszone.

## Zmiany w fabule

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` zmienia fakt, ale zachowuje starą wartość. Oznacza też podsumowania wspominające Sweeneya jako nieaktualne, a `audit` to wymienia.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` zapisuje rozstrzygnięcie. Pojawia się ono potem w `rules lookup` i przy uruchomieniu tej zasady.
- `didact name npc` losuje nowe imię, nigdy takie, którego świat już używa. Zanim wymyślisz własne, sprawdź je przez `didact names check <name>`. `didact names forget <name>` znów je zwalnia.

## Porządki

- `didact history --clear` pokazuje, co usunęłoby wyczyszczenie starej historii; `--yes` usuwa to na dobre, łącznie z usuniętymi wpisami, a cofanie, `diff`, `rewind` i starsze punkty zapisu przestają do tego sięgać (`--before e120` zachowuje tę zmianę i późniejsze, `--rolls` usuwa też zapis kości). Najpierw uruchom `didact snapshot`.
- `didact save --remove 'before the dragon'` usuwa punkt zapisu; `didact undo` go przywraca.
- `didact transcript 3 --clear` usuwa transkrypcję sesji 3 (`--clear --all`: wszystkich sesji). `didact undo` ją przywraca, a tekst zostaje w historii aż do `history --clear`.
- `didact compendium remove <entry>` usuwa dodaną przez ciebie pozycję; wpisy z niej utworzone zostają.
- `didact snapshot --keep 3` usuwa wszystkie kopie zapasowe poza trzema najnowszymi, a `didact snapshot --remove <name>` usuwa jedną. Żadnego z nich nie da się cofnąć.
- `didact session end` sam robi kopię zapasową biblioteki (`snapshot-<time>-auto.zip`), zachowując pięć najnowszych takich kopii; `didact snapshot --list` je oznacza.
- `didact reset` pokazuje, co zabrałoby opróżnienie biblioteki; `--yes` przywraca ją do stanu jak po świeżej instalacji: znikają wszystkie światy, kampanie i wpisy, historia i indeks wyszukiwania, a następna zmiana znów ma numer #e1. Najpierw robi kopię zapasową biblioteki (`…-before-reset.zip`), a kopie zapasowe zostają, podobnie jak zainstalowane pakiety, chyba że podasz `--packs`. Aby zamiast tego wypróbować Didact na gotowej kampanii, `didact sample` buduje przykładową kampanię w pustej bibliotece (`--home` daje jej osobny folder), a `didact serve --demo` serwuje ją za każdym razem od nowa.
- `didact snapshot --restore <name>` pokazuje zawartość kopii zapasowej obok obecnej biblioteki; `--yes` robi kopię zapasową biblioteki w obecnym stanie (`…-before-restore.zip`), a potem wstawia kopię na jej miejsce. Numeracja zmian i rzutów biegnie dalej. Cofanie nie wycofa przywrócenia: przywrócenie tamtej kopii bezpieczeństwa już tak.
