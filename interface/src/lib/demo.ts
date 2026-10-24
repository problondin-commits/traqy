// Mode démo : données entièrement inventées (« Label Démo »), aucune donnée réelle de client.
// Elles ont la même forme que les réponses de l'API, pour pouvoir brancher l'interface ensuite.
import type { BilanFichier, Fuite, LigneCatalogue, Manque, Rapport } from "./types";

export const CLIENT_DEMO = "Label Démo";
export const DATE_DEPOT_DEMO = "24 octobre 2026";

export const fichiersDemo: BilanFichier[] = [
  { fichier: "catalogue_label_demo.xlsx › Ayants droit", format: "Catalogue Traqy · ayants droit et parts", statut: "importé", lignes_importees: 42, lignes_ignorees: 0, messages: [] },
  { fichier: "catalogue_label_demo.xlsx › Œuvres", format: "Catalogue Traqy · œuvres", statut: "importé", lignes_importees: 12, lignes_ignorees: 0, messages: [] },
  { fichier: "sacem_repartitions_2024_2026.csv", format: "Relevé Traqy · droits d'auteur", statut: "importé", lignes_importees: 118, lignes_ignorees: 2, messages: ["Ligne 57 : aucun montant, non importée comme revenu.", "Ligne 88 : aucun montant, non importée comme revenu."] },
  { fichier: "distributeur_2025.csv", format: "Relevé distributeur détaillé", statut: "importé", lignes_importees: 1460, lignes_ignorees: 0, messages: [] },
  { fichier: "soldes_editions_horizon.csv", format: "Relevé Traqy · soldes", statut: "importé", lignes_importees: 6, lignes_ignorees: 0, messages: [] },
  { fichier: "notes_reunion.docx", format: null, statut: "ignoré", lignes_importees: 0, lignes_ignorees: 0, messages: ["Type de fichier non pris en charge (CSV, Excel ou ZIP attendu)."] },
];

export const manquesDemo: Manque[] = [
  {
    gravite: "important", sujet: "Revenus impossibles à rattacher", nombre: 12, montant: 3480.4,
    constat: "12 lignes n'ont ni ISRC, ni ISWC, ni titre exact : impossible de les rattacher à une œuvre (3 480,40 €).",
    action: "Demander au client l'ISRC, l'ISWC ou le titre exact de ces revenus.",
    exemples: ["Compilation été 2025 (titre non détaillé)", "Synchro « Spot TV » sans titre", "Remix promo (relevé distributeur)"],
  },
  {
    gravite: "important", sujet: "Périodes manquantes dans les relevés", nombre: 2, montant: null,
    constat: "2 périodes manquent dans la suite des relevés.",
    action: "Demander au client les relevés de ces périodes.",
    exemples: ["SACEM : répartition d'avril 2025", "Distributeur : 08/2025"],
  },
  {
    gravite: "important", sujet: "Parts absentes", nombre: 3, montant: null,
    constat: "3 œuvres ont des ayants droit connus mais aucune part en %.",
    action: "Demander au client les parts (DEP, DR, PHONO) de ces œuvres.",
    exemples: ["Lumière Basse", "Rive Gauche", "Dernier Métro"],
  },
  {
    gravite: "à compléter", sujet: "Ayants droit sans IPI", nombre: 4, montant: null,
    constat: "4 ayants droit n'ont pas de numéro IPI.",
    action: "Demander les numéros IPI au client (ils figurent sur les relevés SACEM).",
    exemples: ["Jade MARCEAU", "Studio Pixel Son", "Yanis OKORO", "Éditions Vague"],
  },
  {
    gravite: "à compléter", sujet: "Œuvres sans ISWC", nombre: 2, montant: null,
    constat: "2 œuvres n'ont pas d'ISWC, dont 1 sans code SACEM non plus.",
    action: "Demander les ISWC au client ou les retrouver dans son espace SACEM.",
    exemples: ["Archipel", "Interlude 2"],
  },
];

export const fuitesDemo: Fuite[] = [
  {
    regle: "Solde jamais payé", oeuvre: null, iswc: null, isrc: null, payeur: "Éditions Horizon",
    montant: 18420.5, estimation: false,
    methode: "Solde de clôture du compte 2207 – Label Démo au 2026 S1 (18 420,50 €), lu dans le relevé.",
    action: "Réclamer le versement du solde à Éditions Horizon.",
    preuves: ["soldes_editions_horizon.csv, ligne 5 : 2025 S2, ouverture 9 870,00 €, royalties 4 210,30 €, clôture 14 080,30 €", "soldes_editions_horizon.csv, ligne 6 : 2026 S1, ouverture 14 080,30 €, royalties 4 340,20 €, clôture 18 420,50 €"],
  },
  {
    regle: "Revenus qui s'arrêtent", oeuvre: "Minuit Pile", iswc: "T-901.234.567-1", isrc: "FRZ012500011", payeur: "SACEM",
    montant: 2340, estimation: true,
    methode: "Moyenne des 4 derniers paiements (780,00 €) × 3 périodes sans paiement (répartitions de janvier, avril et juillet 2026).",
    action: "Demander à la SACEM pourquoi cette œuvre n'est plus payée depuis octobre 2025.",
    preuves: ["sacem_repartitions_2024_2026.csv, ligne 71 : répartition d'octobre 2025, 812,00 €", "sacem_repartitions_2024_2026.csv, ligne 64 : répartition de juillet 2025, 754,00 €"],
  },
  {
    regle: "Parts incomplètes", oeuvre: "Ciel Ouvert", iswc: "T-901.234.580-3", isrc: "FRZ012500014", payeur: "SACEM",
    montant: 1125, estimation: true,
    methode: "Parts DEP déclarées : 87,5 %. Part manquante : 12,5 %. Revenus relevés de l'œuvre (9 000,00 €) × part manquante.",
    action: "Compléter la déclaration de l'œuvre auprès de la SACEM, puis réclamer la part non répartie.",
    preuves: ["Nova LUNE (Auteur) : DEP 50 %", "Kenzo RIVE (Compositeur) : DEP 25 %", "Éditions Vague (Éditeur) : DEP 12,5 %"],
  },
  {
    regle: "Écoutes sans droits d'auteur", oeuvre: "Ligne 7", iswc: "T-901.234.599-8", isrc: "FRZ012500019", payeur: "SACEM",
    montant: null, estimation: true,
    methode: "L'enregistrement a rapporté 6 240,00 € (droits master), mais l'œuvre n'apparaît dans aucun relevé de droits d'auteur. Non chiffré : aucun taux par défaut.",
    action: "Vérifier que l'œuvre est déclarée à la SACEM avec son ISWC, et réclamer les droits d'auteur des écoutes.",
    preuves: ["distributeur_2025.csv, ligne 212 : 03/2025, 512,00 €", "distributeur_2025.csv, ligne 418 : 04/2025, 498,00 €"],
  },
  {
    regle: "Œuvre sans aucun revenu", oeuvre: "Archipel", iswc: null, isrc: null, payeur: null,
    montant: null, estimation: true,
    methode: "L'œuvre est au catalogue mais n'apparaît dans aucun relevé déposé. Non chiffré.",
    action: "Vérifier sa déclaration (SACEM, distributeur) et demander les relevés qui la concernent.",
    preuves: ["Catalogue : Archipel"],
  },
];

export const catalogueDemo: LigneCatalogue[] = [
  { titre: "Minuit Pile", artiste: "Nova Lune", iswc: "T-901.234.567-1", isrc: "FRZ012500011", ayants_droit: 4, parts_dep: 100, revenus: 14820 },
  { titre: "Ciel Ouvert", artiste: "Nova Lune", iswc: "T-901.234.580-3", isrc: "FRZ012500014", ayants_droit: 3, parts_dep: 87.5, revenus: 9000 },
  { titre: "Ligne 7", artiste: "Kenzo Rive", iswc: "T-901.234.599-8", isrc: "FRZ012500019", ayants_droit: 3, parts_dep: 100, revenus: 6240 },
  { titre: "Rive Gauche", artiste: "Kenzo Rive", iswc: "T-901.234.601-2", isrc: "FRZ012500021", ayants_droit: 2, parts_dep: null, revenus: 5310 },
  { titre: "Lumière Basse", artiste: "Nova Lune", iswc: "T-901.234.612-9", isrc: "FRZ012500023", ayants_droit: 3, parts_dep: null, revenus: 4775 },
  { titre: "Dernier Métro", artiste: "Kenzo Rive", iswc: "T-901.234.620-1", isrc: "FRZ012500027", ayants_droit: 4, parts_dep: null, revenus: 3920 },
  { titre: "Sable Noir", artiste: "Nova Lune", iswc: "T-901.234.633-4", isrc: "FRZ012500031", ayants_droit: 4, parts_dep: 100, revenus: 3105 },
  { titre: "Néon Bleu", artiste: "Kenzo Rive", iswc: "T-901.234.645-0", isrc: "FRZ012500034", ayants_droit: 5, parts_dep: 100, revenus: 2460 },
  { titre: "Interlude 2", artiste: "Nova Lune", iswc: null, isrc: "FRZ012500036", ayants_droit: 2, parts_dep: 100, revenus: 610 },
  { titre: "Archipel", artiste: "Kenzo Rive", iswc: null, isrc: null, ayants_droit: 2, parts_dep: 100, revenus: 0 },
];

export const rapportsDemo: Rapport[] = [
  { titre: "Rapport d'audit", description: "Synthèse, fuites classées par argent en jeu, manques et méthode de calcul.", format: "PDF" },
  { titre: "Dossier de preuves", description: "Chaque fuite avec les lignes de relevés qui la prouvent.", format: "CSV" },
  { titre: "Liste des œuvres et des parts", description: "Catalogue contrôlé : œuvres, ISWC, ISRC, ayants droit et parts.", format: "XML" },
];
