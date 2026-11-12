<!-- translated from 7fe144069f94 -->
# Détails, chronique et localisation

Les notes du MJ qui gardent une partie cohérente : à quoi ressemblent les choses et ce qu'elles veulent, ce qu'elles font et prévoient, ce qui leur est arrivé, et où tout se trouve.

## Détails

De courtes notes nommées sur n'importe quelle fiche : une personne, un objet, un lieu, une faction.

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

- **Noms.** Les noms suggérés dépendent du type de fiche, et n'importe quel nom d'un seul mot fonctionne :
  - personnes : looks, personality, wants, fears, attitude, doing, plan, where, history, secret, thoughts ;
  - objets : looks, history, where, powers, secret, thoughts ;
  - lieux : looks, state, history, secret, thoughts ;
  - groupes : wants, plan, state, history, secret, thoughts.

  Un pack peut suggérer les siens pour chaque type (`details: [mood, grudge]` dans un schéma).
- **Qui voit quoi.** Les joueurs ne voient que `looks` : `show` et `find` omettent le reste, et `--gm` montre tout. Quand les joueurs en découvrent un, `didact reveal sweeney plan` le déplace dans le texte de la fiche, sous `## Revealed`.
- **`thoughts`** sont pour vous : pourquoi vous l'avez créé, où cela peut mener, ce qu'il faudra payer plus tard.
- **Tenez-les à jour.** Inutile de tout noter. Mais quand vous décidez quelque chose (un plan, une rancune, où quelqu'un est parti), écrivez-le, pour que la scène suivante, ou la séance suivante, y reste fidèle.

## La chronique : ce qui est arrivé à qui

Un événement du journal peut nommer les fiches qu'il concerne. Il apparaît alors sur chacune d'elles.

```
didact log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya
didact log note 'Raider scouts find the camp' --about raiders --secret   # out of sight
```

- `show` et `about` listent la chronique d'une fiche : ce qu'elle a fait, et ce qu'on lui a fait.
- **Les événements secrets** se produisent hors de la vue des joueurs. Ils n'apparaissent que dans les vues du MJ (`session show --gm`, `about`, `brief --gm`), et jamais dans `export --as story`.
- Utilisez `--about` pour tout ce qui change quelqu'un ou quelque chose : une trahison, une dette, une mort, un cadeau, une promesse rompue.
- **Corriger un événement :** `didact beat edit S1.4 --about tom` le place dans la chronique de Tom (ou `--not-about`, `--secret`, `--public`, `--text '…'`, `--importance 7`), et `didact beat rm S1.4` le supprime. Les identifiants sont dans `session show`, et les deux peuvent être annulés.
- **Quand les identifiants changent :** un `merge` ou un nouveau slug emporte toutes les références avec lui : liens, détails, fiches concernées par les événements, groupe, combat et position du groupe. Quand une fiche est supprimée avec `rm`, elle quitte aussi le groupe ou le combat où elle se trouvait. Un `merge` entre types garde ce pour quoi la feuille de la fiche conservée a un champ, et dit ce qu'il laisse de côté.

## Localisation : où sont les choses

Les objets vivent dans des inventaires, et tout peut en contenir : un personnage, un lieu, un coffre.

```
didact new item Chest
didact inv add 'my house' item:chest              # the chest is at the house
didact inv move freya sword chest                 # Freya puts the sword in the chest
didact where sword                                # sword: in Chest › at My House
didact show 'my house'                            # contents: Chest › Sword, all the way down
```

- Pendant une séance, déplacer un objet enregistre un événement concernant celui qui donne et celui qui reçoit (« Sword: Freya → Chest »). Leurs chroniques disent alors où sont allées les choses.
- **Les personnes et les monstres** sont des visiteurs des lieux, pas leur contenu : notez où ils sont dans leur détail `where`.

## En scène et en combat

- **`combat status --gm`** montre le `where`, le `doing` et le `plan` de chaque combattant. Mettez-les à jour au fil du combat : `didact about goblin where='on the bridge' plan='cut the rope'`.
- **`brief --gm`** (le résumé par lequel commence une séance) liste ce qui est en jeu (le lieu, les combattants, ceux que concernent les événements de cette scène, et le groupe) avec where, doing, plan et state. Il liste aussi les derniers événements hors champ.
