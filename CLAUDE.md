# Traqy — note de travail

Lis cette note en entier au début de chaque conversation.

## 1. Comment travailler avec Tom
- Tom est le fondateur de Traqy. Il n'est pas technique : il code pour la première fois.
- Réponses courtes. Phrases simples. 5 lignes maximum quand c'est possible.
- Aucun mot technique sans l'expliquer. Ne suppose jamais qu'il sait où se trouve un bouton : dis exactement où cliquer.
- Consigne de Tom (24/10/2026) : ne jamais citer un dossier, un fichier, un onglet, un bouton, un menu ou un programme sans dire ce que c'est ET où le trouver (chemin complet ou endroit exact de l'écran).
- Pas de tableaux. Étapes numérotées.
- N'anticipe pas : réponds à ce qu'il demande, puis attends.
- Rien n'est écrit ni modifié sans son « go » explicite.
- C'est toi qui fais le travail : tu crées et modifies les fichiers, tu lances les commandes. Tom clique sur « Autoriser ».
- Tom s'occupe seulement des comptes et des mots de passe. Ne lui demande jamais de coller un mot de passe, une clé ou une adresse de connexion dans la conversation : dis-lui dans quel écran ou quel fichier les saisir.
- À la fin de chaque tâche, mets à jour la partie 9 « Où on en est ».

## 2. Traqy en bref
- SaaS B2B pour la musique. Il retrouve l'argent non perçu par les ayants droit, mesure la valeur d'un catalogue et prévoit ses revenus.
- Traqy a intégré l'ancien projet Leakr (ancien nom : NEIA). Il n'y a plus qu'un seul outil et un seul nom : Traqy.
- Cible : d'abord les éditeurs et les labels indépendants. Les grands distributeurs viendront plus tard.

## 3. Architecture cible
1. Un socle unique : le client dépose une seule fois son catalogue (ISRC, ISWC), ses ayants droit et leurs parts, ses contrats et ses relevés.
2. Un contrôle d'entrée : Traqy vérifie les fichiers et liste ce qui manque.
3. Quatre modules sur ce socle :
   - Valeur : chiffre d'affaires réel par titre et par album depuis la sortie.
   - Fuites : droits non perçus dans les relevés (fusion des anomalies Traqy et des fuites Leakr).
   - Projection : revenus à venir sur 5 ans, 10 ans ou plus, à terme pays par pays.
   - Surveillance : usages non autorisés sur les réseaux, uniquement par des voies légales (pas d'aspiration de TikTok).
4. Une sortie unique : alertes classées par argent en jeu, rapport d'audit avec dossier de preuves, exports officiels.
5. Une interface en six écrans : Dépôt, Contrôle des manques, Catalogue, Alertes, Projection, Rapports (écran Projection ajouté à la demande de Tom le 24/10/2026). Le client dépose ses fichiers puis valide des alertes.

## 4. Exports officiels
- En entrée : DSR, CRD, RDR-R.
- En sortie : CWR (SACEM), RDR-N (droits voisins), CDM (réclamations aux plateformes).
- Un seul modèle de données interne (œuvre, enregistrement, ayant droit, part, revenu, période) et un traducteur par format.
- À garder en tête :
  1. Le CWR exige un code expéditeur éditeur, que Traqy n'a pas encore.
  2. Chaque fichier officiel doit passer les validateurs officiels.
  3. Le fichier XML actuel n'est ni du DDEX ni du CWR : il sera remplacé.

## 5. Décisions prises
- Charte : celle de Traqy, noire et sobre, avec le logo Traqy.
- Format des rapports : PDF, CSV et XML. Documents en format portrait.
- Prix et modèle économique : rien n'est défini pour l'instant.
- Aucun barème : les montants viennent uniquement des données du client (ses taux ou ses relevés).
- Mode estimation : gardé, sans taux par défaut. Le client saisit son taux. Le résultat est toujours affiché comme une estimation.
- Ton des documents : commercial. Le mot « IA » n'apparaît pas dans les documents remis aux clients.
- Vocabulaire : dire « non perçus », jamais « perdus » ni « bloqués ».
- Le produit s'appelle uniquement « Traqy ». « Gatekeeper » est un nom de code interne, jamais visible.
- Pas de mandat : Traqy ne réclame jamais et ne touche jamais l'argent à la place du client. Le client réclame lui-même avec son Pack d'Audit. C'est ce qui distingue Traqy de Claimy. Les partenaires techniques (hébergement, reconnaissance audio) sont de simples fournisseurs, pas des mandats.
- Nous sommes Traqy : ne plus parler de « Leakr » à Tom, ni dans le code, ni dans ce qui est visible. Dire « ancien Colab » ou « format Traqy ».
- Accès (décision de Tom, 24/10/2026) : le menu « Client » est réservé à Tom (administrateur) ; chaque testeur a son propre espace avec un compte et ne voit que ses fichiers ; un visiteur sans compte ne voit que la démo. Aucun lien n'est envoyé aux testeurs avant l'étape 7. Un testeur ne doit jamais voir les vrais clients (Luidji, S.Pri Noir…).
- Contrats, taux de partage, frais et avances : ce sont les données du client. Traqy les importe comme le reste, sans les cacher ni les marquer « privé » (décision de Tom, 24/10/2026).

## 6. Outils techniques
- Moteur en Python : FastAPI + Pydantic (main.py).
- Calculs : pandas, numpy. Les calculs de l'ancien Colab Leakr seront déplacés dans FastAPI.
- PDF : reportlab.
- Base de données : PostgreSQL (Neon ou Supabase, en Europe).
- Audio : Librosa.
- Données publiques : MusicBrainz, Deezer. Autres sources à vérifier avant usage.
- Interface : Next.js + shadcn/ui, en ligne sur Vercel. Node.js sert uniquement à l'interface.
- Abandonnés : Google Colab, PowerPoint (Node.js/pptxgenjs), Streamlit pour la présentation, Neo4j pour le MVP.
- Plus tard : Redis pour les gros catalogues.

## 7. Plan en 7 étapes
1. Préparer le terrain : compte GitHub, installer Git et Node.js, mettre ce dossier sur GitHub.
2. Finir le moteur : calculs du Colab dans l'API, import du catalogue et des relevés, contrôle des manques, couche Fuites, tests sur de vrais relevés.
3. Base de données PostgreSQL en Europe, avec le modèle unique.
4. Mettre l'API en ligne chez Render (Francfort), protégée par une clé d'API.
5. Construire l'interface : les cinq écrans, d'abord avec des données d'exemple, puis branchés sur l'API.
6. Mettre l'interface en ligne sur Vercel, avec un mode démo sans données réelles de client.
7. Ouvrir aux testeurs : comptes, connexion, invitations.
Ensuite : exports officiels, Surveillance des réseaux, Redis.

À savoir : les offres gratuites mettent l'API en veille. Le premier chargement peut prendre près d'une minute. Le rappeler à Tom avant chaque démo.

## 8. Points encore ouverts
- Les 9 contradictions de chiffres venues de Leakr : à trancher par Tom. N'utilise aucun de ces chiffres comme sûr.
- Une anomalie SACEM citée en exemple est à revérifier avant toute présentation.
- 13 fichiers Leakr restent à décider.
- Routine du lundi et kanban Notion : à reprendre pour Traqy.

## 9. Où on en est
- Le dossier contient main.py (API) et app.py (ancienne interface Streamlit).
- La migration de Leakr vers Traqy est faite.
- Étape 1 terminée (24/10/2026) : Git 2.55 et Node.js 24 (LTS) installés. Compte GitHub : problondin-commits. Dossier envoyé dans le dépôt privé github.com/problondin-commits/traqy (branche main).
- Étape 2 en cours. Fait (24/10/2026) : barème par défaut retiré du moteur. Les montants viennent seulement des taux saisis par le client ; sans taux, l'usage est gardé comme preuve, sans montant. Vocabulaire corrigé (« non perçus », plus de « perdues » ni « Leak »). app.py adapté.
- Fait (24/10/2026) : calculs du Colab Leakr déplacés dans calculs.py (Valeur, Projection, test à rebours, mode estimation). Résultats vérifiés identiques au Colab sur des relevés fictifs. Nouvelles entrées de l'API : /api/v1/releves/produits, /api/v1/valeur, /api/v1/estimation. Le mode estimation exige le taux du client (plus de 3,5 € / 1 000 ni de +4 % par défaut). Contrats, taux de partage et frais renvoyés dans « contrats_et_frais ».
- Colab de référence : Téléchargements > Traqy_migration_Leakr > reference_calcul > NEIA_audit_Colab.ipynb.
- Décision de Tom (24/10/2026) : les 4 coefficients sans source (0,884 ; 1,064 ; 1,12 ; 0,87) sont retirés. L'estimation d'avant les relevés donne un seul montant (le montant central du Colab), marqué « estimation », source Kworb citée, non compté dans le total. Fait et vérifié.
- Décision de Tom (24/10/2026) : Kworb accepté pour l'instant, à condition d'être cité comme source. RAPPEL À FAIRE À TOM : retirer Kworb avant toute remise à un client.
- Fait (24/10/2026) : import du catalogue et des relevés. modele.py = modèle interne unique (œuvre, enregistrement, part, revenu, période). importation.py = un traducteur par format : catalogue Traqy (ayants droit et parts), relevé distributeur détaillé (format de l'ancien Colab, frais et avances compris), relevés au format Traqy (écoutes, droits d'auteur, synchro, réseaux sociaux, retenues). Accepte CSV, Excel et ZIP. Entrées API : /api/v1/import et /api/v1/modele-catalogue. requirements.txt ajouté.
- Test sur les vrais fichiers Luidji / S.Pri Noir (en local, jamais sur GitHub) : 358 parts, 914 revenus, total SACEM 428 255,19 € identique au LISEZMOI.
- Limites connues : le classeur Excel Luidji (onglets faits main) n'est pas reconnu. Tom n'a aucun relevé d'origine (Believe, Universal, Concord, SACEM).
- Données de clients : Téléchargements > Traqy_migration_Leakr > donnees_clients. Le .gitignore bloque les fichiers Excel, ZIP et les dossiers donnees_clients/ et releves/.
- Fait (24/10/2026) : contrôle des manques (controle.py), lancé à chaque import (champ « manques »). Vérifie : catalogue ou relevés absents, œuvres sans ISWC, ayants droit sans IPI, parts ≠ 100 % ou absentes, œuvres payées absentes du catalogue, œuvres sans revenu, périodes manquantes, montants cumulés, périodes illisibles, ventes sans détail, revenus impossibles à rattacher. Classé par gravité puis par argent en jeu. Sur Luidji : 6 manques, dont 21 œuvres sans parts et 36 lignes impossibles à rattacher.
- Fait (24/10/2026) : lecture souple des classeurs. Noms de colonnes simplifiés et rapprochés de leurs synonymes (« Part DEP », « Nom (déclaré) », « N° IPI »…), ligne d'en-tête cherchée dans les 10 premières lignes, parts en fraction converties en %, nouveau format « Catalogue Traqy · œuvres ». Un catalogue déposé deux fois (CSV et Excel) ne compte qu'une fois : rapprochement par IPI ; rien n'est fusionné à l'intérieur d'un même fichier. Classeur Luidji : onglets 1 et 2 reconnus ; classeur seul = CSV seuls = 56 œuvres, 358 parts.
- À faire à l'étape 5 (interface) : écran de correspondance des colonnes, pour les colonnes que la lecture souple ne reconnaît pas.
- Fait (24/10/2026) : couche Fuites (fuites.py), lancée à chaque import (champ « fuites »), classée par argent en jeu. 5 règles, chiffrées uniquement avec les données du client : 1. solde jamais payé (montant lu, pas une estimation) ; 2. revenus qui s'arrêtent (moyenne des derniers paiements × périodes manquées, estimation) ; 3. parts incomplètes (revenus de l'œuvre × part manquante, estimation) ; 4. écoutes sans droits d'auteur (non chiffré) ; 5. œuvre sans aucun revenu (non chiffré, retirée du contrôle des manques). Les soldes de comptes sont maintenant importés (format « Relevé Traqy · soldes »).
- Sur Luidji : 3 fuites, 55 378 € chiffrés. Solde Concord 064639 : 41 404,36 € (30 626,24 € fin 2025 S2 + 10 778,12 € de royalties S1 2026), conforme aux notes. Part auteur Luidji chez Concord : 13 970 € estimés, MAIS les relevés Concord du compte 064638 après le S1 2023 sont absents : à vérifier avant d'en parler comme d'une fuite.
- Pour plus tard : comparer écoutes publiques (Kworb) et écoutes déclarées, une fois Kworb validé ou retiré.
- Étape 2 : il ne reste que les tests sur de vrais relevés d'origine, à faire dès qu'un client en enverra.
- Étape 3 (24/10/2026) : base PostgreSQL chez Supabase, projet « traqy », région Central EU (Frankfurt), organisation « Traqy », offre gratuite, compte créé avec GitHub. Connexion par le « Session pooler ». L'adresse de connexion est dans le fichier secret .env (Bureau > API_TRAQY > .env, bloqué par .gitignore) ; le mot de passe de la base est gardé par Tom.
- base.py : tables dans le schéma « traqy » (pas « public », donc non exposées par l'interface publique de Supabase) : clients, imports, oeuvres, enregistrements, parts, revenus, soldes, bilans_fichiers, manques, fuites. Colonnes tirées de modele.py. /api/v1/import enregistre l'import quand on donne un nom de client ; /api/v1/imports et /api/v1/imports/{n} pour relire. Testé avec des données inventées (enregistré, relu à l'identique, effacé).
- Tom a l'accord de Luidji et de S.Pri Noir (24/10/2026) : leurs données sont dans la base, chacun comme client séparé. Import n° 2 « Luidji » (56 œuvres, 358 parts, 884 revenus, 12 soldes, 6 manques, 3 fuites ; total SACEM 428 255,19 €). Import n° 3 « S.Pri Noir » (30 revenus mensuels de l'album, 187 106 € ; pas de catalogue). Pour tout autre client : demander à Tom avant d'envoyer des données réelles.
- S.Pri Noir : les relevés de l'album « État d'esprit » ne sont pas sur l'ordinateur (sans doute restés dans l'ancien projet claude.ai). Décision de Tom (24/10/2026) : on reste sur « La Cour des Miracles ». Dossier prévu pour de futurs relevés : Bureau > API_TRAQY > donnees_clients (bloqué par .gitignore).
- À conseiller à Tom : accepter le contrat de traitement des données (DPA) de Supabase, exigé par le RGPD dès qu'on stocke des données personnelles de clients.
- Visite quotidienne de la base : .github/workflows/reveil-base.yml (GitHub Actions, chaque jour à 6 h 17). Elle a besoin du secret DATABASE_URL dans GitHub (dépôt traqy > Settings > Secrets and variables > Actions), à saisir par Tom.
- Étape 3 terminée (24/10/2026) : secret DATABASE_URL ajouté dans GitHub par Tom ; visite quotidienne testée avec succès (coche verte).
- Étape 4 terminée (24/10/2026) : API en ligne à https://traqy-api.onrender.com (Render, compte créé avec GitHub, offre gratuite, Francfort, service « traqy-api » créé par le Blueprint « traqy » à partir de render.yaml). Chaque envoi sur GitHub (branche main) remet le service à jour automatiquement.
- Clé d'API : en-tête X-API-Key, obligatoire partout sauf la page d'accueil « / » (qui dit seulement si le service et la base répondent). Clé en ligne : créée par Render, visible dans Render > traqy-api > Environment > TRAQY_API_KEY. Clé de l'ordinateur : dans .env (différente). Vérifié depuis internet : accueil OK, base connectée, accès refusé sans clé.
- Rappel démo : l'offre gratuite de Render endort l'API après 15 minutes sans visite ; le premier chargement peut prendre près d'une minute.
- Étape 5 commencée (24/10/2026) : interface dans le dossier « interface » (Next.js 16, shadcn/ui style base-nova, icônes lucide). Charte : fond nuit #111317, texte #F5F5F3, vert menthe du logo #31F2A4 ; logos copiés depuis Téléchargements > Traqy-logo. Cinq écrans : /depot, /manques, /catalogue, /alertes (valider / écarter chaque fuite), /rapports (dossier de preuves CSV téléchargeable ; PDF et XML « bientôt disponibles »). Données d'exemple 100 % inventées (« Label Démo ») dans interface/src/lib/demo.ts, de même forme que les réponses de l'API (types dans interface/src/lib/types.ts). Mode démo signalé dans la barre de gauche.
- Pour voir l'interface sur l'ordinateur : .claude/launch.json (serveur « interface », http://localhost:3000).
- Fait (24/10/2026) : interface branchée sur le moteur. La clé d'API reste côté serveur de l'interface (interface/src/lib/api.ts, variables TRAQY_API_URL et TRAQY_API_KEY ; sur l'ordinateur : interface/.env.local, bloqué par .gitignore, qui pointe vers le moteur lancé en local sur le port 8000). Menu « Client » dans la barre de gauche (dernier import de chaque client + « Label Démo (démo) »), choix gardé dans un cookie. Dépôt réel (route /api/depot → /api/v1/import), décisions sur les alertes enregistrées dans la base (colonne « decision » de traqy.fuites ; nouvelles colonnes ajoutées automatiquement par base.py). Nouvelles entrées API : /api/v1/imports/{n}/vue et PUT /api/v1/fuites/{n}/decision. Écran « Chargement… » pendant le réveil du moteur. Vérifié dans le navigateur avec Luidji, S.Pri Noir, dépôt de test (effacé) et validation d'alerte (annulée ensuite). Construction finale (npm run build) : OK.
- Pour voir l'interface sur l'ordinateur : lancer les serveurs « moteur » et « interface » de .claude/launch.json, puis http://localhost:3000.
- Fait (24/10/2026) : écran Projection (/projection). Moteur : projection.py construit la courbe mensuelle d'un client à partir de ses relevés importés (chaque revenu réparti sur sa période ; paiement SACEM daté d'un jour = intervalle depuis le paiement précédent ; exclus : cumuls, synchro, frais, avances, retenues), puis applique la même méthode que le Colab (calculs.projeter_courbe, extraite de calculer_valeur ; résultats Colab toujours identiques). Entrées API : GET /api/v1/imports/{n}/projection et POST /api/v1/projection (courbe libre, pour la démo). Écran : horizon 3/5/10/15 ans, baisse min/max réglables, tuiles (relevé, à venir, total, fourchette), graphique mensuel (relevé en barres pleines, prévision hachurée, vert #18A974 validé pour fond sombre), méthode, test sur le passé, tableau par période. Alerte affichée quand la baisse mesurée sort de la fourchette (cas de Luidji : 35,4 % par an). Résultats : S.Pri Noir 52 228 € à venir sur 5 ans ; Luidji 208 469 € ; toujours des estimations.
- Fait (24/10/2026), demande de Tom « 1 artiste = 1 base » : base de baisse propre à chaque artiste (projection.py, base_artiste). Baisse annuelle mesurée titre par titre sur ses seuls relevés (titres avec au moins 24 mois de relevés et payés dans les 6 derniers mois), moyenne pondérée par les revenus des 12 derniers mois, fourchette = 20e à 80e centile des titres. Jamais mélangée avec un autre artiste. Utilisée comme fourchette de la projection dès 5 titres mesurables (sinon réglage à la main, avec l'explication à l'écran). Choix « Base de l'artiste / À la main » sur l'écran Projection. Luidji : 53 titres, baisse moyenne 33,8 %, fourchette 5,5 % à 54,1 %. S.Pri Noir : 1 seul titre (album entier) → réglage à la main. Démo : courbes inventées par titre (titresDemo).
- Règle d'accès validée par Tom (24/10/2026) : voir partie 5 « Accès ». À construire à l'étape 7 ; d'ici là, la version en ligne (étape 6) ne montre que la démo.
- Lancer l'interface pour Tom : deux onglets de terminal, « python -m uvicorn main:app --port 8000 » (moteur) et « npm --prefix interface run dev » (interface), puis http://localhost:3000 dans son navigateur.
- Prochaine tâche : étape 6 (interface en ligne sur Vercel, avec TRAQY_API_URL = https://traqy-api.onrender.com et la clé de Render, en mode démo uniquement tant que l'étape 7 n'est pas faite).
