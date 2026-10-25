"use client";

// Carte des recettes par pays, lues dans les relevés du client. Rien n'est estimé :
// un pays sans relevé reste gris. Plus le vert est soutenu, plus le pays rapporte.
import { useMemo, useState } from "react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import monde from "world-atlas/countries-110m.json";
import pays from "i18n-iso-countries";
import fr from "i18n-iso-countries/langs/fr.json";
import { euros, nombre } from "@/lib/format";
import type { RevenuPays } from "@/lib/types";

pays.registerLocale(fr);

const LARGEUR = 960;
const HAUTEUR = 470;
const topo = monde as unknown as Topology<{ countries: GeometryCollection<{ name: string }> }>;
const formes = feature(topo, topo.objects.countries).features;
const projection = geoNaturalEarth1().fitSize([LARGEUR, HAUTEUR], { type: "FeatureCollection", features: formes });
const chemin = geoPath(projection);

const nomPays = (code: string) => pays.getName(code, "fr") ?? code;

export function CartePays({ donnees }: { donnees: RevenuPays[] }) {
  const [survol, setSurvol] = useState<string | null>(null);
  const parCode = useMemo(() => new Map(donnees.filter((d) => d.montant > 0).map((d) => [d.pays, d])), [donnees]);
  const max = Math.max(1, ...[...parCode.values()].map((d) => d.montant));
  const total = [...parCode.values()].reduce((s, d) => s + d.montant, 0);
  // Échelle logarithmique : la France écrase sinon tous les autres pays
  const intensite = (m: number) => Math.round((0.15 + 0.85 * (Math.log10(1 + m) / Math.log10(1 + max))) * 1000) / 1000;
  const actif = survol ? parCode.get(survol) : null;

  if (parCode.size === 0) {
    return (
      <p className="rounded-xl border border-dashed border-border px-6 py-10 text-center text-sm text-muted-foreground">
        Les relevés déposés n&apos;indiquent pas de pays. La carte se remplira avec des relevés détaillés (distributeur, SACEM par source).
      </p>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_16rem]">
      <div className="relative rounded-xl bg-card p-3 ring-1 ring-foreground/10">
        <svg viewBox={`0 0 ${LARGEUR} ${HAUTEUR}`} className="h-auto w-full" role="img" aria-label="Carte des recettes par pays">
          {formes.map((f) => {
            const code = pays.numericToAlpha2(String(f.id ?? "").padStart(3, "0"));
            const d = code ? parCode.get(code) : undefined;
            return (
              <path
                key={String(f.id) + f.properties.name}
                d={chemin(f) ?? undefined}
                onMouseEnter={() => setSurvol(code ?? null)}
                onMouseLeave={() => setSurvol(null)}
                className="stroke-background stroke-[0.5] transition-opacity"
                style={{ fill: d ? "var(--primary)" : "var(--muted)", fillOpacity: d ? intensite(d.montant) : 1, opacity: survol && survol !== code ? 0.85 : 1 }}
              >
                <title>{d ? `${nomPays(code!)} : ${euros(d.montant)}` : `${f.properties.name} : pas de relevé`}</title>
              </path>
            );
          })}
        </svg>
        <div className="pointer-events-none absolute top-4 left-4 rounded-lg bg-background/85 px-3 py-2 text-sm ring-1 ring-foreground/10">
          {actif ? (
            <>
              <p className="font-medium">{nomPays(actif.pays)}</p>
              <p className="tabular-nums text-primary">{euros(actif.montant)}</p>
              <p className="text-xs text-muted-foreground">{nombre(actif.quantite)} écoutes ou ventes · {(actif.montant / total * 100).toFixed(1).replace(".", ",")} %</p>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">Survolez un pays</p>
          )}
        </div>
        <div className="mt-2 flex items-center gap-2 px-1 text-xs text-muted-foreground">
          <span className="inline-block size-3 rounded-sm bg-muted" /> Pas de relevé
          <span className="ml-3">Moins</span>
          <span className="h-2 w-24 rounded-full" style={{ background: "linear-gradient(to right, color-mix(in oklab, var(--primary) 15%, transparent), var(--primary))" }} />
          <span>Plus</span>
        </div>
      </div>

      <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <p className="text-xs text-muted-foreground">{parCode.size} pays · {euros(total)}</p>
        <ol className="mt-3 space-y-1.5 text-sm">
          {[...parCode.values()].sort((a, b) => b.montant - a.montant).slice(0, 12).map((d) => (
            <li key={d.pays} className="flex justify-between gap-3" onMouseEnter={() => setSurvol(d.pays)} onMouseLeave={() => setSurvol(null)}>
              <span className="truncate">{nomPays(d.pays)}</span>
              <span className="shrink-0 tabular-nums text-muted-foreground">{euros(d.montant)}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
