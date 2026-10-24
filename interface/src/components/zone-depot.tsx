"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileSpreadsheet, Loader2, UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = { clientActuel: string | null; moteurBranche: boolean };

export function ZoneDepot({ clientActuel, moteurBranche }: Props) {
  const router = useRouter();
  const champ = useRef<HTMLInputElement>(null);
  const [survol, setSurvol] = useState(false);
  const [fichiers, setFichiers] = useState<File[]>([]);
  const [client, setClient] = useState(clientActuel ?? "");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const ajouter = (liste: FileList | null) => {
    if (liste) setFichiers((avant) => [...avant, ...Array.from(liste)]);
  };

  const envoyer = async () => {
    setEnvoi(true);
    setErreur(null);
    const formulaire = new FormData();
    formulaire.append("client", client.trim());
    fichiers.forEach((f) => formulaire.append("fichiers", f, f.name));
    try {
      const reponse = await fetch("/api/depot", { method: "POST", body: formulaire });
      const resultat = await reponse.json();
      if (!reponse.ok) throw new Error(resultat.erreur ?? "L'import a échoué.");
      setFichiers([]);
      router.push("/manques");
      router.refresh();
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "L'import a échoué.");
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <>
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
        <span className="text-sm text-muted-foreground">Catalogue, relevés SACEM, relevés du distributeur, soldes des éditeurs (CSV, Excel ou ZIP)</span>
      </button>
      <input ref={champ} type="file" multiple accept=".csv,.tsv,.xlsx,.xlsm,.zip" className="hidden" onChange={(e) => { ajouter(e.target.files); e.target.value = ""; }} />

      {fichiers.length > 0 && (
        <div className="mt-4 rounded-xl bg-card p-5 ring-1 ring-foreground/10">
          <ul className="mb-4 space-y-1">
            {fichiers.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-2 text-sm">
                <FileSpreadsheet className="size-4 text-muted-foreground" />
                <span className="flex-1 truncate">{f.name}</span>
                <button type="button" aria-label={`Retirer ${f.name}`} onClick={() => setFichiers((x) => x.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-foreground">
                  <X className="size-4" />
                </button>
              </li>
            ))}
          </ul>
          {moteurBranche ? (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="flex-1">
                <span className="text-xs text-muted-foreground">Nom du client (artiste, label ou éditeur)</span>
                <input
                  value={client}
                  onChange={(e) => setClient(e.target.value)}
                  placeholder="Par exemple : Luidji"
                  className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                />
              </label>
              <Button size="lg" disabled={envoi || !client.trim()} onClick={envoyer}>
                {envoi ? <><Loader2 className="animate-spin" /> Import et contrôle en cours…</> : "Importer et contrôler"}
              </Button>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Mode démo : ces fichiers ne sont pas envoyés.</p>
          )}
          {erreur && <p className="mt-3 rounded-lg bg-destructive/15 px-4 py-2 text-sm text-destructive">{erreur}</p>}
        </div>
      )}
    </>
  );
}
