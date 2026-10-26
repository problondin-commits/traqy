// Qui voit quoi. Chaque client reçoit un lien d'accès personnel (/acces/<code>) : il ne voit que ses propres dossiers.
// Tom a un code administrateur qui voit tout. Sans code, on ne voit que la démo.
// Les codes sont rangés dans la variable secrète TRAQY_ACCES (réglages de Vercel), jamais dans le code :
//   {"<code de Tom>": "admin", "<code MIS>": "S.Pri Noir", "<code Foufoune Palace>": "Luidji"}
// Sans cette variable (sur l'ordinateur de Tom), tout est visible, comme avant.
import { cookies } from "next/headers";

export const COOKIE_ACCES = "traqy_acces";

// Accès clients en pause (décision de Tom, 26/10/2026) : leur lien n'ouvre plus leurs dossiers, il affiche un message.
// Pour réactiver un client quand il veut consulter, retirer son nom de cette liste.
export const CLIENTS_EN_PAUSE = ["S.Pri Noir", "Luidji"];

export type Role = { type: "admin" } | { type: "client"; client: string } | { type: "pause" } | { type: "public" };

function tableDesCodes(): Record<string, string> | null {
  const brut = process.env.TRAQY_ACCES?.trim();
  if (!brut) return null;
  try {
    const t = JSON.parse(brut);
    return t && typeof t === "object" ? (t as Record<string, string>) : {};
  } catch {
    return {}; // variable mal écrite : personne n'a d'accès, plutôt que tout le monde
  }
}

export function roleDuCode(code: string): Role | null {
  const table = tableDesCodes();
  if (!table || !code || !Object.hasOwn(table, code)) return null;
  const valeur = table[code];
  if (valeur === "admin") return { type: "admin" };
  return CLIENTS_EN_PAUSE.includes(valeur) ? { type: "pause" } : { type: "client", client: valeur };
}

export async function roleActuel(): Promise<Role> {
  if (!tableDesCodes()) return { type: "admin" };
  const code = (await cookies()).get(COOKIE_ACCES)?.value ?? "";
  return roleDuCode(code) ?? { type: "public" };
}
