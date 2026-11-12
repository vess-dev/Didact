<!-- translated from 5a088227a31a -->
# L'application web

`didact serve` ouvre votre bibliothèque dans un navigateur : explorez et modifiez les fiches, voyez leurs liens dans un graphe, lisez le journal, lancez règles et tables, et utilisez chaque commande depuis un formulaire.

```
didact serve                     # http://127.0.0.1:8765/ until Ctrl-C
didact serve --open              # and open it in a browser tab
didact serve --gm                # start with the GM view on
didact serve --port 9000
didact serve --campaign withering --home ~/OtherLibrary
didact serve --demo              # a fresh sample campaign to try things on
```

Elle fonctionne hors ligne : les polices et les icônes sont fournies avec Didact.

**Mode démo.** `--demo` sert la campagne d'exemple (`didact sample` : une vallée fluviale, un PJ, des personnages avec les notes du MJ, des lieux et des chemins, une quête, une horloge, et une séance en cours avec un combat) depuis sa propre bibliothèque, à côté du dossier de cache de Didact. Tous les packs livrés avec Didact y sont installés. Elle est reconstruite à chaque lancement de `--demo`, alors essayez tout ce que vous voulez : votre bibliothèque n'est pas touchée.

## Options

| Option | Par défaut | Effet |
|---|---|---|
| `--port <n>` | 8765 | le port d'écoute |
| `--host <address>` | 127.0.0.1 | l'adresse d'écoute : cette machine uniquement |
| `--open` | désactivé | ouvrir l'application dans un onglet du navigateur |
| `--gm` | désactivé | démarrer avec la vue MJ activée |
| `--demo` | désactivé | servir une campagne d'exemple neuve au lieu de votre bibliothèque |

Les options globales `--home`, `--world` et `--campaign` s'appliquent à tout ce que fait l'application. Ouvrir un autre monde ou une autre campagne dans la page Bibliothèque fait basculer l'application dessus, comme `didact world use` et `didact campaign open`, et Fermer met de côté la campagne ouverte (`didact campaign close`).

## Contenu

- **Aperçu :** le résumé (monde, campagne, séance, scène, groupe, échéances), des actions rapides (lancer des dés, interroger l'oracle avec les chances qu'il connaît, noter un événement, commencer ou terminer une séance, créer une fiche) et les derniers changements.
- **État :** la situation en un coup d'œil : la séance et la scène, l'heure et les rappels à venir, les valeurs de chaque membre du groupe et ce qu'il porte, le combat (à qui le tour, états), les quêtes et compteurs en cours, et où se trouve le groupe avec ses issues. Les valeurs s'ajustent sur place : − et + sur une caractéristique, cocher un compteur, utiliser ou jeter un objet, en ajouter un, terminer une quête, faire avancer le temps (un nombre, et une unité que connaît le calendrier : heures, quarts, jours, …), programmer un rappel (une fois, ou périodiquement) et en annuler un.
- **Fiches :** toutes les fiches, groupées par type, avec un champ de filtre et des puces tout, monde ou campagne. La page d'une fiche montre sa feuille, sa description, ses détails, ses champs, son contenu, ses liens dans les deux sens, sa chronique et son historique, avec des formulaires pour modifier chacun d'eux, et pour l'archiver ou la supprimer. Un personnage dont le système a une montée de niveau a un bouton Level up (`char advance`) : un brouillon qui montre ce qui change, avant et après, jusqu'à ce qu'il soit validé.
- **Brouillons :** création de personnage et générateurs, une étape à la fois. Créer un personnage (pas à pas ou au hasard, en choisissant le type quand le système en propose plusieurs : un personnage joueur, un mercenaire, …) et Générer… se trouvent sur les pages Fiches ; les brouillons en attente y sont listés, ainsi que sur l'Aperçu. La page d'un brouillon montre ce qu'il contient jusqu'ici (ses entités et leurs champs, la carte tracée par un générateur, les jets, les questions du livre) et la question en attente. Chaque option est un bouton qui dit ce qu'elle signifie quand le pack le précise (ce que donne un historique, ce que fait un talent) ; en choisir plusieurs, c'est une case à cocher pour chacune ; les scores achetés avec un budget sont des nombres qui comptent les points au fur et à mesure ; un nom ou toute autre réponse libre peut être saisi ; et Laisser les dés décider tire celle-ci seule (`char roll c3 --one`). Retour annule la dernière étape, et sa question revient (`char back c3` : les jets qu'elle a faits sont marqués comme annulés, et Annuler fait revenir l'étape). Ensuite Tirer le reste, Modifier, Abandonner… (demande confirmation) et Valider, qui ouvre la fiche du nouveau personnage, ou liste ce que le générateur a créé. Le brouillon d'un générateur appartient au MJ : la vue joueur montre seulement qu'il existe.
- **Graphe :** les fiches comme nœuds et les liens comme arêtes. Faites glisser les nœuds, faites glisser le fond pour vous déplacer, zoomez avec la molette ; survolez une fiche pour éclairer ses voisines ; cliquez pour en ouvrir une. Le bouton Graphe sur la page d'une fiche montre uniquement son voisinage.
  - **Carte** (l'interrupteur au-dessus du graphe, ou Ouvrir la carte dans État) : les lieux que connaît le groupe, les chemins entre eux (étiquetés route, sentier, …), la région où se trouve chacun (en pointillés), et la position du groupe. Un chemin vers un lieu pas encore découvert mène à un « ? » ; la vue MJ montre tous les lieux.
- **Journal :** les séances, chacune s'ouvrant sur ses scènes, événements et jets. Chaque événement a Modifier et Supprimer (au survol), qui ouvrent les formulaires `beat edit` et `beat rm`.
- **Référence :** cherchez dans tout (les résultats s'affichent pendant la saisie), lancez les règles des packs activés depuis des formulaires, tirez sur leurs tables, et lisez leurs textes de règles, glossaire et guides.
- **Bibliothèque :** mondes et campagnes (ouvrir, fermer, créer, supprimer), packs (chacun avec sa description ; activer, désactiver, installer, désinstaller ; les packs fournis avec Didact ont un bouton Installer), l'historique (Annuler, Rétablir, Revenir à ce point, Effacer), les points de sauvegarde (revenir, supprimer) et les sauvegardes (sauvegarder maintenant, restaurer, supprimer, garder les plus récentes ; celles faites à la fin d'une séance sont marquées auto). Sans campagne ouverte, l'Aperçu liste les campagnes du monde pour en ouvrir une.
  - Supprimer un monde ou une campagne demande d'abord confirmation, et Annuler rétablit tout.
  - Revenir à ce point (à côté de chaque modification) annule tout ce qui suit cette modification (`didact undo --to e40`) : sa page liste d'abord ce qui disparaît. Chaque modification est annulée et chaque jet marqué comme annulé, rien n'est supprimé : Rétablir, ou revenir à une modification plus récente, les fait revenir. Afficher les modifications plus anciennes remonte plus loin dans l'historique.
  - Le pack core est toujours actif. Un seul système de jeu est utilisé à la fois : celui du monde ouvert, qui le garde pour de bon (choisi à sa création). Un autre système se joue dans un monde qui lui est propre : sa ligne ouvre un monde qui se joue avec lui, ou en crée un nouveau. Désinstaller un pack ne peut pas être annulé : réinstallez son .didactpack.
  - Effacer l'historique montre d'abord exactement ce qui disparaît et ce qui cesse de fonctionner, avec un bouton pour sauvegarder d'abord. Cela ne peut pas être annulé, pas plus que la suppression d'une sauvegarde.
  - Tout recommencer : **Réinitialiser…** vide la bibliothèque, comme si Didact venait d'être installé, et la numérotation repart à #e1. Sa page montre d'abord ce qui disparaît. La bibliothèque est sauvegardée d'abord, et les sauvegardes restent (les packs installés aussi, sauf si vous cochez la case).
  - Restaurer une sauvegarde montre d'abord son contenu à côté de la bibliothèque actuelle. La bibliothèque telle qu'elle était est sauvegardée d'abord : Annuler ne peut pas défaire une restauration, mais restaurer cette sauvegarde le peut.
- **Commandes :** chaque commande sous forme de formulaire, et un champ qui accepte une ligne de commande entière. Chaque champ accepte ce qu'accepte son argument : un nombre, un identifiant ou un événement (`e12`) selon son format, une durée de jeu sous forme d'un nombre et d'une unité, et une liste où choisir parmi les fiches, brouillons, packs, points de sauvegarde, oracles, tables et règles existants.
- **Paramètres :** les options de la campagne (les variantes et règles optionnelles de son système, que suivent ses règles, la création de personnage et les générateurs ; chacune dit ce qu'elle fait : pour une règle optionnelle, ce que change son activation, pour un choix, ce que signifie chacune de ses valeurs, et une valeur par défaut fixée par une autre option dit laquelle), la langue de l'application, le dictionnaire des synonymes (la langue qu'utilisent les recherches pour les synonymes : en télécharger une, avec une barre de progression, passer de l'une à l'autre parmi celles téléchargées, en retirer une) et la documentation du code.
  - L'application, ses guides et ce qu'y affichent les commandes existent en 24 langues. Sans choix, l'application suit la langue du navigateur. La ligne de commande et les LLM qui l'utilisent restent en anglais : la langue choisie ici n'est que celle de l'application.
  - Le bouton code de la barre d'en-tête ouvre la documentation de l'API du code. Elle est générée à partir du code la première fois, puis à chaque changement du code (`didact docs build`).

Chaque changement exécute une vraie commande `didact`, il est donc vérifié, journalisé et annulable exactement comme en ligne de commande. L'application montre à chaque fois la commande exécutée (`didact set sweeney hp-=2`), avec un bouton Annuler quand il y a quelque chose à défaire.

Un champ n'accepte que ce qu'accepte sa commande. Un identifiant (celui d'un monde ou d'une campagne) et un type de fiche acceptent des minuscules, des chiffres et des tirets : les espaces deviennent des tirets et les majuscules passent en minuscules pendant la saisie. Le nom d'un champ de fiche n'accepte pas d'espaces (ils deviennent des tirets bas), celui d'un détail est un seul mot, et les champs numériques n'acceptent que des nombres. Ce qu'accepte un champ est écrit en dessous, et la commande vérifie de toute façon une seconde fois.

Un enregistrement n'écrase jamais un changement que vous n'avez pas vu. Si la fiche a changé après l'affichage de la page (un LLM l'a modifiée en ligne de commande, par exemple, ou un autre onglet l'a fait), l'enregistrement est refusé et indique ce qu'elle contient maintenant. Une description que vous étiez en train de modifier reste dans l'éditeur, à côté de la nouvelle version, pour fusionner et enregistrer à nouveau. − et + passent toujours : ils s'additionnent.

## Vue joueur et vue MJ

L'application montre ce que savent les joueurs, comme `didact show` : les fiches secrètes, les sections `## Secrets`, les champs secrets et les détails réservés au MJ restent cachés. Le bouton **MJ** de la barre d'en-tête active la vue MJ, et un bandeau l'indique (« Vue MJ : spoilers affichés »). Le navigateur retient ce choix.

Dans la vue joueur :
- une description contenant des lignes réservées au MJ ne peut pas être modifiée (l'enregistrer les ferait perdre) : activez d'abord la vue MJ ;
- un détail MJ ou un champ secret que la page ne montre pas ne peut pas être écrasé, mais une nouvelle note pour le MJ peut être ajoutée ;
- l'historique nomme la commande et les fiches que connaissent les joueurs (`set · Freya`), jamais les valeurs, et Annuler dit quel changement il a défait, pas ce qu'il était.

## Sécurité

L'application peut modifier votre bibliothèque, elle n'écoute donc que cette machine par défaut.

- `--host` avec une autre adresse permet à d'autres machines de l'atteindre, et Didact vous en avertit. Ne l'utilisez que sur un réseau de confiance.
- Elle ne répond qu'aux requêtes qui lui sont adressées (sa propre adresse, `localhost`, `127.0.0.1` ou `[::1]`, avec son port). Cela empêche d'autres sites web de l'atteindre par des astuces DNS.
- Chaque changement nécessite un formulaire de l'application elle-même : un jeton secret dans chaque formulaire doit correspondre à un cookie que les autres sites ne peuvent ni lire ni envoyer.
- Il n'y a pas de connexion. Quiconque peut utiliser le navigateur de cet ordinateur peut utiliser l'application.
