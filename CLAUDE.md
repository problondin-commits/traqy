# Traqy — note de travail

Lis cette note en entier au début de chaque conversation.

## 1. Comment travailler avec Tom
- Tom est le fondateur de Traqy. Il n'est pas technique : il code pour la première fois.
- Réponses courtes. Phrases simples. 5 lignes maximum quand c'est possible.
- Aucun mot technique sans l'expliquer. Ne suppose jamais qu'il sait où se trouve un bouton : dis exactement où cliquer.
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
5. Une interface en cinq écrans : Dépôt, Contrôle des manques, Catalogue, Alertes, Rapports. Le client dépose ses fichiers puis valide des alertes.

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
- Prochaine tâche : déplacer les calculs du Colab Leakr dans le moteur (Tom doit fournir le fichier du Colab).
