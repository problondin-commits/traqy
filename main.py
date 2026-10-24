from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, HttpUrl, model_validator
from typing import List, Optional
from datetime import date, datetime, timezone
from enum import Enum
import uuid
import io
import csv
import zipfile
import re
import xml.etree.ElementTree as ET
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import calculs

app = FastAPI(title="Traqy API", version="1.1.0")

class InfractionItem(BaseModel):
    platform: str = Field(min_length=1, max_length=50)
    is_modified_version: bool

class FullReportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    actual_streams: int = Field(ge=0)
    reported_streams: int = Field(ge=0)
    royalty_rate: float = Field(ge=0, le=1)
    infractions: List[InfractionItem] = Field(default_factory=list)

@app.get("/")
def lire_racine():
    return {"status": "online", "system": "Traqy API"}

@app.post("/full-report/")
def generate_full_report(data: FullReportRequest):
    undeclared_streams = max(0, data.actual_streams - data.reported_streams)
    unpaid_royalties = undeclared_streams * data.royalty_rate
    detected_infractions = []
    for inf in data.infractions:
        inf_type = "Version modifiée non autorisée (Sped Up / Slowed)" if inf.is_modified_version else "Fuite d'un titre non commercialisé"
        detected_infractions.append({"platform": inf.platform, "infraction": inf_type})
    return {
        "track": data.title,
        "financial_audit": {"undeclared_streams": undeclared_streams, "estimated_unpaid_royalties_euros": round(unpaid_royalties, 2)},
        "security_audit": {"total_infractions_found": len(detected_infractions), "details": detected_infractions},
        "message": "Rapport d'audit global de synthèse généré avec succès !"
    }


# ---------- Audit réseaux sociaux (TikTok, YouTube, Instagram, Facebook, X) ----------

class Plateforme(str, Enum):
    tiktok = "TikTok"
    youtube = "YouTube"
    instagram = "Instagram"
    facebook = "Facebook"
    x = "X"

class TypeIncident(str, Enum):
    version_modifiee = "modified_version"
    usage_commercial = "unauthorized_commercial_use"
    fuite = "leak"
    contenu_non_reclame = "unclaimed_content"

LIBELLES_INCIDENT = {
    "modified_version": "Version modifiée non autorisée (Sped Up / Slowed)",
    "unauthorized_commercial_use": "Utilisation commerciale non autorisée (marque / publicité)",
    "leak": "Fuite d'un titre non commercialisé",
    "unclaimed_content": "Extrait non associé aux ayants droit",
}

class Incident(BaseModel):
    platform: Plateforme
    incident_type: TypeIncident
    post_url: HttpUrl
    post_id: Optional[str] = Field(default=None, max_length=100)
    detected_at: datetime
    views: int = Field(ge=0, default=0)
    shares: int = Field(ge=0, default=0)
    videos_count: int = Field(ge=1, default=1)

# Taux saisis par le client : Traqy n'applique aucun taux par défaut
class TauxClient(BaseModel):
    leak_per_view: Optional[float] = Field(default=None, ge=0, le=1)
    youtube_per_view: Optional[float] = Field(default=None, ge=0, le=1)
    tiktok_per_video: Optional[float] = Field(default=None, ge=0, le=100)
    meta_per_use: Optional[float] = Field(default=None, ge=0, le=100)
    commercial_fee: Optional[float] = Field(default=None, ge=0)

class SocialAuditRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    isrc: Optional[str] = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$")
    royalty_rate: Optional[float] = Field(default=None, ge=0, le=1)
    client_rates: TauxClient = Field(default_factory=TauxClient)
    incidents: List[Incident] = Field(default_factory=list, max_length=500)

# Retrouve l'identifiant du post à partir du lien (Instagram, TikTok, YouTube, X, Facebook)
MOTIFS_ID = [
    r"/(?:reel|reels|p|tv|shorts|status|video|videos)/([A-Za-z0-9_-]+)",
    r"[?&](?:v|story_fbid|fbid)=([A-Za-z0-9_-]+)",
    r"youtu\.be/([A-Za-z0-9_-]+)",
]

def extraire_id(url):
    for motif in MOTIFS_ID:
        trouve = re.search(motif, url)
        if trouve:
            return trouve.group(1)
    return "non identifié"

SANS_TAUX = "Taux non fourni par le client : preuve seule"
SOURCE_TAUX = "Taux communiqués par le client – montants estimés"

# Chaque type d'usage a sa propre règle de calcul ; renvoie (montant ou None, méthode)
def calculer_impact(inc, data):
    t = data.client_rates
    if inc.incident_type == TypeIncident.usage_commercial:
        valeur, quantite, methode = t.commercial_fee, 1, "Forfait de licence publicitaire du client"
    elif inc.incident_type == TypeIncident.fuite:
        valeur, quantite, methode = t.leak_per_view, inc.views, "Vues × taux par vue du client"
    elif inc.platform == Plateforme.youtube:
        valeur, quantite, methode = t.youtube_per_view, inc.views, "Vues × taux Content ID du client"
    elif inc.platform == Plateforme.tiktok:
        valeur, quantite, methode = t.tiktok_per_video, inc.videos_count, "Vidéos utilisant le son × taux TikTok du client"
    elif inc.platform in (Plateforme.instagram, Plateforme.facebook):
        valeur, quantite, methode = t.meta_per_use, inc.videos_count, "Utilisations du son × taux Meta du client"
    else:
        return None, "Aucun taux applicable sur X : preuve seule"
    if valeur is None:
        return None, SANS_TAUX
    return valeur * quantite, methode

@app.post("/api/v1/social-audit")
def social_audit(data: SocialAuditRequest):
    return calculer_audit_social(data)

def calculer_audit_social(data: SocialAuditRequest):
    par_plateforme = {p.value: 0 for p in Plateforme}
    preuves = []
    for i, inc in enumerate(data.incidents, start=1):
        impact, methode = calculer_impact(inc, data)
        par_plateforme[inc.platform.value] += 1
        preuves.append({
            "evidence_id": f"EV-{i:04d}",
            "platform": inc.platform.value,
            "incident_type": inc.incident_type.value,
            "label": LIBELLES_INCIDENT[inc.incident_type.value],
            "post_url": str(inc.post_url),
            "post_id": inc.post_id or extraire_id(str(inc.post_url)),
            "detected_at": inc.detected_at.isoformat(),
            "views": inc.views,
            "shares": inc.shares,
            "videos_count": inc.videos_count,
            "estimated_impact_euros": None if impact is None else round(impact, 2),
            "calculation_method": methode,
        })
    chiffres = [p["estimated_impact_euros"] for p in preuves if p["estimated_impact_euros"] is not None]
    return {
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "track": data.title,
        "isrc": data.isrc,
        "summary": {
            "total_incidents": len(preuves),
            "total_views": sum(p["views"] for p in preuves),
            "total_shares": sum(p["shares"] for p in preuves),
            "estimated_impact_euros": round(sum(chiffres), 2) if chiffres else None,
            "incidents_without_rate": len(preuves) - len(chiffres),
            "incidents_by_platform": par_plateforme,
        },
        "rates_source": SOURCE_TAUX,
        "evidence": preuves,
    }



# ---------- Pack d'Audit (rapport PDF + dossier de preuves CSV, dans un fichier ZIP) ----------

class Role(str, Enum):
    auteur = "Auteur"
    compositeur = "Compositeur"
    auteur_compositeur = "Auteur-compositeur"
    arrangeur = "Arrangeur"
    editeur = "Éditeur"

class AyantDroit(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: Role
    ipi: Optional[str] = Field(default=None, pattern=r"^[0-9]{9,11}$")
    share_percent: float = Field(gt=0, le=100)

class AuditPackRequest(SocialAuditRequest):
    artist: str = Field(min_length=1, max_length=200)
    actual_streams: int = Field(ge=0)
    reported_streams: int = Field(ge=0)
    iswc: Optional[str] = Field(default=None, pattern=r"^T-?[0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]$")
    rights_holders: List[AyantDroit] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def verifier_repartition(self):
        if self.rights_holders:
            total = sum(a.share_percent for a in self.rights_holders)
            if abs(total - 100) > 0.01:
                raise ValueError(f"La répartition des ayants droit doit faire 100 % (actuellement {total:g} %).")
        return self

def euros(montant):
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")

def nombre(valeur):
    return f"{valeur:,}".replace(",", " ")

def montant(valeur):
    return "Non calculé (taux non fourni)" if valeur is None else euros(valeur)

def somme(*valeurs):
    connues = [v for v in valeurs if v is not None]
    return round(sum(connues), 2) if connues else None

def taux(valeur):
    return f"{valeur:g}".replace(".", ",") + " €"

def regle(valeur, unite):
    return "Taux non fourni : preuve seule" if valeur is None else f"{unite} × {taux(valeur)}"

def creer_csv_preuves(audit):
    sortie = io.StringIO()
    ecrivain = csv.writer(sortie, delimiter=";")
    ecrivain.writerow(["Identifiant preuve", "Plateforme", "Type", "Lien", "Identifiant du post",
                       "Date de détection (UTC)", "Vues", "Partages", "Vidéos utilisant le son",
                       "Impact estimé (€)", "Méthode de calcul"])
    for p in audit["evidence"]:
        impact = p["estimated_impact_euros"]
        ecrivain.writerow([p["evidence_id"], p["platform"], p["label"], p["post_url"], p["post_id"],
                           p["detected_at"], p["views"], p["shares"], p["videos_count"],
                           "" if impact is None else str(impact).replace(".", ","),
                           p["calculation_method"]])
    return sortie.getvalue().encode("utf-8-sig")

def creer_xml_metadonnees(data, audit):
    racine = ET.Element("WorkRegistration", {"version": "1.0", "generatedAt": audit["generated_at"], "reference": audit["audit_id"]})
    oeuvre = ET.SubElement(racine, "Work")
    ET.SubElement(oeuvre, "Title").text = data.title
    ET.SubElement(oeuvre, "Artist").text = data.artist
    ET.SubElement(oeuvre, "ISWC").text = data.iswc or ""
    ET.SubElement(oeuvre, "ISRC").text = data.isrc or ""
    ayants = ET.SubElement(racine, "RightsHolders")
    for numero, a in enumerate(data.rights_holders, start=1):
        bloc = ET.SubElement(ayants, "RightsHolder", {"sequence": str(numero)})
        ET.SubElement(bloc, "Name").text = a.name
        ET.SubElement(bloc, "Role").text = a.role.value
        ET.SubElement(bloc, "IPI").text = a.ipi or ""
        ET.SubElement(bloc, "SharePercent").text = f"{a.share_percent:.2f}"
    ET.indent(racine)
    return ET.tostring(racine, encoding="utf-8", xml_declaration=True)

def creer_pdf_rapport(data, audit, ecoutes_non_declarees, redevances):
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, title="Traqy - Rapport d'audit", author="Traqy")
    styles = getSampleStyleSheet()
    style_tableau = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])
    resume = audit["summary"]
    contenu = [
        Paragraph("Traqy", styles["Title"]),
        Paragraph("Rapport d'audit des redevances et des usages non autorisés", styles["Heading2"]),
        Paragraph(f"{data.artist} – {data.title}" + (f" (ISRC {data.isrc})" if data.isrc else ""), styles["Normal"]),
        Paragraph(f"Référence {audit['audit_id']} – généré le {datetime.fromisoformat(audit['generated_at']).strftime('%d/%m/%Y à %H:%M')} (UTC)", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("Synthèse", styles["Heading3"]),
    ]
    synthese = Table([
        ["Indicateur", "Valeur"],
        ["Écoutes non déclarées", nombre(ecoutes_non_declarees)],
        ["Redevances non perçues (estimation)", montant(redevances)],
        ["Usages non autorisés détectés", str(resume["total_incidents"])],
        ["Audience cumulée des usages (vues)", nombre(resume["total_views"])],
        ["Valeur des usages (estimation)", montant(resume["estimated_impact_euros"])],
        ["Total à récupérer (estimation)", montant(somme(redevances, resume["estimated_impact_euros"]))],
    ], colWidths=[300, 170])
    synthese.setStyle(style_tableau)
    contenu += [synthese, Spacer(1, 16), Paragraph("Usages non autorisés par plateforme", styles["Heading3"])]
    plateformes = Table([["Plateforme", "Incidents"]] + [[p, str(n)] for p, n in audit["summary"]["incidents_by_platform"].items()],
                        colWidths=[300, 170])
    plateformes.setStyle(style_tableau)
    contenu += [plateformes, Spacer(1, 16), Paragraph("Détail des preuves", styles["Heading3"])]
    if audit["evidence"]:
        petit = styles["BodyText"].clone("petit", fontSize=8, leading=10)
        lignes = [["Réf.", "Plateforme", "Type", "Lien", "Vues", "Impact estimé"]]
        for p in audit["evidence"]:
            lignes.append([p["evidence_id"], p["platform"], Paragraph(p["label"], petit), Paragraph(p["post_url"], petit),
                           nombre(p["views"]), Paragraph(montant(p["estimated_impact_euros"]), petit)])
        detail = Table(lignes, colWidths=[45, 55, 115, 140, 50, 90], repeatRows=1)
        detail.setStyle(style_tableau)
        contenu.append(detail)
    else:
        contenu.append(Paragraph("Aucun usage non autorisé n'a été signalé pour ce titre.", styles["Normal"]))
    if data.rights_holders:
        contenu += [Spacer(1, 16), Paragraph("Ayants droit et répartition" + (f" (ISWC {data.iswc})" if data.iswc else ""), styles["Heading3"])]
        ayants = Table([["Nom", "Rôle", "IPI", "Part"]] + [
            [a.name, a.role.value, a.ipi or "–", f"{a.share_percent:g} %".replace(".", ",")] for a in data.rights_holders
        ], colWidths=[180, 120, 100, 70], repeatRows=1)
        ayants.setStyle(style_tableau)
        contenu.append(ayants)
    t = data.client_rates
    contenu += [Spacer(1, 16), Paragraph("Méthode de calcul – taux communiqués par le client", styles["Heading3"])]
    methode = Table([
        ["Type d'usage", "Règle appliquée"],
        ["Écoutes non déclarées", regle(data.royalty_rate, "Écoutes")],
        ["Fuite d'un titre non commercialisé", regle(t.leak_per_view, "Vues")],
        ["Usage sur YouTube (Content ID)", regle(t.youtube_per_view, "Vues")],
        ["Usage sur TikTok", regle(t.tiktok_per_video, "Vidéos")],
        ["Usage sur Instagram / Facebook", regle(t.meta_per_use, "Utilisations")],
        ["Usage sur X", "Aucun taux applicable : preuve seule"],
        ["Publicité non autorisée",
         "Taux non fourni : preuve seule" if t.commercial_fee is None else f"Forfait de {euros(t.commercial_fee)} par usage"],
    ], colWidths=[200, 270], repeatRows=1)
    methode.setStyle(style_tableau)
    contenu += [methode, Spacer(1, 20), Paragraph(
        "Tous les montants sont des estimations, calculées uniquement à partir des taux communiqués par le client. "
        "Traqy n'applique aucun taux par défaut. Document confidentiel.", styles["Italic"])]
    doc.build(contenu)
    return tampon.getvalue()

# Sans taux saisi par le client, les redevances ne sont pas chiffrées
def calculer_redevances(data):
    ecoutes_non_declarees = max(0, data.actual_streams - data.reported_streams)
    if data.royalty_rate is None:
        return ecoutes_non_declarees, None
    return ecoutes_non_declarees, round(ecoutes_non_declarees * data.royalty_rate, 2)

@app.post("/api/v1/audit")
def audit_complet(data: AuditPackRequest):
    audit = calculer_audit_social(data)
    ecoutes_non_declarees, redevances = calculer_redevances(data)
    audit["royalties"] = {
        "undeclared_streams": ecoutes_non_declarees,
        "unpaid_royalties_euros": redevances,
    }
    return audit

@app.post("/api/v1/audit-pack")
def audit_pack(data: AuditPackRequest):
    audit = calculer_audit_social(data)
    ecoutes_non_declarees, redevances = calculer_redevances(data)
    zip_memoire = io.BytesIO()
    with zipfile.ZipFile(zip_memoire, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Rapport_Audit_Traqy.pdf", creer_pdf_rapport(data, audit, ecoutes_non_declarees, redevances))
        archive.writestr("Dossier_Preuves_Traqy.csv", creer_csv_preuves(audit))
        archive.writestr("Metadonnees_Oeuvre_Traqy.xml", creer_xml_metadonnees(data, audit))
    return Response(
        content=zip_memoire.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="Pack_Audit_{audit["audit_id"]}.zip"'},
    )

# ---------- Valeur et Projection (relevés du distributeur, calculs dans calculs.py) ----------

async def lire_fichiers(fichiers: List[UploadFile]):
    controle = []
    try:
        D = calculs.lire_releves([(f.filename or "releve.csv", await f.read()) for f in fichiers], controle)
    except calculs.ErreurReleves as e:
        raise HTTPException(status_code=400, detail=str(e))
    return D, controle

def verifier_date(valeur, nom):
    try:
        return date.fromisoformat(valeur)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{nom} : date attendue au format AAAA-MM-JJ.")

@app.post("/api/v1/releves/produits")
async def produits_des_releves(fichiers: List[UploadFile] = File(...)):
    D, controle = await lire_fichiers(fichiers)
    return {"produits": calculs.lister_produits(D), "controles": controle}

# Les informations privées (contrats, taux de partage, frais) ne sont jamais renvoyées
@app.post("/api/v1/valeur")
async def valeur_et_projection(
    fichiers: List[UploadFile] = File(...),
    produits: List[str] = Form(...),
    fin: str = Form(...),
    aujourdhui: Optional[str] = Form(None),
    baisse_min: float = Form(0.05, gt=0, lt=1),
    baisse_max: float = Form(0.35, gt=0, lt=1),
    fenetre: int = Form(12, ge=3, le=60),
    avec_video: bool = Form(False),
    sortie: Optional[str] = Form(None),
):
    jour = verifier_date(aujourdhui, "Date du jour") if aujourdhui else date.today()
    if verifier_date(fin, "Date de fin") <= jour:
        raise HTTPException(status_code=400, detail="La date de fin doit être après la date du jour.")
    if baisse_min > baisse_max:
        raise HTTPException(status_code=400, detail="La baisse minimale doit être inférieure à la baisse maximale.")
    if sortie and not re.fullmatch(r"[0-9]{4}-[0-9]{2}", sortie[:7]):
        raise HTTPException(status_code=400, detail="Mois de sortie attendu au format AAAA-MM.")
    D, controle = await lire_fichiers(fichiers)
    try:
        resultat, controles, _prive = calculs.calculer_valeur(D, produits, fin, jour.isoformat(), baisse_min, baisse_max,
                                                               fenetre, avec_video, sortie)
    except calculs.ErreurReleves as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"resultat": resultat, "controles": controle + controles}


# ---------- Mode estimation (sans relevés) : taux saisis par le client ----------

class AlbumEstime(BaseModel):
    album: str = Field(min_length=1, max_length=200)
    ecoutes_cumulees: float = Field(ge=0)
    ecoutes_par_jour: float = Field(ge=0)

class EstimationRequest(BaseModel):
    albums: List[AlbumEstime] = Field(min_length=1, max_length=200)
    fin: date
    aujourdhui: Optional[date] = None
    taux_pour_1000: float = Field(gt=0, description="Revenu du client pour 1 000 écoutes, en euros")
    majoration_physique: float = Field(ge=0, le=1, description="Part ajoutée pour les ventes physiques (0,04 = +4 %)")
    baisse_annuelle: float = Field(default=0.24, gt=0, lt=1)

@app.post("/api/v1/estimation")
def estimation(data: EstimationRequest):
    jour = data.aujourdhui or date.today()
    if data.fin <= jour:
        raise HTTPException(status_code=400, detail="La date de fin doit être après la date du jour.")
    return calculs.estimer([a.model_dump() for a in data.albums], data.fin.isoformat(), jour.isoformat(),
                           data.taux_pour_1000, data.majoration_physique, data.baisse_annuelle)
