// Score de santé d'un titre et du catalogue : la part des 5 contrôles réussis (décision de Tom, 25/10/2026).
// 100 % veut dire « tous les contrôles sont réussis », pas « aucun argent ne manque ».
import type { Fuite, LigneCatalogue } from "./types";

export type Etat = "rouge" | "jaune" | "vert";
export type Controle = { libelle: string; ok: boolean };

const SANS_DROITS = ["Écoutes sans droits d'auteur", "Œuvre sans aucun revenu"]; // règles 4 et 5 de fuites.py

export const normaliser = (s: string | null | undefined) =>
  (s ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
const codeIswc = (s: string | null | undefined) => (s ?? "").toUpperCase().replace(/[^0-9A-Z]/g, "");
export const partsCompletes = (p: number | null) => p !== null && Math.abs(p - 100) < 0.1;

// Alertes de l'œuvre (par ISWC, sinon par titre), sans celles que le client a écartées
export function alertesDe(o: LigneCatalogue, fuites: Fuite[]): Fuite[] {
  return fuites.filter(
    (f) => f.decision !== "écartée" && ((f.iswc && o.iswc && codeIswc(f.iswc) === codeIswc(o.iswc)) || (f.oeuvre && normaliser(f.oeuvre) === normaliser(o.titre))),
  );
}

export function controles(o: LigneCatalogue, fuites: Fuite[]): Controle[] {
  const siennes = alertesDe(o, fuites);
  const droitsAuteur = o.detail
    ? o.detail.some((d) => d.type === "Droits d'auteur" && d.montant > 0)
    : !siennes.some((f) => SANS_DROITS.includes(f.regle));
  return [
    { libelle: "ISWC présent", ok: Boolean(o.iswc) },
    { libelle: "ISRC présent", ok: Boolean(o.isrc) },
    { libelle: "Parts à 100 %", ok: partsCompletes(o.parts_dep) },
    { libelle: "Présent dans les relevés de droits d'auteur", ok: droitsAuteur },
    { libelle: "Aucune alerte chiffrée ouverte", ok: !siennes.some((f) => (f.montant ?? 0) > 0) },
  ];
}

export function scoreTitre(o: LigneCatalogue, fuites: Fuite[]): number {
  const c = controles(o, fuites);
  return Math.round((c.filter((x) => x.ok).length / c.length) * 100);
}

// Moyenne des titres, pondérée par leurs revenus relevés (moyenne simple si aucun revenu)
export function scoreCatalogue(lignes: LigneCatalogue[], fuites: Fuite[]): number | null {
  if (lignes.length === 0) return null;
  const poids = lignes.reduce((s, o) => s + Math.max(o.revenus, 0), 0);
  const total = lignes.reduce((s, o) => s + scoreTitre(o, fuites) * (poids > 0 ? Math.max(o.revenus, 0) : 1), 0);
  return Math.round(total / (poids > 0 ? poids : lignes.length));
}

// Pastille : rouge = droits non perçus chiffrés ; jaune = à vérifier ; vert = rien à signaler
export function etatOeuvre(o: LigneCatalogue, fuites: Fuite[]): { etat: Etat; enJeu: number } {
  const siennes = alertesDe(o, fuites);
  const enJeu = siennes.reduce((s, f) => s + (f.montant ?? 0), 0);
  if (enJeu > 0) return { etat: "rouge", enJeu };
  if (siennes.length > 0 || !partsCompletes(o.parts_dep) || !o.iswc || !o.isrc) return { etat: "jaune", enJeu };
  return { etat: "vert", enJeu };
}
