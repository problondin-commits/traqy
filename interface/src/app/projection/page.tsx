import { connection } from "next/server";
import { ChevronDown, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avances } from "@/components/avances";
import { CartePays } from "@/components/carte-pays";
import { EnTete, Indisponible, Tuile } from "@/components/elements";
import { GraphiqueProjection } from "@/components/graphique-projection";
import { ErreurMoteur, lireProjection, moteurConfigure, projeterCourbe } from "@/lib/api";
import { historiqueDemo, titresDemo } from "@/lib/demo";
import { chargerDonnees } from "@/lib/donnees";
import { euros } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Projection as TypeProjection, ReglagesProjection } from "@/lib/types";

const HORIZONS = [3, 5, 10, 15];
const ECART_PEU_FIABLE = 0.5; // au-delà de 50 % d'écart moyen au test sur le passé, la projection est signalée peu fiable
const kEuros = (v: number) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(v / 1000)} k€`;
const pc = (v: number) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(v * 100)} %`;

function lireReglages(p: Record<string, string | string[] | undefined>): ReglagesProjection & { horizon: number } {
  const nombre = (v: unknown, defaut: number, min: number, max: number) => {
    const n = Number(Array.isArray(v) ? v[0] : v);
    return Number.isFinite(n) && n >= min && n <= max ? n : defaut;
  };
  const horizon = nombre(p.horizon, 5, 1, 30);
  let baisse_min = nombre(p.baisse_min, 5, 1, 95) / 100;
  let baisse_max = nombre(p.baisse_max, 35, 1, 95) / 100;
  if (baisse_min > baisse_max) [baisse_min, baisse_max] = [baisse_max, baisse_min];
  const fourchette = p.fourchette === "manuelle" ? "manuelle" : "catalogue";
  const fin = new Date();
  fin.setFullYear(fin.getFullYear() + horizon);
  return { horizon, baisse_min, baisse_max, fourchette, fin: fin.toISOString().slice(0, 10) };
}

export default async function Projection({ searchParams }: PageProps<"/projection">) {
  await connection(); // la date de fin dépend du jour où la page est affichée
  const reglages = lireReglages(await searchParams);
  const { vue, demo, actuel, erreur: erreurDonnees } = await chargerDonnees();
  const entete = (
    <EnTete
      titre="Projection"
      description="Les revenus à venir, prolongés à partir de votre propre historique de relevés. Toujours une estimation : aucun taux par défaut."
    />
  );
  if (!vue) return <>{entete}<Indisponible message={erreurDonnees} /></>;

  let projection: TypeProjection | null = null;
  let erreur: string | null = null;
  if (!moteurConfigure()) {
    erreur = "La projection est calculée par le moteur, qui n'est pas branché ici.";
  } else {
    try {
      projection = demo ? await projeterCourbe(historiqueDemo, titresDemo, reglages) : await lireProjection(Number(actuel), reglages);
    } catch (e) {
      erreur = e instanceof ErreurMoteur ? e.message : "La projection n'a pas pu être calculée.";
    }
  }

  const base = projection?.base_artiste;
  const fiab = projection?.fiabilite.h6 ?? projection?.fiabilite.h3;
  const ecart = fiab ? Object.values(fiab.methodes)[0]?.ecart_moyen : undefined;
  return (
    <>
      {entete}

      <h2 className="mb-3 font-medium">Chiffre d&apos;affaires mensuel et projection</h2>
      <form className="mb-6 flex flex-wrap items-end gap-4 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <label className="text-sm">
          <span className="text-xs text-muted-foreground">Horizon</span>
          <select name="horizon" defaultValue={reglages.horizon} className="mt-1 block rounded-lg border border-input bg-background px-2 py-1.5">
            {HORIZONS.map((h) => <option key={h} value={h}>{h} ans</option>)}
          </select>
        </label>
        <fieldset className="text-sm">
          <legend className="text-xs text-muted-foreground">Fourchette de baisse</legend>
          <div className="mt-1 flex gap-3">
            <label className="flex items-center gap-1.5 rounded-lg border border-input bg-background px-2 py-1.5">
              <input type="radio" name="fourchette" value="catalogue" defaultChecked={reglages.fourchette === "catalogue"} className="accent-primary" />
              Base de l&apos;artiste
            </label>
            <label className="flex items-center gap-1.5 rounded-lg border border-input bg-background px-2 py-1.5">
              <input type="radio" name="fourchette" value="manuelle" defaultChecked={reglages.fourchette === "manuelle"} className="accent-primary" />
              À la main
            </label>
          </div>
        </fieldset>
        <label className="text-sm">
          <span className="text-xs text-muted-foreground">Baisse min. à la main (%)</span>
          <input name="baisse_min" type="number" min={1} max={95} defaultValue={Math.round(reglages.baisse_min * 100)}
            className="mt-1 block w-24 rounded-lg border border-input bg-background px-2 py-1.5" />
        </label>
        <label className="text-sm">
          <span className="text-xs text-muted-foreground">Baisse max. à la main (%)</span>
          <input name="baisse_max" type="number" min={1} max={95} defaultValue={Math.round(reglages.baisse_max * 100)}
            className="mt-1 block w-24 rounded-lg border border-input bg-background px-2 py-1.5" />
        </label>
        <Button type="submit">Recalculer</Button>
      </form>

      {!projection ? (
        <Indisponible message={erreur} />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tuile libelle="Déjà relevé" valeur={euros(projection.realise)} detail={`${projection.debut} – ${projection.dernier}`} />
            <Tuile libelle={`À venir sur ${reglages.horizon} ans`} valeur={euros(projection.avenir)} detail="Estimation" accent />
            <Tuile libelle="Total" valeur={euros(projection.total)} detail="Relevé + à venir" />
            <Tuile libelle="Fourchette du total" valeur={`${kEuros(projection.total_bas)} – ${kEuros(projection.total_haut)}`}
              detail={`Baisse de ${pc(projection.baisse_min)} à ${pc(projection.baisse_max)} par an`} />
          </div>

          <GraphiqueProjection historique={projection.historique} prevision={projection.prevision} />

          {/* L'essentiel du calcul en trois lignes ; le détail reste accessible d'un clic */}
          <ul className="mt-4 space-y-1.5 text-sm text-muted-foreground">
            <li>
              <span className="text-foreground">Baisse retenue :</span> {pc(projection.baisse_min)} à {pc(projection.baisse_max)} par an,{" "}
              {projection.fourchette_source === "catalogue" && base?.disponible
                ? <>mesurée sur {base.titres_mesures} titres de cet artiste (moyenne {pc(base.baisse_moyenne ?? 0)}).</>
                : <>réglée à la main{base && !base.disponible ? " (pas encore assez de titres pour la mesurer)" : ""}.</>}
            </li>
            <li>
              <span className="text-foreground">Baisse constatée sur tous les revenus :</span> {pc(projection.baisse_mesuree)} par an.
              {projection.hors_fourchette && <span className="text-warning"> Elle sort de la fourchette.</span>}
            </li>
            {ecart !== undefined && (
              <li className={cn(ecart > ECART_PEU_FIABLE && "text-warning")}>
                <span className={cn(ecart > ECART_PEU_FIABLE ? "text-warning" : "text-foreground")}>Test sur le passé :</span>{" "}
                écart moyen de {pc(ecart)} sur {fiab?.tests} essais{ecart > ECART_PEU_FIABLE ? " : projection peu fiable pour ce client." : "."}
              </li>
            )}
          </ul>

          <details className="group mt-3 rounded-xl bg-card text-sm ring-1 ring-foreground/10">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-muted-foreground hover:text-foreground">
              <ChevronDown className="size-4 transition-transform group-open:rotate-180" /> Détail du calcul
            </summary>
            <div className="grid gap-6 border-t border-border px-4 py-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <p className="text-muted-foreground">{projection.methode}</p>
                {base?.disponible ? (
                  <ul className="mt-3 grid gap-x-6 gap-y-1 sm:grid-cols-2">
                    {base.titres.slice(0, 8).map((t) => (
                      <li key={t.titre} className="flex justify-between gap-3 border-b border-border py-1">
                        <span className="truncate">{t.titre}</span>
                        <span className="shrink-0 tabular-nums text-muted-foreground">{t.baisse >= 0 ? `−${pc(t.baisse)}` : `+${pc(-t.baisse)}`} / an</span>
                      </li>
                    ))}
                  </ul>
                ) : base?.raison ? (
                  <p className="mt-3 flex gap-2 text-muted-foreground"><Info className="mt-0.5 size-4 shrink-0" />{base.raison}</p>
                ) : null}
              </div>
              <ul className="space-y-1">
                {projection.periodes.map((p) => (
                  <li key={p.label} className="flex justify-between gap-3 border-b border-border py-1">
                    <span className="text-muted-foreground">{p.label}</span>
                    <span className="tabular-nums">{euros(p.valeur)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </>
      )}

      <div className="mt-8"><Avances avances={vue.avances ?? []} compact /></div>

      <section>
        <h2 className="mb-1 font-medium">Recettes par pays</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Ce que chaque pays a rapporté au client, lu dans ses relevés. Un pays sans relevé reste gris.
          {projection ? " Le bouton « Projection » répartit les revenus à venir entre les pays (estimation)." : ""}
        </p>
        <CartePays donnees={vue.pays ?? []} avenir={projection?.avenir} horizon={reglages.horizon} />
      </section>
    </>
  );
}
