import { Avances } from "@/components/avances";
import { BlocContrat } from "@/components/bloc-contrat";
import { BlocsCatalogue } from "@/components/blocs-catalogue";
import { EnTete, Indisponible, Vide } from "@/components/elements";
import { TableauCatalogue } from "@/components/tableau-catalogue";
import { chargerDonnees } from "@/lib/donnees";
import { scoreCatalogue } from "@/lib/score";

export default async function Catalogue() {
  const { vue, erreur } = await chargerDonnees();
  const entete = (
    <EnTete
      titre="Catalogue"
      description="Vos œuvres, leurs revenus et l'argent à aller chercher, en un coup d'œil."
    />
  );
  if (!vue) return <>{entete}<Indisponible message={erreur} /></>;
  const catalogue = vue.catalogue;
  const score = scoreCatalogue(catalogue, vue.fuites);
  return (
    <>
      {entete}
      <BlocsCatalogue vue={vue} score={score} />
      <p className="mb-10 text-xs text-muted-foreground">
        Score : part des 5 contrôles réussis (ISWC, ISRC, parts à 100 %, présence dans les relevés de droits d&apos;auteur, aucune alerte chiffrée ouverte).
        100 % veut dire que tous les contrôles sont réussis, pas qu&apos;aucun argent ne manque.
      </p>

      <BlocContrat contrat={vue.contrat} />

      <Avances avances={vue.avances ?? []} />

      {catalogue.length === 0 ? (
        <Vide message="Aucune œuvre : déposez le catalogue du client (œuvres, ayants droit et parts) dans l'écran Dépôt." />
      ) : (
        <TableauCatalogue lignes={catalogue} fuites={vue.fuites} />
      )}
    </>
  );
}
