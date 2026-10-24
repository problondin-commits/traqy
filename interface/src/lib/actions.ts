"use server";

import { cookies } from "next/headers";
import { refresh } from "next/cache";
import { deciderFuite } from "./api";
import { COOKIE_IMPORT } from "./donnees";
import type { Decision } from "./types";

const UN_AN = 60 * 60 * 24 * 365;

/** Change le client affiché (numéro d'import, ou « demo »). */
export async function choisirClient(valeur: string) {
  (await cookies()).set(COOKIE_IMPORT, valeur, { httpOnly: true, sameSite: "lax", maxAge: UN_AN, path: "/" });
}

/** Enregistre dans la base le choix du client sur une alerte. En démo (numéro négatif), rien n'est envoyé. */
export async function deciderAlerte(fuiteId: number, decision: Decision | null) {
  if (fuiteId < 0) return;
  await deciderFuite(fuiteId, decision);
  refresh();
}
