import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EnTete, Tuile } from "@/components/elements";
import { catalogueDemo } from "@/lib/demo";
import { euros, nombre, pourCent } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function Catalogue() {
  const revenus = catalogueDemo.reduce((s, o) => s + o.revenus, 0);
  const ayants = catalogueDemo.reduce((s, o) => s + o.ayants_droit, 0);
  const completes = catalogueDemo.filter((o) => o.parts_dep !== null && Math.abs(o.parts_dep - 100) < 0.1).length;
  return (
    <>
      <EnTete
        titre="Catalogue"
        description="Vos œuvres et vos enregistrements, leurs ayants droit, leurs parts et les revenus relevés depuis leur sortie."
      />
      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tuile libelle="Œuvres" valeur={nombre(catalogueDemo.length)} />
        <Tuile libelle="Ayants droit" valeur={nombre(ayants)} />
        <Tuile libelle="Parts complètes" valeur={`${completes} / ${catalogueDemo.length}`} />
        <Tuile libelle="Revenus relevés" valeur={euros(revenus)} accent />
      </div>

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
            {catalogueDemo.map((o) => {
              const complete = o.parts_dep !== null && Math.abs(o.parts_dep - 100) < 0.1;
              return (
                <TableRow key={o.titre}>
                  <TableCell className="font-medium">{o.titre}</TableCell>
                  <TableCell className="text-muted-foreground">{o.artiste}</TableCell>
                  <TableCell className={cn("font-mono text-xs", !o.iswc && "text-warning")}>{o.iswc ?? "manquant"}</TableCell>
                  <TableCell className={cn("font-mono text-xs", !o.isrc && "text-warning")}>{o.isrc ?? "manquant"}</TableCell>
                  <TableCell className="text-right tabular-nums">{o.ayants_droit}</TableCell>
                  <TableCell className={cn("text-right tabular-nums", complete ? "text-primary" : "text-warning")}>
                    {o.parts_dep === null ? "absentes" : pourCent(o.parts_dep)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{o.revenus ? euros(o.revenus) : "—"}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
