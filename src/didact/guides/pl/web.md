<!-- translated from 5a088227a31a -->
# Aplikacja w przeglądarce

`didact serve` otwiera twoją bibliotekę w przeglądarce: przeglądaj i edytuj wpisy, zobacz na grafie, jak są ze sobą powiązane, czytaj dziennik, uruchamiaj zasady i tabele i używaj każdego polecenia przez formularz.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Działa offline: czcionki i ikony są dołączone do Didact.

**Tryb demo.** `--demo` serwuje przykładową kampanię (`didact sample`: dolina rzeki, BG, osoby z notatkami MG, miejsca i ścieżki, misja, zegar i trwająca sesja z walką) z osobnej biblioteki, obok folderu pamięci podręcznej Didact. Są w niej zainstalowane wszystkie pakiety dostarczane z Didactem. Przy każdym uruchomieniu `--demo` jest budowana od nowa, więc próbuj, czego chcesz: twoja biblioteka pozostaje nietknięta.

## Opcje

| Opcja | Domyślnie | Co robi |
|---|---|---|
| `--port <n>` | 8765 | port, na którym nasłuchuje |
| `--host <address>` | 127.0.0.1 | adres, na którym nasłuchuje: tylko ten komputer |
| `--open` | wył. | otwiera aplikację w karcie przeglądarki |
| `--gm` | wył. | uruchamia z włączonym widokiem MG |
| `--demo` | wył. | serwuje świeżą przykładową kampanię zamiast twojej biblioteki |

Globalne `--home`, `--world` i `--campaign` dotyczą wszystkiego, co robi aplikacja. Otwarcie innego świata lub kampanii na stronie Biblioteka przełącza na nie, tak jak `didact world use` i `didact campaign open`, a Zamknij odkłada otwartą kampanię (`didact campaign close`).

## Co zawiera

- **Przegląd:** odprawa (świat, kampania, sesja, scena, drużyna, co nadchodzi), szybkie akcje (rzut kośćmi, pytanie do wyroczni z szansami, które zna, zanotowanie wydarzenia, rozpoczęcie lub zakończenie sesji, nowy wpis) i ostatnie zmiany.
- **Stan:** sytuacja w skrócie: sesja i scena, czas i nadchodzące przypomnienia, liczby i ekwipunek każdego członka drużyny, walka (czyja tura, stany), otwarte misje i liczniki oraz miejsce, w którym jest drużyna, wraz z wyjściami. Liczby można poprawiać na miejscu: − i + przy statystyce, zaznaczenie licznika, użycie lub wyrzucenie przedmiotu, dodanie nowego, ukończenie misji, przesunięcie czasu (liczba i jednostka znana kalendarzowi: godziny, warty, dni, …), ustawienie przypomnienia (jednorazowego lub cyklicznego) i anulowanie go.
- **Wpisy:** wszystkie wpisy pogrupowane według typu, z polem filtra i przełącznikami: wszystkie, świat, kampania. Strona wpisu pokazuje jego kartę, opis, szczegóły, pola, zawartość, powiązania w obie strony, kronikę i historię, z formularzami do zmiany każdego z nich oraz do archiwizacji lub usunięcia wpisu. Postać, której system ma awans na wyższy poziom, ma przycisk Level up (`char advance`): szkic, który pokazuje, co się zmienia, przed i po, dopóki nie zostanie zatwierdzony.
- **Szkice:** tworzenie postaci i generatory, krok po kroku. Utwórz postać (krok po kroku lub losowo, z wyborem rodzaju, gdy system ma ich kilka: bohater gracza, najemnik, …) i Generuj… są na stronach Wpisy; oczekujące szkice są wymienione tam i w Przeglądzie. Strona szkicu pokazuje, co zawiera do tej pory (jego obiekty i ich pola, mapę narysowaną przez generator, rzuty, pytania z podręcznika), i pytanie, na które czeka. Każda opcja to przycisk, który mówi, co oznacza, gdy podaje to pakiet (co daje pochodzenie, co robi talent); gdy wybiera się kilka, przy każdej jest pole do zaznaczenia; wartości kupowane z budżetu to liczby, które na bieżąco liczą punkty; imię lub inną otwartą odpowiedź można wpisać; a Niech zdecydują kości rzuca tylko na ten jeden wybór (`char roll c3 --one`). Wstecz cofa ostatni krok, więc jego pytanie pada znowu (`char back c3`: rzuty, które wykonał, zostają oznaczone jako cofnięte, a Cofnij przywraca krok). Potem Rzuć na resztę, Edytuj, Odrzuć… (najpierw pyta) i Zatwierdź, który otwiera wpis nowej postaci albo wymienia, co utworzył generator. Szkic generatora należy do MG: widok graczy pokazuje tylko, że istnieje.
- **Graf:** wpisy jako węzły, powiązania jako krawędzie. Przeciągaj węzły, przeciągnij tło, by przesunąć widok, powiększaj kółkiem myszy; najedź na wpis, by podświetlić jego sąsiadów; kliknij, by go otworzyć. Przycisk Graf na stronie wpisu pokazuje tylko jego otoczenie.
  - **Mapa** (przełącznik nad grafem albo Otwórz mapę na stronie Stan): miejsca, które zna drużyna, ścieżki między nimi (z etykietami droga, szlak, …), region, w którym leży każde z nich (linią przerywaną), i miejsce, gdzie jest drużyna. Ścieżka do jeszcze nieodkrytego miejsca prowadzi do „?”; widok MG pokazuje wszystkie miejsca.
- **Dziennik:** sesje, z których każda rozwija się w sceny, wydarzenia i rzuty. Każde wydarzenie ma Edytuj i Usuń (po najechaniu na nie), które otwierają formularze `beat edit` i `beat rm`.
- **Podręcznik:** przeszukuj wszystko (wyniki pojawiają się w trakcie pisania), uruchamiaj zasady włączonych pakietów z formularzy, rzucaj na ich tabele i czytaj tekst zasad, słowniczek i poradniki.
- **Biblioteka:** światy i kampanie (otwórz, zamknij, utwórz, usuń), pakiety (każdy z opisem, czym jest; włącz, wyłącz, zainstaluj, odinstaluj; pakiety dołączone do Didact mają przycisk Zainstaluj), historia (Cofnij, Ponów, Wróć do zmiany, Wyczyść), punkty zapisu (wróć do punktu, usuń) i kopie zapasowe (zrób kopię zapasową teraz, przywróć, usuń, zachowaj kilka najnowszych; te zrobione na koniec sesji mają oznaczenie auto). Gdy żadna kampania nie jest otwarta, Przegląd wyświetla kampanie świata, by można było którąś otworzyć.
  - Usunięcie świata lub kampanii wymaga najpierw potwierdzenia, a Cofnij przywraca wszystko.
  - Wróć do zmiany (obok każdej zmiany) wycofuje wszystko, co było po tej zmianie (`didact undo --to e40`): jego strona najpierw wymienia, co zniknie. Każda zmiana zostaje cofnięta, a każdy rzut oznaczony jako cofnięty, ale nic nie jest usuwane: Ponów albo powrót do późniejszej zmiany je przywraca. Pokaż starsze zmiany wyświetla więcej historii.
  - Pakiet core jest zawsze włączony. Naraz w użyciu jest jeden system gry: system otwartego świata, który zachowuje go na stałe (wybrany przy tworzeniu świata). W innym systemie gra się w osobnym świecie: jego wiersz otwiera świat, który w nim gra, lub tworzy nowy. Odinstalowania pakietu nie da się cofnąć: zainstaluj ponownie jego .didactpack.
  - Czyszczenie historii najpierw pokazuje dokładnie, co zniknie i co przestanie działać, z przyciskiem, by najpierw zrobić kopię zapasową. Tego nie da się cofnąć, podobnie jak usunięcia kopii zapasowej.
  - Zacznij od nowa: **Resetuj…** opróżnia bibliotekę, jakby Didact był świeżo zainstalowany, a numeracja zaczyna się znów od #e1. Jego strona najpierw pokazuje, co zniknie. Najpierw powstaje kopia zapasowa biblioteki, a kopie zapasowe zostają (zainstalowane pakiety też, chyba że zaznaczysz pole).
  - Przywracanie kopii zapasowej najpierw pokazuje jej zawartość obok obecnej biblioteki. Dotychczasowa biblioteka zostaje najpierw zapisana w kopii zapasowej: Cofnij nie wycofa przywrócenia, ale przywrócenie tamtej kopii już tak.
- **Polecenia:** każde polecenie jako formularz oraz pole, które przyjmuje cały wiersz poleceń. Każde pole przyjmuje to, co przyjmuje jego argument: liczbę, identyfikator lub zdarzenie (`e12`) według swojego wzorca, ilość czasu gry jako liczbę i jednostkę oraz listę do wyboru spośród tutejszych wpisów, szkiców, pakietów, punktów zapisu, wyroczni, tabel i zasad.
- **Ustawienia:** opcje kampanii (warianty i reguły opcjonalne jej systemu, za którymi idą reguły, tworzenie postaci i generatory; każda mówi, co robi: reguła opcjonalna — co zmienia jej włączenie, wybór — co oznacza każda z jego wartości, a wartość domyślna ustawiana przez inną opcję — która to opcja), język aplikacji, tezaurus (język, z którego wyszukiwanie bierze synonimy: pobierz jeden, z paskiem postępu, przełączaj się między pobranymi, usuń jeden) i dokumentacja kodu.
  - Aplikacja, jej poradniki i to, co pokazują w niej polecenia, są dostępne w 24 językach. Jeśli nic nie wybierzesz, aplikacja używa języka przeglądarki. Wiersz poleceń i korzystające z niego modele językowe pozostają po angielsku: wybrany tu język dotyczy tylko aplikacji.
  - Przycisk kodu na pasku nagłówka otwiera dokumentację API kodu. Jest budowana z kodu za pierwszym razem i ponownie przy każdej zmianie kodu (`didact docs build`).

Każda zmiana uruchamia prawdziwe polecenie `didact`, więc jest sprawdzana, zapisywana w logu i możliwa do cofnięcia dokładnie tak jak w wierszu poleceń. Aplikacja za każdym razem pokazuje uruchomione polecenie (`didact set sweeney hp-=2`), z przyciskiem Cofnij, gdy jest co cofnąć.

Pole formularza przyjmuje tylko to, co przyjmuje jego polecenie. Identyfikator (świata lub kampanii) i typ wpisu przyjmują małe litery, cyfry i myślniki: w trakcie pisania spacje zamieniają się w myślniki, a wielkie litery w małe. Nazwa pola wpisu nie przyjmuje spacji (zamieniają się w podkreślenia), nazwa szczegółu to jedno słowo, a pola liczbowe przyjmują liczby. To, co przyjmuje pole formularza, jest napisane pod nim, a polecenie i tak sprawdza to ponownie.

Zapis nigdy nie nadpisuje zmiany, której nie widziałeś. Jeśli wpis zmienił się po wyświetleniu strony (na przykład LLM zmienił go z wiersza poleceń albo zrobiła to inna karta), zapis zostaje odrzucony z informacją, co jest tam teraz. Opis, który edytowałeś, zostaje w edytorze obok nowej wersji, do scalenia i ponownego zapisu. − i + zawsze przechodzą: sumują się.

## Widok graczy i widok MG

Aplikacja pokazuje to, co wiedzą gracze, tak jak `didact show`: tajne wpisy, sekcje `## Secrets`, tajne pola i szczegóły tylko dla MG pozostają ukryte. Przycisk **GM** na pasku nagłówka włącza widok MG, a baner to sygnalizuje („Widok MG: spoilery widoczne”). Przeglądarka zapamiętuje wybór.

W widoku graczy:
- opisu z wierszami tylko dla MG nie da się edytować (zapis by je usunął): najpierw włącz widok MG;
- szczegółu MG ani tajnego pola, których strona nie pokazuje, nie da się nadpisać, choć można dodać nową notatkę dla MG;
- historia podaje polecenie i wpisy znane graczom (`set · Freya`), nigdy wartości, a Cofnij mówi, którą zmianę wycofało, a nie na czym polegała.

## Bezpieczeństwo

Aplikacja może zmieniać twoją bibliotekę, więc domyślnie nasłuchuje tylko na tym komputerze.

- `--host` z innym adresem pozwala łączyć się z nią innym komputerom, a Didact o tym ostrzega. Używaj tego tylko w sieci, której ufasz.
- Odpowiada tylko na żądania skierowane do niej samej (jej własny adres, `localhost`, `127.0.0.1` lub `[::1]`, z jej portem). Dzięki temu inne strony nie dotrą do niej przez sztuczki z DNS.
- Każda zmiana wymaga formularza z samej aplikacji: tajny token w każdym formularzu musi pasować do ciasteczka, którego inne strony nie mogą odczytać ani wysłać.
- Nie ma logowania. Każdy, kto może używać przeglądarki na tym komputerze, może używać aplikacji.
