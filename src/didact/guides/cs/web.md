<!-- translated from 5a088227a31a -->
# Aplikace v prohlížeči

`didact serve` otevře vaši knihovnu ve webovém prohlížeči: procházejte a upravujte záznamy, podívejte se v grafu, jak jsou propojené, čtěte deník, spouštějte pravidla a tabulky a používejte každý příkaz přes formulář.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Funguje offline: písma a ikony jsou součástí Didactu.

**Ukázkový režim.** `--demo` nabídne ukázkovou kampaň (`didact sample`: říční údolí, hráčská postava, osoby s poznámkami PJ, místa a cesty, mise, hodiny a rozehrané sezení s bojem) z vlastní knihovny vedle složky mezipaměti Didactu. Jsou v ní nainstalované všechny balíčky, které se s Didactem dodávají. Při každém spuštění `--demo` se sestaví znovu, takže zkoušejte cokoli: vaší knihovny se to nedotkne.

## Volby

| Volba | Výchozí | Co dělá |
|---|---|---|
| `--port <n>` | 8765 | port, na kterém naslouchá |
| `--host <address>` | 127.0.0.1 | adresa, na které naslouchá: jen tento počítač |
| `--open` | vyp. | otevře aplikaci v kartě prohlížeče |
| `--gm` | vyp. | spustí se se zapnutým pohledem PJ |
| `--demo` | vyp. | místo vaší knihovny nabídne novou ukázkovou kampaň |

Globální `--home`, `--world` a `--campaign` platí pro vše, co aplikace dělá. Otevření jiného světa nebo kampaně na stránce Knihovna na ně přepne, stejně jako `didact world use` a `didact campaign open`, a Zavřít otevřenou kampaň odloží (`didact campaign close`).

## Co v ní najdete

- **Přehled:** briefing (svět, kampaň, sezení, scéna, družina, co je na řadě), rychlé akce (hod kostkami, otázka orákulu se šancemi, které zná, zápis události, začátek či konec sezení, nový záznam) a nejnovější změny.
- **Stav:** jak věci stojí, na první pohled: sezení a scéna, čas a nadcházející připomínky, čísla každého člena družiny a co nese, boj (kdo je na tahu, stavy), otevřené mise a počítadla a kde je družina, i s cestami dál. Čísla jde upravit přímo tam: − a + u statistiky, odškrtnout počítadlo, použít nebo zahodit předmět, přidat nový, dokončit misi, posunout čas (číslo a jednotka, kterou kalendář zná: hodiny, hlídky, dny, …), nastavit připomínku (jednorázovou, nebo opakovanou) a nějakou zrušit.
- **Záznamy:** všechny záznamy seskupené podle typu, s filtrem a přepínači vše, svět a kampaň. Stránka záznamu ukazuje jeho kartu, popis, podrobnosti, pole, obsah, odkazy oběma směry, kroniku a historii, s formuláři pro změnu každé z těchto částí a pro archivaci či smazání záznamu. Postava, jejíž systém má zvyšování úrovně, má tlačítko Level up (`char advance`): koncept, který ukazuje, co se mění, před a po, dokud ho nepotvrdíte.
- **Koncepty:** tvorba postav a generátory, krok za krokem. Vytvořit postavu (krok za krokem nebo náhodně, s výběrem druhu, když jich systém má víc: hráčská postava, najatý pomocník, …) a Generovat… najdete na stránkách Záznamy; čekající koncepty jsou vypsané tam i v Přehledu. Stránka konceptu ukazuje, co zatím obsahuje (své entity a jejich pole, mapu, kterou nakreslil generátor, hody, otázky z knihy), a otázku, na kterou čeká. Každá možnost je tlačítko, které říká, co znamená, pokud to balíček uvádí (co dává zázemí, co dělá talent); při výběru několika možností má každá své políčko k zaškrtnutí; hodnoty nakupované z rozpočtu jsou čísla, která průběžně sčítají body; jméno nebo jinou volnou odpověď lze napsat; a Nechat rozhodnout kostky hodí jen na tuto jednu volbu (`char roll c3 --one`). Tlačítko O krok zpět vrátí poslední krok, takže jeho otázka přijde znovu (`char back c3`: hody, které v něm padly, se označí jako vrácené, a vrácení této změny krok obnoví). Pak Hodit na zbytek, Upravit, Zahodit… (nejdřív se zeptá) a Potvrdit, které otevře záznam nové postavy, nebo vypíše, co generátor vytvořil. Koncept generátoru patří PJ: pohled hráčů ukáže jen, že existuje.
- **Graf:** záznamy jako uzly a odkazy jako hrany. Uzly přetahujte, tažením pozadí posouvejte, kolečkem přibližujte; najetím zvýrazníte sousedy záznamu; kliknutím ho otevřete. Tlačítko Graf na stránce záznamu ukáže jen jeho okolí.
  - **Mapa** (přepínač nad grafem nebo Otevřít mapu ve Stavu): místa, která družina zná, cesty mezi nimi (s popisky silnice, stezka, …), oblast, ve které každé leží (čárkovaně), a kde je družina. Cesta k dosud nenalezenému místu vede k „?“; pohled PJ ukáže všechna místa.
- **Deník:** sezení, každé se rozbalí do scén, událostí a hodů. Každá událost má Upravit a Odebrat (po najetí myší), které otevřou formuláře `beat edit` a `beat rm`.
- **Příručka:** prohledávejte vše (výsledky se objevují během psaní), spouštějte pravidla zapnutých balíčků z formulářů, házejte na jejich tabulky a čtěte text jejich pravidel, glosář a průvodce.
- **Knihovna:** světy a kampaně (otevřít, zavřít, vytvořit, smazat), balíčky (každý s popisem, co je zač; zapnout, vypnout, nainstalovat, odinstalovat; balíčky dodávané s Didactem mají tlačítko Nainstalovat), historie (Zpět, Znovu, Skočit zpět, Vymazat), body uložení (vrátit se, odebrat) a zálohy (zálohovat teď, obnovit, smazat, ponechat několik nejnovějších; ty vytvořené při ukončení sezení jsou označené auto). Když není otevřená žádná kampaň, Přehled vypíše kampaně světa, abyste mohli některou otevřít.
  - Smazání světa nebo kampaně se nejdřív zeptá a Zpět vše vrátí.
  - Skočit zpět (u každé změny) vezme zpět vše po té změně (`didact undo --to e40`): jeho stránka nejdřív ukáže, co vezme zpět. Každá změna bude vrácena a každý hod označen jako vrácený, nic se nesmaže: Znovu nebo skok zpět na pozdější změnu je obnoví. Zobrazit starší změny vypíše další část historie.
  - Balíček core je vždy zapnutý. V jednu chvíli se používá jeden herní systém: ten otevřeného světa, který si ho ponechá natrvalo (volí se při vytvoření světa). Jiný systém se hraje ve vlastním světě: jeho řádek otevře svět, který se podle něj hraje, nebo vytvoří nový. Odinstalování balíčku nelze vrátit zpět: znovu nainstalujte jeho .didactpack.
  - Vymazání historie nejdřív přesně ukáže, co zmizí a co přestane fungovat, s tlačítkem, kterým můžete nejdřív zálohovat. Nelze ho vrátit zpět, stejně jako smazání zálohy.
  - Začít znovu: **Resetovat…** vyprázdní knihovnu, jako by byl Didact čerstvě nainstalovaný, a číslování začne znovu od #e1. Jeho stránka nejdřív ukáže, co zmizí. Knihovna se nejdřív zazálohuje a zálohy zůstanou (i nainstalované balíčky, pokud nezaškrtnete políčko).
  - Obnovení zálohy nejdřív ukáže, co záloha obsahuje, vedle současné knihovny. Dosavadní knihovna se nejdřív zazálohuje: Zpět obnovení nevrátí, obnovení té zálohy ano.
- **Příkazy:** každý příkaz jako formulář a pole, které přijme celý příkazový řádek. Každé pole přijme to, co přijímá jeho argument: číslo, ID nebo událost (`e12`) podle svého vzoru, množství herního času jako číslo a jednotku a seznam k výběru ze záznamů, konceptů, balíčků, bodů uložení, orákul, tabulek a pravidel, které tu jsou.
- **Nastavení:** volby kampaně (varianty a volitelná pravidla jejího systému, kterými se řídí pravidla, tvorba postav i generátory; u každé je popsáno, co dělá: u volitelného pravidla, co změní jeho zapnutí, u volby z několika hodnot, co znamená každá z nich, a výchozí hodnota, kterou určuje jiná volba, řekne kterou), jazyk aplikace, tezaurus (jazyk, ze kterého hledání bere synonyma: stáhnout jeden, s ukazatelem průběhu, přepínat mezi staženými, odebrat jeden) a dokumentace kódu.
  - Aplikace, její průvodci i to, co v ní příkazy zobrazují, jsou ve 24 jazycích. Když žádný nevyberete, aplikace se řídí jazykem prohlížeče. Příkazový řádek a jazykové modely, které ho používají, zůstávají v angličtině: zde zvolený jazyk platí jen pro aplikaci.
  - Tlačítko kódu v záhlaví otevře dokumentaci API kódu. Sestaví se z kódu napoprvé a znovu pokaždé, když se kód změní (`didact docs build`).

Každá změna spouští skutečný příkaz `didact`, takže je ověřená, zapsaná do protokolu a vratná přesně jako na příkazovém řádku. Aplikace pokaždé ukáže příkaz, který spustila (`didact set sweeney hp-=2`), s tlačítkem Zpět, když je co vrátit.

Pole přijme jen to, co přijme jeho příkaz. ID (světa nebo kampaně) a typ záznamu přijmou malá písmena, číslice a pomlčky: mezery se během psaní změní na pomlčky a velká písmena na malá. Název pole záznamu nepřijme mezery (změní se na podtržítka), název podrobnosti je jedno slovo a číselná pole přijmou jen čísla. Co pole přijme, je napsáno pod ním, a příkaz to stejně ověří znovu.

Uložení nikdy nepřepíše změnu, kterou jste neviděli. Pokud se záznam změnil poté, co ho stránka zobrazila (třeba ho z příkazového řádku změnil LLM nebo jiná karta), uložení se odmítne a řekne, co tam je teď. Popis, který jste upravovali, zůstane v editoru vedle nové verze, abyste je sloučili a uložili znovu. − a + projdou vždy: sčítají se.

## Pohled hráčů a pohled PJ

Aplikace ukazuje, co vědí hráči, stejně jako `didact show`: tajné záznamy, sekce `## Secrets`, tajná pole a podrobnosti jen pro PJ zůstávají skryté. Tlačítko **GM** v záhlaví zapne pohled PJ a oznámí to pruh s upozorněním („Pohled PJ: spoilery viditelné“). Prohlížeč si volbu zapamatuje.

V pohledu hráčů:
- popis s řádky jen pro PJ nelze upravit (uložením by se ztratily): nejdřív zapněte pohled PJ;
- podrobnost PJ ani tajné pole, které stránka neukazuje, nelze přepsat, novou poznámku pro PJ ale přidat lze;
- historie uvádí příkaz a záznamy, které hráči znají (`set · Freya`), nikdy hodnoty, a Zpět řekne, kterou změnu vrátilo, ne jaká byla.

## Bezpečnost

Aplikace může měnit vaši knihovnu, proto ve výchozím stavu naslouchá jen tomuto počítači.

- `--host` s jinou adresou ji zpřístupní jiným počítačům a Didact na to upozorní. Používejte to jen v síti, které důvěřujete.
- Odpovídá jen na požadavky adresované jí samotné (její vlastní adrese, `localhost`, `127.0.0.1` nebo `[::1]`, s jejím portem). Tím brání jiným webům, aby se k ní dostaly pomocí triků s DNS.
- Každá změna potřebuje formulář přímo z aplikace: tajný token v každém formuláři musí odpovídat cookie, kterou jiné weby nemohou přečíst ani odeslat.
- Přihlášení neexistuje. Kdokoli, kdo může používat prohlížeč na tomto počítači, může používat aplikaci.
