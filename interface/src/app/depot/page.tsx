import Link from "next/link";
import { CheckCircle2, CircleSlash, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EnTete, Indisponible } from "@/components/elements";
import { ZoneDepot } from "@/components/zone-depot";
import { moteurConfigure } from "@/lib/api";
import { DATE_DEPOT_DEMO } from "@/lib/demo";
import { chargerDonnees } from "@/lib/donnees";
import { nombre } from "@/lib/format";

const ICONE_STATUT = {
  importé: <CheckCircle2 className="size-4 text-primary" />,
  ignoré: <CircleSlash className="size-4 text-muted-foreground" />,
  refusé: <XCircle className="size-4 text-destructive" />,
};

function dateFr(iso: string | null) {
  if (!iso) return DATE_DEPOT_DEMO;
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short", timeZone: "Europe/Paris" }).format(new Date(iso));
}

export default async function Depot() {
  const { vue, demo, erreur, role } = await chargerDonnees();
  return (
    <>
      <EnTete
        titre="Dépôt"
        description="Déposez une seule fois votre catalogue, vos contrats et vos relevés. Traqy reconnaît seul chaque fichier (CSV, Excel ou ZIP) et vérifie ce qui manque."
        action={<Button nativeButton={false} render={<Link href="/manques" />}>Voir le contrôle des manques</Button>}
      />

      {role.type === "client" || role.type === "pause" ? (
        <p className="rounded-xl border border-dashed border-border px-6 py-8 text-center text-sm text-muted-foreground">
          Vos fichiers sont déposés par Traqy. Pour ajouter un relevé ou un catalogue, envoyez-le-nous.
        </p>
      ) : (
        <ZoneDepot clientActuel={demo ? null : vue?.client ?? null} moteurBranche={moteurConfigure() && role.type === "admin"} />
      )}

      <div className="mt-10">
        <h2 className="text-base font-medium">Dernier dépôt</h2>
        {!vue ? (
          <div className="mt-4"><Indisponible message={erreur} /></div>
        ) : (
          <>
            <p className="mb-4 text-sm text-muted-foreground">{vue.client} · {dateFr(vue.cree_le)} · {vue.fichiers.length} fichiers ou onglets</p>
            <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fichier</TableHead>
                    <TableHead>Reconnu comme</TableHead>
                    <TableHead className="text-right">Lignes importées</TableHead>
                    <TableHead>Remarques</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="liste-fondu">
                  {vue.fichiers.map((b, i) => (
                    <TableRow key={`${b.fichier}-${i}`}>
                      <TableCell>
                        <span className="flex items-center gap-2">
                          {ICONE_STATUT[b.statut]}
                          <span className="font-medium">{b.fichier}</span>
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{b.format ?? "Non reconnu"}</TableCell>
                      <TableCell className="text-right tabular-nums">{nombre(b.lignes_importees)}</TableCell>
                      <TableCell className="min-w-64 whitespace-normal text-xs text-muted-foreground">
                        {b.messages[0] ?? "—"}
                        {b.lignes_ignorees > 1 ? ` (+${b.lignes_ignorees - 1} autres)` : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </div>
    </>
  );
}
