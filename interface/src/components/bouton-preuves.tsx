"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Fuite } from "@/lib/types";

// Dossier de preuves en CSV, fabriqué dans le navigateur à partir des alertes (séparateur « ; » pour Excel)
function telecharger(fuites: Fuite[], client: string) {
  const cellule = (v: string | number | null) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lignes = [
    ["Alerte", "Œuvre", "ISWC", "Payeur", "Montant (€)", "Nature du montant", "Décision du client", "Méthode", "Preuves", "À faire"],
    ...fuites.map((f) => [
      f.regle, f.oeuvre, f.iswc, f.payeur,
      f.montant === null ? "" : f.montant.toFixed(2).replace(".", ","),
      f.montant === null ? "Non chiffré" : f.estimation ? "Estimation" : "Montant relevé",
      f.decision ?? "à décider",
      f.methode, f.preuves.join(" | "), f.action,
    ]),
  ];
  const contenu = "﻿" + lignes.map((l) => l.map(cellule).join(";")).join("\r\n");
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(new Blob([contenu], { type: "text/csv;charset=utf-8" }));
  lien.download = `Dossier_Preuves_Traqy_${client.replace(/[^\p{L}\p{N}]+/gu, "_")}.csv`;
  lien.click();
  URL.revokeObjectURL(lien.href);
}

export function BoutonPreuves({ fuites, client, className }: { fuites: Fuite[]; client: string; className?: string }) {
  return (
    <Button className={className} disabled={!fuites.length} onClick={() => telecharger(fuites, client)}>
      <Download /> {fuites.length ? "Télécharger" : "Aucune alerte"}
    </Button>
  );
}
