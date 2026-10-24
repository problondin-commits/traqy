import { Loader2 } from "lucide-react";

// Affiché pendant que l'écran attend les données du moteur.
export default function Chargement() {
  return (
    <div className="flex flex-col items-center gap-3 py-24 text-center">
      <Loader2 className="size-8 animate-spin text-primary" />
      <p className="font-medium">Chargement des données…</p>
      <p className="max-w-sm text-sm text-muted-foreground">
        Si le moteur était en veille, cela peut prendre jusqu’à une minute.
      </p>
    </div>
  );
}
