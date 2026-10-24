"""
Traqy · Vue d'un import pour l'interface : tout ce que les cinq écrans affichent, en une seule réponse,
sans envoyer au navigateur les centaines de lignes de revenus détaillées.
"""
from collections import defaultdict

from controle import cle_iswc, cle_titre
from modele import Categorie

DROITS = {Categorie.droits_auteur}
MASTER = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques}


def lignes_catalogue(imp):
    """Une ligne par œuvre : codes, nombre d'ayants droit, total des parts DEP, revenus relevés (droits d'auteur + master)."""
    parts = defaultdict(list)
    for p in imp.parts:
        parts[cle_iswc(p.iswc) or cle_titre(p.titre)].append(p)
    droits_iswc, droits_code, droits_titre = defaultdict(float), defaultdict(float), defaultdict(float)
    master = defaultdict(float)
    for r in imp.revenus:
        if r.montant is None:
            continue
        if r.categorie in DROITS:
            if r.iswc:
                droits_iswc[cle_iswc(r.iswc)] += r.montant
            elif r.code_sacem:
                droits_code[r.code_sacem] += r.montant
            else:
                droits_titre[cle_titre(r.titre)] += r.montant
        elif r.categorie in MASTER and r.isrc:
            master[r.isrc] += r.montant
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
        sortie.append({
            "titre": o.titre, "artiste": o.artiste or "", "iswc": o.iswc, "isrc": isrcs[0] if isrcs else None,
            "ayants_droit": len(ses_parts), "parts_dep": round(sum(deps), 3) if deps else None, "revenus": round(revenus, 2),
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
