<!-- translated from bef7b2c650cb -->
# Jocul unei sesiuni

Cum decurge un joc prin Didact: LLM-ul narează, iar Didact păstrează fiecare fapt, aruncare și modificare.

## Înainte de prima sesiune

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

O lume își păstrează sistemul cu care a fost creată, iar campaniile ei îl joacă: alt sistem se joacă într-o lume proprie. `didact campaign close` pune o campanie deoparte (lumea ei rămâne deschisă), iar `didact campaign open <id>` o reia de unde a rămas, cu sesiune cu tot.

`didact world delete <id>` și `didact campaign delete <id>` șterg una, arătând mai întâi ce dispare; `--yes` o șterge, iar `didact undo` aduce totul înapoi.

`session zero` listează întrebările de lămurit cu jucătorul. Cele ale pachetului vin primele. Printre ele sunt și opțiunile sistemului (variantele și regulile lui opționale): regulile lui urmează răspunsurile, iar rezumatul spune ce înseamnă fiecare opțiune schimbată. Fiecare rezumat conține răspunsurile.

## O sesiune

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Ture:** fiecare mesaj al jucătorului deschide o tură (hook-ul din Claude Code apelează `didact capture`, iar alți clienți folosesc `turn begin`). `didact undo --turn` retrage tot ce s-a făcut pentru acel mesaj: modificări, evenimente și aruncări. Transcrierea le păstrează.
- **Salt înapoi:** `didact undo --to e40` retrage tot ce urmează după #e40, de la cel mai nou (`--dry-run` le listează): fiecare modificare e desfăcută și fiecare aruncare e marcată ca anulată. Nu se șterge nimic: `redo` sau un salt înapoi la o modificare ulterioară aduce totul înapoi.
- **Timpul:** `didact time advance 1 watch` consumă temporizatoarele, scoate la iveală mementourile și rulează declanșatorii de timp. `didact remind --list` arată mementourile care urmează, iar `didact remind --cancel 2` renunță la unul. O campanie începe la începutul calendarului sau la data pe care o dă `campaign new --date '4 July 1902'`, iar `didact time set '<date>'` o schimbă până la prima sesiune.
- **Locuri:** `didact visit <place>` mută grupul și marchează locul ca vizitat. `didact map` arată ce cunoaște grupul, iar o ieșire neexplorată e `?`.
- **Lupte:** `didact combat start --party troll`, apoi `combat next`, `combat hit freya troll weapon=d8` și `combat end`. Luptătorii vin și pleacă în timpul luptei: `didact combat join wolf-2` (în modul individual aruncă pentru inițiativă) și `didact combat leave troll --why fled`. Nimeni nu-și pierde rândul.
- **Obiecte:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (sau într-un cufăr, sau într-un loc); `didact where rope` îl găsește. `inv add` găsește un obiect din compendiu după ID, după nume sau după un alias.
- **Notele tale:** `didact about sweeney plan='…' doing='…' where='…'` păstrează ce ai hotărât despre oricine sau orice. Jucătorii văd doar `looks`. `didact log … --about sweeney` pune un eveniment pe fișa lui (`--secret` dacă jucătorii nu-l văd). `didact guide details` are mai multe.
- **Lumea merge mai departe:** `didact faction turn`, plus ceasuri: `didact track new 'The flood' --size 6`. O comandă care ia un singur fel de fișă ia un nume împărțit cu altele ca fiind de acel fel: `didact track roll draugr` aruncă fondul numit după un dușman (la fel `track tick` un contor, `quest done` o misiune și `visit` un loc).

## Oracole, generatoare și personaje

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

Nimic din ce face un generator sau o creare de personaj nu se scrie până la `commit`. Descrie în `--prefill` ce vrea jucătorul, iar procedura completează golurile. O întrebare listează ce înseamnă fiecare opțiune, când pachetul o spune (`- Cutpurse: …`): spune-i jucătorului, ca să aleagă știind ce primește.

## Secrete

Vederile sunt implicit sigure pentru jucători: `show`, `find`, `sheet`, `map`, `brief`. Ele omit:
- fișele secrete (`knowledge: secret`);
- secțiunile `## Secrets` și `## GM notes`;
- câmpurile `secret: true`.

`--gm` arată tot. Când jucătorii află ceva:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` scrie ce știu jucătorii sub forma unui mic site, de împărtășit sau de citit pe telefon: grupul, câte o pagină pentru fiecare fișă, jurnalul și harta. E mereu sigur pentru jucători, iar un nou export în același dosar îl actualizează. `didact export --as lonelog` scrie jurnalul în notația Lonelog (`@ ? d: -> =>`, scenele ca `S1`, etichete ca `[N:Sweeney]`), tot sigur pentru jucători.

## Cunoștințe: ce revine când e menționat ceva

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Ce contează:** fiecare PNJ, loc, obiect și facțiune e o carte cu cheile date de numele și aliasurile sale. Intrările de cunoștințe au `keys`, iar deciziile apar prin regula lor. Potrivirea se face pe cuvinte întregi, iar pluralele contează („wolves” se potrivește cu `wolf`).
- **Când apar cunoștințele:** hook-ul din Claude Code scanează fiecare mesaj al jucătorului. `log`, `scene new` și `show` aduc și ele cunoștințele nou declanșate, iar o intrare nu se repetă timp de câteva ture.
- **Reglarea unei intrări:** `--secondary` cu `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (în ture sau scene), `--constant` (mereu în rezumat) și `--no-recurse`.
- **Domenii:** intrările merg în campanie, dacă `--scope` nu spune lume, sistem sau global. O scanare vede doar această campanie, lumea ei, sistemul ei și globalul, niciodată altă lume. O intrare mai restrânsă cu același ID o acoperă pe una mai largă.
- **Lorebook-urile altor instrumente:** `didact lore import <file>` citește World Info din SillyTavern (și pe cel din KoboldAI), lorebook-ul unei cărți de personaj și `.lorebook`-ul din NovelAI; `didact lore export --to <file>` scrie World Info. Cheile, logica, prioritatea, probabilitatea, grupurile și temporizarea se păstrează.

## Schimbarea poveștii

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` schimbă faptul, dar păstrează vechea valoare. Marchează și rezumatele care îl menționează pe Sweeney ca învechite, iar `audit` le listează.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` înregistrează o decizie. Aceasta apare apoi în `rules lookup` și când rulează acea regulă.
- `didact name npc` aruncă pentru un nume nou, niciodată unul pe care lumea îl folosește deja. Înainte să inventezi unul, verifică-l cu `didact names check <name>`. `didact names forget <name>` eliberează din nou unul.

## Întreținere

- `didact history --clear` arată ce s-ar pierde prin golirea istoricului vechi; `--yes` îl elimină definitiv, inclusiv fișele șterse, iar desfacerea, `diff`, `rewind` și punctele de salvare mai vechi nu mai ajung la el (`--before e120` păstrează acel eveniment și pe cele de după, `--rolls` elimină și registrul zarurilor). Rulează mai întâi `didact snapshot`.
- `didact save --remove 'before the dragon'` elimină un punct de salvare; `didact undo` îl aduce înapoi.
- `didact transcript 3 --clear` șterge transcrierea sesiunii 3 (`--clear --all`: a tuturor sesiunilor). `didact undo` o aduce înapoi, iar textul rămâne în istoric până la `history --clear`.
- `didact compendium remove <entry>` șterge o intrare pe care ai adăugat-o; fișele create din ea rămân.
- `didact snapshot --keep 3` șterge toate copiile de rezervă în afară de cele mai noi trei, iar `didact snapshot --remove <name>` șterge una. Niciuna nu se poate desface.
- `didact session end` face singur o copie de rezervă a bibliotecii (`snapshot-<time>-auto.zip`), păstrând cele mai noi cinci dintre acestea; `didact snapshot --list` le marchează.
- `didact reset` arată ce ar lua golirea bibliotecii; `--yes` o face ca proaspăt instalată: toate lumile, campaniile și fișele, istoricul și indexul de căutare dispar, iar următoarea modificare e din nou #e1. Mai întâi face o copie de rezervă a bibliotecii (`…-before-reset.zip`), iar copiile de rezervă rămân, la fel și pachetele instalate, dacă nu dai `--packs`. Ca să încerci Didact pe o campanie gata făcută, `didact sample` construiește campania exemplu într-o bibliotecă goală (`--home` îi dă un dosar propriu), iar `didact serve --demo` o servește de la zero.
- `didact snapshot --restore <name>` arată ce conține o copie de rezervă, alături de biblioteca actuală; `--yes` face o copie de rezervă a bibliotecii așa cum e (`…-before-restore.zip`), apoi pune copia în locul ei. Numerotarea evenimentelor și a aruncărilor continuă. Desfacerea nu poate retrage o restaurare: restaurarea acelei copii de siguranță poate.
