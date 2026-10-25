// Téléchargement du rapport d'audit PDF du client affiché. La clé d'API reste sur le serveur de l'interface.
import { ErreurMoteur, moteurConfigure, rapportPdf } from "@/lib/api";
import { chargerDonnees } from "@/lib/donnees";

export async function GET() {
  if (!moteurConfigure()) return new Response("Le moteur Traqy n'est pas branché ici.", { status: 503 });
  const { vue, erreur } = await chargerDonnees();
  if (!vue) return new Response(erreur ?? "Données indisponibles.", { status: 503 });
  try {
    const { contenu, nom } = await rapportPdf(vue);
    return new Response(contenu, {
      headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="${nom}"`, "Cache-Control": "no-store" },
    });
  } catch (e) {
    if (!(e instanceof ErreurMoteur)) console.error("Rapport PDF :", e);
    return new Response(e instanceof ErreurMoteur ? e.message : "Le rapport n'a pas pu être fabriqué.", { status: 502 });
  }
}
