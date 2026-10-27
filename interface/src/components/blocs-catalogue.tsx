// Design « Blocs » de l'écran Catalogue (choix de Tom, 27/10/2026, maquette maquettes/design_A_blocs.html) :
// un grand bloc pour les droits non perçus, puis des blocs plus petits (revenus, score, œuvres, avances, pays).
// Tous les montants viennent des relevés du client ; rien n'est estimé ici, sauf la date de fin d'avance (signalée).
import Link from "next/link";
import { Download } from "lucide-react";
import pays from "i18n-iso-countries";
import fr from "i18n-iso-countries/langs/fr.json";
import { buttonVariants } from "@/components/ui/button";
import { euros, nombre } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Vue } from "@/lib/types";

pays.registerLocale(fr);

const BLOC = "min-w-0 rounded-xl bg-card p-5 ring-1 ring-foreground/10 sm:p-6";
const ETIQUETTE = "text-sm text-muted-foreground";

export function BlocsCatalogue({ vue, score }: { vue: Vue; score: number | null }) {
  const catalogue = vue.catalogue;
  const revenus = catalogue.reduce((s, o) => s + o.revenus, 0);
  const completes = catalogue.filter((o) => o.parts_dep !== null && Math.abs(o.parts_dep - 100) < 0.1).length;
  const chiffre = vue.fuites.reduce((s, f) => s + (f.montant ?? 0), 0);
  const aValider = vue.fuites.filter((f) => !f.decision).length;
  const avances = vue.avances ?? [];
  const meilleursPays = [...(vue.pays ?? [])].sort((a, b) => b.montant - a.montant).slice(0, 4);

  return (
    <section className="liste-fondu mb-6 grid grid-flow-dense grid-cols-2 gap-3.5 lg:grid-cols-4">
      {/* Droits non perçus : le chiffre à regarder en premier */}
      <article className={cn(BLOC, "col-span-2 flex flex-col ring-primary/40 lg:row-span-2")}>
        <p className={ETIQUETTE}>Droits non perçus chiffrés</p>
        <p className="mt-4 text-5xl leading-none font-bold tracking-tight text-primary tabular-nums sm:text-6xl">{euros(chiffre)}</p>
        <p className="mt-3 max-w-[34ch] text-muted-foreground">
          {aValider > 0
            ? `${aValider} alerte${aValider > 1 ? "s" : ""} à valider avant de les ajouter à votre rapport d'audit.`
            : vue.fuites.length > 0 ? "Toutes les alertes ont été examinées." : "Aucune alerte pour ce dossier."}
        </p>
        <div className="mt-auto flex flex-wrap gap-2.5 pt-6">
          <Link href="/alertes" className={buttonVariants({ size: "lg", className: "rounded-xl px-4" })}>Voir les alertes</Link>
          <a href="/api/rapport" download className={buttonVariants({ size: "lg", variant: "outline", className: "rounded-xl px-4" })}>
            <Download /> Télécharger le rapport
          </a>
        </div>
      </article>

      <BlocRevenus vue={vue} revenus={revenus} />

      <article className={BLOC}>
        <p className={ETIQUETTE}>Score du catalogue</p>
        <div className="mt-3 flex items-center gap-4">
          <Jauge valeur={score} />
          <p className="text-xs text-muted-foreground">Pondéré par les revenus</p>
        </div>
      </article>

      <article className={BLOC}>
        <p className={ETIQUETTE}>Œuvres</p>
        <p className="mt-2 text-3xl font-semibold tracking-tight tabular-nums">{nombre(catalogue.length)}</p>
        <p className="mt-1 text-xs text-muted-foreground">{nombre(completes)} avec parts complètes</p>
      </article>

      {avances.length > 0 && <BlocAvances avances={avances} />}

      {meilleursPays.length > 0 && (
        <article className={cn(BLOC, "col-span-2")}>
          <p className={ETIQUETTE}>Recettes par pays</p>
          <ul className="mt-3 space-y-2.5">
            {meilleursPays.map((p) => (
              <li key={p.pays} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3 text-sm">
                <span className="truncate">{pays.getName(p.pays, "fr") ?? p.pays}</span>
                <span className="h-2 rounded-full bg-primary" style={{ width: `${Math.max(3, (p.montant / meilleursPays[0].montant) * 100)}%` }} />
                <span className="text-right font-medium tabular-nums">{euros(p.montant)}</span>
              </li>
            ))}
          </ul>
        </article>
      )}
    </section>
  );
}

// Revenus relevés, avec une petite courbe des revenus par année de relevé (années sans date exclues).
function BlocRevenus({ vue, revenus }: { vue: Vue; revenus: number }) {
  const parAnnee = new Map<string, number>();
  for (const o of vue.catalogue) {
    for (const d of o.detail ?? []) {
      if (/^\d{4}$/.test(d.annee)) parAnnee.set(d.annee, (parAnnee.get(d.annee) ?? 0) + d.montant);
    }
  }
  const annees = [...parAnnee.entries()].sort(([a], [b]) => a.localeCompare(b));
  return (
    <article className={cn(BLOC, "col-span-2")}>
      <p className={ETIQUETTE}>Revenus relevés</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-4xl font-semibold tracking-tight tabular-nums">{euros(revenus)}</p>
          {annees.length > 1 && (
            <p className="mt-1 text-xs text-muted-foreground">Par année de relevé, de {annees[0][0]} à {annees.at(-1)![0]}</p>
          )}
        </div>
        {annees.length > 1 && <Courbe valeurs={annees.map(([, v]) => v)} titre={annees.map(([a, v]) => `${a} : ${euros(v)}`).join(" · ")} />}
      </div>
    </article>
  );
}

function Courbe({ valeurs, titre }: { valeurs: number[]; titre: string }) {
  const l = 200, h = 60, max = Math.max(...valeurs, 1);
  const points = valeurs.map((v, i) => [(i / (valeurs.length - 1)) * l, h - 4 - (v / max) * (h - 10)] as const);
  const trait = points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${l} ${h}`} className="h-14 w-48 shrink-0 text-primary" role="img" aria-label={titre}>
      <title>{titre}</title>
      <path d={`${trait} L${l} ${h} L0 ${h} Z`} fill="currentColor" fillOpacity={0.15} />
      <path d={trait} fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

function Jauge({ valeur }: { valeur: number | null }) {
  const r = 42, tour = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 100 100" className="size-24 shrink-0" role="img" aria-label={valeur === null ? "Score non calculé" : `Score : ${valeur} %`}>
      <circle cx={50} cy={50} r={r} fill="none" strokeWidth={10} className="stroke-muted" />
      {valeur !== null && (
        <circle cx={50} cy={50} r={r} fill="none" strokeWidth={10} strokeLinecap="round" className="stroke-primary"
          strokeDasharray={`${((valeur / 100) * tour).toFixed(1)} ${tour.toFixed(1)}`} transform="rotate(-90 50 50)" />
      )}
      <text x={50} y={57} textAnchor="middle" className="fill-foreground text-[22px] font-semibold">{valeur === null ? "—" : `${valeur} %`}</text>
    </svg>
  );
}

// Résumé des avances : total recoupé sur le total des avances ; le détail par contrat est juste en dessous.
function BlocAvances({ avances }: { avances: NonNullable<Vue["avances"]> }) {
  const total = avances.reduce((s, a) => s + a.montant, 0);
  const recoupe = avances.reduce((s, a) => s + Math.min(a.recoupe, a.montant), 0);
  const taux = total ? recoupe / total : 0;
  const titre = avances.length === 1 ? `Avance · ${avances[0].projet ?? avances[0].contrat}` : `Avances · ${avances.length} avances`;
  const fins = avances.filter((a) => a.reste > 0 && a.estimation).map((a) => a.estimation!.periode).sort();
  return (
    <article className={cn(BLOC, "col-span-2")}>
      <p className={ETIQUETTE}>{titre}</p>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-3xl font-semibold tracking-tight tabular-nums">{euros(recoupe)}</p>
        <p className="text-sm text-muted-foreground tabular-nums">recoupés sur {euros(total)} · {new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(taux * 100)} %</p>
      </div>
      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(taux, 1) * 100}%` }} />
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        {fins.length ? `Fin du recoupement estimée : ${fins.at(-1)} (estimation)` : avances.every((a) => a.reste <= 0) ? "Toutes les avances sont recoupées." : "Fin du recoupement non estimable."}
      </p>
    </article>
  );
}
