import { Avances } from "@/components/avances";
import { EnTete, Indisponible, Tuile, Vide } from "@/components/elements";
import { TableauCatalogue } from "@/components/tableau-catalogue";
import { chargerDonnees } from "@/lib/donnees";
import { euros, nombre } from "@/lib/format";
import { scoreCatalogue } from "@/lib/score";

export default async function Catalogue() {
  const { vue, erreur } = await chargerDonnees();
  const entete = (
    <EnTete
      titre="Catalogue"
      description="Vos œuvres et vos enregistrements, leurs ayants droit, leurs parts et les revenus relevés depuis leur sortie."
    />
  );
  if (!vue) return <>{entete}<Indisponible message={erreur} /></>;
  const catalogue = vue.catalogue;
  const revenus = catalogue.reduce((s, o) => s + o.revenus, 0);
  const ayants = catalogue.reduce((s, o) => s + o.ayants_droit, 0);
  const complete = (p: number | null) => p !== null && Math.abs(p - 100) < 0.1;
  const score = scoreCatalogue(catalogue, vue.fuites);
  return (
    <>
      {entete}
      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Tuile
          libelle="Score du catalogue"
          valeur={score === null ? "—" : `${score} %`}
          detail="Pondéré par les revenus"
          accent
        />
        <Tuile libelle="Œuvres" valeur={nombre(catalogue.length)} />
        <Tuile libelle="Parts d'ayants droit" valeur={nombre(ayants)} />
        <Tuile libelle="Parts complètes" valeur={`${catalogue.filter((o) => complete(o.parts_dep)).length} / ${catalogue.length}`} />
        <Tuile libelle="Revenus relevés" valeur={euros(revenus)} />
      </div>
      <p className="-mt-5 mb-8 text-xs text-muted-foreground">
        Score : part des 5 contrôles réussis (ISWC, ISRC, parts à 100 %, présence dans les relevés de droits d&apos;auteur, aucune alerte chiffrée ouverte).
        100 % veut dire que tous les contrôles sont réussis, pas qu&apos;aucun argent ne manque.
      </p>

      <Avances avances={vue.avances ?? []} />

      {catalogue.length === 0 ? (
        <Vide message="Aucune œuvre : déposez le catalogue du client (œuvres, ayants droit et parts) dans l'écran Dépôt." />
      ) : (
        <TableauCatalogue lignes={catalogue} fuites={vue.fuites} />
      )}
    </>
  );
}
