<!-- translated from bef7b2c650cb -->
# Πώς παίζεται μια συνεδρία

Πώς τρέχει ένα παιχνίδι μέσω του Didact: το LLM αφηγείται, και το Didact κρατά κάθε γεγονός, ρίψη και αλλαγή.

## Πριν από την πρώτη συνεδρία

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Ένας κόσμος κρατά το σύστημα με το οποίο φτιάχτηκε, και οι καμπάνιες του παίζουν με αυτό: άλλο σύστημα παίζεται σε δικό του κόσμο. Το `didact campaign close` αφήνει στην άκρη μια καμπάνια (ο κόσμος της μένει ανοιχτός) και το `didact campaign open <id>` τη συνεχίζει από εκεί που έμεινε, με τη συνεδρία και όλα τα υπόλοιπα.

Τα `didact world delete <id>` και `didact campaign delete <id>` αφαιρούν έναν κόσμο ή μια καμπάνια, με προεπισκόπηση πρώτα· το `--yes` διαγράφει, και το `didact undo` τα επαναφέρει όλα.

Το `session zero` παραθέτει τις ερωτήσεις που πρέπει να ξεκαθαρίσετε με τον παίκτη. Πρώτα έρχονται του πακέτου. Ανάμεσά τους είναι και οι επιλογές του συστήματος (οι παραλλαγές και οι προαιρετικοί κανόνες του): οι κανόνες του ακολουθούν τις απαντήσεις, και η ενημέρωση λέει τι σημαίνει κάθε επιλογή που άλλαξε. Κάθε ενημέρωση περιέχει τις απαντήσεις.

## Μια συνεδρία

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Γύροι:** κάθε μήνυμα του παίκτη ανοίγει έναν γύρο (το hook του Claude Code καλεί το `didact capture`, και οι άλλοι πελάτες χρησιμοποιούν το `turn begin`). Το `didact undo --turn` παίρνει πίσω ό,τι έγινε για εκείνο το μήνυμα: αλλαγές, συμβάντα και ρίψεις. Τα πρακτικά το κρατούν.
- **Άλμα πίσω:** το `didact undo --to e40` παίρνει πίσω ό,τι έγινε μετά το #e40, με το νεότερο πρώτο (το `--dry-run` τα παραθέτει): κάθε αλλαγή αναιρείται και κάθε ρίψη σημειώνεται ως αναιρεμένη. Τίποτα δεν διαγράφεται: το `redo`, ή ένα άλμα πίσω σε μεταγενέστερη αλλαγή, τα επαναφέρει.
- **Χρόνος:** το `didact time advance 1 watch` εξαντλεί χρονόμετρα, φέρνει υπενθυμίσεις και τρέχει χρονικά εναύσματα. Το `didact remind --list` δείχνει τις υπενθυμίσεις που έρχονται, και το `didact remind --cancel 2` ακυρώνει μία. Μια καμπάνια ξεκινά στην αρχή του ημερολογίου ή στην ημερομηνία που δίνει το `campaign new --date '4 July 1902'`, και το `didact time set '<date>'` την αλλάζει μέχρι την πρώτη συνεδρία.
- **Τοποθεσίες:** το `didact visit <place>` μετακινεί την ομάδα και σημειώνει την τοποθεσία ως επισκεφθείσα. Το `didact map` δείχνει ό,τι γνωρίζει η ομάδα, και μια ανεξερεύνητη έξοδος είναι `?`.
- **Μάχες:** `didact combat start --party troll`, μετά `combat next`, `combat hit freya troll weapon=d8` και `combat end`. Οι μαχητές μπαίνουν και βγαίνουν στη μέση της μάχης: `didact combat join wolf-2` (σε ατομική λειτουργία ρίχνουν πρωτοβουλία) και `didact combat leave troll --why fled`. Κανενός η σειρά δεν παραλείπεται.
- **Αντικείμενα:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (ή σε ένα σεντούκι, ή σε μια τοποθεσία)· το `didact where rope` το βρίσκει. Το `inv add` βρίσκει ένα αντικείμενο της συλλογής με το αναγνωριστικό του, το όνομά του ή ένα ψευδώνυμο.
- **Οι σημειώσεις σας:** το `didact about sweeney plan='…' doing='…' where='…'` κρατά ό,τι έχετε αποφασίσει για οποιονδήποτε ή οτιδήποτε. Οι παίκτες βλέπουν μόνο το `looks`. Το `didact log … --about sweeney` βάζει ένα συμβάν στην εγγραφή του (`--secret` αν οι παίκτες δεν το βλέπουν). Περισσότερα στο `didact guide details`.
- **Ο κόσμος προχωρά:** `didact faction turn`, και ρολόγια: `didact track new 'The flood' --size 6`. Μια εντολή που δέχεται μόνο ένα είδος εγγραφής παίρνει ένα όνομα που μοιράζονται κι άλλες ως εγγραφή αυτού του είδους: το `didact track roll draugr` ρίχνει τη δεξαμενή που φέρει το όνομα ενός εχθρού (το ίδιο το `track tick` έναν μετρητή, το `quest done` μια αποστολή και το `visit` έναν τόπο).

## Μαντεία, γεννήτριες και χαρακτήρες

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

Τίποτα από όσα φτιάχνει μια γεννήτρια ή η δημιουργία χαρακτήρα δεν γράφεται πριν από το `commit`. Περιγράψτε τι θέλει ο παίκτης στο `--prefill`, και η διαδικασία συμπληρώνει τα κενά. Μια ερώτηση παραθέτει τι σημαίνει κάθε επιλογή όταν το λέει το πακέτο (`- Cutpurse: …`): πείτε το στον παίκτη, ώστε να διαλέξει ξέροντας τι παίρνει.

## Μυστικά

Οι προβολές είναι από προεπιλογή ασφαλείς για τους παίκτες: `show`, `find`, `sheet`, `map`, `brief`. Αφήνουν έξω:
- τις μυστικές εγγραφές (`knowledge: secret`)·
- τις ενότητες `## Secrets` και `## GM notes`·
- τα πεδία `secret: true`.

Το `--gm` δείχνει τα πάντα. Όταν οι παίκτες μάθουν κάτι:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

Το `didact export --as site --to ~/Desktop/withering-site` γράφει ό,τι γνωρίζουν οι παίκτες ως έναν μικρό ιστότοπο για να τον μοιραστείτε ή να τον διαβάσετε σε κινητό: την ομάδα, μια σελίδα ανά εγγραφή, το ημερολόγιο και τον χάρτη. Είναι πάντα ασφαλής για τους παίκτες, και μια νέα εξαγωγή στον ίδιο φάκελο τον ενημερώνει. Το `didact export --as lonelog` γράφει το ημερολόγιο σε σημειογραφία Lonelog (`@ ? d: -> =>`, σκηνές ως `S1`, ετικέτες όπως `[N:Sweeney]`), επίσης ασφαλές για τους παίκτες.

## Lore: τι επανέρχεται όταν αναφέρεται κάτι

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Τι μετράει:** κάθε NPC, τοποθεσία, αντικείμενο και φατρία είναι μια κάρτα με κλειδί το όνομα και τα ψευδώνυμά του. Οι καταχωρίσεις lore έχουν `keys`, και οι αποφάσεις έρχονται στην επιφάνεια μέσω του κανόνα τους. Η αντιστοίχιση γίνεται σε ολόκληρες λέξεις, και οι πληθυντικοί μετράνε («wolves» ταιριάζει με `wolf`).
- **Πότε εμφανίζεται το lore:** το hook του Claude Code σαρώνει κάθε μήνυμα του παίκτη. Τα `log`, `scene new` και `show` φέρνουν επίσης lore που μόλις ενεργοποιήθηκε, και μια καταχώριση δεν επαναλαμβάνεται για μερικούς γύρους.
- **Ρύθμιση μιας καταχώρισης:** `--secondary` με `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (σε γύρους ή σκηνές), `--constant` (πάντα στην ενημέρωση) και `--no-recurse`.
- **Εμβέλειες:** οι καταχωρίσεις πάνε στην καμπάνια, εκτός αν το `--scope` λέει world, system ή global. Μια σάρωση βλέπει μόνο αυτή την καμπάνια, τον κόσμο της, το σύστημά της και το global, ποτέ άλλον κόσμο. Μια στενότερη καταχώριση με το ίδιο αναγνωριστικό επισκιάζει μια ευρύτερη.
- **Lorebook άλλων εργαλείων:** το `didact lore import <file>` διαβάζει World Info του SillyTavern (και του KoboldAI), το lorebook μιας κάρτας χαρακτήρα και το `.lorebook` του NovelAI· το `didact lore export --to <file>` γράφει World Info. Μεταφέρονται τα κλειδιά, η λογική, η προτεραιότητα, η πιθανότητα, οι ομάδες και ο χρονισμός.

## Αλλαγές στην ιστορία

- Το `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` αλλάζει το γεγονός αλλά κρατά την παλιά τιμή. Σημειώνει επίσης ως παρωχημένες τις περιλήψεις που αναφέρουν τον Sweeney, και το `audit` τις παραθέτει.
- Το `didact ruling add '<question>' '<ruling>' --rule <rule>` καταγράφει μια απόφαση. Αυτή εμφανίζεται έπειτα στο `rules lookup` και όταν τρέχει εκείνος ο κανόνας.
- Το `didact name npc` ρίχνει ένα νέο όνομα, ποτέ κάποιο που ο κόσμος ήδη χρησιμοποιεί. Πριν επινοήσετε ένα, ελέγξτε το με `didact names check <name>`. Το `didact names forget <name>` ελευθερώνει ξανά ένα όνομα.

## Συντήρηση

- Το `didact history --clear` δείχνει τι θα έχανε η εκκαθάριση του παλιού ιστορικού· το `--yes` το διαγράφει οριστικά, μαζί με τις διαγραμμένες εγγραφές, και η αναίρεση, το `diff`, το `rewind` και τα παλαιότερα σημεία αποθήκευσης δεν το φτάνουν πια (το `--before e120` κρατά εκείνο το γεγονός και τα επόμενα, το `--rolls` διαγράφει και το αρχείο ζαριών). Τρέξτε πρώτα `didact snapshot`.
- Το `didact save --remove 'before the dragon'` αφαιρεί ένα σημείο αποθήκευσης· το `didact undo` το επαναφέρει.
- Το `didact transcript 3 --clear` διαγράφει τα πρακτικά της συνεδρίας 3 (`--clear --all`: όλων των συνεδριών). Το `didact undo` τα επαναφέρει, και το κείμενο μένει στο ιστορικό μέχρι το `history --clear`.
- Το `didact compendium remove <entry>` διαγράφει μια καταχώριση που προσθέσατε· οι εγγραφές που δημιουργήθηκαν από αυτήν μένουν.
- Το `didact snapshot --keep 3` διαγράφει όλα τα αντίγραφα ασφαλείας εκτός από τα τρία νεότερα, και το `didact snapshot --remove <name>` διαγράφει ένα. Κανένα από τα δύο δεν αναιρείται.
- Το `didact session end` παίρνει μόνο του αντίγραφο ασφαλείας της βιβλιοθήκης (`snapshot-<time>-auto.zip`) και κρατά τα πέντε νεότερα από αυτά· το `didact snapshot --list` τα σημειώνει.
- Το `didact reset` δείχνει τι θα έπαιρνε μαζί του το άδειασμα της βιβλιοθήκης· το `--yes` την κάνει όπως μετά από νέα εγκατάσταση: φεύγουν κάθε κόσμος, καμπάνια και εγγραφή, το ιστορικό και το ευρετήριο αναζήτησης, και η επόμενη αλλαγή είναι ξανά #e1. Παίρνει πρώτα αντίγραφο ασφαλείας της βιβλιοθήκης (`…-before-reset.zip`), και τα αντίγραφα ασφαλείας μένουν, όπως και τα εγκατεστημένα πακέτα εκτός αν δοθεί `--packs`. Για να δοκιμάσετε το Didact σε μια έτοιμη καμπάνια, το `didact sample` χτίζει την καμπάνια-δείγμα σε μια άδεια βιβλιοθήκη (το `--home` της δίνει δικό της φάκελο), και το `didact serve --demo` τη σερβίρει από την αρχή.
- Το `didact snapshot --restore <name>` δείχνει τι περιέχει ένα αντίγραφο ασφαλείας δίπλα στη βιβλιοθήκη όπως είναι τώρα· το `--yes` παίρνει αντίγραφο ασφαλείας της βιβλιοθήκης ως έχει (`…-before-restore.zip`) και μετά βάζει το αντίγραφο στη θέση της. Η αρίθμηση γεγονότων και ρίψεων συνεχίζει. Η αναίρεση δεν μπορεί να πάρει πίσω μια επαναφορά: η επαναφορά εκείνου του αντιγράφου ασφαλείας μπορεί.
