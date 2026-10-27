// Bloc « Contrat » : clauses utiles du contrat déclaré par le client, résultat des albums et avances récupérées.
// Les montants viennent des relevés et de la fiche contrat ; la lecture du contrat reste à faire confirmer.
import { CircleCheck, FileSignature, TriangleAlert } from "lucide-react";
import { euros, pourCent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ContratLecture } from "@/lib/types";

const dateFr = (iso: string) => new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(new Date(iso));

export function BlocContrat({ contrat }: { contrat: ContratLecture | null | undefined }) {
  if (!contrat) return null;
  const c = contrat;
  return (
    <section className="mb-8">
      <div className="mb-4 flex items-start gap-3">
        <FileSignature className="mt-0.5 size-5 shrink-0 text-primary" />
        <div className="min-w-0">
          <h2 className="font-medium">{c.nom}{c.date_signature ? ` du ${dateFr(c.date_signature)}` : ""}</h2>
          {c.parties && <p className="text-sm text-muted-foreground">{c.parties}</p>}
          <p className="mt-2 flex flex-wrap gap-1.5">
            {c.albums.map((a) => (
              <span key={a.contrat} className="rounded-full bg-muted px-2.5 py-0.5 text-xs">
                {a.titre}{a.rang ? <span className="text-muted-foreground"> · {a.rang}</span> : null}
              </span>
            ))}
          </p>
        </div>
      </div>

      <div className="grid gap-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10 sm:grid-cols-3 sm:p-5">
        <div>
          <p className="text-xs text-muted-foreground">Résultat des albums (recettes − frais)</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{euros(c.resultat_total)}</p>
          <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
            {c.resultats.map((r) => (
              <li key={r.contrat} className="flex justify-between gap-2">
                <span>{r.album}</span>
                <span className={cn("tabular-nums", r.resultat < 0 && "text-destructive")}>{euros(r.resultat)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="sm:border-l sm:border-border sm:pl-4">
          <p className="text-xs text-muted-foreground">Avances récupérées par Believe</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{euros(c.avances_recuperees)}</p>
          <p className="mt-2 text-xs text-muted-foreground">sur {euros(c.avances_declarees)} d&apos;avances prévues au contrat</p>
        </div>
        {c.ecart !== null && (
          <div className="sm:border-l sm:border-border sm:pl-4">
            <p className="text-xs text-muted-foreground">Récupéré au-delà du résultat</p>
            <p className={cn("mt-1 text-2xl font-semibold tabular-nums", c.ecart > 0 ? "text-destructive" : "text-primary")}>{euros(c.ecart)}</p>
            <p className="mt-2 text-xs text-muted-foreground">Avances récupérées − résultat des albums</p>
          </div>
        )}
      </div>

      {c.resultats.some((r) => r.anterieur !== null) && (
        <p className="mt-2 text-xs text-muted-foreground">
          {c.resultats.filter((r) => r.anterieur !== null).map((r) =>
            `${r.album} : ${euros(r.anterieur!)} de résultat avant le premier relevé détaillé (${r.anterieur_source}).`).join(" ")}
        </p>
      )}

      {c.controle_taux && c.controle_taux.taux.length > 0 && (
        <div className="mt-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10 sm:px-5">
          <p className="flex items-center gap-2 text-sm font-medium">
            {c.controle_taux.hors_contrat > 0
              ? <TriangleAlert className="size-4 shrink-0 text-warning" />
              : <CircleCheck className="size-4 shrink-0 text-primary" />}
            Taux de partage vérifiés avec le contrat
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {c.controle_taux.taux.map((x) => (
              <li key={x.taux} className="flex flex-wrap justify-between gap-x-3 gap-y-0.5">
                <span>
                  <span className="font-medium tabular-nums">{pourCent(x.taux * 100)}</span>
                  <span className={cn("text-muted-foreground", !x.conforme && "text-warning")}> · {x.explication ?? "taux non prévu au contrat"}</span>
                </span>
                <span className="tabular-nums text-muted-foreground">{euros(x.montant)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">
            {c.controle_taux.hors_contrat > 0
              ? `${euros(c.controle_taux.hors_contrat)} de recettes partagées à un taux que le contrat ne prévoit pas : voir l'alerte « Taux de partage inhabituel ».`
              : "Toutes les recettes sont partagées à un taux prévu au contrat : aucun écart. Ces taux sont pris en compte dans les alertes."}
          </p>
        </div>
      )}

      {c.avertissement && (
        <p className="mt-3 flex gap-2 rounded-lg bg-warning/15 px-3 py-2 text-sm text-warning">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          {c.avertissement}
        </p>
      )}

      <div className="liste-fondu liste-rapide mt-4 grid gap-3 md:grid-cols-2">
        {c.clauses.map((x) => (
          <article key={`${x.article}-${x.titre}`} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
            <p className="text-xs font-medium text-primary">{x.article}</p>
            <p className="mt-0.5 font-medium">{x.titre}</p>
            <p className="mt-1.5 text-sm text-muted-foreground">{x.texte}</p>
          </article>
        ))}
      </div>

      {c.sources.length > 0 && (
        <p className="mt-3 text-xs text-muted-foreground">Sources : {c.sources.join(" · ")}.</p>
      )}
    </section>
  );
}
