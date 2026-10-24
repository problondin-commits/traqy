import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { BarreLaterale } from "@/components/barre-laterale";
import { TooltipProvider } from "@/components/ui/tooltip";
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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col md:flex-row">
        <TooltipProvider>
          <BarreLaterale />
          <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:px-12">
            <div className="mx-auto max-w-6xl">{children}</div>
          </main>
        </TooltipProvider>
      </body>
    </html>
  );
}
