import { Suspense } from "react";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { BarreLaterale, BarreSquelette } from "@/components/barre-laterale";
import { TooltipProvider } from "@/components/ui/tooltip";
import { chargerDonnees } from "@/lib/donnees";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Traqy",
  description: "Retrouvez les droits non perçus de votre catalogue.",
};

// Toutes les pages dépendent du client choisi et des données du moteur : elles ne peuvent pas être préparées à l'avance.
// Les écrans d'attente (Suspense, loading.tsx) s'affichent pendant le chargement.
export const instant = false;

// La barre de gauche attend la liste des clients ; le reste de la page s'affiche sans l'attendre.
async function BarreAvecDonnees() {
  const d = await chargerDonnees();
  return (
    <BarreLaterale
      choix={d.choix}
      actuel={d.actuel}
      demo={d.demo}
      manques={d.vue?.manques.length ?? 0}
      alertes={d.vue?.fuites.length ?? 0}
    />
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col md:flex-row">
        <TooltipProvider>
          <Suspense fallback={<BarreSquelette />}>
            <BarreAvecDonnees />
          </Suspense>
          <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:px-12">
            <div className="mx-auto max-w-6xl">{children}</div>
          </main>
        </TooltipProvider>
      </body>
    </html>
  );
}
