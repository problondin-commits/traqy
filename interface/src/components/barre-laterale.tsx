"use client";

import { useTransition } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRing, ClipboardCheck, FileText, Library, Loader2, TrendingUp, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import { choisirClient } from "@/lib/actions";
import type { Choix } from "@/lib/donnees";

type Props = { choix: Choix[]; actuel: string; demo: boolean; manques: number; alertes: number };

/** Barre affichée pendant le chargement de la liste des clients. */
export function BarreSquelette() {
  return (
    <aside className="flex shrink-0 flex-col border-b border-border bg-card/40 md:sticky md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0">
      <div className="px-5 py-4 md:py-6">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/traqy-logo.svg" alt="Traqy" className="h-7 w-auto" />
      </div>
      <div className="space-y-2 px-5">
        {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-8 animate-pulse rounded-lg bg-muted/60" />)}
      </div>
    </aside>
  );
}

export function BarreLaterale({ choix, actuel, demo, manques, alertes }: Props) {
  const chemin = usePathname();
  const [enCours, demarrer] = useTransition();
  const ecrans = [
    { href: "/depot", libelle: "Dépôt", icone: Upload },
    { href: "/manques", libelle: "Contrôle des manques", icone: ClipboardCheck, compteur: manques },
    { href: "/catalogue", libelle: "Catalogue", icone: Library },
    { href: "/alertes", libelle: "Alertes", icone: BellRing, compteur: alertes },
    { href: "/projection", libelle: "Projection", icone: TrendingUp },
    { href: "/rapports", libelle: "Rapports", icone: FileText },
  ];
  return (
    <aside className="flex shrink-0 flex-col border-b border-border bg-card/40 md:sticky md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0">
      <div className="flex items-center justify-between gap-3 px-5 py-4 md:py-6">
        <Link href="/depot" aria-label="Traqy, accueil">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/traqy-logo.svg" alt="Traqy" className="h-7 w-auto" />
        </Link>
        {enCours && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
      </div>
      <label className="block px-5 pb-4">
        <span className="text-xs text-muted-foreground">Client</span>
        <select
          value={actuel}
          disabled={enCours}
          onChange={(e) => {
            const valeur = e.target.value;
            demarrer(() => choisirClient(valeur));
          }}
          className="mt-1 w-full rounded-lg border border-input bg-card px-2 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          {choix.map((c) => (
            <option key={c.valeur} value={c.valeur}>{c.libelle}</option>
          ))}
        </select>
      </label>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-0">
        {ecrans.map(({ href, libelle, icone: Icone, compteur }) => {
          const actif = chemin.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex shrink-0 items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                actif ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icone className="size-4" />
              <span className="flex-1 whitespace-nowrap">{libelle}</span>
              {compteur ? (
                <span className={cn("rounded-full px-2 text-xs tabular-nums", actif ? "bg-primary text-primary-foreground" : "bg-muted text-foreground")}>
                  {compteur}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      {demo && (
        <div className="mt-auto hidden p-5 md:block">
          <div className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Mode démo.</span> Toutes les données affichées sont fictives.
          </div>
        </div>
      )}
    </aside>
  );
}
