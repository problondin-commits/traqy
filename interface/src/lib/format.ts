// Mise en forme française des montants et des nombres.

export function euros(montant: number, decimales = 0): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(montant);
}

export function nombre(valeur: number): string {
  return new Intl.NumberFormat("fr-FR").format(valeur);
}

export function pourCent(valeur: number): string {
  return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(valeur)} %`;
}
