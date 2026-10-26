"use client";

import { useTransition } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRing, ClipboardCheck, FileText, Library, Loader2, TrendingUp, Upload } from "lucide-react";
import { ChoixTheme, Logo } from "@/components/theme";
import { cn } from "@/lib/utils";
import { choisirClient } from "@/lib/actions";
import type { Choix } from "@/lib/donnees";

// verrouille : accès client ou démo, le menu Client est remplacé par le nom du dossier (pas de changement possible)
type Props = { choix: Choix[]; actuel: string; demo: boolean; manques: number; alertes: number; verrouille?: boolean };

/** Barre affichée pendant le chargement de la liste des clients. */
export function BarreSquelette() {
  return (
    <aside className="hidden shrink-0 flex-col border-r border-border bg-card/40 md:sticky md:top-0 md:flex md:h-screen md:w-64">
      <div className="px-5 py-4 md:py-6">
        <Logo className="h-7 w-auto" />
      </div>
      <div className="space-y-2 px-5">
        {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-8 animate-pulse rounded-lg bg-muted/60" />)}
      </div>
    </aside>
  );
}

export function BarreLaterale({ choix, actuel, demo, manques, alertes, verrouille = false }: Props) {
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
  const menuClient = verrouille ? (
    <p className="truncate rounded-lg border border-input bg-card px-2 py-1.5 text-sm font-medium md:mt-1">
      {choix.find((c) => c.valeur === actuel)?.libelle ?? "—"}
    </p>
  ) : (
    <select
      value={actuel}
      disabled={enCours}
      aria-label="Client"
      onChange={(e) => {
        const valeur = e.target.value;
        demarrer(() => choisirClient(valeur));
      }}
      className="w-full rounded-lg border border-input bg-card px-2 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring/50 md:mt-1"
    >
      {choix.map((c) => (
        <option key={c.valeur} value={c.valeur}>{c.libelle}</option>
      ))}
    </select>
  );
  return (
    <>
    {/* Téléphone : en-tête compact (logo, client, thème) ; les écrans sont dans la barre d'onglets en bas */}
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-background/90 px-4 py-2.5 backdrop-blur md:hidden">
      <Link href="/depot" aria-label="Traqy, accueil" className="shrink-0"><Logo className="h-6 w-auto" /></Link>
      <div className="min-w-0 flex-1">{menuClient}</div>
      {enCours ? <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" /> : <ChoixTheme compact />}
    </header>
    <OngletsTelephone chemin={chemin} alertes={alertes} />

    <aside className="hidden shrink-0 flex-col border-r border-border bg-card/40 md:sticky md:top-0 md:flex md:h-screen md:w-64">
      <div className="flex items-center justify-between gap-3 px-5 py-6">
        <Link href="/depot" aria-label="Traqy, accueil">
          <Logo className="h-7 w-auto" />
        </Link>
        {enCours && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
      </div>
      <label className="block px-5 pb-4">
        <span className="text-xs text-muted-foreground">Client</span>
        {menuClient}
      </label>
      <nav className="flex flex-col gap-1 px-3">
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
      <div className="mt-auto space-y-3 p-5">
        {demo && (
          <div className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Mode démo.</span> Toutes les données affichées sont fictives.
          </div>
        )}
        <ChoixTheme />
      </div>
    </aside>
    </>
  );
}

// Barre d'onglets du téléphone, fixée en bas de l'écran, à portée de pouce (comme dans la maquette).
// Le contrôle des manques reste accessible depuis l'écran Dépôt.
const ONGLETS = [
  { href: "/depot", libelle: "Dépôt", icone: Upload },
  { href: "/catalogue", libelle: "Catalogue", icone: Library },
  { href: "/alertes", libelle: "Alertes", icone: BellRing },
  { href: "/projection", libelle: "Projection", icone: TrendingUp },
  { href: "/rapports", libelle: "Rapports", icone: FileText },
];

function OngletsTelephone({ chemin, alertes }: { chemin: string; alertes: number }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-card/95 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-1.5 backdrop-blur md:hidden">
      {ONGLETS.map(({ href, libelle, icone: Icone }) => {
        const actif = chemin.startsWith(href) || (href === "/depot" && chemin.startsWith("/manques"));
        return (
          <Link key={href} href={href} aria-current={actif ? "page" : undefined}
            className={cn("relative flex flex-col items-center gap-0.5 py-1 text-[11px]", actif ? "text-primary" : "text-muted-foreground")}>
            <Icone className="size-5" />
            {libelle}
            {href === "/alertes" && alertes > 0 && (
              <span className="absolute top-0 left-1/2 ml-2 rounded-full bg-primary px-1.5 text-[10px] leading-4 text-primary-foreground tabular-nums">{alertes}</span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
