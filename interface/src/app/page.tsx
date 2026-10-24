import { redirect } from "next/navigation";

// L'accueil ouvre directement le premier écran : le dépôt des fichiers.
export default function Accueil() {
  redirect("/depot");
}
