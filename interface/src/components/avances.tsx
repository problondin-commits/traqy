// Avances et état de leur recoupement, par contrat. Le montant de l'avance est déclaré par le client ;
// le recoupement est lu dans les relevés (lignes « avance »). La date de fin est une estimation.
import { euros } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Avance } from "@/lib/types";

const pc = (v: number) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(v * 100)} %`;

export function Avances({ avances, compact = false }: { avances: Avance[]; compact?: boolean }) {
  if (avances.length === 0) return null;
  return (
    <section className="mb-8">
      <h2 className="mb-1 font-medium">Avances et recoupement</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Montant de l&apos;avance déclaré par le client. Le recoupement est lu dans les relevés, semestre par semestre.
      </p>
      <div className="liste-fondu liste-rapide grid grid-cols-1 gap-3 lg:grid-cols-2">
        {avances.map((a) => {
          const taux = a.taux ?? 0;
          const recoupee = a.reste <= 0;
          return (
            <article key={a.contrat} className="min-w-0 rounded-xl bg-card p-4 ring-1 ring-foreground/10 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium break-words">{a.projet ?? a.contrat}</p>
                  <p className="text-xs text-muted-foreground">Contrat {a.contrat}</p>
                </div>
                <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                  recoupee ? "bg-primary/15 text-primary" : "bg-warning/15 text-warning")}>
                  {recoupee ? "Recoupée" : "En cours de recoupement"}
                </span>
              </div>

              <div className="mt-4 flex items-baseline justify-between text-sm">
                <span className="text-muted-foreground">Recoupé : <span className="text-foreground tabular-nums">{euros(a.recoupe)}</span> sur {euros(a.montant)}</span>
                <span className="font-semibold tabular-nums">{pc(taux)}</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={Math.round(taux * 100)} aria-valuemin={0} aria-valuemax={100}>
                <div className={cn("h-full rounded-full", recoupee ? "bg-primary" : "bg-warning")} style={{ width: `${Math.min(taux, 1) * 100}%` }} />
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-muted-foreground">Reste à recouper</dt>
                <dd className="text-right tabular-nums">{euros(a.reste)}</dd>
                <dt className="text-muted-foreground">Fin estimée du recoupement</dt>
                <dd className="text-right">
                  {recoupee ? "—" : a.estimation ? <>{a.estimation.periode} <span className="text-xs text-muted-foreground">(estimation)</span></> : "Non estimable"}
                </dd>
                {!compact && (
                  <>
                    <dt className="text-muted-foreground">Recettes du label (avant recoupement)</dt>
                    <dd className="text-right tabular-nums">{euros(a.recettes)}</dd>
                    <dt className="text-muted-foreground">Frais imputés</dt>
                    <dd className="text-right tabular-nums">{euros(a.frais)}</dd>
                    <dt className="text-muted-foreground">Solde du compte (somme des relevés)</dt>
                    <dd className={cn("text-right tabular-nums", a.net_verse < 0 && "text-destructive")}>{euros(a.net_verse)}</dd>
                  </>
                )}
              </dl>

              {!compact && a.periodes.length > 0 && (
                <div className="liste-fondu liste-rapide mt-4 flex items-end gap-1" aria-label="Recoupement par semestre">
                  {a.periodes.map((p) => {
                    const max = Math.max(...a.periodes.map((x) => x.recoupe));
                    return (
                      <div key={p.periode} className="flex flex-1 flex-col items-center gap-1" title={`${p.periode} : ${euros(p.recoupe)}`}>
                        <div className="w-full rounded-sm bg-primary" style={{ height: `${max ? Math.max(4, (p.recoupe / max) * 48) : 4}px` }} />
                        <span className="text-[10px] text-muted-foreground">{p.periode.replace(" ", " ")}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {a.estimation && !recoupee && <p className="mt-3 text-xs text-muted-foreground">{a.estimation.methode}</p>}
              {!compact && a.net_verse < 0 && (
                <p className="mt-2 text-xs text-muted-foreground">Solde négatif : les frais imputés au contrat dépassent encore les recettes restantes après recoupement.</p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
