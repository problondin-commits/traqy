"use client";

// Carte des recettes par pays, reprise de l'ancienne carte WpointM : traits depuis Paris, points par pays,
// zones (Monde, Europe, Afrique, Amériques, Asie) et fiche détaillée au toucher d'un pays.
// Tout vient des relevés du client : aucun barème. Seul le mode Projection est une estimation.
import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import monde from "world-atlas/countries-110m.json";
import pays from "i18n-iso-countries";
import fr from "i18n-iso-countries/langs/fr.json";
import { euros, nombre } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RevenuPays } from "@/lib/types";

pays.registerLocale(fr);

const LARGEUR = 960;
const HAUTEUR = 470;
const topo = monde as unknown as Topology<{ countries: GeometryCollection<{ name: string }> }>;
const formes = feature(topo, topo.objects.countries).features.filter((f) => f.properties.name !== "Antarctica");
const projection = geoNaturalEarth1().fitSize([LARGEUR, HAUTEUR], { type: "FeatureCollection", features: formes });
const chemin = geoPath(projection);
const codeDe = (f: (typeof formes)[number]) => pays.numericToAlpha2(String(f.id ?? "").padStart(3, "0")) ?? "";
const CHEMINS = formes.map((f) => ({ code: codeDe(f), nom: f.properties.name, d: chemin(f) ?? "" }));
const nomPays = (code: string) => pays.getName(code, "fr") ?? code;

// Centre de chaque pays, corrigé pour les pays aux territoires éloignés. Les traits partent de Paris.
const point = (lon: number, lat: number) => projection([lon, lat]) as [number, number];
const PARIS = point(2.35, 48.86);
const CORRECTIONS: Record<string, [number, number]> = { FR: PARIS, US: point(-98, 39), CA: point(-102, 57), RU: point(90, 60), NO: point(9, 61), NL: point(5.3, 52.2) };
const CENTRES = new Map<string, [number, number]>(
  formes.flatMap((f) => (codeDe(f) ? [[codeDe(f), CORRECTIONS[codeDe(f)] ?? (chemin.centroid(f) as [number, number])]] : [])),
);

// Zones : cadrage de la carte sur une région (longitudes et latitudes), comme les vues de WpointM
type Zone = "monde" | "europe" | "afrique" | "ameriques" | "asie";
const ZONES: { id: Zone; nom: string; lon?: [number, number]; lat?: [number, number] }[] = [
  { id: "monde", nom: "Monde" },
  { id: "europe", nom: "Europe", lon: [-25, 45], lat: [34, 71] },
  { id: "afrique", nom: "Afrique", lon: [-20, 55], lat: [-36, 38] },
  { id: "ameriques", nom: "Amériques", lon: [-170, -30], lat: [-56, 72] },
  { id: "asie", nom: "Asie", lon: [25, 150], lat: [-12, 60] },
];
type Cadre = { x: number; y: number; l: number; h: number };
const CADRES = Object.fromEntries(ZONES.map((z) => {
  if (!z.lon || !z.lat) return [z.id, { x: 0, y: 0, l: LARGEUR, h: HAUTEUR }];
  const pts: [number, number][] = [];
  for (let i = 0; i <= 20; i++) {
    const lo = z.lon[0] + ((z.lon[1] - z.lon[0]) * i) / 20, la = z.lat[0] + ((z.lat[1] - z.lat[0]) * i) / 20;
    pts.push(point(lo, z.lat[0]), point(lo, z.lat[1]), point(z.lon[0], la), point(z.lon[1], la));
  }
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x = Math.min(...xs) - 8, y = Math.min(...ys) - 8;
  return [z.id, { x, y, l: Math.max(...xs) + 8 - x, h: Math.max(...ys) + 8 - y }];
})) as Record<Zone, Cadre>;
const dansCadre = ([x, y]: [number, number], c: Cadre) => x >= c.x && x <= c.x + c.l && y >= c.y && y <= c.y + c.h;

const TRAITS_MAX = 20; // au-delà, la carte devient illisible
const r1 = (v: number) => Math.round(v * 10) / 10;
function trait([x1, y1]: [number, number], [x2, y2]: [number, number]) {
  const l = Math.hypot(x2 - x1, y2 - y1);
  return `M${r1(x1)},${r1(y1)} Q${r1((x1 + x2) / 2)},${r1((y1 + y2) / 2 - l * 0.3)} ${r1(x2)},${r1(y2)}`;
}
const pc = (v: number) => `${(v * 100).toFixed(1).replace(".", ",")} %`;
const taux = (v: number) => `${v.toFixed(2).replace(".", ",")} €`;

type Mode = "recettes" | "taux" | "projection";

export function CartePays({ donnees, avenir, horizon }: { donnees: RevenuPays[]; avenir?: number; horizon?: number }) {
  const [survol, setSurvol] = useState<string | null>(null);
  const [choisi, setChoisi] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("recettes");
  const [zone, setZone] = useState<Zone>("monde");
  const projetable = avenir !== undefined && avenir > 0;

  // Valeur affichée de chaque pays selon le mode
  const parCode = useMemo(() => {
    const base = (d: RevenuPays) => Math.max(d.recent ?? d.montant, 0);
    const totalRecent = donnees.reduce((s, d) => s + base(d), 0);
    const valeur = (d: RevenuPays) =>
      mode === "taux" ? d.pour_1000 ?? 0 : mode === "projection" && projetable && totalRecent > 0 ? (base(d) / totalRecent) * avenir! : d.montant;
    return new Map(donnees.map((d) => [d.pays, { ...d, valeur: valeur(d), projete: projetable && totalRecent > 0 ? (base(d) / totalRecent) * avenir! : null }]));
  }, [donnees, mode, projetable, avenir]);
  const visibles = [...parCode.values()].filter((d) => d.valeur > (mode === "taux" ? 0 : 0.5));
  const max = Math.max(1e-9, ...visibles.map((d) => d.valeur));
  const totalRecettes = donnees.reduce((s, d) => s + Math.max(d.montant, 0), 0);
  const intensite = (v: number) => Math.round((0.15 + 0.85 * (mode === "taux" ? v / max : Math.log10(1 + v) / Math.log10(1 + max))) * 1000) / 1000;

  const cadre = CADRES[zone];
  const k = cadre.l / LARGEUR; // échelle du zoom : les points et les traits gardent leur taille à l'écran
  const destinations = visibles
    .filter((d) => d.pays !== "FR" && CENTRES.has(d.pays) && dansCadre(CENTRES.get(d.pays)!, cadre))
    .sort((a, b) => b.valeur - a.valeur).slice(0, TRAITS_MAX);
  const maxDest = Math.max(1e-9, ...destinations.map((d) => d.valeur));
  const liste = visibles.filter((d) => zone === "monde" || (CENTRES.has(d.pays) && dansCadre(CENTRES.get(d.pays)!, cadre)))
    .sort((a, b) => b.valeur - a.valeur);
  const fiche = choisi ? parCode.get(choisi) : null;
  const affichage = (v: number) => (mode === "taux" ? taux(v) : euros(v));

  if (donnees.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-border px-6 py-10 text-center text-sm text-muted-foreground">
        Les relevés déposés n&apos;indiquent pas de pays. La carte se remplira avec des relevés détaillés (distributeur, SACEM par source).
      </p>
    );
  }

  const onglet = (actif: boolean) => cn("rounded-md px-3 py-1 text-sm", actif ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground");
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex flex-wrap rounded-lg bg-card p-1 ring-1 ring-foreground/10" role="group" aria-label="Ce que montre la carte">
          <button type="button" className={onglet(mode === "recettes")} aria-pressed={mode === "recettes"} onClick={() => setMode("recettes")}>Recettes</button>
          {projetable && <button type="button" className={onglet(mode === "projection")} aria-pressed={mode === "projection"} onClick={() => setMode("projection")}>Projection{horizon ? ` ${horizon} ans` : ""}</button>}
        </div>
        <div className="inline-flex flex-wrap rounded-lg bg-muted p-1" role="group" aria-label="Zone de la carte">
          {ZONES.map((z) => (
            <button key={z.id} type="button" aria-pressed={zone === z.id} onClick={() => setZone(z.id)}
              className={cn("rounded-md px-2.5 py-1 text-xs", zone === z.id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}>
              {z.nom}
            </button>
          ))}
        </div>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">
        {mode === "recettes" && "Ce que chaque pays a rapporté, lu dans les relevés. Traits depuis Paris vers les pays qui rapportent le plus. Touchez un pays pour sa fiche."}
        {mode === "taux" && "Ce que rapportent réellement 1 000 écoutes en streaming dans chaque pays, part du client, calculé sur ses relevés (pays d'au moins 1 000 écoutes)."}
        {mode === "projection" && `Estimation : les ${euros(avenir!)} à venir répartis selon la part de chaque pays sur les 12 derniers mois relevés. On suppose que cette répartition reste la même.`}
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_17rem]">
        <div className="relative min-w-0 rounded-xl bg-card p-3 ring-1 ring-foreground/10">
          <svg viewBox={`${r1(cadre.x)} ${r1(cadre.y)} ${r1(cadre.l)} ${r1(cadre.h)}`} className="h-auto max-h-[28rem] w-full" role="img" aria-label="Carte des recettes par pays">
            {CHEMINS.map(({ code, nom, d: dessin }) => {
              const d = code ? parCode.get(code) : undefined;
              const actif = d && d.valeur > (mode === "taux" ? 0 : 0.5);
              return (
                <path key={code + nom} d={dessin} vectorEffect="non-scaling-stroke"
                  onMouseEnter={() => setSurvol(code || null)} onMouseLeave={() => setSurvol(null)}
                  onClick={() => actif && setChoisi(code)}
                  className={cn("stroke-background stroke-[0.6] transition-opacity", actif && "cursor-pointer")}
                  style={{ fill: actif ? "var(--primary)" : "var(--muted)", fillOpacity: actif ? intensite(d.valeur) : 1, opacity: survol && survol !== code ? 0.85 : 1 }}>
                  <title>{actif ? `${nomPays(code)} : ${affichage(d.valeur)}${mode === "projection" ? " (estimation)" : ""}` : `${nom} : pas de relevé`}</title>
                </path>
              );
            })}
            {mode !== "taux" && destinations.map((d) => {
              const allume = survol === d.pays || choisi === d.pays;
              return (
                <path key={`t-${d.pays}`} d={trait(PARIS, CENTRES.get(d.pays)!)} fill="none" strokeLinecap="round" vectorEffect="non-scaling-stroke" pointerEvents="none"
                  style={{ stroke: allume ? "var(--primary)" : "var(--foreground)", strokeOpacity: allume ? 0.95 : 0.35, strokeWidth: r1(0.6 + 2.6 * Math.sqrt(d.valeur / maxDest)) }} />
              );
            })}
            {destinations.map((d) => {
              const [x, y] = CENTRES.get(d.pays)!;
              return (
                <circle key={`p-${d.pays}`} cx={r1(x)} cy={r1(y)} r={r1((2 + 5 * Math.sqrt(d.valeur / maxDest)) * k)}
                  onMouseEnter={() => setSurvol(d.pays)} onMouseLeave={() => setSurvol(null)} onClick={() => setChoisi(d.pays)}
                  style={{ fill: choisi === d.pays ? "var(--foreground)" : "var(--primary)", stroke: "var(--background)", strokeWidth: 1.2 * k, cursor: "pointer" }}>
                  <title>{`${nomPays(d.pays)} : ${affichage(d.valeur)}`}</title>
                </circle>
              );
            })}
            {dansCadre(PARIS, cadre) && (
              <g pointerEvents="none">
                <circle cx={r1(PARIS[0])} cy={r1(PARIS[1])} r={7 * k} style={{ fill: "var(--background)", stroke: "var(--primary)", strokeWidth: 2.5 * k }} />
                <circle cx={r1(PARIS[0])} cy={r1(PARIS[1])} r={3 * k} style={{ fill: "var(--primary)" }} />
              </g>
            )}
          </svg>
          {survol && parCode.get(survol) && (
            <div className="pointer-events-none absolute top-4 left-4 rounded-lg bg-background/85 px-3 py-2 text-sm ring-1 ring-foreground/10">
              <p className="font-medium">{nomPays(survol)}</p>
              <p className="tabular-nums text-primary">{affichage(parCode.get(survol)!.valeur)}</p>
            </div>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2 px-1 text-xs text-muted-foreground">
            <span className="inline-block size-3 rounded-sm bg-muted" /> Pas de relevé
            <span className="ml-3">Moins</span>
            <span className="h-2 w-24 rounded-full" style={{ background: "linear-gradient(to right, color-mix(in oklab, var(--primary) 15%, transparent), var(--primary))" }} />
            <span>Plus</span>
          </div>
        </div>

        {fiche ? (
          <div className="min-w-0 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-xs text-muted-foreground">Rang {fiche.rang ?? "—"} sur {donnees.length} pays</p>
                <p className="text-lg font-semibold">{nomPays(fiche.pays)}</p>
              </div>
              <button type="button" onClick={() => setChoisi(null)} aria-label="Fermer la fiche" className="rounded-md p-1 text-muted-foreground hover:text-foreground"><X className="size-4" /></button>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <dt className="text-muted-foreground">Recettes</dt><dd className="text-right tabular-nums">{euros(fiche.montant)}</dd>
              <dt className="text-muted-foreground">Part du total</dt><dd className="text-right tabular-nums">{totalRecettes ? pc(fiche.montant / totalRecettes) : "—"}</dd>
              <dt className="text-muted-foreground">Écoutes et ventes</dt><dd className="text-right tabular-nums">{nombre(fiche.quantite)}</dd>
              <dt className="text-muted-foreground">Pour 1 000 écoutes</dt><dd className="text-right tabular-nums">{fiche.pour_1000 ? taux(fiche.pour_1000) : "—"}</dd>
              {fiche.projete !== null && (<><dt className="text-muted-foreground">À venir{horizon ? `, ${horizon} ans` : ""}</dt><dd className="text-right tabular-nums">{euros(fiche.projete)} <span className="text-xs text-muted-foreground">est.</span></dd></>)}
            </dl>
            {[["Titres qui rapportent le plus", fiche.titres], ["Plateformes", fiche.plateformes]].map(([titre, lignes]) =>
              (lignes as RevenuPays["titres"])?.length ? (
                <div key={titre as string} className="mt-4">
                  <p className="mb-1 text-xs text-muted-foreground">{titre as string}</p>
                  <ol className="space-y-1 text-sm">
                    {(lignes as NonNullable<RevenuPays["titres"]>).map((l) => (
                      <li key={l.nom} className="flex justify-between gap-3"><span className="truncate">{l.nom}</span><span className="shrink-0 tabular-nums text-muted-foreground">{euros(l.montant)}</span></li>
                    ))}
                  </ol>
                </div>
              ) : null)}
          </div>
        ) : (
          <div className="min-w-0 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
            <p className="text-xs text-muted-foreground">
              {liste.length} pays{mode === "taux" ? " · les mieux payés pour 1 000 écoutes" : ` · ${euros(liste.reduce((s, d) => s + d.valeur, 0))}${mode === "projection" ? " à venir" : ""}`}
            </p>
            <ol className="mt-3 space-y-1.5 text-sm">
              {liste.slice(0, 12).map((d) => (
                <li key={d.pays}>
                  <button type="button" onClick={() => setChoisi(d.pays)} onMouseEnter={() => setSurvol(d.pays)} onMouseLeave={() => setSurvol(null)}
                    className="flex w-full justify-between gap-3 text-left hover:text-primary">
                    <span className="truncate">{nomPays(d.pays)}</span>
                    <span className="shrink-0 tabular-nums text-muted-foreground">{affichage(d.valeur)}</span>
                  </button>
                </li>
              ))}
            </ol>
            <p className="mt-3 text-xs text-muted-foreground">Touchez un pays pour voir sa fiche.</p>
          </div>
        )}
      </div>
    </>
  );
}
