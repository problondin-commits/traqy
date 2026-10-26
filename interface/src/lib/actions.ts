"use server";

import { cookies } from "next/headers";
import { refresh } from "next/cache";
import { deciderFuite } from "./api";
import { chargerDonnees, COOKIE_IMPORT } from "./donnees";
import type { Decision } from "./types";

const UN_AN = 60 * 60 * 24 * 365;

/** Change le client affiché (numéro d'import, ou « demo »), seulement parmi ceux que cet accès peut voir. */
export async function choisirClient(valeur: string) {
  const { choix } = await chargerDonnees();
  if (!choix.some((c) => c.valeur === valeur)) throw new Error("Ce dossier n'est pas accessible.");
  (await cookies()).set(COOKIE_IMPORT, valeur, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", maxAge: UN_AN, path: "/" });
}

/** Enregistre dans la base le choix du client sur une alerte. En démo (numéro négatif), rien n'est envoyé.
 *  L'alerte doit appartenir au dossier affiché pour cet accès. */
export async function deciderAlerte(fuiteId: number, decision: Decision | null) {
  if (fuiteId < 0) return;
  const { vue, demo } = await chargerDonnees();
  if (demo || !vue?.fuites.some((f) => f.id === fuiteId)) throw new Error("Cette alerte n'est pas accessible.");
  await deciderFuite(fuiteId, decision);
  refresh();
}
