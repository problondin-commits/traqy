"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRing, ClipboardCheck, FileText, Library, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import { CLIENT_DEMO, fuitesDemo, manquesDemo } from "@/lib/demo";

const ECRANS = [
  { href: "/depot", libelle: "Dépôt", icone: Upload },
  { href: "/manques", libelle: "Contrôle des manques", icone: ClipboardCheck, compteur: manquesDemo.length },
  { href: "/catalogue", libelle: "Catalogue", icone: Library },
  { href: "/alertes", libelle: "Alertes", icone: BellRing, compteur: fuitesDemo.length },
  { href: "/rapports", libelle: "Rapports", icone: FileText },
];

export function BarreLaterale() {
  const chemin = usePathname();
  return (
    <aside className="flex shrink-0 flex-col border-b border-border bg-card/40 md:sticky md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0">
      <div className="flex items-center justify-between px-5 py-4 md:py-6">
        <Link href="/depot" aria-label="Traqy, accueil">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/traqy-logo.svg" alt="Traqy" className="h-7 w-auto" />
        </Link>
      </div>
      <div className="hidden px-5 pb-4 md:block">
        <p className="text-xs text-muted-foreground">Client</p>
        <p className="text-sm font-medium">{CLIENT_DEMO}</p>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-0">
        {ECRANS.map(({ href, libelle, icone: Icone, compteur }) => {
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
      <div className="mt-auto hidden p-5 md:block">
        <div className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Mode démo.</span> Toutes les données affichées sont fictives.
        </div>
      </div>
    </aside>
  );
}
