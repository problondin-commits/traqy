// Lien avec le moteur Traqy. Ce fichier ne tourne que sur le serveur de l'interface :
// la clé d'API (TRAQY_API_KEY) n'est jamais envoyée au navigateur.
import type { ImportResume, MoisMontant, Projection, ReglagesProjection, Vue } from "./types";

const URL_API = (process.env.TRAQY_API_URL ?? "").replace(/\/+$/, "");
const CLE_API = process.env.TRAQY_API_KEY ?? "";

export class ErreurMoteur extends Error {}

export function moteurConfigure() {
  return Boolean(URL_API && CLE_API);
}

async function appel<T>(chemin: string, init: RequestInit = {}): Promise<T> {
  let reponse: Response;
  try {
    reponse = await fetch(`${URL_API}${chemin}`, {
      ...init,
      headers: { "X-API-Key": CLE_API, ...init.headers },
      cache: "no-store",
      signal: AbortSignal.timeout(90_000), // l'offre gratuite peut mettre près d'une minute à se réveiller
    });
  } catch {
    throw new ErreurMoteur("Le moteur ne répond pas. Il se réveille peut-être : réessayez dans une minute.");
  }
  if (!reponse.ok) {
    const detail = await reponse.json().then((j) => j?.detail).catch(() => null);
    throw new ErreurMoteur(typeof detail === "string" ? detail : `Le moteur a répondu par une erreur (${reponse.status}).`);
  }
  return reponse.json() as Promise<T>;
}

/** Dernier import de chaque client, du plus récent au plus ancien. */
export async function derniersImports(): Promise<ImportResume[]> {
  const tous = await appel<ImportResume[]>("/api/v1/imports");
  const vus = new Set<string>();
  return tous.filter((i) => (vus.has(i.client) ? false : (vus.add(i.client), true)));
}

export function lireVue(importId: number) {
  return appel<Vue>(`/api/v1/imports/${importId}/vue`);
}

export function deciderFuite(fuiteId: number, decision: string | null) {
  return appel(`/api/v1/fuites/${fuiteId}/decision`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
}

export function lireProjection(importId: number, r: ReglagesProjection) {
  const q = new URLSearchParams({ fin: r.fin, baisse_min: String(r.baisse_min), baisse_max: String(r.baisse_max) });
  return appel<Projection>(`/api/v1/imports/${importId}/projection?${q}`);
}

/** Projection d'une courbe fournie directement (mode démo). */
export function projeterCourbe(historique: MoisMontant[], r: ReglagesProjection) {
  return appel<Projection>("/api/v1/projection", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ historique, ...r }),
  });
}

/** Envoie les fichiers au moteur, qui les importe, les contrôle et les enregistre pour ce client. */
export function importerFichiers(client: string, fichiers: File[]) {
  const formulaire = new FormData();
  formulaire.append("client", client);
  for (const f of fichiers) formulaire.append("fichiers", f, f.name);
  return appel<{ import_id: number }>("/api/v1/import", { method: "POST", body: formulaire });
}
