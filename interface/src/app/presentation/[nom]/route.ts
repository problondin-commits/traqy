// Présentations investisseurs (pitch et deep dive) : /presentation/pitch et /presentation/deep-dive.
// Elles s'ouvrent sur n'importe quel téléphone, sans compte, après un code d'accès.
// Le code lui-même n'est pas dans le code source : seule son empreinte (SHA-256) y figure.
// Le code est dans donnees_clients/acces_vercel.txt (fichier non envoyé sur GitHub).
import { createHash, timingSafeEqual } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { cookies } from "next/headers";

// Présentations investisseurs : un code partagé. Page « Préparation » (pour Tom seul) : son propre code et son propre cookie.
const INVESTISSEURS = { empreinte: "65c8982bceb0c2ad992db5a424076221e593b1b71069a029bfd2b289c080e102", cookie: "traqy_presentation" };
const PREPARATION = { empreinte: "6ecb1244fd61174676d239e62df9f14b8734ecb5137171d2814cf1eac22af640", cookie: "traqy_preparation" };
const FICHIERS: Record<string, { fichier: string; acces: { empreinte: string; cookie: string } }> = {
  pitch: { fichier: "pitch.html", acces: INVESTISSEURS },
  "deep-dive": { fichier: "deep-dive.html", acces: INVESTISSEURS },
  preparation: { fichier: "preparation.html", acces: PREPARATION },
};
const TRENTE_JOURS = 60 * 60 * 24 * 30;
const ENTETES = { "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "private, no-store" };

function codeValide(code: string | undefined | null, empreinte: string): boolean {
  if (!code) return false;
  const a = Buffer.from(createHash("sha256").update(code.trim().toUpperCase()).digest("hex"));
  const b = Buffer.from(empreinte);
  return a.length === b.length && timingSafeEqual(a, b);
}

function pageCode(nom: string, erreur: boolean): Response {
  const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Traqy · Présentation</title>
<style>
  body { margin:0; min-height:100vh; display:grid; place-items:center; background:#0B0C0F; color:#F5F5F3; font-family:Inter, -apple-system, "Segoe UI", Arial, sans-serif; }
  form { width:min(340px, 88vw); display:flex; flex-direction:column; gap:14px; text-align:center; }
  h1 { font-size:22px; margin:0; } p { color:#8A8F98; margin:0; font-size:14px; }
  input { font-size:20px; letter-spacing:4px; text-align:center; text-transform:uppercase; padding:14px; border-radius:14px; border:1px solid #2A2D33; background:#15171B; color:#F5F5F3; }
  input:focus { outline:2px solid #31F2A4; }
  button { font-size:16px; font-weight:700; padding:14px; border:0; border-radius:30px; background:#31F2A4; color:#0B0D10; }
  .err { color:#F2B84B; }
</style></head><body>
<form method="post" action="/presentation/${nom}">
  <h1>traqy</h1><p>Entrez le code reçu pour ouvrir la présentation.</p>
  <input id="code" name="code" autocomplete="off" autocapitalize="characters" required aria-label="Code d'accès">
  ${erreur ? '<p class="err">Code incorrect.</p>' : ""}
  <button type="submit">Ouvrir</button>
</form></body></html>`;
  return new Response(html, { status: erreur ? 401 : 200, headers: { "Content-Type": "text/html; charset=utf-8", ...ENTETES } });
}

export async function GET(_requete: Request, { params }: RouteContext<"/presentation/[nom]">) {
  const { nom } = await params;
  const entree = FICHIERS[nom];
  if (!entree) return new Response("Introuvable", { status: 404 });
  const pot = await cookies();
  if (!codeValide(pot.get(entree.acces.cookie)?.value, entree.acces.empreinte)) return pageCode(nom, false);
  const html = await readFile(path.join(process.cwd(), "presentations", entree.fichier), "utf8");
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8", ...ENTETES } });
}

export async function POST(requete: Request, { params }: RouteContext<"/presentation/[nom]">) {
  const { nom } = await params;
  const entree = FICHIERS[nom];
  if (!entree) return new Response("Introuvable", { status: 404 });
  const code = String((await requete.formData()).get("code") ?? "");
  if (!codeValide(code, entree.acces.empreinte)) return pageCode(nom, true);
  const pot = await cookies();
  pot.set(entree.acces.cookie, code.trim().toUpperCase(), { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", maxAge: TRENTE_JOURS, path: "/presentation" });
  return Response.redirect(new URL(`/presentation/${nom}`, requete.url), 303);
}
