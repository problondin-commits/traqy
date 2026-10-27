"use client";

import { useState, useTransition } from "react";
import { Check, ChevronDown, Undo2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Bandeau } from "@/components/elements";
import { deciderAlerte } from "@/lib/actions";
import { euros } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Decision, Fuite } from "@/lib/types";

// « 05d_concord_soldes.csv, ligne 12 : 2025 S2, 1 200 € » devient « Concord soldes, ligne 12 » + le détail,
// avec le nom du fichier d'origine en petit dessous (il reste la preuve de la source).
function lirePreuve(p: string): { source: string; detail: string | null; fichier: string | null } {
  const m = p.match(/^(.+?\.(?:csv|xlsx|xls|zip))(?:\s*›\s*([^,]+))?(?:, ligne (\d+))?(?:\s*:\s*(.*))?$/i);
  if (!m) return { source: p, detail: null, fichier: null };
  const [, fichier, onglet, ligne, detail] = m;
  const nom = fichier
    .replace(/^.*[\\/]/, "")
    .replace(/\.(csv|xlsx|xls|zip)$/i, "")
    .replace(/^[0-9]+[a-z]?[_\- ]+/i, "")
    .replace(/[_\-]+/g, " ")
    .trim();
  const lisible = nom ? nom.charAt(0).toUpperCase() + nom.slice(1) : fichier;
  const source = [lisible, onglet?.trim(), ligne ? `ligne ${ligne}` : null].filter(Boolean).join(", ");
  return { source, detail: detail?.trim() || null, fichier };
}

export function ListeAlertes({ fuites }: { fuites: Fuite[] }) {
  // Le choix s'affiche tout de suite, puis il est enregistré dans la base (sauf en démo).
  const [decisions, setDecisions] = useState<Record<number, Decision | null>>(
    () => Object.fromEntries(fuites.map((f) => [f.id ?? 0, f.decision])),
  );
  const [ouverte, setOuverte] = useState<number | null>(fuites[0]?.id ?? null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [, demarrer] = useTransition();

  const decider = (id: number, d: Decision | null) => {
    const avant = decisions[id];
    setDecisions((x) => ({ ...x, [id]: d }));
    setErreur(null);
    demarrer(async () => {
      try {
        await deciderAlerte(id, d);
      } catch {
        setDecisions((x) => ({ ...x, [id]: avant }));
        setErreur("Le choix n'a pas pu être enregistré. Réessayez dans un instant.");
      }
    });
  };

  const chiffre = fuites.reduce((s, f) => s + (f.montant ?? 0), 0);
  const validees = fuites.filter((f) => decisions[f.id ?? 0] === "validée");
  return (
    <>
      <Bandeau chiffres={[
        { libelle: "Droits non perçus chiffrés", valeur: euros(chiffre), detail: "Montants relevés et estimations", accent: true },
        { libelle: "Alertes", valeur: String(fuites.length), detail: `${fuites.filter((f) => f.montant === null).length} non chiffrées` },
        { libelle: "Validées pour réclamation", valeur: euros(validees.reduce((s, f) => s + (f.montant ?? 0), 0)), detail: `${validees.length} alertes` },
      ]} />
      {erreur && <p className="mb-4 rounded-lg bg-destructive/15 px-4 py-2 text-sm text-destructive">{erreur}</p>}

      <div className="liste-fondu space-y-3">
        {fuites.map((f) => {
          const id = f.id ?? 0;
          const decision = decisions[id];
          return (
            <article key={id} className={cn("rounded-xl bg-card ring-1 ring-foreground/10 transition-opacity", decision === "écartée" && "opacity-50")}>
              <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
                <div className="min-w-0 flex-1">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{f.regle}</p>
                  <h2 className="mt-1 text-lg font-medium break-words">{f.oeuvre ?? f.payeur}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {f.payeur ? <>À réclamer à <span className="text-foreground">{f.payeur}</span></> : "Payeur à identifier"}
                    {f.iswc ? <span className="ml-2 text-xs tabular-nums">ISWC {f.iswc}</span> : null}
                  </p>
                </div>
                <div className="text-left sm:text-right">
                  <p className={cn("text-2xl font-semibold tabular-nums", f.montant !== null ? "text-primary" : "text-muted-foreground")}>
                    {f.montant !== null ? euros(f.montant) : "Non chiffré"}
                  </p>
                  {f.montant !== null && (
                    <span className="mt-1 inline-block rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {f.estimation ? "Estimation" : "Montant relevé"}
                    </span>
                  )}
                </div>
              </div>

              <div className="border-t border-border px-5 py-3">
                <button type="button" onClick={() => setOuverte(ouverte === id ? null : id)} className="flex w-full items-center gap-2 text-left text-sm text-muted-foreground hover:text-foreground">
                  <ChevronDown className={cn("size-4 transition-transform", ouverte === id && "rotate-180")} />
                  Méthode et preuves
                </button>
                {ouverte === id && (
                  <div className="mt-3 space-y-3 text-sm">
                    <p>{f.methode}</p>
                    <ul className="space-y-1">
                      {f.preuves.map((p) => {
                        const { source, detail, fichier } = lirePreuve(p);
                        return (
                          <li key={p} className="rounded-md bg-muted px-3 py-2 break-words">
                            <span className="text-foreground">{source}</span>
                            {detail && <span className="text-muted-foreground"> · {detail}</span>}
                            {fichier && <span className="mt-0.5 block text-xs text-muted-foreground/70">Fichier : {fichier}</span>}
                          </li>
                        );
                      })}
                    </ul>
                    <p className="text-muted-foreground"><span className="text-foreground">À faire :</span> {f.action}</p>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 border-t border-border px-5 py-3">
                {decision ? (
                  <>
                    <span className={cn("text-sm", decision === "validée" ? "text-primary" : "text-muted-foreground")}>
                      {decision === "validée" ? "Validée : sera réclamée" : "Écartée"}
                    </span>
                    <Button variant="ghost" size="sm" className="ml-auto" onClick={() => decider(id, null)}>
                      <Undo2 /> Annuler
                    </Button>
                  </>
                ) : (
                  <>
                    <Button className="h-10 flex-1 sm:h-8 sm:flex-none" onClick={() => decider(id, "validée")}><Check /> Valider</Button>
                    <Button variant="outline" className="h-10 flex-1 sm:h-8 sm:flex-none" onClick={() => decider(id, "écartée")}><X /> Écarter</Button>
                  </>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
