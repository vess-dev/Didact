<!-- translated from bef7b2c650cb -->
# Jouer une séance

Comment une partie se déroule avec Didact : le LLM raconte, et Didact garde chaque fait, chaque jet et chaque changement.

## Avant la première séance

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Un monde garde le système avec lequel il a été créé, et ses campagnes se jouent avec lui : un autre système se joue dans un monde qui lui est propre. `didact campaign close` met une campagne de côté (son monde reste ouvert) et `didact campaign open <id>` la reprend là où elle en était, séance comprise.

`didact world delete <id>` et `didact campaign delete <id>` en suppriment un, avec un aperçu d'abord ; `--yes` supprime, et `didact undo` rétablit tout.

`session zero` liste les questions à régler avec le joueur. Celles du pack viennent en premier. Les options du système (ses variantes et règles optionnelles) en font partie : ses règles suivent les réponses, et le résumé dit ce que signifie chaque option changée. Chaque résumé reprend les réponses.

## Une séance

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Tours :** chaque message du joueur ouvre un tour (le hook de Claude Code appelle `didact capture`, et les autres clients utilisent `turn begin`). `didact undo --turn` reprend tout ce qui a été fait pour ce message : changements, événements et jets. La transcription le conserve.
- **Retour en arrière :** `didact undo --to e40` reprend tout ce qui suit #e40, du plus récent au plus ancien (`--dry-run` le liste) : chaque changement est annulé et chaque jet marqué comme annulé. Rien n'est supprimé : `redo`, ou revenir à un changement plus récent, fait tout revenir.
- **Temps :** `didact time advance 1 watch` écoule les minuteurs, fait remonter les rappels et lance les déclencheurs temporels. `didact remind --list` montre les rappels à venir, et `didact remind --cancel 2` en retire un. Une campagne commence au début du calendrier, ou à la date que donne `campaign new --date '4 July 1902'`, et `didact time set '<date>'` la change jusqu'à la première séance.
- **Lieux :** `didact visit <place>` déplace le groupe et marque le lieu comme visité. `didact map` montre ce que le groupe connaît, et une sortie inexplorée est `?`.
- **Combats :** `didact combat start --party troll`, puis `combat next`, `combat hit freya troll weapon=d8` et `combat end`. Les combattants vont et viennent en plein combat : `didact combat join wolf-2` (en mode individuel, ils lancent l'initiative) et `didact combat leave troll --why fled`. Le tour de personne n'est sauté.
- **Objets :** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (ou dans un coffre, ou dans un lieu) ; `didact where rope` le retrouve. `inv add` trouve un objet du compendium par son identifiant, son nom ou un alias.
- **Vos notes :** `didact about sweeney plan='…' doing='…' where='…'` garde ce que vous avez décidé sur quelqu'un ou quelque chose. Les joueurs ne voient que `looks`. `didact log … --about sweeney` place un événement sur sa fiche (`--secret` si les joueurs ne le voient pas). `didact guide details` en dit plus.
- **Le monde avance :** `didact faction turn`, plus les horloges : `didact track new 'The flood' --size 6`. Une commande qui ne vise qu'une sorte de fiche prend un nom que d'autres partagent comme étant de cette sorte : `didact track roll draugr` lance la réserve qui porte le nom d'un ennemi (de même `track tick` un compteur, `quest done` une quête et `visit` un lieu).

## Oracles, générateurs et personnages

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

Rien de ce que crée un générateur ou une création de personnage n'est écrit avant `commit`. Décrivez ce que veut le joueur dans `--prefill`, et la procédure comble les vides. Une question liste ce que signifie chaque option quand le pack le précise (`- Cutpurse: …`) : dites-le au joueur, pour qu'il choisisse en sachant ce qu'il obtient.

## Secrets

Les vues sont sûres pour les joueurs par défaut : `show`, `find`, `sheet`, `map`, `brief`. Elles omettent :
- les fiches secrètes (`knowledge: secret`) ;
- les sections `## Secrets` et `## GM notes` ;
- les champs `secret: true`.

`--gm` montre tout. Quand les joueurs apprennent quelque chose :

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` écrit ce que savent les joueurs sous forme d'un petit site web à partager ou à lire sur un téléphone : le groupe, une page par fiche, le journal et la carte. Il est toujours sûr pour les joueurs, et exporter à nouveau vers ce dossier le met à jour. `didact export --as lonelog` écrit le journal en notation Lonelog (`@ ? d: -> =>`, les scènes en `S1`, des tags comme `[N:Sweeney]`), lui aussi sûr pour les joueurs.

## Lore : ce qui revient quand quelque chose est mentionné

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Ce qui compte :** chaque PNJ, lieu, objet et faction est une carte dont les clés sont son nom et ses alias. Les entrées de lore ont des `keys`, et les arbitrages remontent via leur règle. La correspondance se fait sur des mots entiers, et les pluriels comptent (« wolves » correspond à `wolf`).
- **Quand le lore remonte :** le hook de Claude Code analyse chaque message du joueur. `log`, `scene new` et `show` apportent aussi le lore nouvellement déclenché, et une entrée n'est pas répétée pendant quelques tours.
- **Régler une entrée :** `--secondary` avec `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (en tours ou en scènes), `--constant` (toujours dans le résumé) et `--no-recurse`.
- **Portées :** les entrées vont dans la campagne, sauf si `--scope` indique world, system ou global. Une analyse ne voit que cette campagne, son monde, son système et le global, jamais un autre monde. Une entrée plus restreinte avec le même identifiant masque une entrée plus large.
- **Lorebooks d'autres outils :** `didact lore import <file>` lit le World Info de SillyTavern (celui de KoboldAI aussi), le lorebook d'une carte de personnage et le `.lorebook` de NovelAI ; `didact lore export --to <file>` écrit du World Info. Les clés, la logique, la priorité, la probabilité, les groupes et la temporisation sont repris.

## Changer l'histoire

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` change le fait mais garde l'ancienne valeur. Il marque aussi comme périmés les résumés qui mentionnent Sweeney, et `audit` le liste.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` enregistre un arbitrage. Il apparaît ensuite dans `rules lookup` et quand cette règle s'exécute.
- `didact name npc` tire un nom nouveau, jamais un nom déjà utilisé dans le monde. Avant d'en inventer un, vérifiez-le avec `didact names check <name>`. `didact names forget <name>` en libère un.

## Entretien

- `didact history --clear` montre ce qu'effacer l'ancien historique supprimerait ; `--yes` le supprime définitivement, fiches supprimées comprises, et undo, `diff`, `rewind` et les anciens points de sauvegarde ne peuvent plus l'atteindre (`--before e120` garde cet événement et les suivants, `--rolls` supprime aussi l'historique des dés). Lancez `didact snapshot` d'abord.
- `didact save --remove 'before the dragon'` supprime un point de sauvegarde ; `didact undo` le rétablit.
- `didact transcript 3 --clear` supprime la transcription de la séance 3 (`--clear --all` : celles de toutes les séances). `didact undo` la rétablit, et le texte reste dans l'historique jusqu'à `history --clear`.
- `didact compendium remove <entry>` supprime une entrée que vous avez ajoutée ; les fiches créées à partir d'elle restent.
- `didact snapshot --keep 3` supprime toutes les sauvegardes sauf les trois plus récentes, et `didact snapshot --remove <name>` en supprime une. Aucune des deux ne peut être annulée.
- `didact session end` sauvegarde la bibliothèque de lui-même (`snapshot-<time>-auto.zip`), en gardant les cinq plus récentes ; `didact snapshot --list` les signale.
- `didact reset` montre ce que vider la bibliothèque emporterait ; `--yes` la remet comme fraîchement installée : chaque monde, campagne et fiche, l'historique et l'index de recherche disparaissent, et le prochain changement redevient #e1. Il sauvegarde d'abord la bibliothèque (`…-before-reset.zip`), et les sauvegardes restent, tout comme les packs installés sauf avec `--packs`. Pour essayer plutôt Didact sur une campagne toute prête, `didact sample` construit la campagne d'exemple dans une bibliothèque vide (`--home` lui donne son propre dossier), et `didact serve --demo` la sert à neuf.
- `didact snapshot --restore <name>` montre le contenu d'une sauvegarde à côté de la bibliothèque actuelle ; `--yes` sauvegarde la bibliothèque telle quelle (`…-before-restore.zip`), puis met la sauvegarde à sa place. Les numéros d'événement et de jet continuent. Undo ne peut pas annuler une restauration : restaurer cette sauvegarde de sécurité le peut.
