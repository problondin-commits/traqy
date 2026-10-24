import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EnTete, Indisponible, Tuile, Vide } from "@/components/elements";
import { chargerDonnees } from "@/lib/donnees";
import { euros, nombre, pourCent } from "@/lib/format";
import { cn } from "@/lib/utils";

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
  return (
    <>
      {entete}
      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tuile libelle="Œuvres" valeur={nombre(catalogue.length)} />
        <Tuile libelle="Parts d'ayants droit" valeur={nombre(ayants)} />
        <Tuile libelle="Parts complètes" valeur={`${catalogue.filter((o) => complete(o.parts_dep)).length} / ${catalogue.length}`} />
        <Tuile libelle="Revenus relevés" valeur={euros(revenus)} accent />
      </div>

      {catalogue.length === 0 ? (
        <Vide message="Aucune œuvre : déposez le catalogue du client (œuvres, ayants droit et parts) dans l'écran Dépôt." />
      ) : (
        <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Titre</TableHead>
                <TableHead>Artiste</TableHead>
                <TableHead>ISWC</TableHead>
                <TableHead>ISRC</TableHead>
                <TableHead className="text-right">Ayants droit</TableHead>
                <TableHead className="text-right">Parts (DEP)</TableHead>
                <TableHead className="text-right">Revenus relevés</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {catalogue.map((o) => (
                <TableRow key={`${o.titre}-${o.iswc}`}>
                  <TableCell className="font-medium">{o.titre}</TableCell>
                  <TableCell className="text-muted-foreground">{o.artiste || "—"}</TableCell>
                  <TableCell className={cn("font-mono text-xs", !o.iswc && "text-warning")}>{o.iswc ?? "manquant"}</TableCell>
                  <TableCell className={cn("font-mono text-xs", !o.isrc && "text-warning")}>{o.isrc ?? "manquant"}</TableCell>
                  <TableCell className="text-right tabular-nums">{o.ayants_droit || "—"}</TableCell>
                  <TableCell className={cn("text-right tabular-nums", complete(o.parts_dep) ? "text-primary" : "text-warning")}>
                    {o.parts_dep === null ? "absentes" : pourCent(o.parts_dep)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{o.revenus ? euros(o.revenus) : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
