"""
Traqy · Module Projection : revenus à venir d'un client, d'après ses propres relevés importés.

1. Courbe mensuelle : chaque revenu est réparti sur les mois de sa période (un mois, un semestre…).
   Un paiement daté d'un seul jour (répartition SACEM) couvre l'intervalle depuis le paiement précédent du même payeur.
   Sont exclus : montants cumulés sans période, synchro et publicité (ponctuelles), frais, avances et retenues.
2. Projection : même méthode que le module Valeur (calculs.projeter_courbe), avec la fourchette de baisse annuelle.
Le résultat est toujours une estimation, calculée sans aucun taux par défaut.
"""
from collections import defaultdict
from datetime import date

import pandas as pd

from calculs import MOIS_LONG, projeter_courbe, test_a_rebours
from modele import Categorie

EXCLUES = {Categorie.synchro, Categorie.frais, Categorie.avance, Categorie.retenue}
ECART_PAR_DEFAUT = 3     # mois couverts par un paiement isolé (répartition trimestrielle)
MOIS_MINIMUM = 6


class HistoriqueInsuffisant(ValueError):
    pass


def indice(d):
    return d.year * 12 + d.month - 1

def serie_mensuelle(revenus):
    lignes = [r for r in revenus if r.categorie not in EXCLUES and r.montant is not None and r.debut and r.fin]
    dates_par_payeur = defaultdict(set)
    for r in lignes:
        if r.fin <= r.debut:
            dates_par_payeur[r.payeur].add(indice(r.debut))
    ecart = {}
    for payeur, indices in dates_par_payeur.items():
        tries = sorted(indices)
        for avant, apres in zip([None] + tries, tries):
            ecart[(payeur, apres)] = min(12, apres - avant) if avant is not None else ECART_PAR_DEFAUT
    mois = defaultdict(float)
    for r in lignes:
        if r.fin > r.debut:
            premiers, derniers = indice(r.debut), indice(r.fin)
        else:
            derniers = indice(r.debut)
            premiers = derniers - ecart[(r.payeur, derniers)] + 1
        n = derniers - premiers + 1
        for i in range(premiers, derniers + 1):
            mois[i] += r.montant / n
    if not mois:
        return pd.Series(dtype=float)
    idx = pd.period_range(pd.Period(year=min(mois) // 12, month=min(mois) % 12 + 1, freq="M"),
                          pd.Period(year=max(mois) // 12, month=max(mois) % 12 + 1, freq="M"), freq="M")
    return pd.Series([mois.get(p.year * 12 + p.month - 1, 0.0) for p in idx], index=idx)

def projeter_serie(mm, fin, aujourdhui, baisse_min=0.05, baisse_max=0.35, fenetre=12):
    """Projection d'une courbe mensuelle déjà construite (utilisée aussi par le mode démo)."""
    if len(mm) < MOIS_MINIMUM or mm.sum() <= 0:
        raise HistoriqueInsuffisant(f"Il faut au moins {MOIS_MINIMUM} mois de relevés datés pour faire une projection "
                                    f"(ici : {len(mm)}).")
    fenetre = min(fenetre, len(mm))
    realise = float(mm.sum())
    P = projeter_courbe(mm, realise, aujourdhui, fin, baisse_min, baisse_max, fenetre)
    mois_fr = lambda p: f"{MOIS_LONG[p.month - 1]} {p.year}"
    return {
        "nature": "estimation",
        "methode": f"Baisse mesurée sur les {P['mois_mesures']} derniers mois de relevés, prolongée jusqu'à la date de fin. "
                   f"Fourchette : baisse annuelle de {baisse_min:.0%} à {baisse_max:.0%}. Aucun taux par défaut.",
        "debut": mois_fr(mm.index.min()), "dernier": mois_fr(mm.index.max()),
        "aujourdhui": aujourdhui.isoformat(), "fin": fin.isoformat(),
        "historique": [{"mois": str(p), "valeur": round(float(v), 2)} for p, v in mm.items()],
        "prevision": [{"mois": m["mois"], "valeur": round(m["valeur"], 2)} for m in P["mois_prevus"]],
        "realise": round(realise, 2), "avenir": round(P["avenir"], 2), "total": round(realise + P["avenir"], 2),
        "total_bas": round(P["total_bas"], 2), "total_haut": round(P["total_haut"], 2),
        "baisse_mesuree": round(P["baisse"], 4), "baisse_min": baisse_min, "baisse_max": baisse_max,
        # la baisse mesurée peut sortir de la fourchette réglée : l'estimation centrale sort alors de la fourchette
        "hors_fourchette": not (baisse_min <= P["baisse"] <= baisse_max),
        "niveau_mensuel": round(P["niveau_depart"], 2),
        "periodes": [p for p in P["periodes"] if p["valeur"] > 0],   # sans la période « non relevée » quand elle est vide
        "fiabilite": test_a_rebours(mm, fenetre),
    }

def projeter_import(imp, fin, aujourdhui=None, baisse_min=0.05, baisse_max=0.35):
    mm = serie_mensuelle(imp.revenus)
    return projeter_serie(mm, fin, aujourdhui or date.today(), baisse_min, baisse_max)
