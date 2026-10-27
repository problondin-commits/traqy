"use client";

import { useTransition } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRing, FileText, Library, Loader2, TrendingUp, Upload } from "lucide-react";
import { ChoixTheme, Logo } from "@/components/theme";
import { cn } from "@/lib/utils";
import { choisirClient } from "@/lib/actions";
import type { Choix } from "@/lib/donnees";

// verrouille : accès client ou démo, le menu Client est remplacé par le nom du dossier (pas de changement possible)
type Props = { choix: Choix[]; actuel: string; demo: boolean; manques: number; alertes: number; verrouille?: boolean };

// Design « Blocs » (choix de Tom, 27/10/2026) : une barre en haut avec le logo, les écrans en onglets arrondis,
// le client et le thème à droite. Sur téléphone, les écrans passent dans la barre d'onglets en bas.
const STYLE_BARRE = "sticky top-0 z-30 border-b border-foreground/10 bg-background/60 backdrop-blur-xl backdrop-saturate-150";

/** Barre affichée pendant le chargement de la liste des clients. */
export function BarreSquelette() {
  return (
    <header className={cn(STYLE_BARRE, "flex items-center gap-6 px-4 py-2.5 sm:px-8 md:py-3.5")}>
      <Logo className="h-6 w-auto" />
      <div className="hidden h-9 w-[34rem] animate-pulse rounded-full bg-muted/60 lg:block" />
      <div className="ml-auto h-8 w-40 animate-pulse rounded-lg bg-muted/60" />
    </header>
  );
}

export function BarreLaterale({ choix, actuel, demo, manques, alertes, verrouille = false }: Props) {
  const chemin = usePathname();
  const [enCours, demarrer] = useTransition();
  const ecrans = [
    { href: "/depot", libelle: "Dépôt" },
    { href: "/manques", libelle: "Manques", titre: "Contrôle des manques", compteur: manques },
    { href: "/catalogue", libelle: "Catalogue" },
    { href: "/alertes", libelle: "Alertes", compteur: alertes },
    { href: "/projection", libelle: "Projection" },
    { href: "/rapports", libelle: "Rapports" },
  ];
  const nomClient = choix.find((c) => c.valeur === actuel)?.libelle ?? "—";
  const menuClient = verrouille ? (
    <p className="truncate rounded-lg border border-input bg-card px-2 py-1.5 text-sm font-medium">{nomClient}</p>
  ) : (
    <select
      value={actuel}
      disabled={enCours}
      aria-label="Client"
      onChange={(e) => {
        const valeur = e.target.value;
        demarrer(() => choisirClient(valeur));
      }}
      className="w-full rounded-lg border border-input bg-card px-2 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
    >
      {choix.map((c) => (
        <option key={c.valeur} value={c.valeur}>{c.libelle}</option>
      ))}
    </select>
  );
  return (
    <>
    {/* Ordinateur : logo, onglets, client et thème sur une ligne (onglets sur une 2e ligne entre 768 et 1024 px).
        Téléphone : logo, client et thème ; les écrans sont dans la barre d'onglets en bas. */}
    <header className={cn(STYLE_BARRE, "flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-2.5 sm:px-8 md:py-3.5")}>
      <Link href="/depot" aria-label="Traqy, accueil" className="shrink-0"><Logo className="h-6 w-auto" /></Link>
      <nav aria-label="Écrans" className="order-last hidden w-full md:flex lg:order-none lg:w-auto">
        <div className="flex gap-1 rounded-full bg-card p-1 ring-1 ring-foreground/10">
          {ecrans.map(({ href, libelle, titre, compteur }) => {
            const actif = chemin.startsWith(href);
            return (
              <Link key={href} href={href} title={titre} aria-current={actif ? "page" : undefined}
                className={cn("flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm transition-colors",
                  actif ? "bg-primary font-semibold text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
                {libelle}
                {compteur ? (
                  <span className={cn("rounded-full px-1.5 text-[11px] leading-4 tabular-nums",
                    actif ? "bg-primary-foreground/15" : "bg-muted text-foreground")}>{compteur}</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </nav>
      <div className="ml-auto flex min-w-0 flex-1 items-center justify-end gap-3 md:flex-none">
        {demo && <span className="hidden rounded-full border border-dashed border-border px-2.5 py-1 text-xs text-muted-foreground sm:inline" title="Toutes les données affichées sont fictives.">Mode démo</span>}
        <span className="hidden text-sm text-muted-foreground xl:inline">Client</span>
        <div className="min-w-0 flex-1 md:w-44 md:flex-none">{menuClient}</div>
        {enCours ? <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" /> : <ChoixTheme compact />}
      </div>
    </header>
    <OngletsTelephone chemin={chemin} alertes={alertes} />
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
    <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-foreground/10 bg-card/60 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-1.5 backdrop-blur-xl backdrop-saturate-150 md:hidden">
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
