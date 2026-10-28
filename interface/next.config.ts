import type { NextConfig } from "next";

// Consignes de sécurité envoyées au navigateur avec chaque page (rapport OWASP ZAP du 28/10/2026) :
// Traqy ne s'affiche jamais à l'intérieur d'un autre site, connexion sécurisée imposée, pas de caméra ni de micro, etc.
const ENTETES_SECURITE = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: ENTETES_SECURITE }];
  },
  cacheComponents: true,
  partialPrefetching: true,
  // Tous les écrans dépendent du client choisi : la vérification « navigation instantanée »
  // ne s'applique qu'aux pages qui la demandent (export const instant = true).
  experimental: {
    instantInsights: { validationLevel: "manual-warning" },
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
