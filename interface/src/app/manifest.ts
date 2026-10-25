// Fiche de l'app : sur téléphone, Traqy s'ajoute à l'écran d'accueil et s'ouvre en plein écran, avec son icône.
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Traqy",
    short_name: "Traqy",
    description: "Retrouvez les droits non perçus de votre catalogue.",
    lang: "fr",
    start_url: "/depot",
    display: "standalone",
    background_color: "#111317",
    theme_color: "#111317",
    icons: [
      { src: "/icone-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icone-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icone-512-masque.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
