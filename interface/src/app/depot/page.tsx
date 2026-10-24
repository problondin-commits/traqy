"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { CheckCircle2, CircleSlash, FileSpreadsheet, UploadCloud, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EnTete } from "@/components/elements";
import { DATE_DEPOT_DEMO, fichiersDemo } from "@/lib/demo";
import { nombre } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BilanFichier } from "@/lib/types";

const ICONE_STATUT = {
  importé: <CheckCircle2 className="size-4 text-primary" />,
  ignoré: <CircleSlash className="size-4 text-muted-foreground" />,
  refusé: <XCircle className="size-4 text-destructive" />,
};

export default function Depot() {
  const champ = useRef<HTMLInputElement>(null);
  const [survol, setSurvol] = useState(false);
  const [nouveaux, setNouveaux] = useState<string[]>([]);

  const ajouter = (liste: FileList | null) => {
    if (liste) setNouveaux((avant) => [...avant, ...Array.from(liste, (f) => f.name)]);
  };

  return (
    <>
      <EnTete
        titre="Dépôt"
        description="Déposez une seule fois votre catalogue, vos contrats et vos relevés. Traqy reconnaît seul chaque fichier (CSV, Excel ou ZIP) et vérifie ce qui manque."
        action={<Button nativeButton={false} render={<Link href="/manques" />}>Voir le contrôle des manques</Button>}
      />

      <button
        type="button"
        onClick={() => champ.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setSurvol(true); }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(e) => { e.preventDefault(); setSurvol(false); ajouter(e.dataTransfer.files); }}
        className={cn(
          "flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
          survol ? "border-primary bg-primary/5" : "border-border hover:border-primary/60 hover:bg-card",
        )}
      >
        <UploadCloud className="size-10 text-primary" />
        <span className="text-base font-medium">Glissez vos fichiers ici, ou cliquez pour les choisir</span>
        <span className="text-sm text-muted-foreground">Catalogue, relevés SACEM, relevés du distributeur, soldes des éditeurs</span>
      </button>
      <input ref={champ} type="file" multiple accept=".csv,.xlsx,.xlsm,.zip" className="hidden" onChange={(e) => ajouter(e.target.files)} />

      {nouveaux.length > 0 && (
        <div className="mt-4 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <p className="text-sm font-medium">Fichiers choisis</p>
          <p className="mb-3 text-xs text-muted-foreground">Mode démo : ces fichiers ne sont pas envoyés. Une fois l’interface branchée au moteur, ils seront importés et contrôlés.</p>
          <ul className="space-y-1">
            {nouveaux.map((nom, i) => (
              <li key={`${nom}-${i}`} className="flex items-center gap-2 text-sm">
                <FileSpreadsheet className="size-4 text-muted-foreground" />
                {nom}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-10">
        <h2 className="text-base font-medium">Dernier dépôt</h2>
        <p className="mb-4 text-sm text-muted-foreground">Le {DATE_DEPOT_DEMO} · {fichiersDemo.length} fichiers</p>
        <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fichier</TableHead>
                <TableHead>Reconnu comme</TableHead>
                <TableHead className="text-right">Lignes importées</TableHead>
                <TableHead>Remarques</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {fichiersDemo.map((b: BilanFichier) => (
                <TableRow key={b.fichier}>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      {ICONE_STATUT[b.statut]}
                      <span className="font-medium">{b.fichier}</span>
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{b.format ?? "Non reconnu"}</TableCell>
                  <TableCell className="text-right tabular-nums">{nombre(b.lignes_importees)}</TableCell>
                  <TableCell className="max-w-sm whitespace-normal text-xs text-muted-foreground">
                    {b.messages[0] ?? "—"}
                    {b.lignes_ignorees > 1 ? ` (+${b.lignes_ignorees - 1} autre)` : ""}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </>
  );
}
