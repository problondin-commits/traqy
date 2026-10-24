// Reçoit les fichiers déposés dans l'écran Dépôt et les transmet au moteur avec la clé d'API (gardée côté serveur).
import { cookies } from "next/headers";
import { ErreurMoteur, importerFichiers, moteurConfigure } from "@/lib/api";
import { COOKIE_IMPORT } from "@/lib/donnees";

export async function POST(requete: Request) {
  if (!moteurConfigure()) {
    return Response.json({ erreur: "Le moteur n'est pas branché : mode démo uniquement." }, { status: 503 });
  }
  const formulaire = await requete.formData();
  const client = String(formulaire.get("client") ?? "").trim();
  const fichiers = formulaire.getAll("fichiers").filter((f): f is File => f instanceof File && f.size > 0);
  if (!client) return Response.json({ erreur: "Indiquez le nom du client." }, { status: 400 });
  if (!fichiers.length) return Response.json({ erreur: "Ajoutez au moins un fichier." }, { status: 400 });
  try {
    const resultat = await importerFichiers(client, fichiers);
    (await cookies()).set(COOKIE_IMPORT, String(resultat.import_id), { httpOnly: true, sameSite: "lax", maxAge: 60 * 60 * 24 * 365, path: "/" });
    return Response.json({ import_id: resultat.import_id });
  } catch (e) {
    return Response.json({ erreur: e instanceof ErreurMoteur ? e.message : "L'import a échoué." }, { status: 502 });
  }
}
