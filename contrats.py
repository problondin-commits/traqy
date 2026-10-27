"""
Traqy · Lecture d'un contrat déclaré par le client (modele.Contrat), appliquée à ses relevés.

1. Avances regroupées par avance, pas par compte : une ligne « Advance » rembourse l'avance dont un motif apparaît
   dans son libellé, quel que soit le compte (album) où elle est prélevée. On voit ainsi qui a remboursé quoi.
2. Résultat de chaque album : recettes moins frais de son compte, hors avances et hors royautés d'artiste,
   plus le résultat antérieur au premier relevé détaillé quand le client le déclare (ex. Backstage de Believe).
3. Écart : avances récupérées moins résultat, quand le contrat dit que l'avance ne se compense que sur le résultat.
Tous les montants viennent des relevés ou de la fiche contrat du client ; rien n'est estimé, sauf la fin du recoupement.
"""
import math
from collections import defaultdict
from datetime import date

from modele import Categorie

HORS_RESULTAT = {Categorie.avance, Categorie.retenue}


def _euros(x):
    return f"{x:,.2f} €".replace(",", " ").replace(".", ",")


def contrat_actif(imp):
    """La dernière fiche contrat déposée pour ce client, ou None."""
    return imp.contrats[-1] if imp.contrats else None


def _comptes(c):
    return {a["contrat"]: a.get("titre") or a["contrat"] for a in c.albums}


def lignes_avance(imp, c, avance):
    """Lignes « Advance » des comptes du contrat dont le libellé contient un motif de cette avance."""
    comptes = _comptes(c)
    motifs = avance.get("motifs") or []
    return [r for r in imp.revenus if r.categorie == Categorie.avance and r.contrat in comptes
            and any(m in (r.titre or "") for m in motifs)]


def avances(imp, c=None):
    """Avances du contrat, même forme que vues.avances (pour l'écran, la projection et le rapport),
    avec en plus : nom, part remboursée par chaque album, et la part recoupée avant le premier relevé détaillé."""
    c = c or contrat_actif(imp)
    if c is None:
        return []
    comptes = _comptes(c)
    sortie = []
    for a in c.avances:
        lignes = lignes_avance(imp, c, a)
        par_periode, par_compte = defaultdict(float), defaultdict(float)
        for r in lignes:
            par_periode[(r.debut, r.periode)] += -(r.montant or 0)
            par_compte[r.contrat] += -(r.montant or 0)
        periodes = [{"periode": p, "recoupe": round(m, 2)}
                    for (_, p), m in sorted(par_periode.items(), key=lambda x: (x[0][0] is None, x[0][0]))]
        avant = float(a.get("recoupe_avant_releves") or 0)
        recoupe = avant + sum(par_compte.values())
        montant = float(a["montant"])
        reste = max(montant - recoupe, 0.0)
        estimation = None
        derniers = [x["recoupe"] for x in periodes[-2:] if x["recoupe"] > 0]
        dates = [d for (d, _p) in par_periode if d]
        if reste > 0.005 and derniers and dates:
            rythme = sum(derniers) / len(derniers)
            semestres = math.ceil(reste / rythme)
            dernier = max(dates)
            rang = dernier.year * 2 + (dernier.month > 6) + semestres
            estimation = {
                "periode": f"{rang // 2} S{rang % 2 + 1}", "semestres": semestres, "rythme": round(rythme, 2),
                "methode": f"Reste à recouper ({_euros(reste)}) ÷ moyenne des {len(derniers)} derniers recoupements "
                           f"({_euros(rythme)} par semestre) = {semestres} semestre(s). Estimation, pas un engagement.",
            }
        par_album = [{"album": comptes[k], "contrat": k, "recoupe": round(v, 2)} for k, v in par_compte.items()]
        if avant:
            par_album.insert(0, {"album": comptes.get(a.get("contrat"), a.get("album")), "contrat": a.get("contrat"),
                                 "recoupe": round(avant, 2), "avant_releves": True})
        sortie.append({
            "cle": f"{a.get('contrat')}|{a['nom']}", "nom": a["nom"], "contrat": a.get("contrat") or "", "projet": a["nom"],
            "album": a.get("album"), "montant": montant, "devise": "EUR",
            "recoupe": round(recoupe, 2), "reste": round(reste, 2), "taux": round(min(recoupe / montant, 1.0), 4) if montant else None,
            "recettes": None, "frais": None, "net_verse": None,
            "periodes": periodes, "estimation": estimation,
            "par_album": par_album,
            "avant_releves": {"montant": round(avant, 2), "source": a.get("source_avant_releves")} if avant else None,
            "source": "Montant de l'avance : fiche contrat du client. Recoupement lu dans les relevés, sur tous les albums du contrat",
        })
    return sortie


def resultats(imp, c=None):
    """Résultat de chaque album (recettes - frais), du début jusqu'au dernier relevé."""
    c = c or contrat_actif(imp)
    if c is None:
        return []
    anterieurs = {x["contrat"]: x for x in c.resultats_anterieurs}
    sortie = []
    for compte, titre in _comptes(c).items():
        ant = anterieurs.get(compte)
        limite = date.fromisoformat(ant["jusqu_au"]) if ant and ant.get("jusqu_au") else None
        lignes = [r for r in imp.revenus if r.contrat == compte and r.categorie not in HORS_RESULTAT
                  and (limite is None or (r.debut and r.debut > limite))]
        recettes = sum(r.montant or 0 for r in lignes if r.categorie != Categorie.frais)
        frais = -sum(r.montant or 0 for r in lignes if r.categorie == Categorie.frais)
        anterieur = float(ant["montant"]) if ant else 0.0
        sortie.append({
            "album": titre, "contrat": compte, "recettes": round(recettes, 2), "frais": round(frais, 2),
            "anterieur": round(anterieur, 2) if ant else None, "anterieur_jusqu_au": ant.get("jusqu_au") if ant else None,
            "anterieur_source": ant.get("source") if ant else None,
            "resultat": round(anterieur + recettes - frais, 2),
        })
    return sortie


def _pc(x):
    return f"{x * 100:g} %".replace(".", ",")


def taux_prevus(c):
    """Taux de partage prévus au contrat pour la part du client : {taux arrondi : explication}. Vide sans partage déclaré."""
    if c is None or not c.partage_client:
        return {}
    p, g = c.partage_client, c.commission_gestion
    prevus = {round(p, 4): f"partage à {_pc(p)} prévu au contrat"}
    if g:
        prevus[round(p * (1 - g), 4)] = f"{_pc(p)} moins la commission de gestion de {_pc(g)} prévue au contrat"
    return prevus


def controle_taux(imp, c=None):
    """Taux de partage des recettes des comptes du contrat, comparés aux taux prévus au contrat.
    Renvoie un résumé par taux (montant de la part du client, conforme ou non) ; None sans taux déclaré."""
    from fuites import RECETTES, lire_taux
    c = c or contrat_actif(imp)
    prevus = taux_prevus(c)
    if not prevus:
        return None
    comptes = _comptes(c)
    par_taux = defaultdict(float)
    for r in imp.revenus:
        t = lire_taux(r.taux_partage)
        if r.contrat in comptes and r.categorie in RECETTES and t and t > 0:
            par_taux[round(t, 4)] += r.montant or 0
    taux = [{"taux": t, "montant": round(m, 2), "conforme": t in prevus, "explication": prevus.get(t)}
            for t, m in sorted(par_taux.items(), key=lambda x: -x[1])]
    return {"taux": taux, "hors_contrat": round(sum(x["montant"] for x in taux if not x["conforme"]), 2)}


def lecture(imp):
    """Tout ce que l'écran affiche du contrat : fiche, avances regroupées, résultat, écart. None sans fiche contrat."""
    c = contrat_actif(imp)
    if c is None:
        return None
    av, res = avances(imp, c), resultats(imp, c)
    recupere = round(sum(a["recoupe"] for a in av), 2)
    resultat = round(sum(r["resultat"] for r in res), 2)
    ecart = round(recupere - max(resultat, 0.0), 2) if c.avances_non_remboursables else None
    return {
        "nom": c.nom, "parties": c.parties, "date_signature": c.date_signature.isoformat() if c.date_signature else None,
        "albums": c.albums, "clauses": c.clauses, "avertissement": c.avertissement, "sources": c.sources,
        "avances_non_remboursables": c.avances_non_remboursables, "seuil_accord_depenses": c.seuil_accord_depenses,
        "resultats": res, "resultat_total": resultat, "avances_recuperees": recupere,
        "avances_declarees": round(sum(float(a["montant"]) for a in c.avances), 2),
        "ecart": ecart if ecart is None or ecart > 0.005 else 0.0,
        "controle_taux": controle_taux(imp, c),
    }


def depenses_sans_accord(imp, c=None):
    """Lignes de frais des comptes du contrat dont le montant total HT (avant partage) dépasse le seuil d'accord écrit.
    Montant total = part du client ÷ son taux de partage (ex. 50 %). Lignes regroupées par libellé et semestre."""
    from fuites import lire_taux
    c = c or contrat_actif(imp)
    if c is None or not c.seuil_accord_depenses:
        return []
    comptes = _comptes(c)
    sortie = []
    for r in imp.revenus:
        if r.categorie != Categorie.frais or r.contrat not in comptes or not r.montant or r.montant >= 0:
            continue
        taux = lire_taux(r.taux_partage)
        total = -r.montant / taux if taux else None
        if total is not None and total > c.seuil_accord_depenses:
            sortie.append((r, total, comptes[r.contrat]))
    return sorted(sortie, key=lambda x: -x[1])
