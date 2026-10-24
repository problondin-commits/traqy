// Choisit les données à afficher : le client choisi (cookie « traqy_import ») ou le mode démo.
import { cookies } from "next/headers";
import { cache } from "react";
import { derniersImports, ErreurMoteur, lireVue, moteurConfigure } from "./api";
import { CLIENT_DEMO, vueDemo } from "./demo";
import type { Vue } from "./types";

export const COOKIE_IMPORT = "traqy_import";
export const DEMO = "demo";

export type Choix = { valeur: string; libelle: string };

export type Donnees = {
  vue: Vue | null; // null : le moteur n'a pas répondu
  demo: boolean;
  choix: Choix[];
  actuel: string;
  erreur: string | null;
};

// Une seule lecture par affichage de page, même si la barre et la page en ont besoin toutes les deux.
export const chargerDonnees = cache(async (): Promise<Donnees> => {
  const choixDemo: Choix = { valeur: DEMO, libelle: `${CLIENT_DEMO} (démo)` };
  if (!moteurConfigure()) {
    return { vue: vueDemo, demo: true, choix: [choixDemo], actuel: DEMO, erreur: null };
  }
  const demande = (await cookies()).get(COOKIE_IMPORT)?.value;
  try {
    const imports = await derniersImports();
    const choix = [...imports.map((i) => ({ valeur: String(i.id), libelle: i.client })), choixDemo];
    const actuel = demande && choix.some((c) => c.valeur === demande) ? demande : choix[0].valeur;
    if (actuel === DEMO) return { vue: vueDemo, demo: true, choix, actuel, erreur: null };
    return { vue: await lireVue(Number(actuel)), demo: false, choix, actuel, erreur: null };
  } catch (e) {
    if (demande === DEMO) return { vue: vueDemo, demo: true, choix: [choixDemo], actuel: DEMO, erreur: null };
    const message = e instanceof ErreurMoteur ? e.message : "Erreur inattendue en lisant les données.";
    return { vue: null, demo: false, choix: [choixDemo], actuel: demande ?? "", erreur: message };
  }
});
