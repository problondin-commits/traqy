"""
Traqy · Vue d'un import pour l'interface : tout ce que les cinq écrans affichent, en une seule réponse,
sans envoyer au navigateur les centaines de lignes de revenus détaillées.
"""
import re
from collections import defaultdict

from controle import cle_iswc, cle_titre
from modele import Categorie

DROITS = {Categorie.droits_auteur}
MASTER = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques}
TYPES = {Categorie.droits_auteur: "Droits d'auteur"} | {c: "Enregistrement (master)" for c in MASTER}


def _annee(r):
    """Année de la ligne de revenu : date lue, sinon 4 chiffres dans le libellé de période."""
    if r.debut:
        return str(r.debut.year)
    trouve = re.search(r"(19|20)\d{2}", r.periode or "")
    return trouve.group(0) if trouve else "Non datée"


def _ajouter(detail, r):
    cle = (_annee(r), (r.plateforme or "").strip() or "Non précisée", TYPES[r.categorie])
    detail[cle] += r.montant


def _fusion(*details):
    total = defaultdict(float)
    for d in details:
        for cle, montant in d.items():
            total[cle] += montant
    return [{"annee": a, "plateforme": p, "type": t, "montant": round(m, 2)} for (a, p, t), m in sorted(total.items())]


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
    return sorted(sortie, key=lambda l: -l["revenus"])


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
    }
