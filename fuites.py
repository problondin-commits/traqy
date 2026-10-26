"""
Traqy · Couche Fuites : droits non perçus dans les relevés du client.

Cinq règles, chiffrées uniquement avec les données du client (aucun taux par défaut) :
  1. Soldes jamais payés     : un compte termine en faveur du client, sans paiement visible. Montant lu dans le relevé.
  2. Revenus qui s'arrêtent  : une œuvre payée régulièrement ne l'est plus, alors que le payeur continue de payer les autres.
                               Estimation : moyenne de ses derniers paiements × périodes sans paiement.
  3. Parts incomplètes       : les parts d'une œuvre font moins de 100 %. Estimation : revenus relevés de l'œuvre × part manquante.
  4. Écoutes sans droits d'auteur : l'enregistrement rapporte, son œuvre ne touche aucun droit d'auteur. Non chiffré.
  5. Œuvres sans aucun revenu : l'œuvre est au catalogue mais n'apparaît dans aucun relevé. Non chiffré.
  6. Frais et avance à vérifier : un contrat avec avance reste négatif à cause de frais imputés, alors que l'avance est
                               recoupée sur toute la part du client. Si l'avance a financé ces frais, la dépense compte deux fois.
                               Non chiffré : seul le contrat le dit.
  7. Taux de partage inhabituel : sur un contrat, des lignes de recettes ont un autre taux que le taux habituel du contrat.
                               Estimation : écart de taux × base de ces lignes (lue dans le relevé). À vérifier au contrat.
"""
from collections import defaultdict

from controle import cle_iswc, cle_titre, euros, pour_cent
from modele import Categorie, Fuite

PREUVES_MAX = 6
DROITS = {Categorie.droits_auteur}
MASTER = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques}
SERIES = DROITS | MASTER | {Categorie.droits_voisins}
REGLES = ["Solde jamais payé", "Revenus qui s'arrêtent", "Parts incomplètes",
          "Écoutes sans droits d'auteur", "Œuvre sans aucun revenu", "Frais et avance à vérifier",
          "Taux de partage inhabituel"]
RECETTES = MASTER | {Categorie.droits_voisins, Categorie.autres_revenus}


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
            preuves=[f"{s.fichier}, ligne {s.ligne} : {s.periode}, "
                     f"ouverture {euros(s.ouverture) if s.ouverture is not None else 'non indiquée'}, "
                     f"royalties {euros(s.royalties) if s.royalties is not None else 'non indiquées'}, "
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


def frais_et_avance(imp):
    """Règle 6 : contrat avec avance déclarée, compte négatif à cause des frais, avance pourtant recoupée sur les recettes."""
    sortie = []
    for a in imp.avances:
        lignes = [r for r in imp.revenus if r.contrat == a.contrat and r.categorie != Categorie.retenue]
        recoupements = [r for r in lignes if r.categorie == Categorie.avance]
        frais = [r for r in lignes if r.categorie == Categorie.frais and (r.montant or 0) < 0]
        recoupe = -sum(r.montant or 0 for r in recoupements)
        solde = sum(r.montant or 0 for r in lignes)
        if recoupe <= 0 or solde >= -1 or not frais:
            continue
        debut_recoupement = min((r.debut for r in recoupements if r.debut), default=None)
        avant = [r for r in frais if debut_recoupement and r.debut and r.debut < debut_recoupement]
        frais_total = -sum(r.montant or 0 for r in lignes if r.categorie == Categorie.frais)   # net des avoirs éventuels
        frais_avant = -sum(r.montant or 0 for r in avant)
        payeur = next((r.payeur for r in lignes if r.payeur), None) or "le distributeur"
        nom = a.projet or a.contrat
        sortie.append(Fuite(
            regle=REGLES[5], oeuvre=nom, payeur=payeur if payeur != "le distributeur" else None, montant=None,
            methode=(f"Frais imputés au contrat {a.contrat} : {euros(frais_total)}"
                     + (f", dont {euros(frais_avant)} avant les premières recettes" if frais_avant else "") + ". "
                     f"Depuis, la part du client sert à recouper l'avance ({euros(recoupe)} recoupés sur {euros(a.montant)}), "
                     f"sans réduire ces frais : le compte reste à {euros(solde)}. Si l'avance a servi à financer ces frais, "
                     "la même dépense est comptée deux fois. Non chiffré : seul le contrat permet de trancher."),
            action=(f"Demander à {payeur} le détail des frais du contrat {a.contrat}, et vérifier dans le contrat s'ils sont "
                    "financés par l'avance ou à la charge du compte."),
            preuves=[f"{r.fichier}, ligne {r.ligne} : {r.periode or 'période non indiquée'}, {r.titre or 'frais'}, {euros(r.montant or 0)}"
                     for r in sorted(frais, key=lambda r: r.montant or 0)[:PREUVES_MAX]]))
    return sortie

def lire_taux(s):
    try:
        return float(str(s).replace("%", "").replace(",", ".").strip()) / 100
    except (TypeError, ValueError):
        return None

def taux_inhabituels(imp):
    """Règle 7 : lignes de recettes d'un contrat avec un autre taux que le taux habituel de ce contrat."""
    sortie, par_contrat = [], defaultdict(list)
    for r in imp.revenus:
        t = lire_taux(r.taux_partage)
        if r.contrat and r.categorie in RECETTES and t and t > 0:
            par_contrat[r.contrat].append((r, t))
    for contrat, lignes in par_contrat.items():
        poids = defaultdict(float)
        for r, t in lignes:
            poids[t] += abs(r.montant or 0)
        habituel = max(poids, key=poids.get)
        autres = [(r, t) for r, t in lignes if abs(t - habituel) > 1e-6 and (r.montant or 0) > 0]
        if not autres:
            continue
        ecart = sum((r.montant / t) * (habituel - t) for r, t in autres)
        if abs(ecart) < 1:
            continue
        taux = sorted({t for _, t in autres})
        sortie.append(Fuite(
            regle=REGLES[6], oeuvre=f"Contrat {contrat}", payeur=next((r.payeur for r, _ in autres if r.payeur), None),
            montant=round(ecart, 2) if ecart > 0 else None,
            methode=(f"Taux habituel du contrat : {pour_cent(round(habituel * 100, 2))}. {len(autres)} ligne(s) de recettes à "
                     f"{', '.join(pour_cent(round(t * 100, 2)) for t in taux)}. Écart estimé : base de ces lignes × différence de taux. "
                     "C'est peut-être prévu au contrat (par exemple pour le merchandising) : à vérifier."),
            action="Vérifier dans le contrat si ce taux est prévu pour ces recettes ; sinon, réclamer la différence.",
            preuves=[f"{r.fichier}, ligne {r.ligne} : {r.periode or 'période non indiquée'}, {r.titre or 'recette'}, "
                     f"taux {r.taux_partage}, {euros(r.montant or 0)}" for r, _ in autres[:PREUVES_MAX]]))
    return sortie


def detecter(imp):
    revenus = [r for r in imp.revenus if r.categorie not in (Categorie.frais, Categorie.avance)]
    tout = (soldes_non_payes(imp) + revenus_interrompus(revenus) + parts_incompletes(imp, revenus)
            + sans_droits_ni_revenus(imp, revenus) + frais_et_avance(imp) + taux_inhabituels(imp))
    return sorted(tout, key=lambda f: (f.montant is None, -(f.montant or 0), REGLES.index(f.regle)))
