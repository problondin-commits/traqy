// Éléments d'écran partagés : en-tête de page, tuile chiffrée, pastille de gravité.
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { Gravite } from "@/lib/types";

export function EnTete({ titre, description, action }: { titre: string; description: string; action?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{titre}</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function Tuile({ libelle, valeur, detail, accent }: { libelle: string; valeur: string; detail?: string; accent?: boolean }) {
  return (
    <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <p className="text-xs text-muted-foreground">{libelle}</p>
      <p className={cn("mt-1 text-2xl font-semibold tabular-nums", accent && "text-primary")}>{valeur}</p>
      {detail ? <p className="mt-1 text-xs text-muted-foreground">{detail}</p> : null}
    </div>
  );
}

const STYLE_GRAVITE: Record<Gravite, string> = {
  bloquant: "bg-destructive/15 text-destructive",
  important: "bg-warning/15 text-warning",
  "à compléter": "bg-muted text-muted-foreground",
};

export function PastilleGravite({ gravite }: { gravite: Gravite }) {
  return (
    <span className={cn("inline-flex h-5 items-center rounded-full px-2 text-xs font-medium capitalize", STYLE_GRAVITE[gravite])}>
      {gravite}
    </span>
  );
}
