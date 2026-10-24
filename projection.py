"""
Traqy · Module Projection : revenus à venir d'un client, d'après ses propres relevés importés.

1. Courbe mensuelle : chaque revenu est réparti sur les mois de sa période (un mois, un semestre…).
   Un paiement daté d'un seul jour (répartition SACEM) couvre l'intervalle depuis le paiement précédent du même payeur.
   Sont exclus : montants cumulés sans période, synchro et publicité (ponctuelles), frais, avances et retenues.
2. Base de l'artiste : la baisse annuelle de chacun de ses titres, mesurée sur ses seuls relevés.
   Moyenne pondérée par les revenus récents, et fourchette allant des titres qui résistent le mieux
   (20e centile) à ceux qui baissent le plus vite (80e centile). Jamais mélangée avec un autre artiste.
3. Projection : même méthode que le module Valeur (calculs.projeter_courbe). La fourchette vient de la base
   de l'artiste quand au moins 5 titres sont mesurables, sinon du réglage à la main.
Le résultat est toujours une estimation, calculée sans aucun taux par défaut.
"""
from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd

from calculs import MOIS_LONG, projeter_courbe, test_a_rebours
from controle import cle_titre
from modele import Categorie

EXCLUES = {Categorie.synchro, Categorie.frais, Categorie.avance, Categorie.retenue}
ECART_PAR_DEFAUT = 3     # mois couverts par un paiement isolé (répartition trimestrielle)
MOIS_MINIMUM = 6
# Base de l'artiste
TITRES_MINIMUM = 5       # en dessous, la fourchette reste celle réglée à la main
HISTORIQUE_TITRE = 24    # mois de relevés nécessaires pour mesurer la baisse d'un titre
TITRE_ACTIF = 6          # un titre sans paiement depuis plus de 6 mois n'est pas mesuré (c'est une piste de fuite)
BORNES = (0.20, 0.80)    # centiles de la fourchette


class HistoriqueInsuffisant(ValueError):
    pass


def indice(d):
    return d.year * 12 + d.month - 1

def lignes_utiles(revenus):
    return [r for r in revenus if r.categorie not in EXCLUES and r.montant is not None and r.debut and r.fin]

def ecarts(lignes):
    """Pour un paiement daté d'un jour : nombre de mois écoulés depuis le paiement précédent du même payeur."""
    dates_par_payeur = defaultdict(set)
    for r in lignes:
        if r.fin <= r.debut:
            dates_par_payeur[r.payeur].add(indice(r.debut))
    ecart = {}
    for payeur, indices in dates_par_payeur.items():
        tries = sorted(indices)
        for avant, apres in zip([None] + tries, tries):
            ecart[(payeur, apres)] = min(12, apres - avant) if avant is not None else ECART_PAR_DEFAUT
    return ecart

def repartir(lignes, ecart):
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
    return mois

def en_serie(mois, debut=None, fin=None):
    if not mois:
        return pd.Series(dtype=float)
    a, b = debut if debut is not None else min(mois), fin if fin is not None else max(mois)
    idx = pd.period_range(pd.Period(year=a // 12, month=a % 12 + 1, freq="M"), pd.Period(year=b // 12, month=b % 12 + 1, freq="M"), freq="M")
    return pd.Series([mois.get(p.year * 12 + p.month - 1, 0.0) for p in idx], index=idx)

def serie_mensuelle(revenus):
    lignes = lignes_utiles(revenus)
    return en_serie(repartir(lignes, ecarts(lignes)))

def series_par_titre(revenus):
    """Une courbe mensuelle par titre de l'artiste. Les écarts entre paiements sont mesurés sur tout l'artiste,
    pour qu'un titre absent d'une répartition ne voie pas son paiement suivant étalé sur une période trop longue."""
    lignes = lignes_utiles(revenus)
    ecart = ecarts(lignes)
    groupes, libelles = defaultdict(list), {}
    for r in lignes:
        if not r.titre or r.titre.lower().startswith("non indiqu"):
            continue
        cle = cle_titre(r.titre)
        groupes[cle].append(r)
        libelles.setdefault(cle, r.titre)
    return {libelles[c]: repartir(g, ecart) for c, g in groupes.items()}


def mesurer_baisse(serie, fenetre):
    y = serie.iloc[-fenetre:]
    b, _ = np.polyfit(np.arange(len(y)), np.log(y.clip(lower=1).values), 1)
    return float(1 - np.exp(12 * b))

def centile_pondere(valeurs, poids, q):
    ordre = np.argsort(valeurs)
    v, p = np.asarray(valeurs)[ordre], np.asarray(poids)[ordre]
    cumul = (np.cumsum(p) - p / 2) / p.sum()
    return float(np.interp(q, cumul, v))

def base_artiste(titres, fin_artiste):
    """titres : {titre: {indice de mois: montant}}. fin_artiste : dernier mois relevé de l'artiste."""
    mesures = []
    for titre, mois in titres.items():
        payes = [m for m, v in mois.items() if v > 0]
        if not payes:
            continue
        if fin_artiste - min(payes) + 1 < HISTORIQUE_TITRE or fin_artiste - max(payes) > TITRE_ACTIF:
            continue
        serie = en_serie(mois, min(payes), fin_artiste)
        recents = float(serie.iloc[-12:].sum())
        if recents <= 0:
            continue
        mesures.append({"titre": titre, "baisse": mesurer_baisse(serie, HISTORIQUE_TITRE), "revenus_12_mois": round(recents, 2)})
    mesures.sort(key=lambda m: -m["revenus_12_mois"])
    base = {"titres_mesures": len(mesures), "titres_minimum": TITRES_MINIMUM, "titres": [
        {**m, "baisse": round(m["baisse"], 4)} for m in mesures[:12]]}
    if len(mesures) < TITRES_MINIMUM:
        return {**base, "disponible": False,
                "raison": f"{len(mesures)} titre(s) mesurable(s) sur au moins {TITRES_MINIMUM} nécessaires "
                          f"({HISTORIQUE_TITRE} mois de relevés par titre, encore payé ces {TITRE_ACTIF} derniers mois)."}
    baisses = [m["baisse"] for m in mesures]
    poids = [m["revenus_12_mois"] for m in mesures]
    bas = min(0.95, max(0.01, centile_pondere(baisses, poids, BORNES[0])))
    haut = min(0.95, max(0.01, centile_pondere(baisses, poids, BORNES[1])))
    if haut - bas < 0.02:
        bas, haut = max(0.01, bas - 0.01), min(0.95, haut + 0.01)
    return {**base, "disponible": True, "raison": None,
            "baisse_moyenne": round(float(np.average(baisses, weights=poids)), 4),
            "baisse_basse": round(bas, 4), "baisse_haute": round(haut, 4)}


def projeter_serie(mm, fin, aujourdhui, baisse_min=0.05, baisse_max=0.35, fenetre=12, base=None, fourchette="catalogue"):
    """Projection d'une courbe mensuelle déjà construite. Avec la base de l'artiste disponible et la fourchette
    « catalogue », la fourchette de baisse vient des titres de l'artiste ; sinon du réglage à la main."""
    if len(mm) < MOIS_MINIMUM or mm.sum() <= 0:
        raise HistoriqueInsuffisant(f"Il faut au moins {MOIS_MINIMUM} mois de relevés datés pour faire une projection "
                                    f"(ici : {len(mm)}).")
    base = base or {"disponible": False, "titres_mesures": 0, "titres_minimum": TITRES_MINIMUM, "titres": [],
                    "raison": "Le détail par titre n'est pas disponible."}
    source = "catalogue" if fourchette == "catalogue" and base["disponible"] else "manuelle"
    if source == "catalogue":
        baisse_min, baisse_max = base["baisse_basse"], base["baisse_haute"]
    fenetre = min(fenetre, len(mm))
    realise = float(mm.sum())
    P = projeter_courbe(mm, realise, aujourdhui, fin, baisse_min, baisse_max, fenetre)
    mois_fr = lambda p: f"{MOIS_LONG[p.month - 1]} {p.year}"
    origine = (f"base de l'artiste, mesurée sur {base['titres_mesures']} titres de ses relevés" if source == "catalogue"
               else "réglée à la main")
    return {
        "nature": "estimation",
        "methode": f"Baisse mesurée sur les {P['mois_mesures']} derniers mois de relevés, prolongée jusqu'à la date de fin. "
                   f"Fourchette ({origine}) : baisse annuelle de {baisse_min:.0%} à {baisse_max:.0%}. Aucun taux par défaut.",
        "debut": mois_fr(mm.index.min()), "dernier": mois_fr(mm.index.max()),
        "aujourdhui": aujourdhui.isoformat(), "fin": fin.isoformat(),
        "historique": [{"mois": str(p), "valeur": round(float(v), 2)} for p, v in mm.items()],
        "prevision": [{"mois": m["mois"], "valeur": round(m["valeur"], 2)} for m in P["mois_prevus"]],
        "realise": round(realise, 2), "avenir": round(P["avenir"], 2), "total": round(realise + P["avenir"], 2),
        "total_bas": round(P["total_bas"], 2), "total_haut": round(P["total_haut"], 2),
        "baisse_mesuree": round(P["baisse"], 4), "baisse_min": round(baisse_min, 4), "baisse_max": round(baisse_max, 4),
        "fourchette_source": source,
        "base_artiste": base,
        # la baisse mesurée peut sortir de la fourchette : l'estimation centrale sort alors de la fourchette
        "hors_fourchette": not (baisse_min <= P["baisse"] <= baisse_max),
        "niveau_mensuel": round(P["niveau_depart"], 2),
        "periodes": [p for p in P["periodes"] if p["valeur"] > 0],   # sans la période « non relevée » quand elle est vide
        "fiabilite": test_a_rebours(mm, fenetre),
    }

def projeter_import(imp, fin, aujourdhui=None, baisse_min=0.05, baisse_max=0.35, fourchette="catalogue"):
    mm = serie_mensuelle(imp.revenus)
    base = base_artiste(series_par_titre(imp.revenus), indice(mm.index.max().start_time.date())) if len(mm) else None
    return projeter_serie(mm, fin, aujourdhui or date.today(), baisse_min, baisse_max, base=base, fourchette=fourchette)

def base_depuis_courbes(courbes, fin_artiste):
    """Base de l'artiste à partir de courbes mensuelles par titre déjà construites (mode démo)."""
    titres = {t: {pd.Period(m, "M").year * 12 + pd.Period(m, "M").month - 1: v for m, v in c.items()} for t, c in courbes.items()}
    return base_artiste(titres, fin_artiste)
