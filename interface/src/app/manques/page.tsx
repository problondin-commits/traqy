import { ArrowRight } from "lucide-react";
import { Bandeau, EnTete, Indisponible, PastilleGravite, Vide } from "@/components/elements";
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
  // Barre de répartition : part de chaque gravité dans le nombre total de manques.
  const parts = [
    { n: compter("bloquant"), couleur: "bg-destructive" },
    { n: compter("important"), couleur: "bg-warning" },
    { n: compter("à compléter"), couleur: "bg-muted-foreground/40" },
  ];
  return (
    <>
      {entete}
      <Bandeau chiffres={[
        { libelle: "Bloquants", valeur: String(parts[0].n), detail: "Empêchent l'analyse", couleur: parts[0].couleur },
        { libelle: "Importants", valeur: String(parts[1].n), detail: "Peuvent cacher des droits non perçus", couleur: parts[1].couleur },
        { libelle: "À compléter", valeur: String(parts[2].n), detail: "Informations à ajouter", couleur: parts[2].couleur },
      ]}>
        {vue.manques.length > 0 ? (
          <div className="flex h-2 gap-0.5 overflow-hidden rounded-full" role="img"
            aria-label={`${parts[0].n} bloquants, ${parts[1].n} importants, ${parts[2].n} à compléter`}>
            {parts.filter((p) => p.n > 0).map((p) => (
              <span key={p.couleur} className={p.couleur} style={{ flexGrow: p.n }} />
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Dossier complet.</p>
        )}
      </Bandeau>

      {vue.manques.length === 0 && <Vide message="Aucun manque : le dossier est complet." />}
      <div className="liste-fondu space-y-3">
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
