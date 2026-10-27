// Formes de données renvoyées par l'API Traqy (voir modele.py et vues.py côté moteur).

export type Gravite = "bloquant" | "important" | "à compléter";

export type BilanFichier = {
  fichier: string;
  format: string | null;
  statut: "importé" | "ignoré" | "refusé";
  lignes_importees: number;
  lignes_ignorees: number;
  messages: string[];
};

export type Manque = {
  gravite: Gravite;
  sujet: string;
  constat: string;
  action: string;
  nombre: number;
  montant: number | null;
  exemples: string[];
};

export type Decision = "validée" | "écartée";

export type Fuite = {
  id: number | null;
  regle: string;
  oeuvre: string | null;
  iswc: string | null;
  isrc: string | null;
  payeur: string | null;
  montant: number | null; // null : non chiffré
  estimation: boolean; // false : montant lu tel quel dans un relevé
  methode: string;
  action: string;
  preuves: string[];
  decision: Decision | null;
};

// Revenus d'une œuvre regroupés par année, plateforme et type de droit (pour les filtres du Catalogue)
export type DetailRevenu = {
  annee: string; // « 2025 », ou « Non datée »
  plateforme: string; // « Non précisée » quand le relevé ne la donne pas
  type: string; // « Droits d'auteur » ou « Enregistrement (master) »
  montant: number;
};

// Ligne du catalogue telle qu'affichée (œuvre, ses parts et ses revenus relevés)
export type LigneCatalogue = {
  titre: string;
  artiste: string;
  iswc: string | null;
  isrc: string | null;
  ayants_droit: number;
  parts_dep: number | null; // total des parts DEP en %
  revenus: number;
  projet?: string | null; // album, quand seul un relevé distributeur est déposé
  detail?: DetailRevenu[]; // absent sur un moteur plus ancien
};

// Avance versée sur un contrat (montant déclaré par le client) et son recoupement lu dans les relevés
export type Avance = {
  contrat: string;
  projet: string | null;
  montant: number;
  devise: string | null;
  recoupe: number;
  reste: number;
  taux: number | null; // part recoupée, de 0 à 1
  recettes: number | null; // part du client avant recoupement (null : avance suivie sur plusieurs comptes)
  frais: number | null;
  net_verse: number | null; // somme des relevés du contrat (négatif : frais encore à couvrir)
  periodes: { periode: string; recoupe: number }[];
  estimation: { periode: string; semestres: number; rythme: number; methode: string } | null;
  source: string;
  // Avec une fiche contrat : avance suivie sur tous les albums du contrat
  cle?: string;
  nom?: string;
  album?: string | null;
  par_album?: { album: string; contrat: string; recoupe: number; avant_releves?: boolean }[];
  avant_releves?: { montant: number; source: string | null } | null;
};

// Lecture d'un contrat déclaré par le client (contrats.py) : fiche, résultat des albums et écart
export type ContratLecture = {
  nom: string;
  parties: string | null;
  date_signature: string | null;
  albums: { contrat: string; titre: string; rang?: string }[];
  clauses: { article: string; titre: string; texte: string }[];
  avertissement: string | null;
  sources: string[];
  avances_non_remboursables: boolean;
  seuil_accord_depenses: number | null;
  resultats: {
    album: string; contrat: string; recettes: number; frais: number; resultat: number;
    anterieur: number | null; anterieur_jusqu_au: string | null; anterieur_source: string | null;
  }[];
  resultat_total: number;
  avances_recuperees: number;
  avances_declarees: number;
  ecart: number | null;
};

// Recettes par pays (code à deux lettres), lues dans les relevés
// « recent » : recettes des 12 derniers mois relevés, pour répartir la projection entre les pays
export type DetailPays = { nom: string; montant: number; quantite: number | null };
export type RevenuPays = {
  pays: string;
  montant: number;
  quantite: number;
  recent?: number;
  rang?: number;
  pour_1000?: number | null; // part du client pour 1 000 écoutes en streaming dans ce pays (lue dans ses relevés)
  titres?: DetailPays[];
  plateformes?: DetailPays[];
};

// Tout ce que les cinq écrans affichent pour un import (réponse de /api/v1/imports/{n}/vue)
export type Vue = {
  import_id: number | null;
  client: string | null;
  cree_le: string | null;
  fichiers: BilanFichier[];
  manques: Manque[];
  fuites: Fuite[];
  catalogue: LigneCatalogue[];
  avances?: Avance[];
  contrat?: ContratLecture | null;
  pays?: RevenuPays[];
};

export type ImportResume = { id: number; client: string; cree_le: string };

export type MoisMontant = { mois: string; valeur: number }; // mois au format AAAA-MM

// Réponse de /api/v1/imports/{n}/projection et /api/v1/projection (projection.py)
export type Projection = {
  nature: "estimation";
  methode: string;
  debut: string;
  dernier: string;
  aujourdhui: string;
  fin: string;
  historique: MoisMontant[];
  prevision: MoisMontant[];
  realise: number;
  avenir: number;
  total: number;
  total_bas: number;
  total_haut: number;
  baisse_mesuree: number;
  baisse_min: number;
  baisse_max: number;
  hors_fourchette: boolean;
  fourchette_source: "catalogue" | "manuelle";
  base_artiste: BaseArtiste;
  niveau_mensuel: number;
  periodes: { label: string; valeur: number }[];
  fiabilite: {
    ok: boolean;
    mois: number;
    h6?: { tests: number; methodes: Record<string, { ecart_moyen: number; biais: number; pire: number }> };
    h3?: { tests: number; methodes: Record<string, { ecart_moyen: number; biais: number; pire: number }> };
  };
};

// Base de l'artiste : baisse de chacun de ses titres, mesurée sur ses seuls relevés
export type BaseArtiste = {
  disponible: boolean;
  raison: string | null;
  titres_mesures: number;
  titres_minimum: number;
  baisse_moyenne?: number;
  baisse_basse?: number;
  baisse_haute?: number;
  titres: { titre: string; baisse: number; revenus_12_mois: number }[];
};

export type Fourchette = "catalogue" | "manuelle";

export type ReglagesProjection = { fin: string; baisse_min: number; baisse_max: number; fourchette: Fourchette };

export type Rapport = {
  titre: string;
  description: string;
  format: "PDF" | "CSV" | "XML";
};
