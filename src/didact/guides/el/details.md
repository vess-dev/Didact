<!-- translated from 7fe144069f94 -->
# Λεπτομέρειες, χρονικό και θέσεις

Οι σημειώσεις του GM που κρατούν ένα παιχνίδι συνεπές: πώς μοιάζουν τα πράγματα και τι θέλουν, τι κάνουν και τι σχεδιάζουν μετά, τι τους συνέβη και πού βρίσκεται το καθετί.

## Λεπτομέρειες

Σύντομες σημειώσεις με όνομα σε οποιαδήποτε εγγραφή: ένα πρόσωπο, ένα αντικείμενο, μια τοποθεσία, μια φατρία.

```
didact about sweeney looks='tall, one eye clouded' personality='jovial, greedy'
didact about sweeney wants='buy back the mill' plan='sell the route to the raiders'
didact about sweeney doing='whittling by the fire' where='the back room of the inn'
didact about item:old-sword history='forged for the last king' powers='cuts through wards'
didact about loc:the-ford state='flooded' secret='a drowned shrine under the stones'
didact about sweeney thoughts='built to foreshadow the betrayal; pay it off at the ford'
didact about sweeney                  # the notes, what's still open, chronicle, whereabouts
didact about sweeney --clear doing    # or doing='' 
```

- **Ονόματα.** Τα προτεινόμενα εξαρτώνται από το είδος της εγγραφής, και δουλεύει κάθε όνομα μίας λέξης:
  - πρόσωπα: looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts·
  - αντικείμενα: looks, history, where, powers, secret, thoughts·
  - τοποθεσίες: looks, state, history, secret, thoughts·
  - οργανώσεις: wants, plan, state, history, secret, thoughts.

  Ένα πακέτο μπορεί να προτείνει δικά του ανά τύπο (`details: [mood, grudge]` σε ένα σχήμα).
- **Ποιος βλέπει τι.** Οι παίκτες βλέπουν μόνο το `looks`: τα `show` και `find` αφήνουν έξω τα υπόλοιπα, και το `--gm` δείχνει τα πάντα. Όταν οι παίκτες μάθουν μία, το `didact reveal sweeney plan` τη μεταφέρει στο κείμενο της εγγραφής, κάτω από το `## Revealed`.
- **Τα `thoughts`** είναι δικά σας: γιατί το φτιάξατε, πού μπορεί να οδηγήσει, τι να αξιοποιήσετε αργότερα.
- **Κρατήστε τις ενημερωμένες.** Δεν χρειάζεται να σημειώνετε τα πάντα. Όταν όμως αποφασίζετε κάτι (ένα σχέδιο, μια έχθρα, πού πήγε κάποιος), γράψτε το, ώστε η επόμενη σκηνή, ή η επόμενη συνεδρία, να μείνει πιστή σε αυτό.

## Το χρονικό: τι συνέβη σε ποιον

Ένα συμβάν του ημερολογίου μπορεί να κατονομάζει τις εγγραφές που αφορά. Τότε εμφανίζεται στην καθεμία τους.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- Τα `show` και `about` παραθέτουν το χρονικό μιας εγγραφής: τι έκανε και τι της έκαναν.
- **Τα μυστικά συμβάντα** γίνονται μακριά από τα μάτια των παικτών. Εμφανίζονται μόνο στις προβολές GM (`session show --gm`, `about`, `brief --gm`), και ποτέ στο `export --as story`.
- Χρησιμοποιήστε το `--about` για ό,τι αλλάζει κάποιον ή κάτι: μια προδοσία, ένα χρέος, έναν θάνατο, ένα δώρο, μια αθετημένη υπόσχεση.
- **Διόρθωση συμβάντος:** το `didact beat edit S1.4 --about tom` το βάζει στο χρονικό του Tom (ή `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), και το `didact beat rm S1.4` το αφαιρεί. Τα αναγνωριστικά φαίνονται στο `session show`, και τα δύο αναιρούνται.
- **Όταν αλλάζουν τα αναγνωριστικά:** ένα `merge` ή ένα νέο slug παίρνει μαζί του κάθε αναφορά: συνδέσμους, λεπτομέρειες, τις εγγραφές που αφορούν τα συμβάντα, την ομάδα, τη μάχη και την τοποθεσία της ομάδας. Όταν μια εγγραφή διαγράφεται με `rm`, βγαίνει και από κάθε ομάδα ή μάχη. Ένα `merge` ανάμεσα σε τύπους κρατά ό,τι έχει πεδίο στο φύλλο της εγγραφής που μένει, και λέει τι αφήνει έξω.

## Θέσεις: πού βρίσκεται το καθετί

Τα αντικείμενα βρίσκονται σε αποθέματα, και οτιδήποτε μπορεί να τα κρατά: ένας χαρακτήρας, μια τοποθεσία, ένα σεντούκι.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Κατά τη διάρκεια μιας συνεδρίας, η μετακίνηση ενός αντικειμένου καταγράφει ένα συμβάν για αυτόν που δίνει και αυτόν που παίρνει («Sword: Freya → Chest»). Έτσι τα χρονικά τους λένε πού πήγαν τα πράγματα.
- **Τα πρόσωπα και τα τέρατα** είναι επισκέπτες των τοποθεσιών, όχι περιεχόμενό τους: κρατήστε πού βρίσκονται στη λεπτομέρεια `where`.

## Σε σκηνές και μάχες

- **Το `combat status --gm`** δείχνει το `where`, το `doing` και το `plan` κάθε μαχητή. Ενημερώνετέ τα καθώς εξελίσσεται η μάχη: `didact about goblin where='on the bridge' plan='cut the rope'`.
- **Το `brief --gm`** (η ενημέρωση με την οποία ξεκινά μια συνεδρία) παραθέτει ό,τι παίζει ρόλο (την τοποθεσία, τους μαχητές, όποιον αφορούν τα συμβάντα αυτής της σκηνής και την ομάδα) με where, doing, plan και state. Παραθέτει επίσης τα πιο πρόσφατα συμβάντα εκτός σκηνής.
