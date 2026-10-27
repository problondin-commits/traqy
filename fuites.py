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
                               Non chiffré : seul le contrat le dit. Signale aussi les frais facturés deux fois
                               (même libellé, même montant, dans deux relevés différents). Si le client déclare l'avance
                               « versée au client », pas de double comptage possible : l'alerte porte alors sur l'ordre
                               frais / avance et chiffre les frais facturés deux fois (montant lu dans les relevés).
  7. Taux de partage inhabituel : sur un contrat, des lignes de recettes ont un autre taux que le taux habituel du contrat.
                               Estimation : écart de taux × base de ces lignes (lue dans le relevé). À vérifier au contrat.
Avec une fiche contrat déposée par le client (contrats.py) :
  8. Avances récupérées au-delà du résultat : le contrat dit que l'avance ne se compense que sur le résultat
                               (« compensable mais non remboursable »). Montant : avances récupérées − résultat des albums,
                               lus dans les relevés et la fiche contrat. Lecture du contrat à faire confirmer par un avocat.
  9. Dépenses sans accord écrit à vérifier : frais au-delà du seuil d'accord écrit du contrat. Non chiffré : il faut
                               d'abord retrouver les accords.
"""
from collections import defaultdict
from datetime import date

from controle import cle_iswc, cle_titre, euros, pour_cent
from modele import Categorie, Fuite

PREUVES_MAX = 6
DROITS = {Categorie.droits_auteur}
MASTER = {Categorie.streaming, Categorie.ventes_numeriques, Categorie.ventes_physiques}
SERIES = DROITS | MASTER | {Categorie.droits_voisins}
REGLES = ["Solde jamais payé", "Revenus qui s'arrêtent", "Parts incomplètes",
          "Écoutes sans droits d'auteur", "Œuvre sans aucun revenu", "Frais et avance à vérifier",
          "Taux de partage inhabituel", "Avances récupérées au-delà du résultat", "Dépenses sans accord écrit à vérifier"]
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
                action=(f"Demander à {payeur}" if payeur != "payeur non indiqué" else "Demander au distributeur")
                       + f" pourquoi cette œuvre n'est plus payée depuis {libelles[payees[-1]]}.",
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
        tous_frais = [r for r in lignes if r.categorie == Categorie.frais]
        avant_recoupement = lambda r: debut_recoupement and r.debut and r.debut < debut_recoupement
        frais_total = -sum(r.montant or 0 for r in tous_frais)   # net des subventions et avoirs
        credits = sum(r.montant or 0 for r in tous_frais if (r.montant or 0) > 0)
        frais_avant = -sum(r.montant or 0 for r in tous_frais if avant_recoupement(r))
        recettes = sum(r.montant or 0 for r in lignes if r.categorie in RECETTES)
        premieres = min((r.debut for r in lignes if r.categorie in RECETTES and (r.montant or 0) > 0 and r.debut), default=None)
        libelle_premieres = next((r.periode for r in lignes if r.debut == premieres and r.periode), None)
        doublons = frais_en_double(frais)
        en_trop = -sum(r.montant or 0 for _, r in doublons)
        payeur = next((r.payeur for r in lignes if r.payeur), None)
        nom = a.projet or a.contrat
        # Solde du compte juste avant le recoupement : s'il n'a plus bougé depuis, toutes les recettes partent dans l'avance
        solde_debut = sum(r.montant or 0 for r in lignes if avant_recoupement(r))
        fige = debut_recoupement and abs(solde - solde_debut) < 1
        libelle_debut = next((r.periode for r in recoupements if r.debut == debut_recoupement and r.periode), None)
        compte = (f"Frais imputés au contrat {a.contrat} : {euros(frais_total)}"
                  + (f" (après {euros(credits)} de subventions et remboursements)" if credits else "")
                  + (f", dont {euros(frais_avant)} avant le début du recoupement de l'avance" if frais_avant else "")
                  + (f" ; premières recettes en {libelle_premieres}" if libelle_premieres else "") + ". "
                  f"Compte du client : {euros(recettes)} de recettes − {euros(frais_total)} de frais − {euros(recoupe)} "
                  f"d'avance recoupée ({euros(recoupe)} sur {euros(a.montant)}) = {euros(solde)}. ")
        doubles = (f"{len(doublons)} ligne{'s' if len(doublons) > 1 else ''} de frais facturée{'s' if len(doublons) > 1 else ''} "
                   f"deux fois (même libellé, même montant, deux relevés) : {euros(en_trop)} en trop." if doublons else "")
        demander = f"Demander à {payeur}" if payeur else "Demander au distributeur"
        if a.versee_au_client:
            # L'avance a été versée au client : elle n'a pas payé ces frais, pas de double comptage entre frais et avance.
            methode = (compte + f"L'avance de {euros(a.montant)} a été versée au client : elle n'a pas financé ces frais, "
                       "il n'y a donc pas de double comptage entre frais et avance. "
                       + (f"En revanche, le solde n'a plus bougé depuis le début du recoupement ({libelle_debut}) : chaque "
                          "relevé, tout ce qui reste des recettes une fois les frais payés part dans l'avance, et le déficit "
                          "de frais ne baisse jamais. À vérifier : l'ordre que le contrat prévoit pour couvrir les frais et l'avance. "
                          if fige else "À vérifier : l'ordre que le contrat prévoit pour couvrir les frais et l'avance. ")
                       + doubles)
            action = (demander + (f" le remboursement des {euros(en_trop)} de frais facturés deux fois, et" if doublons else "")
                      + f" dans quel ordre le contrat {a.contrat} prévoit de couvrir les frais et l'avance.")
            montant, estimation = (round(en_trop, 2), False) if doublons else (None, False)
        else:
            methode = (compte + "Si l'avance a servi à financer ces frais, la même dépense est payée deux fois : une fois en "
                       "frais, une fois en remboursement d'avance. Si l'avance était sans lien avec ces frais, le calcul est "
                       "normal. Non chiffré : seul le contrat permet de trancher." + (f" À part : {doubles}" if doublons else ""))
            action = (demander + f" si l'avance du contrat {a.contrat} a été versée au client ou a financé ces frais, et le détail des frais"
                      + (f" ; réclamer le remboursement des {euros(en_trop)} facturés deux fois" if doublons else "") + ".")
            montant, estimation = None, False
        sortie.append(Fuite(
            regle=REGLES[5], oeuvre=nom, payeur=payeur, montant=montant, estimation=estimation,
            methode=methode,
            action=action,
            preuves=[f"Facturé deux fois : {r.titre or 'frais'}, {euros(-(r.montant or 0))} (relevé {premier.periode}, "
                     f"ligne {premier.ligne}, puis relevé {r.periode}, ligne {r.ligne})" for premier, r in doublons]
                    + [f"{r.fichier}, ligne {r.ligne} : {r.periode or 'période non indiquée'}, {r.titre or 'frais'}, {euros(r.montant or 0)}"
                       for r in sorted(frais, key=lambda r: r.montant or 0)[:PREUVES_MAX]]))
    return sortie


def frais_en_double(frais):
    """Frais facturés deux fois : même libellé et même montant, dans deux relevés (semestres) différents.
    Renvoie des paires (première ligne, ligne en double). Un libellé daté (ex. « TRA BARRY PARIS 261123 ») désigne
    une dépense précise : la retrouver à l'identique dans un autre relevé indique une refacturation."""
    vus, doublons = {}, []
    for r in sorted(frais, key=lambda r: (r.debut or r.fin or date.min, r.ligne or 0)):
        cle = (cle_titre(r.titre), round(r.montant or 0, 2))
        if not r.titre or cle not in vus:
            vus.setdefault(cle, r)
        elif vus[cle].periode != r.periode:
            doublons.append((vus[cle], r))
    return doublons

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


def avances_au_dela_du_resultat(imp):
    """Règle 8 : avances récupérées au-delà du résultat, quand le contrat ne les compense que sur le résultat."""
    import contrats
    c, lecture = contrats.contrat_actif(imp), contrats.lecture(imp)
    if not lecture or not lecture["avances_non_remboursables"] or not lecture["ecart"]:
        return []
    payeur = next((r.payeur for r in imp.revenus if r.payeur and r.contrat in {a["contrat"] for a in c.albums}), None)
    res = "; ".join(f"{r['album']} {euros(r['resultat'])}"
                    + (f" (dont {euros(r['anterieur'])} avant le premier relevé détaillé, source : {r['anterieur_source']})"
                       if r["anterieur"] is not None else "") for r in lecture["resultats"])
    preuves = []
    for a in contrats.avances(imp, c):
        detail = ", ".join(f"{euros(p['recoupe'])} sur {p['album']}" + (" avant les relevés" if p.get("avant_releves") else "")
                           for p in a["par_album"])
        preuves.append(f"{a['nom']} : {euros(a['recoupe'])} récupérés sur {euros(a['montant'])} ({detail})")
    clause = next((x for x in c.clauses if "11" in str(x.get("article", ""))), None)
    return [Fuite(
        regle=REGLES[7], oeuvre=c.nom + (f" du {c.date_signature:%d/%m/%Y}" if c.date_signature else ""), payeur=payeur, montant=lecture["ecart"], estimation=True,
        methode=(f"Avances récupérées : {euros(lecture['avances_recuperees'])}. Résultat des albums (recettes − frais) : "
                 f"{euros(lecture['resultat_total'])} ({res}). Écart : {euros(lecture['ecart'])}. "
                 + (f"{clause['article']} : {clause['texte']} " if clause else "")
                 + "Si l'avance ne se compense que sur le résultat, la part récupérée au-delà n'avait pas à l'être. "
                 + (c.avertissement or "Lecture du contrat à faire confirmer par un avocat.")),
        action=("Faire confirmer la lecture du contrat par un avocat, puis demander " + (f"à {payeur}" if payeur else "au distributeur")
                + " le détail du compte de chaque album et la restitution de ce qui a été récupéré au-delà du résultat."),
        preuves=preuves)]


def depenses_sans_accord(imp):
    """Règle 9 : dépenses au-delà du seuil d'accord écrit du contrat. Non chiffré tant que les accords ne sont pas retrouvés."""
    import contrats
    c = contrats.contrat_actif(imp)
    lignes = contrats.depenses_sans_accord(imp, c)
    if not lignes:
        return []
    part = sum(-r.montant for r, _, _ in lignes)
    total = sum(t for _, t, _ in lignes)
    par_album = defaultdict(int)
    for _, _, album in lignes:
        par_album[album] += 1
    clause = next((x for x in c.clauses if "8.3" in str(x.get("article", ""))), None)
    seuil = f"{c.seuil_accord_depenses:,.0f} € HT".replace(",", " ")
    return [Fuite(
        regle=REGLES[8], oeuvre=f"Dépenses de plus de {seuil}", montant=None, estimation=True,
        payeur=next((r.payeur for r, _, _ in lignes if r.payeur), None),
        methode=(f"{len(lignes)} lignes de frais dépassent {seuil} au total, avant partage "
                 f"({', '.join(f'{n} sur {a}' for a, n in par_album.items())}), soit {euros(total)} HT, dont {euros(part)} "
                 "à la charge du client. Total HT = part du client ÷ son taux de partage ; lignes regroupées par libellé et semestre. "
                 + (f"{clause['article']} : {clause['texte']} " if clause else "")
                 + "Non chiffré : une dépense sans accord écrit n'avait pas à être imputée, mais il faut d'abord retrouver les accords."),
        action="Retrouver l'accord écrit donné pour chacune de ces dépenses ; pour celles sans accord, demander leur retrait du compte.",
        preuves=[f"{album}, {r.periode} : {r.titre or 'frais'}, {euros(t)} HT (part du client {euros(-r.montant)})"
                 for r, t, album in lignes[:PREUVES_MAX]])]


def detecter(imp):
    revenus = [r for r in imp.revenus if r.categorie not in (Categorie.frais, Categorie.avance)]
    tout = (soldes_non_payes(imp) + revenus_interrompus(revenus) + parts_incompletes(imp, revenus)
            + sans_droits_ni_revenus(imp, revenus) + frais_et_avance(imp) + taux_inhabituels(imp)
            + avances_au_dela_du_resultat(imp) + depenses_sans_accord(imp))
    return sorted(tout, key=lambda f: (f.montant is None, -(f.montant or 0), REGLES.index(f.regle)))
