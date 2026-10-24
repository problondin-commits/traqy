import { ArrowRight } from "lucide-react";
import { EnTete, Indisponible, PastilleGravite, Tuile, Vide } from "@/components/elements";
import { chargerDonnees } from "@/lib/donnees";
import { euros } from "@/lib/format";

export default async function ControleDesManques() {
  const { vue, erreur } = await chargerDonnees();
  const entete = (
    <EnTete
      titre="Contrôle des manques"
      description="Ce qui manque dans les fichiers déposés, classé par importance, avec ce qu'il faut demander pour compléter le dossier."
    />
  );
  if (!vue) return <>{entete}<Indisponible message={erreur} /></>;
  const compter = (g: string) => vue.manques.filter((m) => m.gravite === g).length;
  return (
    <>
      {entete}
      <div className="mb-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Tuile libelle="Bloquants" valeur={String(compter("bloquant"))} detail="Empêchent l'analyse" />
        <Tuile libelle="Importants" valeur={String(compter("important"))} detail="Peuvent cacher des droits non perçus" />
        <Tuile libelle="À compléter" valeur={String(compter("à compléter"))} detail="Informations à ajouter" />
      </div>

      {vue.manques.length === 0 && <Vide message="Aucun manque : le dossier est complet." />}
      <div className="space-y-3">
        {vue.manques.map((m) => (
          <article key={m.sujet} className="rounded-xl bg-card p-5 ring-1 ring-foreground/10">
            <div className="flex flex-wrap items-center gap-2">
              <PastilleGravite gravite={m.gravite} />
              <h2 className="font-medium">{m.sujet}</h2>
              {m.montant ? <span className="ml-auto text-sm tabular-nums text-muted-foreground">{euros(m.montant)} concernés</span> : null}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{m.constat}</p>
            <p className="mt-3 flex items-start gap-2 text-sm">
              <ArrowRight className="mt-0.5 size-4 shrink-0 text-primary" />
              <span>{m.action}</span>
            </p>
            {m.exemples.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2">
                {m.exemples.map((e) => (
                  <li key={e} className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">{e}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
