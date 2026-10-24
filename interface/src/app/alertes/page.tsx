"use client";

import { useState } from "react";
import { Check, ChevronDown, Undo2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EnTete, Tuile } from "@/components/elements";
import { fuitesDemo } from "@/lib/demo";
import { euros } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Fuite } from "@/lib/types";

type Decision = "validée" | "écartée";

export default function Alertes() {
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});
  const [ouverte, setOuverte] = useState<number | null>(0);
  const chiffre = fuitesDemo.reduce((s, f) => s + (f.montant ?? 0), 0);
  const valide = fuitesDemo.reduce((s, f, i) => s + (decisions[i] === "validée" ? f.montant ?? 0 : 0), 0);
  const decider = (i: number, d: Decision | null) =>
    setDecisions((avant) => {
      const suite = { ...avant };
      if (d) suite[i] = d; else delete suite[i];
      return suite;
    });

  return (
    <>
      <EnTete
        titre="Alertes"
        description="Les droits non perçus trouvés dans vos relevés, classés par argent en jeu. Validez celles à réclamer : elles iront dans votre rapport."
      />
      <div className="mb-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Tuile libelle="Droits non perçus chiffrés" valeur={euros(chiffre)} detail="Montants relevés et estimations" accent />
        <Tuile libelle="Alertes" valeur={String(fuitesDemo.length)} detail={`${fuitesDemo.filter((f) => f.montant === null).length} non chiffrées`} />
        <Tuile libelle="Validées pour réclamation" valeur={euros(valide)} detail={`${Object.values(decisions).filter((d) => d === "validée").length} alertes`} />
      </div>

      <div className="space-y-3">
        {fuitesDemo.map((f: Fuite, i) => {
          const decision = decisions[i];
          return (
            <article key={`${f.regle}-${f.oeuvre ?? f.payeur}`} className={cn("rounded-xl bg-card ring-1 ring-foreground/10 transition-opacity", decision === "écartée" && "opacity-50")}>
              <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start">
                <div className="min-w-0 flex-1">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{f.regle}</p>
                  <h2 className="mt-1 text-lg font-medium">{f.oeuvre ?? f.payeur}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {f.payeur ? <>À réclamer à <span className="text-foreground">{f.payeur}</span></> : "Payeur à identifier"}
                    {f.iswc ? <span className="ml-2 font-mono text-xs">ISWC {f.iswc}</span> : null}
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
                <button type="button" onClick={() => setOuverte(ouverte === i ? null : i)} className="flex w-full items-center gap-2 text-left text-sm text-muted-foreground hover:text-foreground">
                  <ChevronDown className={cn("size-4 transition-transform", ouverte === i && "rotate-180")} />
                  Méthode et preuves
                </button>
                {ouverte === i && (
                  <div className="mt-3 space-y-3 text-sm">
                    <p>{f.methode}</p>
                    <ul className="space-y-1">
                      {f.preuves.map((p) => (
                        <li key={p} className="rounded-md bg-muted px-3 py-1.5 font-mono text-xs text-muted-foreground">{p}</li>
                      ))}
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
                    <Button variant="ghost" size="sm" className="ml-auto" onClick={() => decider(i, null)}>
                      <Undo2 /> Annuler
                    </Button>
                  </>
                ) : (
                  <>
                    <Button size="sm" onClick={() => decider(i, "validée")}><Check /> Valider</Button>
                    <Button variant="outline" size="sm" onClick={() => decider(i, "écartée")}><X /> Écarter</Button>
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
