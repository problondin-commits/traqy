// Choisit les données à afficher selon l'accès (lib/acces.ts) : le client choisi (cookie « traqy_import »)
// pour Tom, les seuls dossiers du client pour un lien client, la démo pour tous les autres.
import { cookies } from "next/headers";
import { cache } from "react";
import { roleActuel, type Role } from "./acces";
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
  role: Role;
};

// Une seule lecture par affichage de page, même si la barre et la page en ont besoin toutes les deux.
export const chargerDonnees = cache(async (): Promise<Donnees> => {
  const role = await roleActuel();
  const choixDemo: Choix = { valeur: DEMO, libelle: `${CLIENT_DEMO} (démo)` };
  const demoSeule: Donnees = { vue: vueDemo, demo: true, choix: [choixDemo], actuel: DEMO, erreur: null, role };
  if (role.type === "pause") {
    return { vue: null, demo: false, choix: [], actuel: "", erreur: "Votre accès est en pause. Contactez Traqy pour le réactiver.", role };
  }
  if (!moteurConfigure() || role.type === "public") return demoSeule;

  const demande = (await cookies()).get(COOKIE_IMPORT)?.value;
  try {
    const imports = await derniersImports();
    const permis = role.type === "client" ? imports.filter((i) => i.client === role.client) : imports;
    const choix = [...permis.map((i) => ({ valeur: String(i.id), libelle: i.client })), ...(role.type === "admin" ? [choixDemo] : [])];
    if (!choix.length) {
      return { vue: null, demo: false, choix, actuel: "", erreur: "Aucun dossier n'est encore disponible pour cet accès.", role };
    }
    const actuel = demande && choix.some((c) => c.valeur === demande) ? demande : choix[0].valeur;
    if (actuel === DEMO) return { ...demoSeule, choix, actuel };
    return { vue: await lireVue(Number(actuel)), demo: false, choix, actuel, erreur: null, role };
  } catch (e) {
    if (role.type === "admin" && demande === DEMO) return { ...demoSeule };
    const message = e instanceof ErreurMoteur ? e.message : "Erreur inattendue en lisant les données.";
    return { vue: null, demo: false, choix: role.type === "admin" ? [choixDemo] : [], actuel: demande ?? "", erreur: message, role };
  }
});
