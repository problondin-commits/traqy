"""
Traqy · Couche Fuites : droits non perçus dans les relevés du client.

Cinq règles, chiffrées uniquement avec les données du client (aucun taux par défaut) :
  1. Soldes jamais payés     : un compte termine en faveur du client, sans paiement visible. Montant lu dans le relevé.
  2. Revenus qui s'arrêtent  : une œuvre payée régulièrement ne l'est plus, alors que le payeur continue de payer les autres.
                               Estimation : moyenne de ses derniers paiements × périodes sans paiement.
  3. Parts incomplètes       : les parts d'une œuvre font moins de 100 %. Estimation : revenus relevés de l'œuvre × part manquante.
  4. Écoutes sans droits d'auteur : l'enregistrement rapporte, son œuvre ne touche aucun droit d'auteur. Non chiffré.
  5. Œuvres sans aucun revenu : l'œuvre est au catalogue mais n'apparaît dans aucun relevé. Non chiffré.
"""
from collections import defaultdict

from controle import cle_iswc, cle_titre, euros, pour_cent
from modele import Categorie, Fuite

PREUVES_MAX = 6
DROITS = {Categorie.droits_auteur}
MASTER = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques}
SERIES = DROITS | MASTER | {Categorie.droits_voisins}
REGLES = ["Solde jamais payé", "Revenus qui s'arrêtent", "Parts incomplètes",
          "Écoutes sans droits d'auteur", "Œuvre sans aucun revenu"]


def preuve(r):
    return f"{r.fichier}, ligne {r.ligne} : {r.periode or 'période non indiquée'}, {euros(r.montant or 0)}"

def cle_oeuvre(r):
    if r.categorie in DROITS:
        return cle_iswc(r.iswc) or r.code_sacem or cle_titre(r.titre)
    return r.isrc or cle_titre(r.titre)


def soldes_non_payes(imp):
    """Règle 1 : dernier solde de chaque compte. Positif = somme due au client, non versée à la date du relevé."""
    sortie, comptes = [], defaultdict(list)
    for s in imp.soldes:
        comptes[(s.payeur, s.compte)].append(s)
    for (payeur, compte), liste in comptes.items():
        liste.sort(key=lambda s: (s.debut is None, s.debut))
        connus = [i for i, s in enumerate(liste) if s.cloture is not None]
        if not connus:
            continue
        dernier = liste[connus[-1]]
        # Périodes suivantes sans solde de clôture : leurs royalties s'ajoutent au dernier solde connu
        apres = [s for s in liste[connus[-1] + 1:] if s.royalties]
        du = dernier.cloture + sum(s.royalties for s in apres)
        if du <= 0:
            continue
        methode = f"Solde de clôture du compte {compte} au {dernier.periode or 'dernier relevé'} ({euros(dernier.cloture)}), lu dans le relevé"
        if apres:
            methode += ", plus les royalties des périodes suivantes, sans solde indiqué (" + \
                       ", ".join(f"{s.periode} : {euros(s.royalties)}" for s in apres) + ")"
        sortie.append(Fuite(
            regle=REGLES[0], payeur=payeur, montant=round(du, 2), estimation=False, methode=methode + ".",
            action=f"Réclamer le versement du solde à {payeur or 'ce payeur'}.",
            preuves=[f"{s.fichier}, ligne {s.ligne} : {s.periode}, ouverture {euros(s.ouverture or 0)}, royalties {euros(s.royalties or 0)}, "
                     f"clôture {euros(s.cloture) if s.cloture is not None else 'non indiquée'}" for s in liste[-4:]]))
    return sortie

def revenus_interrompus(revenus):
    """Règle 2 : par payeur, une œuvre payée au moins 3 fois puis absente des périodes suivantes du même payeur."""
    sortie = []
    par_payeur = defaultdict(list)
    for r in revenus:
        if r.categorie in SERIES and r.debut and r.fin and r.montant is not None:
            par_payeur[r.payeur or "payeur non indiqué"].append(r)
    for payeur, lignes in par_payeur.items():
        periodes = sorted({r.debut for r in lignes})
        libelles = {}
        for r in lignes:
            libelles.setdefault(r.debut, r.periode)
        par_oeuvre = defaultdict(list)
        for r in lignes:
            par_oeuvre[cle_oeuvre(r)].append(r)
        for liste in par_oeuvre.values():
            montants = defaultdict(float)
            for r in liste:
                montants[r.debut] += r.montant
            payees = sorted(d for d, m in montants.items() if m > 0)
            if len(payees) < 3:
                continue
            manquees = [p for p in periodes if p > payees[-1]]
            if not manquees:
                continue
            derniers = [montants[d] for d in payees[-4:]]
            moyenne = sum(derniers) / len(derniers)
            exemple = liste[0]
            sortie.append(Fuite(
                regle=REGLES[1], oeuvre=exemple.titre, iswc=exemple.iswc, isrc=exemple.isrc, payeur=payeur,
                montant=round(moyenne * len(manquees), 2),
                methode=f"Moyenne des {len(derniers)} derniers paiements ({euros(moyenne)}) × {len(manquees)} périodes sans paiement "
                        f"({', '.join(libelles[p] for p in manquees[:4])}{'…' if len(manquees) > 4 else ''}).",
                action=f"Demander à {payeur} pourquoi cette œuvre n'est plus payée depuis {libelles[payees[-1]]}.",
                preuves=[preuve(r) for r in sorted(liste, key=lambda r: r.debut)[-PREUVES_MAX:]]))
    return sortie

def parts_incompletes(imp, revenus):
    """Règle 3 : parts inférieures à 100 %. La part manquante n'est versée à personne."""
    sortie, par_oeuvre = [], defaultdict(list)
    for p in imp.parts:
        par_oeuvre[cle_iswc(p.iswc) or cle_titre(p.titre)].append(p)
    droits = [r for r in revenus if r.categorie in DROITS]
    for liste in par_oeuvre.values():
        ecarts = []
        for k, nom in (("part_dep", "DEP"), ("part_dr", "DR"), ("part_phono", "PHONO")):
            if any(getattr(p, k) is not None for p in liste):
                total = sum(getattr(p, k) or 0 for p in liste)
                if total < 100 - 0.1:
                    ecarts.append((100 - total, nom, total))
        if not ecarts:
            continue
        manque, nom, total = max(ecarts)
        p0 = liste[0]
        lignes = [r for r in droits if (p0.iswc and cle_iswc(r.iswc) == cle_iswc(p0.iswc)) or cle_titre(r.titre) == cle_titre(p0.titre)]
        recu = sum(r.montant or 0 for r in lignes)
        sortie.append(Fuite(
            regle=REGLES[2], oeuvre=p0.titre, iswc=p0.iswc, payeur="SACEM",
            montant=round(recu * manque / 100, 2) if recu > 0 else None,
            methode=f"Parts {nom} déclarées : {pour_cent(round(total, 3))}. Part manquante : {pour_cent(round(manque, 3))}. "
                    + (f"Revenus relevés de l'œuvre ({euros(recu)}) × part manquante." if recu > 0 else "Aucun revenu relevé : non chiffré."),
            action="Compléter la déclaration de l'œuvre auprès de la SACEM, puis réclamer la part non répartie.",
            preuves=[f"{p.ayant_droit} ({p.role or 'rôle non indiqué'}) : {nom} {pour_cent(getattr(p, 'part_' + nom.lower()) or 0)}"
                     for p in liste][:PREUVES_MAX]))
    return sortie

def sans_droits_ni_revenus(imp, revenus):
    """Règles 4 et 5 : œuvres du catalogue sans droits d'auteur (mais avec revenus master), ou sans aucun revenu."""
    sortie = []
    droits = [r for r in revenus if r.categorie in DROITS]
    payees_iswc = {cle_iswc(r.iswc) for r in droits if r.iswc}
    payees_code = {r.code_sacem for r in droits if r.code_sacem}
    payees_titre = {cle_titre(r.titre) for r in droits}
    master = defaultdict(list)
    for r in revenus:
        if r.categorie in MASTER and r.isrc:
            master[r.isrc].append(r)
    isrc_par_oeuvre = defaultdict(list)
    for e in imp.enregistrements:
        if e.iswc:
            isrc_par_oeuvre[cle_iswc(e.iswc)].append(e.isrc)
    catalogue = {cle_iswc(p.iswc) or cle_titre(p.titre) for p in imp.parts}
    for o in imp.oeuvres:
        cle = cle_iswc(o.iswc) or cle_titre(o.titre)
        if cle not in catalogue and not isrc_par_oeuvre.get(cle_iswc(o.iswc)):
            continue   # œuvre connue seulement par un relevé : elle a donc un revenu
        a_des_droits = (o.iswc and cle_iswc(o.iswc) in payees_iswc) or (o.code_sacem in payees_code) or cle_titre(o.titre) in payees_titre
        if a_des_droits:
            continue
        lignes_master = [r for isrc in isrc_par_oeuvre.get(cle_iswc(o.iswc), []) for r in master.get(isrc, [])]
        if lignes_master and droits:
            recu = sum(r.montant or 0 for r in lignes_master)
            sortie.append(Fuite(
                regle=REGLES[3], oeuvre=o.titre, iswc=o.iswc, isrc=lignes_master[0].isrc, payeur="SACEM",
                montant=None,
                methode=f"L'enregistrement a rapporté {euros(recu)} (droits master), mais l'œuvre n'apparaît dans aucun relevé "
                        "de droits d'auteur. Non chiffré : aucun taux par défaut.",
                action="Vérifier que l'œuvre est déclarée à la SACEM avec son ISWC, et réclamer les droits d'auteur des écoutes.",
                preuves=[preuve(r) for r in lignes_master[:PREUVES_MAX]]))
        elif not lignes_master and revenus:
            sortie.append(Fuite(
                regle=REGLES[4], oeuvre=o.titre, iswc=o.iswc, payeur=None, montant=None,
                methode="L'œuvre est au catalogue mais n'apparaît dans aucun relevé déposé. Non chiffré.",
                action="Vérifier sa déclaration (SACEM, distributeur) et demander les relevés qui la concernent.",
                preuves=[f"Catalogue : {o.titre}" + (f" (ISWC {o.iswc})" if o.iswc else "")]))
    return sortie


def detecter(imp):
    revenus = [r for r in imp.revenus if r.categorie not in (Categorie.frais, Categorie.avance)]
    tout = (soldes_non_payes(imp) + revenus_interrompus(revenus) + parts_incompletes(imp, revenus)
            + sans_droits_ni_revenus(imp, revenus))
    return sorted(tout, key=lambda f: (f.montant is None, -(f.montant or 0), REGLES.index(f.regle)))
