"""
Traqy · Rapport d'audit en PDF (A4 portrait), fabriqué à partir de la vue d'un import (vues.vue) :
synthèse, droits non perçus à réclamer, avances, recettes par pays, manques, catalogue, méthode et sources.

Règles : tous les montants viennent des données du client ; chaque estimation est signalée comme telle ;
le mot « IA » n'apparaît pas ; le produit s'appelle uniquement Traqy.
Les polices standard du PDF (Helvetica) ne connaissent que l'alphabet latin courant : les espaces fines
et le signe moins typographique sont donc remplacés par leurs équivalents simples.
"""
import io
import re
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

# Charte Traqy : nuit, blanc cassé, vert menthe du logo (#31F2A4), le même vert partout (décision de Tom)
NUIT = colors.HexColor("#111317")
MENTHE = colors.HexColor("#31F2A4")
MENTHE_TEXTE = colors.HexColor("#10A06A")   # vert du logo, juste assez foncé pour se lire sur fond blanc (contraste 3,4:1)
GRIS = colors.HexColor("#6B7280")
FILET = colors.HexColor("#E5E7EB")
FOND = colors.HexColor("#F6F7F5")
ROUGE = colors.HexColor("#C2410C")
ORANGE = colors.HexColor("#B7791F")

# Noms des pays les plus fréquents dans les relevés (les autres gardent leur code à deux lettres)
PAYS = {"FR": "France", "BE": "Belgique", "CH": "Suisse", "CA": "Canada", "DE": "Allemagne", "US": "États-Unis",
        "GB": "Royaume-Uni", "NL": "Pays-Bas", "LU": "Luxembourg", "SE": "Suède", "ES": "Espagne", "IT": "Italie",
        "PT": "Portugal", "IE": "Irlande", "AT": "Autriche", "DK": "Danemark", "NO": "Norvège", "FI": "Finlande",
        "PL": "Pologne", "MA": "Maroc", "DZ": "Algérie", "TN": "Tunisie", "SN": "Sénégal", "CI": "Côte d'Ivoire",
        "CM": "Cameroun", "CD": "Congo-Kinshasa", "CG": "Congo-Brazzaville", "GA": "Gabon", "ML": "Mali",
        "BF": "Burkina Faso", "BJ": "Bénin", "NE": "Niger", "GN": "Guinée", "MG": "Madagascar", "MR": "Mauritanie",
        "TG": "Togo", "HT": "Haïti", "RE": "La Réunion", "GP": "Guadeloupe", "MQ": "Martinique", "GF": "Guyane",
        "AU": "Australie", "BR": "Brésil", "MX": "Mexique", "JP": "Japon", "TR": "Turquie", "AE": "Émirats arabes unis",
        "IL": "Israël", "ZA": "Afrique du Sud", "NG": "Nigeria", "GR": "Grèce", "RO": "Roumanie", "CZ": "Tchéquie"}

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
SANS_DROITS = ("Écoutes sans droits d'auteur", "Œuvre sans aucun revenu")


# --- Mise en forme ---------------------------------------------------------------------------

def euros(v, decimales=0):
    if v is None:
        return "Non chiffré"
    s = f"{abs(v):,.{decimales}f}".replace(",", " ").replace(".", ",").replace(" ", "\xa0")
    return f"{'-' if v < 0 else ''}{s}\xa0€"

def pc(v, decimales=1):
    return f"{v * 100:.{decimales}f}".replace(".", ",") + "\xa0%"

def t(s):
    """Texte sûr pour un paragraphe : caractères spéciaux échappés, typographie compatible Helvetica."""
    s = str(s if s is not None else "")
    s = s.replace(" ", "\xa0").replace("−", "-").replace("–", "-").replace("—", "-")
    return escape(s)

STYLES = {
    "titre": ParagraphStyle("titre", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=NUIT),
    "sous_titre": ParagraphStyle("sous_titre", fontName="Helvetica", fontSize=10.5, leading=14, textColor=GRIS),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=NUIT, spaceBefore=14, spaceAfter=6, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=NUIT, spaceBefore=6, spaceAfter=2, keepWithNext=1),
    "texte": ParagraphStyle("texte", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=NUIT),
    "petit": ParagraphStyle("petit", fontName="Helvetica", fontSize=8, leading=10.5, textColor=GRIS),
    "cellule": ParagraphStyle("cellule", fontName="Helvetica", fontSize=8.5, leading=11, textColor=NUIT),
    "cellule_d": ParagraphStyle("cellule_d", fontName="Helvetica", fontSize=8.5, leading=11, textColor=NUIT, alignment=TA_RIGHT),
    "entete": ParagraphStyle("entete", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
    "entete_d": ParagraphStyle("entete_d", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=TA_RIGHT),
    "kpi_libelle": ParagraphStyle("kpi_libelle", fontName="Helvetica", fontSize=8, leading=10, textColor=GRIS),
    "kpi_valeur": ParagraphStyle("kpi_valeur", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=NUIT),
    "kpi_detail": ParagraphStyle("kpi_detail", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=GRIS),
}

def p(texte, style="texte"):
    return Paragraph(texte, STYLES[style])

def tableau(entetes, lignes, largeurs, droite=()):
    """Tableau à en-tête nuit, lignes alternées. droite : index des colonnes alignées à droite (montants)."""
    donnees = [[p(t(e), "entete_d" if i in droite else "entete") for i, e in enumerate(entetes)]]
    for l in lignes:
        donnees.append([c if not isinstance(c, str) else p(t(c), "cellule_d" if i in droite else "cellule") for i, c in enumerate(l)])
    tb = Table(donnees, colWidths=largeurs, repeatRows=1)
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NUIT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FOND]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, FILET),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tb

def tuiles(elements, largeur):
    """Rangée de chiffres clés : (libellé, valeur, détail, couleur de la valeur)."""
    cellules = [[p(t(l), "kpi_libelle"), Paragraph(t(v), ParagraphStyle("v", parent=STYLES["kpi_valeur"], textColor=c or NUIT)),
                 p(t(d), "kpi_detail")] for l, v, d, c in elements]
    tb = Table([cellules], colWidths=[largeur / len(elements)] * len(elements))
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FOND), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER", (0, 0), (-2, -1), 3, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tb


# --- Calculs repris de l'interface (mêmes règles que l'écran Catalogue) ----------------------------

def _norm(s):
    import unicodedata
    return unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode().strip()

def _code(s):
    return re.sub(r"[^0-9A-Z]", "", (s or "").upper())

def alertes_de(o, fuites):
    return [f for f in fuites if f.get("decision") != "écartée" and (
        (f.get("iswc") and o.get("iswc") and _code(f["iswc"]) == _code(o["iswc"])) or
        (f.get("oeuvre") and _norm(f["oeuvre"]) == _norm(o["titre"])))]

def controles(o, fuites):
    siennes = alertes_de(o, fuites)
    parts = o.get("parts_dep")
    if o.get("detail") is not None:
        droits = any(d["type"] == "Droits d'auteur" and d["montant"] > 0 for d in o["detail"])
    else:
        droits = not any(f["regle"] in SANS_DROITS for f in siennes)
    return [bool(o.get("iswc")), bool(o.get("isrc")), parts is not None and abs(parts - 100) < 0.1, droits,
            not any((f.get("montant") or 0) > 0 for f in siennes)]

def score_titre(o, fuites):
    c = controles(o, fuites)
    return round(sum(c) / len(c) * 100)

def score_catalogue(lignes, fuites):
    if not lignes:
        return None
    poids = sum(max(o["revenus"], 0) for o in lignes)
    total = sum(score_titre(o, fuites) * (max(o["revenus"], 0) if poids > 0 else 1) for o in lignes)
    return round(total / (poids if poids > 0 else len(lignes)))

def preuve_lisible(s):
    """« 05d_concord_soldes.csv, ligne 12 : 2025 S2, … » -> « Concord soldes, ligne 12 · 2025 S2, … » (fichier gardé en note)."""
    m = re.match(r"^(.+?\.(?:csv|xlsx|xls|zip))(?:\s*›\s*([^,]+))?(?:, ligne (\d+))?(?:\s*:\s*(.*))?$", s, re.IGNORECASE)
    if not m:
        return s, None
    fichier, onglet, ligne, detail = m.groups()
    nom = re.sub(r"\.(csv|xlsx|xls|zip)$", "", fichier.split("/")[-1].split("\\")[-1], flags=re.IGNORECASE)
    nom = re.sub(r"[_\-]+", " ", re.sub(r"^[0-9]+[a-z]?[_\- ]+", "", nom, flags=re.IGNORECASE)).strip() or fichier
    source = ", ".join(x for x in (nom[:1].upper() + nom[1:], (onglet or "").strip() or None, f"ligne {ligne}" if ligne else None) if x)
    return source + (f" · {detail.strip()}" if detail else ""), fichier


# Ce qu'il faut corriger quand chacun des 5 contrôles échoue (même ordre que controles())
A_CORRIGER = ("ISWC manquant", "ISRC manquant", "parts incomplètes ou absentes", "absente des relevés de droits d'auteur",
              "alerte chiffrée ouverte")

def fiche_oeuvre(o, fuites, en_jeu, largeur):
    """Fiche d'une œuvre : titre, codes, score et contrôles manqués, revenus par type de droit, alertes."""
    c = controles(o, fuites)
    s = round(sum(c) / len(c) * 100)
    couleur = "#10A06A" if s == 100 else ("#B7791F" if s >= 60 else "#C2410C")
    manques = [nom for nom, ok in zip(A_CORRIGER, c) if not ok]
    par_type = {}
    for d in o.get("detail") or []:
        par_type[d["type"]] = par_type.get(d["type"], 0) + d["montant"]
    if o.get("parts_dep") is not None:
        parts = pc(o["parts_dep"] / 100, 2)
    else:
        parts = "non renseignées (DEP)" if o.get("ayants_droit") else "absentes"
    gauche = [
        p(f"<b>{t(o['titre'])}</b>" + (f" <font color='#6B7280'>· {t(o['artiste'])}</font>" if o.get("artiste") else ""), "texte"),
        p(f"ISWC {t(o.get('iswc') or 'manquant')} · ISRC {t(o.get('isrc') or 'manquant')} · Parts {parts}"
          + (f" · {o['ayants_droit']} ayants droit" if o.get("ayants_droit") else ""), "petit"),
        p(f"<font color='{couleur}'><b>Score {s} %</b></font>"
          + (f" · à corriger : {t(', '.join(manques))}" if manques else " · tous les contrôles sont réussis"), "petit"),
    ]
    if par_type:
        gauche.append(p("Revenus relevés : " + t(" · ".join(f"{k} {euros(v)}" for k, v in sorted(par_type.items(), key=lambda x: -x[1]))), "petit"))
    for f in alertes_de(o, fuites):
        gauche.append(p(f"<font color='#C2410C'>Alerte</font> · {t(f['regle'])} : <b>{euros(f.get('montant'), 2)}</b>"
                        + (" (estimation)" if f.get("montant") is not None and f.get("estimation") else "")
                        + (" · validée" if f.get("decision") == "validée" else ""), "petit"))
    droite = [p(f"<b>{euros(o['revenus'])}</b>", "cellule_d"), p("revenus relevés", "petit")]
    if en_jeu:
        droite += [Spacer(1, 2), p(f"<font color='#C2410C'><b>{euros(en_jeu, 2 if en_jeu < 100 else 0)}</b></font>", "cellule_d"),
                   p("en jeu", "petit")]
    tb = Table([[gauche, droite]], colWidths=[largeur - 32 * mm, 32 * mm])
    tb.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, FILET),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return [tb]


# --- Le rapport --------------------------------------------------------------------------------------

def generer(vue, aujourdhui=None):
    """vue : réponse de /api/v1/imports/{n}/vue (ou la vue de démonstration). Renvoie le PDF en octets."""
    aujourdhui = aujourdhui or date.today()
    client = vue.get("client") or "Client"
    catalogue, fuites, manques = vue.get("catalogue") or [], vue.get("fuites") or [], vue.get("manques") or []
    avances, pays = vue.get("avances") or [], vue.get("pays") or []
    ouvertes = [f for f in fuites if f.get("decision") != "écartée"]
    ecartees = len(fuites) - len(ouvertes)
    validees = [f for f in ouvertes if f.get("decision") == "validée"]
    chiffre = sum(f.get("montant") or 0 for f in ouvertes)
    releve = sum(f.get("montant") or 0 for f in ouvertes if f.get("montant") is not None and not f.get("estimation"))
    revenus = sum(o["revenus"] for o in catalogue)
    score = score_catalogue(catalogue, fuites)
    importes = [b for b in vue.get("fichiers") or [] if b.get("statut") == "importé"]

    tampon = io.BytesIO()
    marge = 16 * mm
    largeur = A4[0] - 2 * marge
    date_txt = f"{aujourdhui.day} {MOIS[aujourdhui.month - 1]} {aujourdhui.year}"

    def decor(canvas, doc):
        canvas.saveState()
        # Bandeau : symbole Traqy (trois barres et un point) et nom
        canvas.setFillColor(NUIT)
        canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, stroke=0, fill=1)
        canvas.setFillColor(MENTHE)
        x0, y0, k = marge, A4[1] - 11 * mm, 8 * mm / 353          # symbole du logo (249 x 353 unités) ramené à 8 mm de haut
        for x, y, w, hb in ((0, 160, 70, 139), (89, 91, 70, 208), (179, 2, 70, 228)):
            canvas.roundRect(x0 + x * k, y0 + (355 - y - hb) * k, w * k, hb * k, 35 * k, stroke=0, fill=1)
        canvas.circle(x0 + 214 * k, y0 + (355 - 320) * k, 35 * k, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(marge + 8 * mm, A4[1] - 9.4 * mm, "traqy")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#C9CDD3"))
        canvas.drawRightString(A4[0] - marge, A4[1] - 9 * mm, f"Rapport d'audit · {client}".replace(" ", " "))
        # Pied de page
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GRIS)
        canvas.drawString(marge, 9 * mm, "Traqy · Document confidentiel · Montants issus uniquement des données du client")
        canvas.drawRightString(A4[0] - marge, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=marge, rightMargin=marge, topMargin=24 * mm, bottomMargin=18 * mm,
                            title=f"Traqy - Rapport d'audit - {client}", author="Traqy")
    h = []

    # 1. Couverture et chiffres clés
    h += [p("Rapport d'audit", "titre"), Spacer(1, 2 * mm),
          p(t(f"{client} · établi le {date_txt}"), "sous_titre"), Spacer(1, 7 * mm)]
    h.append(tuiles([
        ("Score du catalogue", f"{score} %" if score is not None else "-", "Contrôles réussis, pondérés par les revenus", MENTHE_TEXTE),
        ("Revenus relevés", euros(revenus), f"{len(catalogue)} titres analysés", None),
        ("Droits non perçus chiffrés", euros(chiffre), f"dont {euros(releve)} lus dans les relevés", ROUGE if chiffre > 0 else None),
        ("Alertes", str(len(ouvertes)), f"{len(validees)} validées pour réclamation", None),
    ], largeur))
    h.append(Spacer(1, 5 * mm))

    synthese = (f"Traqy a analysé <b>{len(importes)} fichiers</b> déposés par {t(client)} et contrôlé <b>{len(catalogue)} titres</b>. "
                f"<b>{len(ouvertes)} alertes</b> ont été relevées"
                + (f", dont {len(validees)} validées par le client pour réclamation" if validees else "")
                + (f" ({ecartees} écartées par le client ne figurent pas dans ce rapport)" if ecartees else "") + ". ")
    if chiffre > 0:
        synthese += (f"Les droits non perçus chiffrés atteignent <b>{euros(chiffre)}</b> : {euros(releve)} lus tels quels dans les relevés "
                     f"et {euros(chiffre - releve)} estimés à partir des relevés du client. ")
    if avances:
        synthese += f"{len(avances)} avance(s) en cours de suivi, détaillée(s) plus bas. "
    synthese += "Chaque montant renvoie aux lignes de relevés qui le justifient."
    h += [p("Synthèse", "h2"), p(synthese)]

    # 2. Droits non perçus à réclamer
    h.append(p("Droits non perçus à réclamer", "h2"))
    if ouvertes:
        ordre = sorted(ouvertes, key=lambda f: (f.get("decision") != "validée", -(f.get("montant") or 0)))
        lignes = [[
            "Validée" if f.get("decision") == "validée" else "À décider", f["regle"], f.get("oeuvre") or f.get("payeur") or "-",
            f.get("payeur") or "À identifier", euros(f.get("montant"), 2),
            "-" if f.get("montant") is None else ("Estimation" if f.get("estimation") else "Relevé"),
        ] for f in ordre]
        h.append(tableau(["Statut", "Alerte", "Œuvre ou compte", "À réclamer à", "Montant", "Nature"], lignes,
                         [17 * mm, 34 * mm, 45 * mm, 32 * mm, 23 * mm, largeur - 151 * mm], droite=(4,)))
        h.append(p("Détail et preuves", "h3"))
        for i, f in enumerate(ordre, 1):
            bloc = [p(f"<b>{i}. {t(f.get('oeuvre') or f.get('payeur') or f['regle'])}</b> · {t(f['regle'])} · "
                      f"<font color='#10A06A'><b>{euros(f.get('montant'), 2)}</b></font>"
                      + (" <font color='#6B7280'>(estimation)</font>" if f.get("montant") is not None and f.get("estimation") else ""), "texte"),
                    p(f"<b>Méthode :</b> {t(f.get('methode'))}", "petit")]
            for pr in (f.get("preuves") or [])[:6]:
                source, fichier = preuve_lisible(pr)
                bloc.append(p(f"• {t(source)}" + (f" <font color='#9AA1AD'>(fichier : {t(fichier)})</font>" if fichier else ""), "petit"))
            bloc += [p(f"<b>À faire :</b> {t(f.get('action'))}", "petit"), Spacer(1, 3 * mm)]
            h.append(KeepTogether(bloc))
    else:
        h.append(p("Aucune alerte ouverte pour ce client avec les fichiers déposés."))

    # 3. Avances et recoupement
    if avances:
        h.append(p("Avances et recoupement", "h2"))
        h.append(p("Montant de l'avance déclaré par le client. Le recoupement est lu dans les relevés, semestre par semestre.", "petit"))
        h.append(Spacer(1, 2 * mm))
        lignes = [[a.get("projet") or a["contrat"], euros(a["montant"]), euros(a["recoupe"]),
                   pc(a["taux"]) if a.get("taux") is not None else "-", euros(a["reste"]),
                   "Recoupée" if a["reste"] <= 0 else (f"{a['estimation']['periode']} (estimation)" if a.get("estimation") else "Non estimable"),
                   euros(a.get("net_verse"))] for a in avances]
        h.append(tableau(["Projet", "Avance", "Recoupé", "Part", "Reste", "Fin estimée", "Solde du compte"], lignes,
                         [44 * mm, 21 * mm, 21 * mm, 15 * mm, 20 * mm, 30 * mm, largeur - 151 * mm], droite=(1, 2, 3, 4, 6)))
        for a in avances:
            if a.get("estimation") and a["reste"] > 0:
                h.append(p(t(f"{a.get('projet') or a['contrat']} : {a['estimation']['methode']}"), "petit"))

    # 4. Recettes par pays
    positifs = [x for x in pays if x["montant"] > 0]
    if positifs:
        total_pays = sum(x["montant"] for x in positifs)
        h.append(p("Recettes par pays", "h2"))
        h.append(p(f"{len(positifs)} pays · {euros(total_pays)} lus dans les relevés. Les 10 premiers :", "petit"))
        h.append(Spacer(1, 2 * mm))
        lignes = [[PAYS.get(x["pays"], x["pays"]), euros(x["montant"]), pc(x["montant"] / total_pays)] for x in positifs[:10]]
        h.append(tableau(["Pays", "Recettes", "Part"], lignes, [50 * mm, 40 * mm, 30 * mm], droite=(1, 2)))

    # 5. Manques à combler
    h.append(p("Ce qui manque dans les fichiers", "h2"))
    if manques:
        lignes = [[m["gravite"].capitalize(), m["sujet"], m["constat"], m["action"]] for m in manques]
        h.append(tableau(["Gravité", "Sujet", "Constat", "À demander"], lignes,
                         [20 * mm, 38 * mm, 62 * mm, largeur - 120 * mm]))
    else:
        h.append(p("Rien ne manque dans les fichiers déposés."))

    # 6. Une fiche par œuvre, regroupées par projet (album) quand il est connu
    if catalogue:
        h += [PageBreak(), p("Fiches par œuvre", "h2"),
              p("Une fiche par œuvre, classées par argent en jeu puis par revenus. Score : part des 5 contrôles réussis "
                "(ISWC présent, ISRC présent, parts à 100 %, présence dans les relevés de droits d'auteur, aucune alerte chiffrée ouverte) ; "
                "les contrôles manqués sont nommés. 100 % veut dire que tous les contrôles sont réussis, pas qu'aucun argent ne manque.", "petit"),
              Spacer(1, 3 * mm)]
        en_jeu_de = lambda o: sum(f.get("montant") or 0 for f in alertes_de(o, fuites))
        groupes = {}
        for o in catalogue:
            groupes.setdefault(o.get("projet") or "", []).append(o)
        ordre_groupes = sorted(groupes.items(), key=lambda g: (g[0] == "", -sum(o["revenus"] for o in g[1])))
        for projet, oeuvres in ordre_groupes:
            if len(groupes) > 1:
                h.append(p(t(projet or "Sans projet indiqué") + f" <font color='#6B7280' size='9'>· {len(oeuvres)} œuvre(s) · "
                           f"{euros(sum(o['revenus'] for o in oeuvres))}</font>", "h3"))
            for o in sorted(oeuvres, key=lambda o: (-en_jeu_de(o), -o["revenus"])):
                h.append(KeepTogether(fiche_oeuvre(o, fuites, en_jeu_de(o), largeur)))

    # 7. Méthode et sources
    h += [p("Méthode et sources", "h2"),
          p("Traqy ne fait appel à aucun barème : tous les montants viennent des relevés, catalogues et contrats déposés par le client. "
            "Un montant « relevé » est lu tel quel dans un relevé ; un montant « estimation » est calculé à partir des propres relevés "
            "du client, selon la méthode indiquée pour chaque alerte. Les montants non chiffrables sont signalés « Non chiffré ». "
            "Le client reste seul juge des réclamations à engager : il valide ou écarte chaque alerte."),
          Spacer(1, 2 * mm), p("Fichiers analysés", "h3")]
    for b in importes[:40]:
        h.append(p(t(f"• {b['fichier']} : {b.get('format') or 'format reconnu'}, {b.get('lignes_importees', 0)} lignes"), "petit"))
    if len(importes) > 40:
        h.append(p(f"… et {len(importes) - 40} autres fichiers.", "petit"))

    doc.build(h, onFirstPage=decor, onLaterPages=decor)
    return tampon.getvalue()
