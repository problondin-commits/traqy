"""
Traqy · Contrôle des manques.

Après l'import, liste ce qui manque dans les fichiers déposés par le client,
classé par importance, avec ce qu'il faut lui demander.
"""
import re
from collections import Counter, defaultdict

from modele import Categorie, Gravite, Manque

EXEMPLES_MAX = 5
VENTES = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques}
ORDRE = {Gravite.bloquant: 0, Gravite.important: 1, Gravite.a_completer: 2}


def cle_iswc(s):
    return re.sub(r"[^0-9A-Z]", "", s.upper()) if s else None

def cle_titre(s):
    return re.sub(r"\s+", " ", s.strip().lower()) if s else None

def euros(montant):
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")

def pour_cent(v):
    return f"{v:g} %".replace(".", ",")

def exemples(elements):
    elements = list(dict.fromkeys(e for e in elements if e))
    return elements[:EXEMPLES_MAX] + ([f"… et {len(elements) - EXEMPLES_MAX} autres"] if len(elements) > EXEMPLES_MAX else [])

def libelle_periode(indice, pas):
    annee, mois = divmod(indice, 12)
    if pas == 6:
        return f"{annee} S{1 if mois < 6 else 2}"
    return f"{mois + 1:02d}/{annee}"


def controler(imp):
    manques = []
    ajouter = lambda **k: manques.append(Manque(**k))
    revenus = [r for r in imp.revenus if r.categorie not in (Categorie.frais, Categorie.avance)]

    if not imp.parts:
        ajouter(gravite=Gravite.bloquant, sujet="Catalogue absent",
                constat="Aucun fichier d'ayants droit et de parts n'a été déposé.",
                action="Demander au client son catalogue : œuvres, ISWC, ayants droit, IPI et parts (fichier type Traqy).")
    if not revenus:
        ajouter(gravite=Gravite.bloquant, sujet="Relevés absents",
                constat="Aucun relevé de revenus n'a été déposé.",
                action="Demander au client ses relevés : distributeur, SACEM, éditeurs, synchro.")

    # --- Catalogue ---------------------------------------------------------------------
    sans_iswc = [o for o in imp.oeuvres if not o.iswc]
    if sans_iswc:
        aucun_code = sum(1 for o in sans_iswc if not o.code_sacem)
        ajouter(gravite=Gravite.a_completer, sujet="Œuvres sans ISWC", nombre=len(sans_iswc),
                constat=f"{len(sans_iswc)} œuvres n'ont pas d'ISWC, dont {aucun_code} sans code SACEM non plus.",
                action="Demander les ISWC au client ou les retrouver dans son espace SACEM.",
                exemples=exemples(o.titre for o in sans_iswc))

    sans_ipi = sorted({p.ayant_droit for p in imp.parts if not p.ipi})
    if sans_ipi:
        ajouter(gravite=Gravite.a_completer, sujet="Ayants droit sans IPI", nombre=len(sans_ipi),
                constat=f"{len(sans_ipi)} ayants droit n'ont pas de numéro IPI.",
                action="Demander les numéros IPI au client (ils figurent sur les relevés SACEM).",
                exemples=exemples(sans_ipi))

    par_oeuvre = defaultdict(list)
    for p in imp.parts:
        par_oeuvre[cle_iswc(p.iswc) or cle_titre(p.titre)].append(p)
    fausses, absentes = [], []
    for liste in par_oeuvre.values():
        titre = liste[0].titre
        cles = [(k, nom) for k, nom in (("part_dep", "DEP"), ("part_dr", "DR"), ("part_phono", "PHONO"))
                if any(getattr(p, k) is not None for p in liste)]
        if not cles:
            absentes.append(titre)
            continue
        for k, nom in cles:
            total = sum(getattr(p, k) or 0 for p in liste)
            if abs(total - 100) > 0.1:
                fausses.append(f"{titre} ({nom} {pour_cent(round(total, 3))})")
    if fausses:
        ajouter(gravite=Gravite.important, sujet="Parts qui ne font pas 100 %", nombre=len(fausses),
                constat=f"{len(fausses)} répartitions d'œuvres ne totalisent pas 100 %.",
                action="Faire vérifier ces répartitions par le client : une part manquante peut cacher des droits non perçus.",
                exemples=exemples(fausses))
    if absentes:
        ajouter(gravite=Gravite.important, sujet="Parts absentes", nombre=len(absentes),
                constat=f"{len(absentes)} œuvres ont des ayants droit connus mais aucune part en %.",
                action="Demander au client les parts (DEP, DR, PHONO) de ces œuvres.",
                exemples=exemples(absentes))

    # --- Rapprochement catalogue / relevés de droits d'auteur ----------------------------
    droits = [r for r in revenus if r.categorie == Categorie.droits_auteur]
    if imp.parts and droits:
        cat_iswc = {cle_iswc(p.iswc) for p in imp.parts if p.iswc}
        cat_titre = {cle_titre(p.titre) for p in imp.parts}
        connu = lambda iswc, titre: (iswc and cle_iswc(iswc) in cat_iswc) or cle_titre(titre) in cat_titre
        hors = [r for r in droits if not connu(r.iswc, r.titre)]
        if hors:
            titres = {cle_titre(r.titre) for r in hors}
            ajouter(gravite=Gravite.important, sujet="Œuvres payées absentes du catalogue", nombre=len(titres),
                    montant=round(sum(r.montant or 0 for r in hors), 2),
                    constat=f"{len(titres)} œuvres apparaissent dans les relevés mais pas dans le catalogue, "
                            f"pour {euros(sum(r.montant or 0 for r in hors))}.",
                    action="Ajouter ces œuvres au catalogue avec leurs ayants droit et leurs parts.",
                    exemples=exemples(r.titre for r in hors))
        payees_iswc = {cle_iswc(r.iswc) for r in droits if r.iswc}
        payees_titre = {cle_titre(r.titre) for r in droits}
        sans_revenu = [l[0].titre for l in par_oeuvre.values()
                       if not ((l[0].iswc and cle_iswc(l[0].iswc) in payees_iswc) or cle_titre(l[0].titre) in payees_titre)]
        if sans_revenu:
            ajouter(gravite=Gravite.important, sujet="Œuvres du catalogue sans aucun revenu", nombre=len(sans_revenu),
                    constat=f"{len(sans_revenu)} œuvres du catalogue n'apparaissent dans aucun relevé de droits d'auteur. "
                            "C'est une piste de droits non perçus.",
                    action="Vérifier que ces œuvres sont bien déclarées, et demander les relevés manquants.",
                    exemples=exemples(sans_revenu))

    # --- Relevés -------------------------------------------------------------------------
    suites = defaultdict(set)
    for r in revenus:
        if r.debut and r.fin:
            suites[(r.categorie, r.payeur or "payeur non indiqué")].add(r.debut.year * 12 + r.debut.month - 1)
    trous = []
    for (categorie, payeur), indices in sorted(suites.items(), key=lambda s: (s[0][0].value, s[0][1])):
        indices = sorted(indices)
        if len(indices) < 3:
            continue
        pas = Counter(b - a for a, b in zip(indices, indices[1:])).most_common(1)[0][0]
        for a, b in zip(indices, indices[1:]):
            trous += [f"{payeur} : {libelle_periode(k, pas)}" for k in range(a + pas, b, pas)]
    if trous:
        ajouter(gravite=Gravite.important, sujet="Périodes manquantes dans les relevés", nombre=len(trous),
                constat=f"{len(trous)} périodes manquent dans la suite des relevés.",
                action="Demander au client les relevés de ces périodes.",
                exemples=exemples(trous))

    cumuls = [r for r in revenus if r.debut and not r.fin]
    if cumuls:
        ajouter(gravite=Gravite.a_completer, sujet="Montants cumulés sans détail", nombre=len(cumuls),
                montant=round(sum(r.montant or 0 for r in cumuls), 2),
                constat=f"{len(cumuls)} lignes donnent un montant cumulé sur plusieurs années, sans détail mois par mois "
                        f"({euros(sum(r.montant or 0 for r in cumuls))}).",
                action="Demander les relevés détaillés, mois par mois.",
                exemples=exemples(r.titre for r in cumuls))

    illisibles = [r for r in revenus if not r.debut]
    if illisibles:
        ajouter(gravite=Gravite.a_completer, sujet="Période illisible", nombre=len(illisibles),
                montant=round(sum(r.montant or 0 for r in illisibles), 2),
                constat=f"{len(illisibles)} lignes ont une période absente ou illisible.",
                action="Demander au client la période exacte de ces revenus.",
                exemples=exemples(f"{r.titre} : « {r.periode or 'vide'} »" for r in illisibles))

    sans_detail = [r for r in revenus if r.categorie in VENTES and (not r.plateforme or not r.pays or r.quantite is None)]
    if sans_detail:
        ajouter(gravite=Gravite.a_completer, sujet="Lignes de ventes sans détail", nombre=len(sans_detail),
                montant=round(sum(r.montant or 0 for r in sans_detail), 2),
                constat=f"{len(sans_detail)} lignes de ventes n'indiquent pas la plateforme, le pays ou le nombre d'écoutes.",
                action="Demander les relevés détaillés du distributeur (par plateforme, pays et nombre d'écoutes).",
                exemples=exemples(r.titre for r in sans_detail))

    def rattachable(r):
        if r.categorie in VENTES or r.categorie == Categorie.reseaux_sociaux:
            return bool(r.isrc)
        if r.categorie == Categorie.droits_auteur:
            return bool(r.iswc or r.code_sacem)
        return bool(r.titre) and not r.titre.lower().startswith("non indiqu")
    orphelins = [r for r in revenus if not rattachable(r)]
    if orphelins:
        ajouter(gravite=Gravite.important, sujet="Revenus impossibles à rattacher", nombre=len(orphelins),
                montant=round(sum(r.montant or 0 for r in orphelins), 2),
                constat=f"{len(orphelins)} lignes n'ont ni ISRC, ni ISWC, ni titre exact : impossible de les rattacher à une œuvre "
                        f"({euros(sum(r.montant or 0 for r in orphelins))}).",
                action="Demander au client l'ISRC, l'ISWC ou le titre exact de ces revenus.",
                exemples=exemples(r.titre or f"{r.fichier}, ligne {r.ligne}" for r in orphelins))

    return sorted(manques, key=lambda m: (ORDRE[m.gravite], -(m.montant or 0), -m.nombre))
