"use client";

import { useState } from "react";
import { euros } from "@/lib/format";
import type { MoisMontant } from "@/lib/types";

// Une seule série (le chiffre d'affaires mensuel) en deux états : relevé (barres pleines) et prévision (barres hachurées).
// Vert de la charte : #31F2A4 (logo) en mode sombre, #10A06A en mode clair (variable --primary de globals.css).
const VERT = "var(--primary)";
const MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const libelleMois = (m: string) => `${MOIS[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}`;
const compact = (v: number) => new Intl.NumberFormat("fr-FR", { notation: "compact", maximumFractionDigits: 1 }).format(v) + " €";

export function GraphiqueProjection({ historique, prevision }: { historique: MoisMontant[]; prevision: MoisMontant[] }) {
  const barres = [
    ...historique.map((m) => ({ ...m, prevu: false })),
    ...prevision.map((m) => ({ ...m, prevu: true })),
  ];
  const [survol, setSurvol] = useState<number | null>(null);
  const L = 900, H = 260, G = 72, B = 30, Hh = 12; // largeur, hauteur, marge gauche, marge basse, marge haute
  const max = Math.max(...barres.map((b) => b.valeur), 1);
  const pas = (L - G) / barres.length;
  const largeur = Math.max(1, pas - 2); // 2 px d'écart entre les barres
  const y = (v: number) => H - B - (v / max) * (H - B - Hh);
  const graduations = [0, max / 2, max];
  const separation = G + historique.length * pas;
  const actif = survol !== null ? barres[survol] : null;

  return (
    <figure className="rounded-xl bg-card p-5 ring-1 ring-foreground/10">
      <figcaption className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm font-medium">Chiffre d&apos;affaires mensuel</span>
        <span className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="inline-block size-3 rounded-sm" style={{ background: VERT }} /> Relevé</span>
          <span className="flex items-center gap-1.5">
            <svg className="size-3" viewBox="0 0 12 12" aria-hidden><rect width="12" height="12" rx="2" fill="url(#hachures)" style={{ stroke: VERT }} /></svg>
            Prévision (estimation)
          </span>
        </span>
      </figcaption>
      <div className="relative">
        <svg viewBox={`0 0 ${L} ${H}`} className="h-auto w-full" role="img" aria-label="Chiffre d'affaires mensuel relevé puis prévu">
          <defs>
            <pattern id="hachures" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="6" height="6" style={{ fill: VERT }} fillOpacity="0.18" />
              <line x1="0" y1="0" x2="0" y2="6" style={{ stroke: VERT }} strokeWidth="2" />
            </pattern>
          </defs>
          {graduations.map((g) => (
            <g key={g}>
              <line x1={G} x2={L} y1={y(g)} y2={y(g)} stroke="currentColor" className="text-border" strokeWidth="1" />
              <text x={G - 8} y={y(g) + 4} textAnchor="end" className="fill-muted-foreground text-[14px]">{compact(g)}</text>
            </g>
          ))}
          {barres.map((b, i) => {
            const x = G + i * pas + 1;
            const haut = Math.max(0, H - B - y(b.valeur));
            const rayon = Math.min(4, largeur / 2, haut);
            // barre arrondie seulement en haut, posée sur l'axe
            const chemin = `M${x},${H - B} V${H - B - haut + rayon} Q${x},${H - B - haut} ${x + rayon},${H - B - haut} H${x + largeur - rayon} Q${x + largeur},${H - B - haut} ${x + largeur},${H - B - haut + rayon} V${H - B} Z`;
            return (
              <path key={b.mois} d={chemin} style={{ fill: b.prevu ? "url(#hachures)" : VERT }}
                opacity={survol === null || survol === i ? 1 : 0.55} />
            );
          })}
          {/* séparation entre le relevé et la prévision */}
          <line x1={separation} x2={separation} y1={Hh} y2={H - B} stroke="currentColor" className="text-muted-foreground" strokeDasharray="3 3" />
          <text x={separation + 6} y={Hh + 10} className="fill-muted-foreground text-[14px]">prévision →</text>
          {/* une étiquette en janvier, une année sur N pour garder au moins 48 px entre deux étiquettes */}
          {barres
            .map((b, i) => ({ annee: b.mois.slice(0, 4), x: G + i * pas, debut: b.mois.endsWith("-01") }))
            .filter((e) => e.debut && Number(e.annee) % Math.max(1, Math.ceil(48 / (12 * pas))) === 0)
            .map((e) => (
              <text key={`a-${e.annee}`} x={e.x} y={H - 8} className="fill-muted-foreground text-[14px]">{e.annee}</text>
            ))}
          {/* zones de survol plus larges que les barres */}
          {barres.map((b, i) => (
            <rect key={`z-${b.mois}`} x={G + i * pas} y={Hh} width={pas} height={H - B - Hh} fill="transparent"
              onMouseEnter={() => setSurvol(i)} onMouseLeave={() => setSurvol(null)} />
          ))}
        </svg>
        {actif && (
          <div className="pointer-events-none absolute top-0 rounded-lg bg-popover px-3 py-2 text-xs shadow-lg ring-1 ring-foreground/10"
            style={{ left: `${Math.min(80, ((G + (survol ?? 0) * pas) / L) * 100)}%` }}>
            <p className="font-medium">{libelleMois(actif.mois)}</p>
            <p className="tabular-nums">{euros(actif.valeur)}</p>
            <p className="text-muted-foreground">{actif.prevu ? "Prévision (estimation)" : "Relevé"}</p>
          </div>
        )}
      </div>
    </figure>
  );
}
