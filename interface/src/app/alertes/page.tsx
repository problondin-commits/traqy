import { EnTete, Indisponible, Vide } from "@/components/elements";
import { ListeAlertes } from "@/components/liste-alertes";
import { chargerDonnees } from "@/lib/donnees";

export default async function Alertes() {
  const { vue, erreur } = await chargerDonnees();
  return (
    <>
      <EnTete
        titre="Alertes"
        description="Les droits non perçus trouvés dans vos relevés, classés par argent en jeu. Validez celles à réclamer : elles iront dans votre rapport."
      />
      {!vue ? (
        <Indisponible message={erreur} />
      ) : vue.fuites.length === 0 ? (
        <Vide message="Aucune alerte pour ce client avec les fichiers déposés." />
      ) : (
        <ListeAlertes fuites={vue.fuites} />
      )}
    </>
  );
}
