<!-- translated from 5a088227a31a -->
# Aplicația din browser

`didact serve` îți deschide biblioteca într-un browser web: explorezi și editezi fișe, vezi într-un graf cum se leagă, citești jurnalul, rulezi reguli și tabele și folosești orice comandă dintr-un formular.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Funcționează offline: fonturile și pictogramele vin cu Didact.

**Modul demo.** `--demo` servește campania exemplu (`didact sample`: o vale cu un râu, un PJ, oameni cu notele MJ-ului, locuri și drumuri, o misiune, un ceas și o sesiune în desfășurare, cu o luptă) dintr-o bibliotecă proprie, lângă dosarul cache al lui Didact. Acolo sunt instalate toate pachetele care vin cu Didact. E construită de la zero la fiecare pornire cu `--demo`, așa că încearcă orice: biblioteca ta nu e atinsă.

## Opțiuni

| Opțiune | Implicit | Ce face |
|---|---|---|
| `--port <n>` | 8765 | portul pe care ascultă |
| `--host <address>` | 127.0.0.1 | adresa pe care ascultă: doar acest calculator |
| `--open` | oprit | deschide aplicația într-o filă a browserului |
| `--gm` | oprit | pornește cu modul MJ activ |
| `--demo` | oprit | servește o campanie exemplu nouă în locul bibliotecii tale |

Opțiunile globale `--home`, `--world` și `--campaign` se aplică la tot ce face aplicația. Dacă deschizi altă lume sau altă campanie pe pagina Bibliotecă a aplicației, treci la ea, ca la `didact world use` și `didact campaign open`, iar „Închide” pune deoparte campania deschisă (`didact campaign close`).

## Ce conține

- **Prezentare generală:** rezumatul (lumea, campania, sesiunea, scena, grupul, ce urmează), acțiuni rapide (aruncă zarurile, întreabă oracolul cu șansele pe care le cunoaște, notează un eveniment, începe sau încheie o sesiune, o fișă nouă) și cele mai recente modificări.
- **Stare:** unde se află lucrurile, dintr-o privire: sesiunea și scena, timpul și mementourile care urmează, numerele fiecărui membru al grupului și ce poartă, lupta (cine e la rând, condiții), misiunile și contoarele deschise și unde e grupul, cu ieșirile lui. Numerele se pot ajusta chiar acolo: − și + pe o valoare, bifezi un contor, folosești sau arunci un obiect, adaugi unul, închei o misiune, avansezi timpul (un număr și o unitate pe care o cunoaște calendarul: ore, carturi, zile, …), setezi un memento (o dată sau periodic) și anulezi unul.
- **Fișe:** fiecare fișă, grupată pe tipuri, cu o casetă de filtrare și butoanele Toate, Lume sau Campanie. Pagina unei fișe arată foaia, descrierea, detaliile, câmpurile, conținutul, legăturile în ambele sensuri, cronica și istoricul ei, cu formulare pentru a schimba fiecare dintre ele și pentru a o arhiva sau șterge. Un personaj al cărui sistem are avansare în nivel are un buton „Level up” (`char advance`): o ciornă care arată ce se schimbă, înainte și după, până când e confirmată.
- **Ciorne:** crearea de personaje și generatoarele, pas cu pas. „Creează un personaj” (pas cu pas sau la întâmplare, alegând tipul când sistemul are mai multe: un personaj jucător, un mercenar, …) și „Generează…” sunt pe paginile Fișe; ciornele în așteptare sunt listate acolo și pe Prezentare generală. Pagina unei ciorne arată ce conține până acum (entitățile și câmpurile lor, harta desenată de un generator, aruncările, întrebările cărții) și întrebarea la care așteaptă. Fiecare opțiune e un buton care spune ce înseamnă, când pachetul o spune (ce oferă o origine, ce face un talent); când alegi mai multe, fiecare are o căsuță de bifat; scorurile cumpărate dintr-un buget sunt numere care țin socoteala punctelor pe măsură ce le schimbi; un nume sau alt răspuns liber se poate scrie; iar „Lasă zarurile să decidă” aruncă doar pentru aceea (`char roll c3 --one`). „Înapoi” retrage ultimul pas, așa că întrebarea lui revine (`char back c3`: aruncările făcute în el sunt marcate ca anulate, iar „Desfă” aduce pasul înapoi). Apoi „Aruncă pentru rest”, „Editează”, „Renunță…” (întreabă mai întâi) și „Confirmă”, care deschide fișa noului personaj sau listează ce a creat generatorul. Ciorna unui generator e a MJ-ului: modul jucătorilor arată doar că există.
- **Graf:** fișele ca noduri și legăturile ca muchii. Trage nodurile, trage fundalul ca să deplasezi vederea, fă zoom cu rotița; ține mouse-ul deasupra ca să luminezi vecinii unei fișe; dă clic ca s-o deschizi. Butonul Graf de pe pagina unei fișe arată doar vecinătatea ei.
  - **Hartă** (comutatorul de deasupra grafului sau „Deschide harta” pe Stare): locurile pe care le cunoaște grupul, drumurile dintre ele (etichetate road, trail, …), regiunea în care se află fiecare (punctat) și unde e grupul. Un drum spre un loc încă negăsit duce la un „?”; modul MJ arată toate locurile.
- **Jurnal:** sesiunile, fiecare deschizându-se spre scenele, evenimentele și aruncările ei. Fiecare eveniment are „Editează” și „Elimină” (ține mouse-ul deasupra), care deschid formularele `beat edit` și `beat rm`.
- **Referințe:** caută peste tot (rezultatele apar pe măsură ce scrii), rulează regulile pachetelor activate din formulare, aruncă pe tabelele lor și citește-le textul regulilor, glosarul și ghidurile.
- **Bibliotecă:** lumi și campanii (deschide, închide, creează, șterge), pachete (fiecare cu ce este; activează, dezactivează, instalează, dezinstalează; pachetele incluse în Didact au un buton Instalează), istoricul (Desfă, Refă, Sari înapoi, Golește), punctele de salvare (revino, elimină) și copiile de rezervă (fă o copie de rezervă acum, restaurează, șterge, păstrează cele mai noi câteva; cele făcute la încheierea unei sesiuni sunt marcate auto). Când nicio campanie nu e deschisă, pagina Prezentare generală listează campaniile lumii, ca să deschizi una.
  - Ștergerea unei lumi sau a unei campanii întreabă mai întâi, iar „Desfă” aduce totul înapoi.
  - „Sari înapoi” (lângă fiecare modificare) retrage tot ce a urmat după acea modificare (`didact undo --to e40`): pagina lui arată mai întâi ce se retrage. Fiecare modificare e desfăcută și fiecare aruncare e marcată ca anulată, nu ștearsă: „Refă” sau un salt înapoi la o modificare ulterioară le aduce înapoi. „Arată modificările mai vechi” listează mai mult din istoric.
  - Pachetul core e mereu activ. Un singur sistem de joc e în uz la un moment dat: al lumii deschise, care îl păstrează definitiv (e ales când lumea e creată). Alt sistem se joacă într-o lume proprie: rândul lui deschide o lume care îl joacă sau creează una nouă. Dezinstalarea unui pachet nu se poate desface: instalează din nou fișierul lui .didactpack.
  - Golirea istoricului arată mai întâi exact ce dispare și ce nu mai funcționează, cu un buton pentru a face mai întâi o copie de rezervă. Nu se poate desface, și nici ștergerea unei copii de rezervă.
  - Ia-o de la capăt: **Resetează…** golește biblioteca, ca și cum Didact ar fi proaspăt instalat, iar numerotarea reîncepe de la #e1. Pagina lui arată mai întâi ce dispare. Mai întâi se face o copie de rezervă a bibliotecii, iar copiile de rezervă rămân (și pachetele instalate, dacă nu bifezi căsuța).
  - Restaurarea unei copii de rezervă arată mai întâi ce conține, alături de biblioteca actuală. Mai întâi se face o copie de rezervă a bibliotecii așa cum era: „Desfă” nu poate retrage o restaurare, dar restaurarea acelei copii poate.
- **Comenzi:** fiecare comandă ca formular și o casetă care primește o linie de comandă întreagă. Fiecare casetă primește ce primește argumentul ei: un număr, un ID sau un eveniment (`e12`) după tiparul lui, o durată din timpul jocului ca număr și unitate, și o listă din care alegi fișele, ciornele, pachetele, punctele de salvare, oracolele, tabelele și regulile de aici.
- **Setări:** opțiunile campaniei (variantele și regulile opționale ale sistemului ei, pe care le urmează regulile, crearea personajelor și generatoarele; fiecare spune ce face: o regulă opțională, ce schimbă activarea ei, o alegere, ce înseamnă fiecare dintre valorile ei, iar o valoare implicită stabilită de altă opțiune spune care anume), limba aplicației, tezaurul (limba pe care o folosesc căutările pentru sinonime: descarci unul, cu o bară de progres, comuți între cele descărcate, elimini unul) și documentația codului.
  - Aplicația, ghidurile ei și ce afișează comenzile în ea sunt disponibile în 24 de limbi. Dacă nu alegi, aplicația urmează limba browserului. Linia de comandă și LLM-urile care o folosesc rămân în engleză: limba aleasă aici e doar a aplicației.
  - Butonul de cod din bara antetului deschide documentația API a codului. E generată din cod prima dată și din nou ori de câte ori se schimbă codul (`didact docs build`).

Fiecare modificare rulează o comandă `didact` reală, deci e verificată, notată și se poate desface exact ca în linia de comandă. Aplicația arată de fiecare dată comanda pe care a rulat-o (`didact set sweeney hp-=2`), cu un buton Desfă când e ceva de retras.

O casetă primește doar ce primește comanda ei. Un ID (al unei lumi sau al unei campanii) și un tip de fișă primesc litere mici, cifre și cratime: spațiile devin cratime, iar majusculele devin minuscule pe măsură ce scrii. Numele unui câmp nu primește spații (devin _), numele unui detaliu e un singur cuvânt, iar casetele numerice primesc doar numere. Ce primește o casetă e scris sub ea, iar comanda verifică oricum din nou.

Salvarea nu suprascrie niciodată o modificare pe care n-ai văzut-o. Dacă fișa s-a schimbat după ce pagina a afișat-o (de exemplu, un LLM a schimbat-o din linia de comandă, sau altă filă), salvarea e refuzată și spune ce e acolo acum. O descriere pe care o editai rămâne în editor, lângă noua versiune, ca s-o combini și s-o salvezi din nou. − și + trec mereu: se adună.

## Modul jucătorilor și modul MJ

Aplicația arată ce știu jucătorii, cum face `didact show`: fișele secrete, secțiunile `## Secrets`, câmpurile secrete și detaliile doar pentru MJ rămân pe dinafară. Butonul **GM** din bara antetului pornește modul MJ, iar un banner o spune („Modul MJ: spoilere vizibile”). Browserul ține minte alegerea.

În modul jucătorilor:
- o descriere cu rânduri doar pentru MJ nu se poate edita (salvarea le-ar pierde): pornește mai întâi modul MJ;
- un detaliu al MJ-ului sau un câmp secret pe care pagina nu-l arată nu poate fi suprascris, deși se poate adăuga o notă nouă pentru MJ;
- istoricul numește comanda și fișele pe care le știu jucătorii (`set · Freya`), niciodată valorile, iar „Desfă” spune ce modificare a retras, nu ce conținea.

## Siguranță

Aplicația îți poate schimba biblioteca, așa că implicit ascultă doar pe acest calculator.

- `--host` cu altă adresă le permite altor calculatoare s-o acceseze, iar Didact te avertizează despre asta. Folosește-l doar într-o rețea în care ai încredere.
- Răspunde doar cererilor adresate ei (adresa ei proprie, `localhost`, `127.0.0.1` sau `[::1]`, cu portul ei). Asta împiedică alte site-uri s-o acceseze prin trucuri DNS.
- Fiecare modificare are nevoie de un formular din aplicația însăși: un token secret din fiecare formular trebuie să se potrivească cu un cookie pe care alte site-uri nu-l pot citi sau trimite.
- Nu există autentificare. Oricine poate folosi browserul acestui calculator poate folosi aplicația.
