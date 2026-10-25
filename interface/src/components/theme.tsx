"use client";

// Thème de l'interface : sombre (charte Traqy, par défaut), clair, ou automatique (selon le réglage de l'appareil).
// Le choix est gardé dans le navigateur.
import { useSyncExternalStore, type ReactNode } from "react";
import { ThemeProvider, useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

export function Theme({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange storageKey="traqy-theme">
      {children}
    </ThemeProvider>
  );
}

/** Logo Traqy : texte blanc cassé sur fond sombre, texte nuit sur fond clair. */
export function Logo({ className }: { className?: string }) {
  return (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/traqy-logo.svg" alt="Traqy" className={cn("hidden dark:block", className)} />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/traqy-logo-clair.svg" alt="Traqy" className={cn("dark:hidden", className)} />
    </>
  );
}

const CHOIX = [
  { valeur: "dark", libelle: "Sombre", icone: Moon },
  { valeur: "light", libelle: "Clair", icone: Sun },
  { valeur: "system", libelle: "Auto", icone: Monitor },
] as const;

const pret = () => () => {};

export function ChoixTheme({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useTheme();
  // Le choix enregistré n'est connu que dans le navigateur : rien n'est surligné avant.
  const monte = useSyncExternalStore(pret, () => true, () => false);
  if (compact) {
    // Téléphone : un seul bouton qui passe de Sombre à Clair puis à Auto
    const i = Math.max(0, CHOIX.findIndex((c) => c.valeur === theme));
    const actuel = monte ? CHOIX[i] : CHOIX[0];
    const suivant = CHOIX[(i + 1) % CHOIX.length];
    const Icone = actuel.icone;
    return (
      <button type="button" onClick={() => setTheme(suivant.valeur)} aria-label={`Thème : ${actuel.libelle}. Passer en ${suivant.libelle}`}
        className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground hover:text-foreground">
        <Icone className="size-4" />
      </button>
    );
  }
  return (
    <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted p-1" role="group" aria-label="Thème de l'interface">
      {CHOIX.map(({ valeur, libelle, icone: Icone }) => {
        const actif = monte && theme === valeur;
        return (
          <button
            key={valeur}
            type="button"
            onClick={() => setTheme(valeur)}
            aria-pressed={actif}
            className={cn("flex items-center justify-center gap-1 rounded-md px-1.5 py-1 text-xs transition-colors",
              actif ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}
          >
            <Icone className="size-3.5" /> {libelle}
          </button>
        );
      })}
    </div>
  );
}
