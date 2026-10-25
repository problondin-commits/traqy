"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { euros, pourCent } from "@/lib/format";
import { controles, etatOeuvre, normaliser, partsCompletes as complete, type Etat } from "@/lib/score";
import { cn } from "@/lib/utils";
import type { Fuite, LigneCatalogue } from "@/lib/types";

const TOUS = "";

// Score du titre : vert à 100 %, jaune à partir de 60 %, rouge en dessous. Au survol : les contrôles manqués.
function Score({ o, fuites }: { o: LigneCatalogue; fuites: Fuite[] }) {
  const c = controles(o, fuites);
  const score = Math.round((c.filter((x) => x.ok).length / c.length) * 100);
  const manques = c.filter((x) => !x.ok).map((x) => `✕ ${x.libelle}`);
  const bulle = manques.length ? `Contrôles manqués :\n${manques.join("\n")}` : "Les 5 contrôles sont réussis";
  return (
    <span title={bulle} className={cn("tabular-nums font-medium", score === 100 ? "text-primary" : score >= 60 ? "text-warning" : "text-destructive")}>
      {score} %
    </span>
  );
}

const COULEUR: Record<Etat, string> = { rouge: "bg-destructive", jaune: "bg-warning", vert: "bg-primary" };
const LIBELLE: Record<Etat, string> = { rouge: "Droits non perçus chiffrés", jaune: "À vérifier", vert: "Rien à signaler" };

function Pastille({ etat }: { etat: Etat }) {
  return <span title={LIBELLE[etat]} aria-label={LIBELLE[etat]} className={cn("inline-block size-2.5 shrink-0 rounded-full", COULEUR[etat])} />;
}

function Choix({ libelle, valeur, options, onChange }: { libelle: string; valeur: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted-foreground">
      {libelle}
      <select
        value={valeur}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-lg bg-card px-3 text-sm text-foreground ring-1 ring-foreground/10 outline-none focus:ring-ring"
      >
        <option value={TOUS}>Tous</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

export function TableauCatalogue({ lignes, fuites }: { lignes: LigneCatalogue[]; fuites: Fuite[] }) {
  const [texte, setTexte] = useState("");
  const [annee, setAnnee] = useState(TOUS);
  const [plateforme, setPlateforme] = useState(TOUS);
  const [type, setType] = useState(TOUS);

  const details = lignes.flatMap((l) => l.detail ?? []);
  const options = (cle: "annee" | "plateforme" | "type") => [...new Set(details.map((d) => d[cle]))].sort((a, b) => a.localeCompare(b, "fr"));
  const filtreActif = annee !== TOUS || plateforme !== TOUS || type !== TOUS;

  const affichees = useMemo(() => {
    const t = normaliser(texte);
    return lignes
      .map((l) => {
        const revenus = filtreActif
          ? (l.detail ?? [])
              .filter((d) => (annee === TOUS || d.annee === annee) && (plateforme === TOUS || d.plateforme === plateforme) && (type === TOUS || d.type === type))
              .reduce((s, d) => s + d.montant, 0)
          : l.revenus;
        return { ...l, revenus, ...etatOeuvre(l, fuites) };
      })
      .filter((l) => !t || [l.titre, l.artiste, l.iswc, l.isrc].some((v) => normaliser(v).includes(t)))
      .filter((l) => !filtreActif || l.revenus > 0)
      .sort((a, b) => b.enJeu - a.enJeu || b.revenus - a.revenus);
  }, [lignes, fuites, texte, annee, plateforme, type, filtreActif]);

  const total = affichees.reduce((s, l) => s + l.revenus, 0);
  const compte = (e: Etat) => affichees.filter((l) => l.etat === e).length;

  return (
    <>
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end">
        <label className="relative flex-1">
          <span className="sr-only">Rechercher</span>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            placeholder="Titre, artiste, ISWC ou ISRC"
            className="h-9 w-full rounded-lg bg-card pr-3 pl-9 text-sm ring-1 ring-foreground/10 outline-none placeholder:text-muted-foreground focus:ring-ring"
          />
        </label>
        {details.length > 0 && (
          <div className="grid grid-cols-3 gap-3 lg:w-[30rem]">
            <Choix libelle="Période" valeur={annee} options={options("annee")} onChange={setAnnee} />
            <Choix libelle="Plateforme" valeur={plateforme} options={options("plateforme")} onChange={setPlateforme} />
            <Choix libelle="Type de droit" valeur={type} options={options("type")} onChange={setType} />
          </div>
        )}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
        {(["rouge", "jaune", "vert"] as Etat[]).map((e) => (
          <span key={e} className="flex items-center gap-1.5"><Pastille etat={e} /> {LIBELLE[e]} ({compte(e)})</span>
        ))}
        <span className="ml-auto">{affichees.length} œuvres · {euros(total)}{filtreActif ? " pour ces filtres" : ""}</span>
      </div>

      <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8"><span className="sr-only">État</span></TableHead>
              <TableHead>Titre</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead>Artiste</TableHead>
              <TableHead>ISWC</TableHead>
              <TableHead>ISRC</TableHead>
              <TableHead className="text-right">Ayants droit</TableHead>
              <TableHead className="text-right">Parts (DEP)</TableHead>
              <TableHead className="text-right">Argent en jeu</TableHead>
              <TableHead className="text-right">Revenus relevés</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {affichees.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10}className="py-8 text-center text-muted-foreground">Aucune œuvre ne correspond à cette recherche.</TableCell>
              </TableRow>
            ) : (
              affichees.map((o) => (
                <TableRow key={`${o.titre}-${o.iswc}-${o.isrc}`}>
                  <TableCell><Pastille etat={o.etat} /></TableCell>
                  <TableCell className="font-medium">{o.titre}</TableCell>
                  <TableCell className="text-right"><Score o={o} fuites={fuites} /></TableCell>
                  <TableCell className="text-muted-foreground">{o.artiste || "—"}</TableCell>
                  <TableCell className={cn("text-sm tabular-nums", o.iswc ? "text-muted-foreground" : "text-warning")}>{o.iswc ?? "manquant"}</TableCell>
                  <TableCell className={cn("text-sm tabular-nums", o.isrc ? "text-muted-foreground" : "text-warning")}>{o.isrc ?? "manquant"}</TableCell>
                  <TableCell className="text-right tabular-nums">{o.ayants_droit || "—"}</TableCell>
                  <TableCell className={cn("text-right tabular-nums", complete(o.parts_dep) ? "text-primary" : "text-warning")}>
                    {o.parts_dep === null ? "absentes" : pourCent(o.parts_dep)}
                  </TableCell>
                  <TableCell className={cn("text-right tabular-nums", o.enJeu > 0 ? "text-destructive" : "text-muted-foreground")}>
                    {o.enJeu > 0 ? euros(o.enJeu) : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{o.revenus ? euros(o.revenus) : "—"}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
