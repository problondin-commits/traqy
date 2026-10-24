"""
Traqy · Import du catalogue et des relevés.

Chaque fichier déposé (CSV, Excel ou ZIP) est reconnu d'après ses colonnes,
puis traduit dans le modèle interne unique (modele.py). Un traducteur par format.

Formats reconnus aujourd'hui :
  - Catalogue Traqy (ayants droit et parts, une ligne par ayant droit et par œuvre)
  - Relevé distributeur détaillé (format lu par l'ancien Colab)
  - Relevés au format Traqy : écoutes, droits d'auteur, synchro et publicité, réseaux sociaux, retenues
"""
import calendar
import hashlib
import io
import math
import re
import zipfile
from datetime import date

import pandas as pd

import controle
from modele import BilanFichier, Categorie, Enregistrement, Import, Oeuvre, Part, Revenu

MOIS_NOMS = {m: i for i, m in enumerate(["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                                          "août", "septembre", "octobre", "novembre", "décembre"], start=1)}
MESSAGES_MAX = 5

# Colonnes du fichier type de catalogue Traqy (les colonnes isrc, code_sacem et projet sont facultatives)
COLONNES_CATALOGUE = ["artiste", "titre", "iswc", "code_sacem", "isrc", "projet", "role", "ayant_droit", "ipi",
                      "part_DEP_%", "part_DR_%", "part_PHONO_%", "societe"]


class ErreurLigne(ValueError):
    pass


# --- Lecture des valeurs ------------------------------------------------------------

def texte(v, garder_non_indique=False):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "-", "–"):
        return None
    if not garder_non_indique and s.lower().startswith("non indiqu"):
        return None
    return s

def nombre(v, colonne):
    s = texte(v)
    if s is None:
        return None
    s = s.replace(" ", "").replace("\xa0", "").replace(" ", "").replace("€", "").replace("%", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ErreurLigne(f"{colonne} illisible : « {v} »")

def fin_mois(annee, mois):
    return date(annee, mois, calendar.monthrange(annee, mois)[1])

def lire_periode(s):
    """Renvoie (début, fin) quand le libellé de période est reconnu, sinon (None, None)."""
    if not s:
        return None, None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)               # 15/03/2024 : mois de reporting
    if m:
        a, mo = int(m.group(3)), int(m.group(2))
        return date(a, mo, 1), fin_mois(a, mo)
    m = re.search(r"(\d{4})\s*(?:semestre\s*)?S([12])\b", s, re.IGNORECASE)   # 2022 S1, 2022 semestre S1
    if m:
        a, sem = int(m.group(1)), int(m.group(2))
        return (date(a, 1, 1), date(a, 6, 30)) if sem == 1 else (date(a, 7, 1), date(a, 12, 31))
    m = re.search(r"du (\d{1,2}) (\w+) (\d{4})", s, re.IGNORECASE)     # Répartition SACEM 665 du 4 Janvier 2024
    if m and m.group(2).lower() in MOIS_NOMS:
        d = date(int(m.group(3)), MOIS_NOMS[m.group(2).lower()], int(m.group(1)))
        return d, d
    m = re.search(r"\b(\d{1,2})/(\d{4})\b", s)                         # 07/2024, ou « cumul depuis 01/2018 »
    if m:
        a, mo = int(m.group(2)), int(m.group(1))
        return date(a, mo, 1), (None if "cumul" in s.lower() else fin_mois(a, mo))
    return None, None


# --- Lecture des fichiers -------------------------------------------------------------

def lire_csv(brut):
    for enc in ("utf-8-sig", "cp1252"):
        try:
            contenu = brut.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    entete = contenu.split("\n", 1)[0]
    sep = max([";", ",", "\t"], key=entete.count)
    return pd.read_csv(io.StringIO(contenu), sep=sep, dtype=str, keep_default_na=False)

def tableaux(nom, brut, bilans):
    """Renvoie la liste des (nom affiché, tableau) contenus dans un fichier déposé."""
    bas = nom.lower()
    if bas.endswith(".zip"):
        try:
            archive = zipfile.ZipFile(io.BytesIO(brut))
        except zipfile.BadZipFile:
            bilans.append(BilanFichier(fichier=nom, statut="refusé", messages=["Archive ZIP illisible."]))
            return []
        sortie = []
        for info in archive.infolist():
            if info.is_dir() or "__MACOSX" in info.filename or info.filename.split("/")[-1].startswith("."):
                continue
            sortie += tableaux(f"{nom} › {info.filename}", archive.read(info), bilans)
        return sortie
    if bas.endswith((".csv", ".tsv")):
        try:
            return [(nom, lire_csv(brut))]
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
            bilans.append(BilanFichier(fichier=nom, statut="refusé", messages=["Fichier CSV illisible."]))
            return []
    if bas.endswith((".xlsx", ".xlsm")):
        try:
            feuilles = pd.read_excel(io.BytesIO(brut), sheet_name=None, dtype=str, keep_default_na=False)
        except Exception:
            bilans.append(BilanFichier(fichier=nom, statut="refusé", messages=["Fichier Excel illisible."]))
            return []
        return [(f"{nom} › {feuille}", d) for feuille, d in feuilles.items()]
    bilans.append(BilanFichier(fichier=nom, statut="ignoré", messages=["Type de fichier non pris en charge (CSV, Excel ou ZIP attendu)."]))
    return []


# --- Traducteurs ------------------------------------------------------------------------

# Relevés au format Traqy : catégorie et correspondance champ Traqy -> colonne du fichier
RELEVES_TRAQY = [
    ("Relevé Traqy · écoutes", {"isrc", "nombre_ecoutes", "montant", "periode"}, Categorie.streaming,
     {"titre": "titre", "artiste": "artiste", "isrc": "isrc", "periode": "periode", "payeur": "distributeur",
      "plateforme": "plateforme", "pays": "pays_territoire", "quantite": "nombre_ecoutes", "montant": "montant", "devise": "devise"}),
    ("Relevé Traqy · droits d'auteur", {"iswc", "code_oeuvre_sacem", "societe_ou_payeur", "montant"}, Categorie.droits_auteur,
     {"titre": "titre", "artiste": "artiste", "iswc": "iswc", "code_sacem": "code_oeuvre_sacem", "periode": "periode",
      "payeur": "societe_ou_payeur", "montant": "montant", "devise": "devise", "beneficiaire": "beneficiaire_du_montant"}),
    ("Relevé Traqy · synchro et publicité", {"client_ou_marque", "type_usage", "montant"}, Categorie.synchro,
     {"titre": "titre", "artiste": "artiste", "periode": "date", "payeur": "client_ou_marque", "pays": "territoire",
      "montant": "montant", "devise": "devise"}),
    ("Relevé Traqy · réseaux sociaux", {"nombre_videos_utilisant_le_son", "nombre_vues", "montant"}, Categorie.reseaux_sociaux,
     {"titre": "titre", "artiste": "artiste", "isrc": "isrc", "periode": "periode", "plateforme": "plateforme",
      "quantite": "nombre_vues", "montant": "montant", "devise": "devise"}),
    ("Relevé Traqy · retenues", {"motif", "montant", "plateforme"}, Categorie.retenue,
     {"titre": "titre", "artiste": "artiste", "periode": "mois", "plateforme": "plateforme", "montant": "montant", "devise": "devise"}),
]
CHAMPS_NOMBRE = {"quantite", "montant"}

def traduire_releve_traqy(d, nom, categorie, champs, res, bilan):
    for i, ligne in d.iterrows():
        try:
            valeurs = {}
            for champ, colonne in champs.items():
                if colonne not in d:
                    continue
                v = ligne[colonne]
                valeurs[champ] = nombre(v, colonne) if champ in CHAMPS_NOMBRE else texte(v, garder_non_indique=(champ == "titre"))
        except ErreurLigne as e:
            noter(bilan, f"Ligne {i + 2} ignorée : {e}.")
            continue
        if valeurs.get("isrc") and valeurs.get("titre"):
            res.enregistrements.append(Enregistrement(titre=valeurs["titre"], isrc=valeurs["isrc"].upper(),
                                                      projet=texte(ligne.get("projet")), artiste=valeurs.get("artiste")))
        if categorie == Categorie.droits_auteur and valeurs.get("titre") and (valeurs.get("iswc") or valeurs.get("code_sacem")):
            res.oeuvres.append(Oeuvre(titre=valeurs["titre"], iswc=valeurs.get("iswc"), code_sacem=valeurs.get("code_sacem"),
                                      artiste=valeurs.get("artiste")))
        if valeurs.get("montant") is None:
            noter(bilan, f"Ligne {i + 2} : aucun montant, non importée comme revenu.")
            continue
        valeurs["debut"], valeurs["fin"] = lire_periode(valeurs.get("periode"))
        res.revenus.append(Revenu(categorie=categorie, fichier=nom, ligne=i + 2, **valeurs))
        bilan.lignes_importees += 1

def traduire_distributeur(d, nom, res, bilan):
    """Relevé distributeur détaillé. Tout est importé : ventes, droits voisins, frais et avances, avec contrat et taux de partage."""
    for i, ligne in d.iterrows():
        type_ligne = texte(ligne["type"])
        if type_ligne == "Physical Sales":
            categorie = Categorie.ventes_physiques
        elif type_ligne == "Digital Sales":
            categorie = Categorie.streaming if texte(ligne.get("type dexploitation")) == "Streaming" else Categorie.ventes_numeriques
        elif type_ligne == "Neighboring Rights":
            categorie = Categorie.droits_voisins
        elif type_ligne == "Expense":
            categorie = Categorie.frais
        elif type_ligne == "Advance":
            categorie = Categorie.avance
        else:
            noter(bilan, f"Ligne {i + 2} ignorée : type de ligne inconnu « {type_ligne} ».")
            continue
        try:
            montant, quantite = nombre(ligne["revenu"], "Revenu"), nombre(ligne.get("ventes nettes"), "Ventes nettes")
        except ErreurLigne as e:
            noter(bilan, f"Ligne {i + 2} ignorée : {e}.")
            continue
        if montant is None:
            noter(bilan, f"Ligne {i + 2} : aucun montant, non importée.")
            continue
        periode = texte(ligne["date de reporting"])
        debut, fin = lire_periode(periode)
        isrc = texte(ligne.get("isrc"))
        res.revenus.append(Revenu(categorie=categorie, titre=texte(ligne["titre du produit / description"]),
                                  isrc=isrc.upper() if isrc else None, periode=periode, debut=debut, fin=fin,
                                  plateforme=texte(ligne.get("plateforme")), pays=texte(ligne.get("pays")),
                                  quantite=quantite, montant=montant, devise=texte(ligne.get("devise")),
                                  contrat=texte(ligne.get("numéro de contrat")), taux_partage=texte(ligne.get("taux")),
                                  fichier=nom, ligne=i + 2))
        bilan.lignes_importees += 1

def traduire_catalogue(d, nom, res, bilan):
    col = lambda *noms: next((n for n in noms if n in d), None)
    c_dep, c_dr, c_phono = col("part_dep_%", "part_dep"), col("part_dr_%", "part_dr"), col("part_phono_%", "part_phono")
    for i, ligne in d.iterrows():
        titre, ayant = texte(ligne["titre"], garder_non_indique=True), texte(ligne["ayant_droit"])
        if not titre or not ayant:
            noter(bilan, f"Ligne {i + 2} ignorée : titre ou ayant droit absent.")
            continue
        try:
            parts = {k: nombre(ligne[c], c) if c else None for k, c in (("part_dep", c_dep), ("part_dr", c_dr), ("part_phono", c_phono))}
        except ErreurLigne as e:
            noter(bilan, f"Ligne {i + 2} ignorée : {e}.")
            continue
        iswc, isrc = texte(ligne.get("iswc")), texte(ligne.get("isrc"))
        res.parts.append(Part(titre=titre, iswc=iswc, ayant_droit=ayant, role=texte(ligne.get("role")),
                              ipi=texte(ligne.get("ipi")), societe=texte(ligne.get("societe")), **parts))
        res.oeuvres.append(Oeuvre(titre=titre, iswc=iswc, code_sacem=texte(ligne.get("code_sacem")), artiste=texte(ligne.get("artiste"))))
        if isrc:
            res.enregistrements.append(Enregistrement(titre=titre, isrc=isrc.upper(), projet=texte(ligne.get("projet")),
                                                      artiste=texte(ligne.get("artiste"))))
        bilan.lignes_importees += 1

def noter(bilan, message):
    bilan.lignes_ignorees += 1
    if len(bilan.messages) < MESSAGES_MAX:
        bilan.messages.append(message)
    elif len(bilan.messages) == MESSAGES_MAX:
        bilan.messages.append("Autres lignes ignorées : voir le nombre total.")


# --- Import complet -------------------------------------------------------------------------

def reconnaitre(colonnes):
    if {"type", "titre du produit / description", "date de reporting", "revenu"} <= colonnes:
        return "Relevé distributeur détaillé"
    for nom_format, requises, _, _ in RELEVES_TRAQY:
        if requises <= colonnes:
            return nom_format
    if {"titre", "ayant_droit"} <= colonnes:
        return "Catalogue Traqy (ayants droit et parts)"
    if {"repartition", "annee"} <= colonnes or {"compte_concord", "solde_ouverture"} <= colonnes:
        return "Synthèse (totaux ou soldes)"
    return None

def importer(fichiers):
    """fichiers : liste de (nom, contenu en octets). Renvoie un Import dans le modèle interne."""
    res, vus = Import(), {}
    for nom, brut in fichiers:
        h = hashlib.md5(brut).hexdigest()
        if h in vus:
            res.fichiers.append(BilanFichier(fichier=nom, statut="ignoré", messages=[f"Doublon exact de {vus[h]}."]))
            continue
        vus[h] = nom
        for nom_tab, d in tableaux(nom, brut, res.fichiers):
            d = d.rename(columns=lambda c: str(c).strip().lower())
            format_ = reconnaitre(set(d.columns))
            bilan = BilanFichier(fichier=nom_tab, format=format_, statut="importé")
            if format_ is None:
                bilan.statut = "ignoré"
                bilan.messages.append("Format non reconnu. Colonnes trouvées : " + ", ".join(list(d.columns)[:12]))
            elif format_.startswith("Synthèse"):
                bilan.statut = "ignoré"
                bilan.messages.append("Fichier de totaux ou de soldes : non importé, les lignes détaillées des relevés suffisent.")
            elif format_.startswith("Catalogue"):
                traduire_catalogue(d, nom_tab, res, bilan)
            elif format_.startswith("Relevé distributeur"):
                traduire_distributeur(d, nom_tab, res, bilan)
            else:
                _, _, categorie, champs = next(f for f in RELEVES_TRAQY if f[0] == format_)
                traduire_releve_traqy(d, nom_tab, categorie, champs, res, bilan)
            if bilan.statut == "importé" and bilan.lignes_importees == 0:
                bilan.messages.append("Aucune ligne importée (fichier vide ou sans montant).")
            res.fichiers.append(bilan)
    res.oeuvres = fusionner(res.oeuvres, lambda o: (o.iswc or o.code_sacem or o.titre).lower())
    res.enregistrements = fusionner(res.enregistrements, lambda e: e.isrc)
    res.manques = controle.controler(res)
    res.resume = {
        "fichiers_importes": sum(b.statut == "importé" for b in res.fichiers),
        "fichiers_ignores_ou_refuses": sum(b.statut != "importé" for b in res.fichiers),
        "oeuvres": len(res.oeuvres), "enregistrements": len(res.enregistrements),
        "parts": len(res.parts), "revenus": len(res.revenus), "manques": len(res.manques),
        **{f"revenus_{c.value}": sum(r.categorie == c for r in res.revenus) for c in Categorie},
    }
    return res

def fusionner(elements, cle):
    """Garde un seul élément par clé et complète les champs vides avec les doublons."""
    uniques = {}
    for e in elements:
        k = cle(e)
        if k not in uniques:
            uniques[k] = e
            continue
        for champ, valeur in e.model_dump().items():
            if getattr(uniques[k], champ) is None and valeur is not None:
                setattr(uniques[k], champ, valeur)
    return list(uniques.values())

def modele_catalogue():
    """Fichier type de catalogue Traqy (CSV, séparateur « ; »), avec une ligne d'exemple."""
    exemple = ["Artiste", "Titre de l'œuvre", "T-123.456.789-0", "0000.0000.0000", "FRXXX2600001", "Album",
               "Auteur", "NOM Prénom", "123456789", "50", "50", "50", "SACEM"]
    return ("﻿" + ";".join(COLONNES_CATALOGUE) + "\n" + ";".join(exemple) + "\n").encode("utf-8")
