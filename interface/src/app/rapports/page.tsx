"use client";

import { Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EnTete } from "@/components/elements";
import { CLIENT_DEMO, fuitesDemo, rapportsDemo } from "@/lib/demo";

// Dossier de preuves en CSV, fabriqué directement dans le navigateur à partir des alertes (séparateur « ; » pour Excel)
function telechargerPreuves() {
  const cellule = (v: string | number | null) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lignes = [
    ["Alerte", "Œuvre", "ISWC", "Payeur", "Montant (€)", "Nature du montant", "Méthode", "Preuves", "À faire"],
    ...fuitesDemo.map((f) => [
      f.regle, f.oeuvre, f.iswc, f.payeur,
      f.montant === null ? "" : f.montant.toFixed(2).replace(".", ","),
      f.montant === null ? "Non chiffré" : f.estimation ? "Estimation" : "Montant relevé",
      f.methode, f.preuves.join(" | "), f.action,
    ]),
  ];
  const contenu = "﻿" + lignes.map((l) => l.map(cellule).join(";")).join("\r\n");
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(new Blob([contenu], { type: "text/csv;charset=utf-8" }));
  lien.download = `Dossier_Preuves_Traqy_${CLIENT_DEMO.replace(/\s+/g, "_")}.csv`;
  lien.click();
  URL.revokeObjectURL(lien.href);
}

export default function Rapports() {
  return (
    <>
      <EnTete
        titre="Rapports"
        description="Les documents à remettre ou à transmettre : rapport d'audit, dossier de preuves et liste des œuvres."
      />
      <div className="grid gap-3 md:grid-cols-3">
        {rapportsDemo.map((r) => {
          const pret = r.format === "CSV";
          return (
            <article key={r.titre} className="flex flex-col rounded-xl bg-card p-5 ring-1 ring-foreground/10">
              <div className="flex items-center justify-between">
                <FileText className="size-5 text-primary" />
                <span className="rounded-md bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">{r.format}</span>
              </div>
              <h2 className="mt-4 font-medium">{r.titre}</h2>
              <p className="mt-1 flex-1 text-sm text-muted-foreground">{r.description}</p>
              <Button className="mt-5" variant={pret ? "default" : "outline"} disabled={!pret} onClick={pret ? telechargerPreuves : undefined}>
                <Download /> {pret ? "Télécharger" : "Bientôt disponible"}
              </Button>
              {!pret && <p className="mt-2 text-center text-xs text-muted-foreground">Une fois l’interface branchée au moteur</p>}
            </article>
          );
        })}
      </div>
      <p className="mt-6 text-xs text-muted-foreground">
        Tous les montants sont calculés uniquement à partir des données du client. Les estimations sont signalées comme telles.
      </p>
    </>
  );
}
