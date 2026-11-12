<!-- translated from b1dfa1159ff4 -->
# Πακέτα

Ένα πακέτο είναι ένα σύστημα παιχνιδιού, μαντείο, σκηνικό, περιπέτεια ή συμπλήρωμα, γραμμένο ως αρχεία YAML μαζί με ένα προαιρετικό πρόσθετο Python. Αυτός ο οδηγός δείχνει πώς γράφεται ένα: πώς μετατρέπετε ένα βιβλίο κανόνων σε πακέτο, ή πώς προσθέτετε δικό σας υλικό.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Ένα πακέτο μπορεί επίσης να φτιαχτεί από ό,τι υπάρχει στη βιβλιοθήκη σας. Το `didact pack new my-brew --from-overlay my-system` μετατρέπει το δικό σας υλικό για ένα σύστημα (`compendium add`, εγγραφές που κρατούνται με `--scope system`, lore) σε συμπλήρωμα, και το `didact world export --as setting` μετατρέπει έναν κόσμο σε πακέτο σκηνικού: τα πρόσωπα, τις τοποθεσίες και το lore του ως καταχωρίσεις της συλλογής και lore του πακέτου, που τα φέρνετε σε άλλον κόσμο με το `compendium import`. Και τα δύο αφήνουν έξω τα μυστικά και τις σημειώσεις του GM, εκτός με `--secrets`, και κανένα δεν σημειώνεται ως κοινοποιήσιμο μέχρι να ορίσετε την άδειά του.

## Δομή

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

Ένα αρχείο περιέχει ένα στοιχείο, μια λίστα στοιχείων ή πολλά στοιχεία χωρισμένα με `---`. Κάθε στοιχείο δηλώνει το αναγνωριστικό του με το κλειδί του είδους του: `table: weather`, `check: save`, `type: pc`, ή `id: troll` για καταχωρίσεις της συλλογής. Αναφέρεστε σε στοιχεία ως `pack.id` (`my-system.save`), ή με σκέτο αναγνωριστικό όταν το έχει μόνο ένα ενεργό πακέτο.

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

Ένα hack δηλώνει τη βάση του στο `extends` και περιέχει μόνο ό,τι διαφέρει:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Το στοιχείο του με το ίδιο αναγνωριστικό αντικαθιστά εκείνο της βάσης, όποιο κι αν είναι το είδος (ένας πίνακας, ένας κανόνας, μια καταχώριση της συλλογής, μια ενότητα αναφοράς, ένας όρος γλωσσαρίου). Τα `settings` του εφαρμόζονται πάνω σε εκείνα της βάσης, κλειδί προς κλειδί: ένα κλειδί που ορίζει αντικαθιστά ολόκληρη την τιμή της βάσης (οι πίνακες ονομάτων του στο `names` παίρνουν τη θέση εκείνων της βάσης), και οι κανόνες της βάσης διαβάζουν κι αυτοί τις τιμές του hack. Το `hides` αφαιρεί ό,τι απομένει και δεν χρειάζεται το hack: το `*` ταιριάζει με οποιαδήποτε ακολουθία χαρακτήρων, αποφασίζει το τελευταίο μοτίβο που ταιριάζει με ένα αναγνωριστικό, και ένα μοτίβο που αρχίζει με `!` κρατά το στοιχείο. Ό,τι αντικαθιστά το hack δεν αποκρύπτεται ποτέ. Τα είδη είναι `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` και `term`. Η εντολή `didact pack validate` προειδοποιεί για μοτίβο που δεν ταιριάζει με τίποτα.

## Εκφράσεις

Κάθε συνθήκη και τύπος χρησιμοποιεί τη γλώσσα των ζαριών (`didact guide dice`), και επιπλέον:
- **Τιμές:** το `@name` διαβάζει μια τιμή: `@roll`, `@who.STR`, `@settings.x`. Το `$name` επικολλά πρώτα το κείμενο μιας παραμέτρου, οπότε το `@who.$attr` γίνεται `@who.STR`. Διαβάστε μια παράμετρο ελεύθερου κειμένου ως `@name`, όχι σε εισαγωγικά (`'$name'`): μια απόστροφος στο κείμενό της θα έκλεινε τα εισαγωγικά (το `pack validate` προειδοποιεί).
- **Λογική:** `and`, `or`, `not`, και `in` (`'deprived' in @who.conditions`).
- **Σταθερές:** κείμενο (`'travel'`) και `true`/`false`.
- **Συναρτήσεις:** το `if(cond, a, b)` ρίχνει μόνο τον κλάδο που ακολουθεί. Το `default(@thread.flashpoint, 0)` είναι η τιμή, ή η εναλλακτική όταν δεν έχει οριστεί. Τα `sum`, `count` (το `count(@roll.dice, 6)` μετράει τα εξάρια), `min`, `max`, `any` και `all` δέχονται λίστες.

## Φύλλα: `schemas/`

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

| Είδος | Περιέχει | Επιλογές |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | μια απλή τιμή | min, max· `values` για enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: το `@hp` είναι η τιμή, το `@hp.max` το ανώτατο | range· min· max ή max_field· die |
| `counter` | έναν αριθμό | min, max, thresholds, occupies (ένα πεδίο slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | αντικείμενα (`Rope` ή `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | ό,τι λέει το όνομα | `to` (για refs), `allowed` |
| `derived` | υπολογίζεται, δεν αποθηκεύεται ποτέ | expr |

Κάθε πεδίο δέχεται επίσης `label`, `help`, `default`, `required` και `roll`: το `new pc Hero --fill`, ή μια τιμή `"roll"`, το ρίχνει μέσω του αρχείου καταγραφής. Οι τύποι του πακέτου `core` κρατούν κείμενο ανεξάρτητο από σύστημα στα `fields`. Οι τύποι ενός συστήματος κρατούν τους αριθμούς του στο `mechanics.<system>`. Το `set hero hp-=2` βρίσκει το πεδίο, το περιορίζει στα όριά του και αναφέρει κάθε υπέρβαση. Το `+=` προσθέτει σε μια λίστα: ένα πεδίο `list` (όπως το `slots`) κρατά μια τιμή που προστίθεται ξανά, τα `tags`, `conditions` και `refs` την κρατούν μία φορά, και το `-=` αφαιρεί όλα τα αντίγραφά της.

Τα **hooks** λένε τι συμβαίνει όταν μια τιμή περνά ένα όριο. Ενεργοποιούνται σε κάθε αλλαγή (`set`, `inv`, ένα βήμα `set` κανόνα), αλλά μόνο όταν το όριο περαστεί: το 3 → 0 τα ενεργοποιεί, το 0 → 0 όχι. Οι επεξεργασίες με `--force` τα παρακάμπτουν.

| Hook | Ενεργοποιείται όταν |
|---|---|
| `on_zero` | ένας αριθμός ή ένα `{value}` φτάνει το 0 |
| `on_full` (`when_full` στα slots) | φτάνει το max, το size ή το capacity του |
| `thresholds: {10: …, 20: …}` (counters) | ξεπερνά κάθε σημάδι καθώς ανεβαίνει |

Μια ενέργεια είναι κείμενο (μια σημείωση για το LLM), `{set: {hp: 0}}` ή `{condition: paralyzed}` στην ίδια εγγραφή, `{trigger: death}` (τρέχει εκείνον τον κανόνα με `who` = την εγγραφή), ή μια λίστα από αυτά.

Το **απόθεμα** (`didact inv …`) δουλεύει στο πεδίο `slots` του φύλλου:
- **Χώρος:** τα αντικείμενα πιάνουν `size` × `count`, και οι counters που κάνουν `occupies` στο πεδίο πιάνουν την τιμή τους. Πέρα από το `capacity` απορρίπτεται, εκτός με `--force`.
- **Ομάδες:** το `groups: {backpack: 6, body: 4}` δίνει σε κάθε ομάδα τον δικό της χώρο, καθώς και δικές της στήλες και σύνολα: το `@inventory.body.armor` είναι μόνο ό,τι φοριέται ή κρατιέται στο χέρι, το `@inventory.body.free` ο χώρος που της απομένει.
- **Χρήσεις:** το `uses: 3` μετράει αντίστροφα με το `inv use`. Το `uses: d8` είναι ζάρι χρήσης: με 1–2 πέφτει ένα βήμα. Ένα αντικείμενο που εξαντλήθηκε χάνεται, εκτός αν έχει `recharge` ή `keep: true`. Από πολλά αντικείμενα με το ίδιο όνομα, το όνομα σημαίνει το πρώτο· για να ξοδέψετε μια χρήση (`inv use`, το `use:` ενός κανόνα, `set …uses-=1`), το πρώτο που έχει ακόμη χρήση.
- **Κλειδιά ενός αντικειμένου:** το `didact set freya inventory.sword.damage=d10` (όπως και το `set: who.inventory.$item.damage` ενός κανόνα) αλλάζει ένα από αυτά, ονομάζοντας το αντικείμενο όπως το ονομάζει το `inv`, με ένα μέρος του ονόματός του ή με όλο, μαζί με κενά και τελείες (`'inventory.12.7mm pistol.damage=d10'`, σε εισαγωγικά για το κέλυφος)· τα `uses` και `charges` μετριούνται όπως σε ένα πεδίο `uses` (το `charges+=2` σταματά στο μέγιστο), και ο χώρος ελέγχεται όπως τον ελέγχει το `inv add`. Ένας κανόνας διαβάζει ένα τέτοιο κλειδί ως `@{who.inventory.$item.damage}` (ένα ζάρι χρήσης ως το ζάρι του, τις χρήσεις ως το πλήθος τους)· ένα αντικείμενο ή ένα κλειδί που δεν υπάρχει διαβάζεται ως απόν, οπότε το `default(…)` δίνει την εφεδρική του τιμή.
- **Συλλογή:** οι καταχωρίσεις τύπου `item` (ή weapon, armor, relic, …, ή ενός δικού τύπου του πακέτου που επεκτείνει κάποιον από αυτούς με `extends`) δανείζουν στο `inv add` τις λεπτομέρειές τους, και βρίσκονται με το αναγνωριστικό, το όνομα ή ένα ψευδώνυμο (αν δύο μοιράζονται ένα: ονομάστε τη σωστή ως `pack.id`)· κάθε άλλο όνομα, με το `:` και όλα, είναι το δικό όνομα του αντικειμένου.

## Πίνακες: `tables/`

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

Άλλες μορφές:
- **Σταθμισμένες λίστες:** τα `entries` ως λίστα, με `weight:` ανά καταχώριση.
- **Στήλες:** το `columns: [a, b]` ρίχνει ξεχωριστά για κάθε στήλη μιας γραμμής. Μια απλή καταχώριση (όχι λίστα) γεμίζει κάθε στήλη, οπότε το `columns: [first, second]` πάνω σε μια λίστα λέξεων σημαίνει «ρίξε δύο φορές σε αυτή τη λίστα». Το `labels: false` αφήνει τα ονόματα των στηλών έξω από το αποτέλεσμα («Abandon · Advantage»). Το `read: "It's a {first} {second} with {third} {fourth} inside."` διαβάζει τις στήλες ως πρόταση.
- **Πίνακες αναζήτησης:** `lookup: hp_lost`, ή `[odds, chaos]` για διδιάστατο πίνακα.
- **Διπλά:** `duplicates: reroll | keep | make_it_worse` για το «ρίξε δύο φορές».
- **Δύο βήματα:** μια καταχώριση που ρίχνει σε άλλον πίνακα (`{table: lightning}` αντί για κείμενο, ή `then:` μετά από αυτό) φέρνει μαζί της τα data εκείνης της ρίψης: ένας κανόνας ή ένα πρόχειρο που τη ρίχνει διαβάζει και τα δύο, πρώτα τα κλειδιά της ίδιας της καταχώρισης και μετά εκείνα του πρώτου πίνακα που ρίχνεται στη συνέχεια. Ένα `--prefill` μπορεί να ονομάσει μια καταχώριση πιο κάτω, σε οποιοδήποτε βάθος (`Ring of the Hunt`), με τα δεδομένα κάθε καταχώρισης στη διαδρομή: από δύο με το ίδιο όνομα εννοείται η πιο κοντινή (μετά η πρώτη), μια που συνεχίζει ρίχνει από εκεί και πέρα, και μια που μοιάζει με κάποια από αυτές χωρίς να είναι καμία απορρίπτεται, και κατονομάζεται η πλησιέστερη. Ένα καθοδηγούμενο πρόχειρο προσφέρει το πρώτο βήμα όταν οι καταχωρίσεις του λένε τι είναι (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): η επιλογή μιας ρίχνει στον επόμενο πίνακα, όπως μια ρίψη που πέφτει πάνω της.
- **Ανάγνωση και προς τις δύο πλευρές:** το `both_ways: true` σε πίνακα d66 προσθέτει την άλλη ανάγνωση: το 31 δίνει και το 13, και διαλέγει όποιος διαβάζει.
- **Τι σημαίνει μια καταχώριση:** το `about: "Knows: {skills}. Also known as: {aka}."` συμπληρώνεται με τα data κάθε καταχώρισης (μια λίστα διαβάζεται `a, b`· το `{text}` είναι η ίδια η καταχώριση) για να πει τι δίνει όταν την προσφέρει μια επιλογή· μια καταχώριση με δικό της `note:` το λέει αυτό στη θέση του. Χωρίς κανένα από τα δύο, μια καταχώριση της οποίας τα data έχουν ένα `id` που κατονομάζει μια καταχώριση της συλλογής περιγράφεται από εκείνη την καταχώριση.
- **Τράπουλες και σακούλες:** `deck: tarot` με `cards` (ή `standard: true`)· `bag: initiative` με `tokens`.

Η επικύρωση ελέγχει ότι κάθε αποτέλεσμα που μπορούν να φέρουν τα ζάρια πέφτει σε μια καταχώριση.

## Κανόνες: `rules/`

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

Οι ενέργειες και οι διαδικασίες είναι λίστες βημάτων, και τα εναύσματα είναι βήματα με φύλακα `when:`. Τα βήματα είναι:

| Βήμα | Κάνει |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | μια καταγεγραμμένη ρίψη· δεσμεύει `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`· ένα `{…}` συμπληρώνεται πρώτα, όπως σε κάθε κείμενο, οπότε τα ζάρια που μια τιμή κρατά ως κείμενο ρίχνονται (`{@{who.inventory.$item.damage}}`), και το ημερολόγιο τα δείχνει: μια τιμή που δεν είναι ζάρια απορρίπτεται, όπως και το `roll: "@die"` με τέτοιο κείμενο, που δεν ρίχνει τίποτα· ένα σύνολο ρίψεων (`{d8, d6}kh1`) μένει σύνολο |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | υπολογίζει τιμές· όπως στο `value` του `set`, το κείμενο με `{…}` είναι πρότυπο και μια σκέτη λέξη είναι κείμενο· σε κάθε κείμενο που συμπληρώνεται, τα `{{` και `}}` γράφουν την ίδια την αγκύλη |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (ή `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | αλλάζει μια εγγραφή: με επικύρωση, περιορισμό στα όρια, αναίρεση· το `set: who.$attr` ορίζει το πεδίο που ονομάζει μια παράμετρος, και το `set: who.inventory.$item.damage` ένα κλειδί ενός αντικειμένου που κουβαλά (δείτε «Απόθεμα»)· το `-=` αφαιρεί μια τιμή από μια λίστα, και μια τιμή που δεν περιέχει δεν αλλάζει τίποτα (μια σημείωση το λέει· μια που δεν θα μπορούσε ποτέ να περιέχει απορρίπτεται)· το `unset:` αφαιρεί ένα πεδίο, όπως το `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | δίνει σε μια εγγραφή ένα αντικείμενο ή της παίρνει ένα, όπως τα `inv add` και `inv drop`: οι λεπτομέρειές του έρχονται από τη συλλογή, αρκεί ένα μοναδικό μέρος του ονόματός του, και ελέγχονται ο χώρος και τα hooks του πεδίου |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | χρησιμοποιεί ένα αντικείμενο που κουβαλά, όπως το `inv use`: οι χρήσεις ή τα φορτία μετρούν αντίστροφα, ένα ζάρι χρήσης ρίχνεται και με 1–2 πέφτει ένα βήμα, και ένα που εξαντλείται χάνεται, εκτός αν επαναφορτίζεται ή κρατιέται· από πολλά με αυτό το όνομα, το πρώτο που έχει ακόμη χρήση· δεσμεύει τα `@torch.out` (η τελευταία του χρήση πήγε), `@torch.gone` (δεν έμεινε τίποτα από αυτό), `@torch.left`, `@torch.die` και `@torch.rolled` (το `as:` είναι εξ ορισμού `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | φτιάχνει αμέσως μια εγγραφή, που περιγράφεται όπως στο βήμα `entity` ενός πρόχειρου (παρακάτω) και ελέγχεται έναντι του φύλλου της· το `as:` (αλλιώς το `key` της, αλλιώς ο τύπος της) τη δεσμεύει ως εγγραφή, που τη διαβάζετε και την αλλάζετε όπως μια παράμετρο `ref` (`pool: "@bleeding"`, `@bleeding.name`), και δεν είναι ποτέ όνομα παραμέτρου· χωρίς `key:` κανένα πεδίο δεν λογίζεται ως κλειδί (το `kind: track` μένει όπως γράφτηκε)· αν υπάρχει ήδη εδώ εγγραφή με τον ίδιο τύπο και το ίδιο όνομα, χρησιμοποιείται αυτή όπως είναι, οπότε ένας κανόνας που τρέχει ξανά δεν φτιάχνει τίποτα καινούργιο |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | τρέχει έναν έλεγχο και δεσμεύει την έκβασή του |
| `do: other-action`, `with: {…}`, `as: trip` | τρέχει άλλον κανόνα· το `@trip` είναι το αποτέλεσμά του και το `@trip.<name>` ό,τι δέσμευσε εκείνος (`@trip.found` για το `let: {found: 2}` του, `@trip.luck` για το `roll: d6`, `as: luck` του)· το `as:` είναι εξ ορισμού το αναγνωριστικό του |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | μια καταγεγραμμένη ρίψη σε πίνακα· δεσμεύει το κείμενο και τα `data` της καταχώρισης (`@scar.<key>`, και τα κλειδιά μιας αντιστοίχισης με τη διαδρομή τους: `@scar.cost.hp`), μαζί με εκείνα κάθε πίνακα στον οποίο ρίχνει στη συνέχεια· μια λίστα αντικειμένων (`[Rope, {name: Laser, damage: d8}]`) διαβάζεται ως τα ονόματά τους (`count(@scar.gear)`, `'Laser' in @scar.gear`), και όταν δίνεται σε ένα βήμα όπως είναι (`apply: "@scar.gear"`) είναι τα ίδια τα αντικείμενα· μια λίστα άλλων αντιστοιχίσεων τη διαβάζει μόνο ένα βήμα |
| `table: "setting-{@drop.difficulty}-terrain"` | ένας υπολογιζόμενος πίνακας: τα `{…}` και `$param` συμπληρώνονται |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | πολλά αποτελέσματα ως λίστα (το `distinct` ξαναρίχνει τις επαναλήψεις) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | διακλαδώσεις |
| `repeat: "@count"`, `as: i`, `steps: […]` | ένας βρόχος: εκτελεί τα βήματα όσες φορές ορίζει η τιμή του, με το `@i` να μετράει από το 1 |
| `for: pcs` (ή `party`), `as: member`, `steps: […]` | εκτελεί τα βήματα μία φορά για κάθε χαρακτήρα παίκτη (ή μέλος της ομάδας), ως `@member`: μια εγγραφή, όπως αυτή που δεσμεύει το `entity:` (`@member.name`, `set: member.fatigue`)· το `as:` δεν παίρνει ποτέ το όνομα μιας παραμέτρου, οπότε το `who` του ίδιου του κανόνα μένει δικό του |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | έξοδος για το LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (ή `every: 1 day`) | μια υπενθύμιση που έρχεται η ώρα της καθώς περνά ο χρόνος του παιχνιδιού, όπως αυτές που ορίζει το `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | ξαναρίχνει μερικά από τα ζάρια μιας ρίψης (μηχανισμοί «πιέσματος») |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | ρίχνει σε μια τιμή-λίστα (τις λίστες ενός μαντείου): δεσμεύει την καταχώριση, το `@who.choose` (μια κενή γραμμή) και το `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | ρίχνει τη φθίνουσα δεξαμενή ενός μετρητή όπως το `track roll` (τα ζάρια με 1-3 αφαιρούνται· τα ζάρια του `drop` αφαιρούνται πρώτα, τα ζάρια του `extra` ρίχνονται μαζί) ή μόνο αφαιρεί ζάρια (`mode: drop`: ένα «πίεσμα», ένα τσεκάρισμα)· ακολουθούν οι συνδεδεμένες φάσεις και το γεγονός της δεξαμενής· δεσμεύει `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Η έκβαση ενός ελέγχου είναι αναγνώσιμη από τον κανόνα που τον έτρεξε (το `check: … as: answer` δίνει `@answer`), όπως και οι σημαίες του: `'random-event' in @answer.flags`. Οι τιμές του `with:` αποτιμώνται όταν περιέχουν `@`, συμπληρώνονται όταν περιέχουν `$param` ή `{…}` («Does $npc flee?») και περνούν όπως είναι γραμμένες σε κάθε άλλη περίπτωση. Ένας κανόνας με παράμετρο `oracle` παίρνει την εγγραφή κατάστασης του μαντείου της καμπάνιας χωρίς να του το πει κανείς. Μια παράμετρος `ref` με `to: monster` παίρνει μια εγγραφή αυτού του τύπου: ένα όνομα που μοιράζεται με άλλη εγγραφή (η δεξαμενή ενός εχθρού, με το όνομα της κάρτας του) είναι εκείνη αυτού του τύπου.

Τα εναύσματα τρέχουν μόνα τους όταν συμβεί το γεγονός τους, και μόνο αν ισχύει το `when:` τους:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Κάθε κανόνας (ακόμη και μια γεννήτρια ή η δημιουργία χαρακτήρων) μπορεί να διαβάσει `@system` (το αναγνωριστικό του συστήματος με το οποίο παίζει ο κόσμος, ώστε ένα σκηνικό γραμμένο για δύο συστήματα να μπορεί να τα ξεχωρίσει), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` και `@time.is_night` και, με ημερολόγιο με μήνες, `@time.month`, `@time.month_name`, `@time.day_of_month` και `@time.year`· όσο είναι σε εξέλιξη μια μάχη, `@combat.round` και `@combat.fighters` (τα αναγνωριστικά όσων συμμετέχουν σε αυτήν). Ένα χρονικό έναυσμα μπορεί επίσης να διαβάσει το `@time.passed`, τα δευτερόλεπτα που μόλις πέρασαν, ένα έναυσμα `combat_start` ή `combat_end` διαβάζει τη μάχη που ξεκινά ή τελειώνει (τα τρέχουν οι εντολές `combat start` και `combat end`· η αποχώρηση ενός μαχητή δεν τερματίζει τη μάχη), και ένας κανόνας που τον τρέχει ένα έναυσμα διαβάζει ό,τι διαβάζει και το έναυσμα. Ένα έναυσμα με υποχρεωτικές παραμέτρους τρέχει μόνο από το `didact do` ή από ένα hook πεδίου (`who` = η εγγραφή). Τα εναύσματα `on: manual` τρέχουν μόνο όταν καλούνται. Το `for: pcs` (ή `party`) εκτελεί ένα έναυσμα μία φορά για κάθε χαρακτήρα παίκτη (ή μέλος της ομάδας), ως `who`: την εμπειρία μετά από κάθε συνεδρία, ας πούμε. Ένα έναυσμα που αποτυγχάνει σταματά την εντολή που το πυροδότησε, και λέει ποιο έναυσμα ήταν και πώς να συνεχίσετε χωρίς αυτό (`didact override add trigger <id> --data '{"on": "manual"}'`).

Το ημερολόγιο βρίσκεται στα `settings` ενός πακέτου: εκείνο ενός πακέτου σκηνικού υπερισχύει εκείνου του συστήματος, και το δικό του ημερολόγιο ενός κόσμου (`calendar:` στο `world.yaml` του) υπερισχύει και των δύο:

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

Το `leap: 4` κάνει έναν μήνα μία ημέρα μεγαλύτερο κάθε 4ο έτος, και το `leap: [4, 100, 400]` κάθε 4ο, όχι όμως κάθε 100ό, αλλά πάλι κάθε 400ό: κάθε αριθμός ανατρέπει τον προηγούμενο. Το `weekday` ονομάζει την ημέρα της εβδομάδας της αρχής (αλλιώς είναι η πρώτη της εβδομάδας), και το `year` είναι το πώς μια ημερομηνία γράφει το έτος της, τόσο σε όσες δείχνει το Didact όσο και σε όσες διαβάζει (`"3A {year}"`: `17 Frost 3A 201`)· το `pack validate` ελέγχει και τα τρία. Μια καμπάνια μπορεί να ξεκινήσει σε άλλη ημερομηνία του ημερολογίου, πριν από την αρχή του ή μετά: `didact campaign new <id> --date '4 July 1902'`, ή `didact time set '<date>'` μέχρι την πρώτη της συνεδρία. Μια ημέρα της εβδομάδας γραμμένη πριν από την ημερομηνία ελέγχεται: αποφασίζει η ημερομηνία, και μια σημείωση το λέει όταν πέφτει σε άλλη ημέρα.

Οι επιλογές είναι οι παραλλαγές και οι προαιρετικοί κανόνες του συστήματος, που κάθε καμπάνια διαλέγει στη μηδενική συνεδρία:

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

Το `didact campaign profile lethality=deadly supplies=on` τις αποθηκεύει (ή η σελίδα Ρυθμίσεις της διαδικτυακής εφαρμογής). Οι κανόνες, η δημιουργία χαρακτήρων και οι γεννήτριες τις διαβάζουν (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): μια απάντηση υπερισχύει αυτού που συνεπάγεται μια άλλη επιλογή, κι αυτό υπερισχύει της προεπιλογής. Ό,τι συνεπάγεται μια επιλογή ακολουθείται μέχρι τέλους (ένα ύφος που ορίζει τη θνησιμότητα ορίζει και ό,τι συνεπάγεται εκείνη η θνησιμότητα), και από δύο συνεπαγωγές υπερισχύει η πιο κοντινή. Η ενημέρωση απαριθμεί όσες διαφέρουν από την προεπιλογή τους, με το τι σημαίνουν, ώστε ο αφηγητής να εφαρμόζει ό,τι δεν μπορούν οι κανόνες. Μια γεννήτρια που δεν μπορεί να τρέξει υπό αυτές σταματά με `stop:` και τον λόγο, και δεν δημιουργείται πρόχειρο.

## Μαντεία: `oracles/`

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

- **Ερωτήσεις:** το `didact ask '…' --odds likely` τρέχει τον έλεγχο `ask`. Η απάντηση είναι η έκβασή του (μια ζώνη), και οι σημαίες του έρχονται μαζί.
- **Κατάσταση:** βρίσκεται σε μια εγγραφή που ο έλεγχος λαμβάνει ως `oracle`. Ένας έλεγχος την αλλάζει με `set: oracle.chaos += 1`.
- **Λίστες:** το `lists: {names: […], method: sections, most: 3}` κρατά σταθμισμένες λίστες σε εκείνη την εγγραφή. Τα `didact lists add|drop|roll|show` τις διαχειρίζονται, και οι κανόνες ρίχνουν σε αυτές με `pick`. Το `sections` ρίχνει για μια ενότητα πέντε γραμμών, και μετά για μια γραμμή μέσα της (μια κενή γραμμή σημαίνει «διαλέξτε»)· το `uniform` δίνει σε κάθε γραμμή την ίδια πιθανότητα.
- **Επιπλέον για τον έλεγχο:** το `didact ask '…' --with as_rule=true` περνά επιπλέον παραμέτρους στον έλεγχο του μαντείου.
- **Το αρχείο καταγραφής:** κάθε απάντηση αριθμείται (`#o12`) και καταγράφεται, και το `didact interpret o12 '…'` κρατά τι σήμαινε. Το μαντείο `yes-no` του πακέτου core είναι η εναλλακτική.

## Γεννήτριες και δημιουργία χαρακτήρων: `generators/`, `chargen/`

Και οι δύο είναι διαδικασίες που χτίζουν ένα **πρόχειρο**. Χρησιμοποιούν κάθε βήμα κανόνα (`roll`, `table`, `if`, `let`, `prompt`, …) και επιπλέον αυτά:

| Βήμα | Κάνει |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | προσθέτει μια εγγραφή στο πρόχειρο (κλειδιά `poi-1`, `poi-2`, …)· ένα πεδίο ή ένας σύνδεσμος που κατονομάζει ένα κλειδί που έγραψε το πακέτο (`key:` ή ένα όνομα `as:`) γίνεται το αναγνωριστικό εκείνης της εγγραφής κατά την οριστικοποίηση, οπότε διαλέξτε κλειδιά που κανένα πεδίο δεν έχει ως κείμενο (μια οντότητα χωρίς κανένα από τα δύο δεν έχει κλειδί προς αντικατάσταση)· το `from: "@relic.id"` την ξεκινά από μια καταχώριση της συλλογής (τον τύπο, το όνομα και τα πεδία της) |
| `choose: {from: [a, b], as: x}` (ή `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | μια επιλογή· σε καθοδηγούμενη λειτουργία το πρόχειρο περιμένει το `choose`· το `exclude` αποκλείει προηγούμενες επιλογές (μια που ρίχτηκε ξαναρίχνεται)· το `records:` προσθέτει στις επιλογές τις εγγραφές εκείνου του τύπου που υπάρχουν εδώ, με το id τους (όσες φτιάχτηκαν στο παιχνίδι)· το `answer:` κάνει την επιλογή χωρίς να ρωτήσει, όταν η τιμή του είναι μία από τις επιλογές (το μονοπάτι που έχει ήδη ο χαρακτήρας) |
| `choose_or_roll: {table: backgrounds, as: background}` | μια επιλογή που μπορούν να κάνουν τα ζάρια· τα data μιας επιλεγμένης καταχώρισης είναι `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | ρίψεις στον χαρακτήρα |
| `swap: {among: [STR, DEX, WIL], optional: true}` | ανταλλαγή δύο τιμών, ή διατήρηση |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | μοιράζει μια σταθερή σειρά τιμών |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | αγορά τιμών μέσα σε έναν προϋπολογισμό (το `default: random` τον ξοδεύει τυχαία σε τυχαία λειτουργία) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | μια λίστα πηγαίνει στο απόθεμα· μια αντιστοίχιση ορίζει πεδία (οι λίστες αθροίζονται) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | προσθέτει σε ένα πεδίο του χαρακτήρα (ή μιας οντότητας του πρόχειρου): οι αριθμοί αθροίζονται, οτιδήποτε άλλο μπαίνει σε λίστα· αν δεν υπάρχει τίποτα να προστεθεί, κανένα πρόβλημα |
| `remove: {field: talents, value: "@old"}` | αφαιρεί κάτι από ένα πεδίο λίστας (ένα ταλέντο που αντικαταστάθηκε, έναν δεσμό που επιλύθηκε)· αν δεν υπάρχει, κανένα πρόβλημα |
| `roll_tables: [physique, vice]` | ρίχνει σε πίνακες για τα `traits`· το `data.gear` μιας καταχώρισης πηγαίνει στο απόθεμα και το `data.add: {gold: 20}` προσθέτει σε πεδία |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | το όνομα· το `name: {prompt: …}` χωρίς κάτι για να ρίξει περιμένει ένα όνομα, ακόμη και σε τυχαία λειτουργία |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | μια ερώτηση που δέχεται οποιαδήποτε απάντηση (έναν στόχο, το όνομα άλλης εγγραφής): το πρόχειρο την περιμένει, ακόμη και σε τυχαία λειτουργία, εκτός αν έχει συμπληρωθεί από πριν· το `field:` αποθηκεύει την απάντηση |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | ένα pointcrawl: μια καταγεγραμμένη ρίψη ζαριών πάνω στον χάρτη, διαδρομές (πάντα συνδεδεμένες), αποστάσεις, κρυφές διαδρομές (δείτε παρακάτω) |

Το βήμα map δέχεται κι άλλα, για τις διαδικασίες του βιβλίου με ρίψη ζαριών πάνω στον χάρτη:

| Κλειδί | Κάνει |
|---|---|
| `regions: terrain` | ρίχνονται κι αυτές οι οντότητες· κάθε τοποθεσία εντάσσεται στην πλησιέστερη (το `region` της) |
| `hidden: 6`, `conditional: 5` | ένα d6 ανά διαδρομή: στον αριθμό ή πάνω, μια κρυφή ή υπό όρους διαδρομή (οι κρυφές διαδρομές μένουν εκτός του χάρτη των παικτών) |
| `describe: [path-feature, path-condition]` | πίνακες που ρίχνονται για κάθε διαδρομή, και κρατιούνται ως `details` της |
| `entrance: true`, `exit: true` | η τοποθεσία πιο κοντά στην άκρη είναι η είσοδος· οι υπόλοιπες αριθμούνται από εκεί κατά μήκος των διαδρομών (`map.n`), οι διαδρομές απομακρύνονται από αυτήν, και η έξοδος είναι μια μακρινή τοποθεσία κοντά σε άκρη, με τον τελευταίο αριθμό |
| `number: "{@dungeon_name}, room {@n}"` | μετονομάζει τις αριθμημένες τοποθεσίες (τα κλειδιά τους στο πρόχειρο ακολουθούν: το `room-1` είναι το δωμάτιο 1) |

Ένας πίνακας ρίψης στον χάρτη μπορεί να κατονομάζει τους επόμενους πίνακες στα data των καταχωρίσεών του, ώστε η διαδικασία να διαβάζεται όπως το βιβλίο: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, και μετά `table: "{@drop.what}"`. Τα πεδία λίστας χωρίς τιμή (conditions, lists, tags) διαβάζονται ως κενές λίστες, οπότε το `'deprived' in @who.conditions` δουλεύει από την αρχή.

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

Ένα chargen με `advances:` αλλάζει μια εγγραφή αντί να φτιάχνει καινούργια: η άνοδος επιπέδου του συστήματος.

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

- **Μία εγγραφή:** μια γεννήτρια με `creates: npc` χτίζει εκείνη την εγγραφή όπως η δημιουργία χαρακτήρα χτίζει έναν χαρακτήρα (`apply`, `add`, `name`, `field:`)· τα βήματά της `entity` προσθέτουν εγγραφές δίπλα της, και ένας σύνδεσμος `to: character` δείχνει σε αυτήν.
- **Εκτέλεση:** τα `gen run` και `char new` φτιάχνουν ένα πρόχειρο (`#g7`, `#c3`) και δεν γράφουν τίποτα. Ένα `stop:` τερματίζει την εκτέλεση χωρίς πρόχειρο: κάτω από ένα `if:` που διαβάζει μια επιλογή της καμπάνιας, η υπόδειξή του δείχνει τις επιλογές (`didact session zero`)· αλλιώς, τα δικά του λόγια λένε τι να κάνετε αντί γι' αυτό.
- **Αποφάσεις:** το `--prefill '{…}'` αποφασίζει πράγματα εκ των προτέρων, με το όνομα που δεσμεύει ένα βήμα (`as:`): μια μεμονωμένη τιμή απαντά σε κάθε εμφάνιση, μια λίστα σε μία εμφάνιση το κάθε στοιχείο (μια λίστα για `choose` με `count` είναι ολόκληρη η επιλογή). Και οι τιμές `let` μπορούν να προσυμπληρωθούν (`{"hp": 6}`), ενώ ένα όνομα, ένα `ask` ή ένα `let` κρατά οποιοδήποτε κείμενο όπως δόθηκε. Μια τιμή για μια επιλογή ανάμεσα σε γνωστές δυνατότητες (ένα `choose`, μια καταχώριση πίνακα) είναι η δυνατότητα που κατονομάζει, όπως είναι γραμμένη ή με διαφορετικά πεζά/κεφαλαία, με το `id` της καταχώρισής της ή με μια ρίψη που πέφτει σε αυτήν (`{"group": 3}`), και φέρνει μαζί τα data εκείνης της καταχώρισης· μια τιμή που μοιάζει με κάποια δυνατότητα χωρίς να είναι καμία από αυτές απορρίπτεται, με αναφορά στην πλησιέστερη, και κάθε άλλη είναι μια δική σας απάντηση, χωρίς data. Το `--auto` (ή `char new --mode random`) αφήνει τα ζάρια να αποφασίσουν τα υπόλοιπα. Αλλιώς το πρόχειρο περιμένει σε κάθε επιλογή.
- **Περιγραφή:** μια επιλογή λέει, για τον παίκτη που διαλέγει, τι σημαίνει καθεμία από τις δυνατότητές της: το `note:` μιας καταχώρισης πίνακα ή το `about:` του πίνακά της, αλλιώς η καταχώριση της συλλογής που κατονομάζει (το `id` στα data της), ή εκείνη που είναι η ίδια η δυνατότητα (μια επιλογή ανάμεσα σε αναγνωριστικά της συλλογής δείχνει το όνομα της καθεμίας): τα `tagline` και `summary` της, το `description` ή το `effect` της, αλλιώς η πρώτη παράγραφος του κειμένου της.
- **Επιστροφή:** το `char back` (ή το `gen back`) παίρνει πίσω την τελευταία απάντηση, ρίψη ή επεξεργασία, οπότε το πρόχειρο κάνει ξανά εκείνη την ερώτηση· οι ρίψεις που έγιναν σε εκείνο το βήμα σημειώνονται ως αναιρεμένες.
- **Συνέχιση:** ένα πρόχειρο που συνεχίζεται αναπαράγει τη διαδρομή του: κάθε τιμή που ρίχτηκε ή επιλέχθηκε, η καθεμία μία φορά και με τη σειρά (και η ρίψη πάνω στον χάρτη), οπότε τίποτα δεν ρίχνεται δύο φορές και τίποτα ήδη αποφασισμένο δεν αλλάζει.
- **Εγγραφή:** το `commit` γράφει τις εγγραφές, ελεγμένες έναντι των φύλλων τους.
- **Εξέλιξη:** ένα πρόχειρο `advances:` ξεκινά από αντίγραφο της εγγραφής (με τις προεπιλογές του φύλλου της), τα βήματά του διαβάζουν την εγγραφή ως `@who` και τις τιμές του πρόχειρου ως `@character.*`, και το `commit` γράφει μόνο ό,τι άλλαξε, ελεγμένο όπως με το `set`· οι εγγραφές από τα βήματά του `entity` (το νήμα ενός νέου δεσμού) δημιουργούνται δίπλα της: ένας σύνδεσμος `to: character` δείχνει στην εγγραφή, και ένα πεδίο που κατονομάζει ένα κλειδί κρατά το αναγνωριστικό της εγγραφής αυτού του κλειδιού, όπως όταν φτιάχνεται ένας χαρακτήρας (`apply: {blood: "@pool"}`). Ένα `stop:` λέει γιατί όχι ακόμη (δεν φτάνουν τα XP), και δεν δημιουργείται πρόχειρο. Ένα σύστημα όπου η εξέλιξη είναι ένας μόνο κανόνας τον ονομάζει αντί γι' αυτό στο chargen του: `advance: {rule: grow}`.
- **Λειτουργίες:** το `modes: [guided]` κρατά μια διαδικασία βήμα βήμα: το `--mode random` απορρίπτεται.

## Συλλογή, αναφορά και γλωσσάριο

- **Οι καταχωρίσεις της συλλογής** γράφονται όπως το `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Μια τιμή `"roll 2d8"` ρίχνεται όταν δημιουργείται η καταχώριση. Τρέξτε `didact spawn troll` ή φέρτε τις καταχωρίσεις ενός πακέτου στον κόσμο με `didact compendium import <pack>` (`--type loc`, και `--tag coast` για όσες έχουν κάθε ετικέτα που δίνεται).
- **Για πολλά συστήματα:** ένα κλειδί στο ανώτατο επίπεδο πηγαίνει εκεί που το βάζει το `set`: στο μπλοκ του συστήματος, όταν το φύλλο του έχει αυτό το πεδίο, αλλιώς στα `fields`. Μια καταχώριση που γράφει ένα σκηνικό για περισσότερα από ένα συστήματα δίνει τους αριθμούς του καθενός στο δικό του μπλοκ (`mechanics: {my-system: {hp: 12}}`): το `pack validate` ελέγχει το καθένα με βάση το φύλλο του συστήματός του, όταν είναι εγκατεστημένο, και σημειώνει ένα κλειδί στο ανώτατο επίπεδο που το έχουν και αυτό το φύλλο και εκείνο του core. Ό,τι λέει ένα μπλοκ ισχύει: δίπλα στο `mechanics: {my-system: {role: tactician}}`, ένα `role: innkeeper` στο ανώτατο επίπεδο είναι πεδίο του core, όπως και οτιδήποτε κάτω από `fields:`. Ένα μπλοκ που ονομάζει το πακέτο που επικυρώνεται ελέγχεται έναντι εκείνου του πακέτου όπως είναι στον φάκελό του.
- **Οι ενότητες αναφοράς** μπαίνουν στο `reference/*.md`, με front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). Το `didact rules lookup <topic>` τις βρίσκει· μια φράση σε εισαγωγικά που δεν υπάρχει εκεί δοκιμάζεται με τις λέξεις της.
- **Το γλωσσάριο** είναι το `glossary.yaml`: `term: definition`, ή μια λίστα από `{term, definition, aliases, see}`. Το `didact define <term>` το διαβάζει.

## Τεστ: `tests/`

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

## Κοινή χρήση και αφαίρεση πακέτων

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Ένα πακέτο που δηλώνει `redistributable: false` δεν μπορεί να εξαχθεί.
- Το **core** είναι μέρος του Didact και πάντα ενεργό: κάθε σύστημα χτίζεται πάνω του, οπότε δεν απενεργοποιείται ούτε απεγκαθίσταται.
- Τα άλλα πακέτα που έρχονται με το Didact είναι αρχεία `.didactpack` στον φάκελο `packs/` του. Το `pack list` τα δείχνει μέχρι να εγκατασταθούν, και η εγκατάσταση ενός φέρνει και τα πακέτα που χρειάζεται, εφόσον έρχονται κι αυτά με το Didact.
- Το `pack update` ψάχνει για νεότερες εκδόσεις στον φάκελο `packs/` του Didact και στο GitHub (`vess-dev/Didact`· το `DIDACT_PACK_UPDATES` ορίζει άλλο μέρος, ή τίποτα για να μην ψάχνει). Μια νέα έκδοση εγκαθίσταται δίπλα στην παλιά: οι καμπάνιες κρατούν τη δική τους μέχρι το `didact campaign upgrade`.
- Κάθε φορά είναι σε χρήση ένα σύστημα παιχνιδιού: αυτό του ανοιχτού κόσμου. Ένας κόσμος κρατά το σύστημα με το οποίο φτιάχτηκε (`didact world new <id> --system <pack>`· ένας κόσμος που φτιάχτηκε χωρίς σύστημα παίρνει το πρώτο που του δίνεται, με `pack enable` ή `world set system=`), οι καμπάνιες του παίζουν με αυτό, και ένα πακέτο που χρειάζεται άλλο σύστημα (ένα σκηνικό γραμμένο γι' αυτό) δεν μπορεί να προστεθεί: άλλο σύστημα παίζεται σε δικό του κόσμο.
- Το `uninstall` αρνείται όσο ένας κόσμος ή μια καμπάνια χρησιμοποιεί το μοναδικό αντίγραφο του πακέτου (το `--force` το αφαιρεί παρ' όλα αυτά). Δεν αναιρείται: εγκαταστήστε ξανά το .didactpack.

## Από το βιβλίο κανόνων στο πακέτο: η λίστα ελέγχου

Περάστε τους μηχανισμούς του βιβλίου με αυτή τη σειρά. Ο καθένας αντιστοιχεί σε κάτι από τα παραπάνω:

1. **Επίλυση:** πώς πετυχαίνει μια ρίψη (ένας έλεγχος: `success`, `bands`, `auto`).
2. **Ζάρια:** ασυνήθιστα ζάρια, σύμβολα, βήματα (`dice.yaml`, ζάρια με όνομα, αλυσίδες).
3. **Το φύλλο:** χαρακτηριστικά, παράγωγοι αριθμοί (`schemas/`, παράγωγα πεδία).
4. **Πόροι:** HP, τύχη, ορμή (πεδία resource και counter· βήματα `set`).
5. **Καταστάσεις:** καταστάσεις και τι κάνουν (πεδία `conditions`· βήματα `if`).
6. **Μάχη:** επιθέσεις, ζημιά, πρωτοβουλία (ενέργειες· `bag`/`deck` για τη σειρά).
7. **Διαδικασίες:** εξερεύνηση, ταξίδι, ανάπαυλα (διαδικασίες με ερωτήματα).
8. **Πίνακες:** κάθε πίνακας τυχαίων αποτελεσμάτων (`tables/`· `pack import` για πίνακες Markdown).
9. **Ο κατάλογος τεράτων:** τέρατα και NPC (`compendium/`).
10. **Αντικείμενα:** εξοπλισμός, ξόρκια, κειμήλια (`compendium/`, πεδία slots).
11. **Οδηγίες για τον GM:** αρχές και συμβουλές (`GUIDE.md`, `reference/`, `guidance:` στους τύπους).
12. **Δημιουργία χαρακτήρα:** πώς φτιάχνεται ένας χαρακτήρας (μια διαδικασία `chargen/`, ή `roll:` σε κάθε πεδίο).

Αναφέρετε σελίδες με `source:` παντού, ώστε να φαίνονται τα κενά. Προσθέστε ένα τεστ smoke-play που φτιάχνει έναν χαρακτήρα, ρίχνει έναν έλεγχο, δίνει μια μάχη και τρέχει μια διαδικασία.
