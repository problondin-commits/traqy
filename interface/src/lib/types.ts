// Formes de données renvoyées par l'API Traqy (voir modele.py côté moteur).

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

export type Fuite = {
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
};

export type Rapport = {
  titre: string;
  description: string;
  format: "PDF" | "CSV" | "XML";
};
