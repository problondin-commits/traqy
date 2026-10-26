"""
Traqy · Vue d'un import pour l'interface : tout ce que les cinq écrans affichent, en une seule réponse,
sans envoyer au navigateur les centaines de lignes de revenus détaillées.
"""
import math
import re
from collections import defaultdict

from controle import cle_iswc, cle_titre
from modele import Categorie

DROITS = {Categorie.droits_auteur}
MASTER = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques, Categorie.droits_voisins}
TYPES = ({Categorie.droits_auteur: "Droits d'auteur"} | {c: "Enregistrement (master)" for c in MASTER}
         | {Categorie.droits_voisins: "Droits voisins"})
RECETTES = DROITS | MASTER | {Categorie.synchro, Categorie.reseaux_sociaux, Categorie.autres_revenus}


def _annee(r):
    """Année de la ligne de revenu : date lue, sinon 4 chiffres dans le libellé de période."""
    if r.debut:
        return str(r.debut.year)
    trouve = re.search(r"(19|20)\d{2}", r.periode or "")
    return trouve.group(0) if trouve else "Non datée"


def _ajouter(detail, r):
    cle = (_annee(r), (r.plateforme or "").strip() or "Non précisée", TYPES[r.categorie])
    detail[cle] += r.montant


PLATEFORMES_MAX = 6   # par œuvre, les autres plateformes sont regroupées (page plus légère, surtout sur téléphone)


def _fusion(*details):
    total = defaultdict(float)
    for d in details:
        for cle, montant in d.items():
            total[cle] += montant
    par_plateforme = defaultdict(float)
    for (_a, p, _t), m in total.items():
        par_plateforme[p] += abs(m)
    gardees = set(sorted(par_plateforme, key=par_plateforme.get, reverse=True)[:PLATEFORMES_MAX])
    regroupe = defaultdict(float)
    for (a, p, t), m in total.items():
        regroupe[(a, p if p in gardees else "Autres plateformes", t)] += m
    return [{"annee": a, "plateforme": p, "type": t, "montant": round(m, 2)} for (a, p, t), m in sorted(regroupe.items())
            if round(m, 2) != 0]


def _euros(x):
    return f"{x:,.0f} €".replace(",", " ")


def lignes_catalogue(imp):
    """Une ligne par œuvre : codes, nombre d'ayants droit, total des parts DEP, revenus relevés (droits d'auteur + master),
    et leur détail par année, plateforme et type de droit (pour les filtres de l'écran Catalogue)."""
    parts = defaultdict(list)
    for p in imp.parts:
        parts[cle_iswc(p.iswc) or cle_titre(p.titre)].append(p)
    droits_iswc, droits_code, droits_titre = defaultdict(float), defaultdict(float), defaultdict(float)
    master = defaultdict(float)
    nouveau = lambda: defaultdict(float)
    det_iswc, det_code, det_titre, det_master = defaultdict(nouveau), defaultdict(nouveau), defaultdict(nouveau), defaultdict(nouveau)
    for r in imp.revenus:
        if r.montant is None:
            continue
        if r.categorie in DROITS:
            if r.iswc:
                droits_iswc[cle_iswc(r.iswc)] += r.montant
                _ajouter(det_iswc[cle_iswc(r.iswc)], r)
            elif r.code_sacem:
                droits_code[r.code_sacem] += r.montant
                _ajouter(det_code[r.code_sacem], r)
            else:
                droits_titre[cle_titre(r.titre)] += r.montant
                _ajouter(det_titre[cle_titre(r.titre)], r)
        elif r.categorie in MASTER and r.isrc:
            master[r.isrc] += r.montant
            _ajouter(det_master[r.isrc], r)
    isrc_par_oeuvre = defaultdict(list)
    for e in imp.enregistrements:
        isrc_par_oeuvre[cle_iswc(e.iswc) or cle_titre(e.titre)].append(e.isrc)

    sortie = []
    for o in imp.oeuvres:
        cle = cle_iswc(o.iswc) or cle_titre(o.titre)
        ses_parts = parts.get(cle) or parts.get(cle_titre(o.titre), [])
        deps = [p.part_dep for p in ses_parts if p.part_dep is not None]
        isrcs = isrc_par_oeuvre.get(cle) or isrc_par_oeuvre.get(cle_titre(o.titre), [])
        revenus = (droits_iswc.get(cle_iswc(o.iswc), 0) if o.iswc else 0) + droits_code.get(o.code_sacem, 0) \
            + droits_titre.get(cle_titre(o.titre), 0) + sum(master.get(i, 0) for i in isrcs)
        detail = _fusion(det_iswc.get(cle_iswc(o.iswc), {}) if o.iswc else {}, det_code.get(o.code_sacem, {}),
                         det_titre.get(cle_titre(o.titre), {}), *(det_master.get(i, {}) for i in isrcs))
        sortie.append({
            "titre": o.titre, "artiste": o.artiste or "", "iswc": o.iswc, "isrc": isrcs[0] if isrcs else None,
            "ayants_droit": len(ses_parts), "parts_dep": round(sum(deps), 3) if deps else None, "revenus": round(revenus, 2),
            "detail": detail,
        })
    # Sans catalogue d'œuvres (ex. relevés distributeur seuls) : une ligne par enregistrement (ISRC)
    for e in ([] if imp.oeuvres else imp.enregistrements):
        sortie.append({
            "titre": e.titre, "artiste": e.artiste or "", "iswc": e.iswc, "isrc": e.isrc, "projet": e.projet,
            "ayants_droit": 0, "parts_dep": None, "revenus": round(master.get(e.isrc, 0), 2),
            "detail": _fusion(det_master.get(e.isrc, {})),
        })
    return sorted(sortie, key=lambda l: -l["revenus"])


def avances(imp):
    """Avances déclarées et leur recoupement, lu dans les lignes « avance » des relevés (montants négatifs)."""
    sortie = []
    for a in imp.avances:
        lignes = [r for r in imp.revenus if r.contrat == a.contrat]
        par_periode = defaultdict(float)
        for r in lignes:
            if r.categorie == Categorie.avance:
                par_periode[(r.debut, r.periode)] += -(r.montant or 0)
        periodes = [{"periode": p, "recoupe": round(m, 2)} for (_, p), m in sorted(par_periode.items(), key=lambda x: (x[0][0] is None, x[0][0]))]
        recoupe = sum(x["recoupe"] for x in periodes)
        reste = max(a.montant - recoupe, 0.0)
        recettes = sum(r.montant or 0 for r in lignes if r.categorie in RECETTES)
        frais = -sum(r.montant or 0 for r in lignes if r.categorie == Categorie.frais)
        net = sum(r.montant or 0 for r in lignes if r.categorie not in (Categorie.retenue,))
        estimation = None
        derniers = [x["recoupe"] for x in periodes[-2:] if x["recoupe"] > 0]
        if reste > 0 and derniers:
            rythme = sum(derniers) / len(derniers)
            semestres = math.ceil(reste / rythme)
            dernier = next((d for (d, _p) in sorted(par_periode, key=lambda x: (x[0] is None, x[0]), reverse=True) if d), None)
            if dernier:
                rang = dernier.year * 2 + (dernier.month > 6) + semestres
                estimation = {
                    "periode": f"{rang // 2} S{rang % 2 + 1}", "semestres": semestres, "rythme": round(rythme, 2),
                    "methode": f"Reste à recouper ({_euros(reste)}) ÷ moyenne des {len(derniers)} derniers recoupements "
                               f"({_euros(rythme)} par semestre) = {semestres} semestre(s). Estimation, pas un engagement.",
                }
        sortie.append({
            "contrat": a.contrat, "projet": a.projet, "montant": a.montant, "devise": a.devise,
            "recoupe": round(recoupe, 2), "reste": round(reste, 2), "taux": round(min(recoupe / a.montant, 1.0), 4) if a.montant else None,
            "recettes": round(recettes, 2), "frais": round(frais, 2), "net_verse": round(net, 2),
            "periodes": periodes, "estimation": estimation, "source": "Montant de l'avance déclaré par le client ; recoupement lu dans les relevés",
        })
    return sortie


def pays(imp):
    """Recettes par pays (code à deux lettres), lues dans les relevés. Rien n'est estimé ici.
    « recent » : recettes des 12 derniers mois relevés (les 2 derniers semestres), qui servent à répartir
    la projection entre les pays dans l'interface."""
    from importation import lire_periode
    lignes = [r for r in imp.revenus_pays if r.categorie in RECETTES]
    debuts = {p: lire_periode(p)[0] for p in {r.periode for r in lignes}}
    recents = set(sorted((p for p, d in debuts.items() if d), key=lambda p: debuts[p])[-2:])
    total = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0])   # montant, quantité, récent, streaming (montant, écoutes)
    for r in lignes:
        t = total[r.pays]
        t[0] += r.montant
        t[1] += r.quantite or 0
        if r.periode in recents:
            t[2] += r.montant
        if r.categorie == Categorie.streaming:
            t[3] += r.montant
            t[4] += r.quantite or 0
    detail = defaultdict(lambda: {"titre": [], "plateforme": []})
    for d in imp.detail_pays:
        detail[d.pays][d.dimension].append({"nom": d.valeur, "montant": d.montant, "quantite": d.quantite})
    sortie = sorted(({
        "pays": p, "montant": round(m, 2), "quantite": round(q), "recent": round(rc, 2),
        # revenu réel du client pour 1 000 écoutes en streaming dans ce pays (lu dans ses relevés, aucun barème)
        "pour_1000": round(sm / se * 1000, 3) if se >= 1000 and sm > 0 else None,
        "titres": sorted(detail[p]["titre"], key=lambda x: -x["montant"])[:5],
        "plateformes": sorted(detail[p]["plateforme"], key=lambda x: -x["montant"])[:5],
    } for p, (m, q, rc, sm, se) in total.items()), key=lambda x: -x["montant"])
    for i, x in enumerate(sortie, 1):
        x["rang"] = i
    return sortie


def vue(imp, cree_le=None):
    return {
        "import_id": imp.import_id,
        "client": imp.client,
        "cree_le": cree_le,
        "resume": imp.resume,
        "fichiers": [b.model_dump() for b in imp.fichiers],
        "manques": [m.model_dump(mode="json") for m in imp.manques],
        "fuites": [f.model_dump(mode="json") for f in imp.fuites],
        "catalogue": lignes_catalogue(imp),
        "avances": avances(imp),
        "pays": pays(imp),
    }
