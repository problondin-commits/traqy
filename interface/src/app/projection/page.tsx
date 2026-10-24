import { connection } from "next/server";
import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EnTete, Indisponible, Tuile } from "@/components/elements";
import { GraphiqueProjection } from "@/components/graphique-projection";
import { ErreurMoteur, lireProjection, moteurConfigure, projeterCourbe } from "@/lib/api";
import { historiqueDemo, titresDemo } from "@/lib/demo";
import { chargerDonnees } from "@/lib/donnees";
import { euros } from "@/lib/format";
import type { Projection as TypeProjection, ReglagesProjection } from "@/lib/types";

const HORIZONS = [3, 5, 10, 15];
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
      <form className="mb-8 flex flex-wrap items-end gap-4 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
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
              detail={`Baisse de ${pc(projection.baisse_min)} à ${pc(projection.baisse_max)} par an · ${
                projection.fourchette_source === "catalogue" ? "base de l'artiste" : "réglée à la main"}`} />
          </div>

          <GraphiqueProjection historique={projection.historique} prevision={projection.prevision} />

          <section className="mt-6 rounded-xl bg-card p-5 text-sm ring-1 ring-foreground/10">
            <h2 className="font-medium">Base de l&apos;artiste</h2>
            {base?.disponible ? (
              <>
                <p className="mt-2 text-muted-foreground">
                  Calculée uniquement à partir des relevés déposés pour cet artiste, sans aucune donnée d&apos;un autre artiste.
                  Baisse annuelle mesurée sur <span className="text-foreground">{base.titres_mesures} titres</span> ayant au moins deux ans de relevés,
                  pondérée par ce qu&apos;ils rapportent aujourd&apos;hui.
                </p>
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <Tuile libelle="Baisse moyenne du catalogue" valeur={`${pc(base.baisse_moyenne ?? 0)} / an`} accent />
                  <Tuile libelle="Titres qui résistent le mieux" valeur={`${pc(base.baisse_basse ?? 0)} / an`} detail="Bas de la fourchette" />
                  <Tuile libelle="Titres qui baissent le plus vite" valeur={`${pc(base.baisse_haute ?? 0)} / an`} detail="Haut de la fourchette" />
                </div>
                <ul className="mt-4 grid gap-x-6 gap-y-1 sm:grid-cols-2">
                  {base.titres.slice(0, 8).map((t) => (
                    <li key={t.titre} className="flex justify-between gap-3 border-b border-border py-1.5">
                      <span className="truncate">{t.titre}</span>
                      <span className="shrink-0 tabular-nums text-muted-foreground">
                        {t.baisse >= 0 ? `−${pc(t.baisse)}` : `+${pc(-t.baisse)}`} / an
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-xs text-muted-foreground">Les titres qui rapportent le plus aujourd&apos;hui, avec leur baisse annuelle mesurée.</p>
              </>
            ) : (
              <p className="mt-2 flex gap-2 text-muted-foreground">
                <Info className="mt-0.5 size-4 shrink-0" />
                Pas encore assez de titres pour calculer la base de cet artiste : {base?.raison} La fourchette réglée à la main est utilisée.
              </p>
            )}
          </section>

          <div className="mt-6 grid gap-3 lg:grid-cols-[1fr_1fr]">
            <section className="rounded-xl bg-card p-5 text-sm ring-1 ring-foreground/10">
              <h2 className="font-medium">Comment c&apos;est calculé</h2>
              <p className="mt-2 text-muted-foreground">{projection.methode}</p>
              <p className="mt-3">Baisse mesurée sur l&apos;ensemble des revenus : <span className="font-medium tabular-nums">{pc(projection.baisse_mesuree)}</span> par an.</p>
              {projection.hors_fourchette && (
                <p className="mt-3 flex gap-2 rounded-lg bg-warning/15 px-3 py-2 text-warning">
                  <Info className="mt-0.5 size-4 shrink-0" />
                  La baisse mesurée sort de la fourchette : le total estimé sort donc lui aussi de la fourchette.
                </p>
              )}
              {ecart !== undefined && (
                <p className="mt-3 text-muted-foreground">
                  Test sur le passé : en cachant les derniers mois et en les prévoyant avec cette méthode, l&apos;écart moyen avec la réalité est de{" "}
                  <span className="font-medium text-foreground tabular-nums">{pc(ecart)}</span> ({fiab?.tests} essais).
                </p>
              )}
            </section>
            <section className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
              <Table>
                <TableHeader>
                  <TableRow><TableHead>Période</TableHead><TableHead className="text-right">Estimation</TableHead></TableRow>
                </TableHeader>
                <TableBody>
                  {projection.periodes.map((p) => (
                    <TableRow key={p.label}>
                      <TableCell>{p.label}</TableCell>
                      <TableCell className="text-right tabular-nums">{euros(p.valeur)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </section>
          </div>
        </>
      )}
    </>
  );
}
