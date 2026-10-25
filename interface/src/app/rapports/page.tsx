import { Download, FileText } from "lucide-react";
import { EnTete, Indisponible } from "@/components/elements";
import { BoutonPreuves } from "@/components/bouton-preuves";
import { Button, buttonVariants } from "@/components/ui/button";
import { rapports } from "@/lib/demo";
import { chargerDonnees } from "@/lib/donnees";

export default async function Rapports() {
  const { vue, erreur } = await chargerDonnees();
  return (
    <>
      <EnTete
        titre="Rapports"
        description="Les documents à remettre ou à transmettre : rapport d'audit, dossier de preuves et liste des œuvres."
      />
      {!vue ? (
        <Indisponible message={erreur} />
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {rapports.map((r) => (
            <article key={r.titre} className="flex flex-col rounded-xl bg-card p-5 ring-1 ring-foreground/10">
              <div className="flex items-center justify-between">
                <FileText className="size-5 text-primary" />
                <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">{r.format}</span>
              </div>
              <h2 className="mt-4 font-medium">{r.titre}</h2>
              <p className="mt-1 flex-1 text-sm text-muted-foreground">{r.description}</p>
              {r.format === "CSV" ? (
                <BoutonPreuves fuites={vue.fuites} client={vue.client ?? "client"} />
              ) : r.format === "PDF" ? (
                <>
                  <a href="/api/rapport" download className={buttonVariants({ className: "mt-5" })}>
                    <Download /> Télécharger
                  </a>
                  <p className="mt-2 text-center text-xs text-muted-foreground">Fabriqué à la demande : quelques secondes</p>
                </>
              ) : (
                <>
                  <Button className="mt-5" variant="outline" disabled>Bientôt disponible</Button>
                  <p className="mt-2 text-center text-xs text-muted-foreground">Prochaine étape</p>
                </>
              )}
            </article>
          ))}
        </div>
      )}
      <p className="mt-6 text-xs text-muted-foreground">
        Tous les montants sont calculés uniquement à partir des données du client. Les estimations sont signalées comme telles.
      </p>
    </>
  );
}
