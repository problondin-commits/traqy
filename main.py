from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel, Field, HttpUrl, model_validator
from typing import List, Optional
from datetime import datetime, timezone
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
    hidden_streams = max(0, data.actual_streams - data.reported_streams)
    missing_money = hidden_streams * data.royalty_rate
    detected_infractions = []
    for inf in data.infractions:
        inf_type = "Version modifiée non autorisée (Sped Up / Slowed)" if inf.is_modified_version else "Leak détecté"
        detected_infractions.append({"platform": inf.platform, "infraction": inf_type})
    return {
        "track": data.title,
        "financial_audit": {"hidden_streams_detected": hidden_streams, "estimated_missing_money_euros": round(missing_money, 2)},
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

class Notoriete(str, Enum):
    independant = "independant"
    connu = "connu"
    major = "major"

class SocialAuditRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    isrc: Optional[str] = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$")
    royalty_rate: Optional[float] = Field(default=None, ge=0, le=1)
    artist_tier: Notoriete = Notoriete.independant
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

# Barème Traqy par défaut : fourchettes (bas, haut) en euros, tirées de sources publiques
# Détail et sources : document « Traqy – Barème d'impact par défaut »
BAREME_TRAQY = {
    "version": "Barème Traqy – octobre 2026",
    "streaming": (0.003, 0.005),      # par écoute (TuneCore, Royalty Exchange)
    "fuite": (0.001, 0.005),          # par vue, hypothèse : une vue = une écoute perdue
    "youtube": (0.0005, 0.002),       # par vue monétisée, Content ID (Ditto Music)
    "tiktok": (0.004, 0.01),          # par vidéo qui utilise le son (Ditto Music)
    "meta": (0.002, 0.006),           # par utilisation, Instagram et Facebook (Ditto Music)
    "x": (0.0, 0.0),                  # aucune source publique : preuve seule
    "pub": {                          # forfait par usage (Swell, Foxi, relevés réels)
        "independant": (500, 12000),
        "connu": (12000, 40000),
        "major": (50000, 300000),
    },
}
SOURCES_BAREME = "TuneCore, Royalty Exchange, Ditto Music, Swell, Foxi (pages consultées le 23/10/2026)."
LIBELLES_NOTORIETE = {"independant": "artiste indépendant", "connu": "artiste connu", "major": "major ou tube"}

def taux_streaming(data):
    if data.royalty_rate is not None:
        return (data.royalty_rate, data.royalty_rate)
    return BAREME_TRAQY["streaming"]

# Chaque type d'usage a sa propre règle de calcul ; renvoie (bas, haut, méthode)
def calculer_impact(inc, data):
    if inc.incident_type == TypeIncident.usage_commercial:
        bas, haut = BAREME_TRAQY["pub"][data.artist_tier.value]
        return bas, haut, f"Forfait de licence publicitaire ({LIBELLES_NOTORIETE[data.artist_tier.value]})"
    if inc.incident_type == TypeIncident.fuite:
        bas, haut = BAREME_TRAQY["fuite"]
        return inc.views * bas, inc.views * haut, "Vues × taux par écoute (écoutes perdues)"
    if inc.platform == Plateforme.youtube:
        bas, haut = BAREME_TRAQY["youtube"]
        return inc.views * bas, inc.views * haut, "Vues × taux Content ID"
    if inc.platform == Plateforme.tiktok:
        bas, haut = BAREME_TRAQY["tiktok"]
        return inc.videos_count * bas, inc.videos_count * haut, "Vidéos utilisant le son × taux TikTok"
    if inc.platform in (Plateforme.instagram, Plateforme.facebook):
        bas, haut = BAREME_TRAQY["meta"]
        return inc.videos_count * bas, inc.videos_count * haut, "Utilisations du son × taux Meta"
    return 0.0, 0.0, "Aucune rémunération publique connue sur X : preuve seule"

@app.post("/api/v1/social-audit")
def social_audit(data: SocialAuditRequest):
    return calculer_audit_social(data)

def calculer_audit_social(data: SocialAuditRequest):
    par_plateforme = {p.value: 0 for p in Plateforme}
    preuves = []
    for i, inc in enumerate(data.incidents, start=1):
        bas, haut, methode = calculer_impact(inc, data)
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
            "estimated_impact_low_euros": round(bas, 2),
            "estimated_impact_high_euros": round(haut, 2),
            "estimated_impact_euros": round((bas + haut) / 2, 2),
            "calculation_method": methode,
        })
    return {
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "track": data.title,
        "isrc": data.isrc,
        "summary": {
            "total_incidents": len(preuves),
            "total_views": sum(p["views"] for p in preuves),
            "total_shares": sum(p["shares"] for p in preuves),
            "estimated_impact_low_euros": round(sum(p["estimated_impact_low_euros"] for p in preuves), 2),
            "estimated_impact_high_euros": round(sum(p["estimated_impact_high_euros"] for p in preuves), 2),
            "estimated_impact_euros": round(sum(p["estimated_impact_euros"] for p in preuves), 2),
            "incidents_by_platform": par_plateforme,
        },
        "rate_card": BAREME_TRAQY["version"] + (" (taux par écoute fourni par le client)" if data.royalty_rate is not None else ""),
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

def fourchette(bas, haut):
    return euros(bas) if round(bas, 2) == round(haut, 2) else f"{euros(bas)} – {euros(haut)}"

def taux(valeur):
    return f"{valeur:g}".replace(".", ",") + " €"

def creer_csv_preuves(audit):
    sortie = io.StringIO()
    ecrivain = csv.writer(sortie, delimiter=";")
    ecrivain.writerow(["Identifiant preuve", "Plateforme", "Type", "Lien", "Identifiant du post",
                       "Date de détection (UTC)", "Vues", "Partages", "Vidéos utilisant le son",
                       "Impact bas (€)", "Impact haut (€)", "Méthode de calcul"])
    for p in audit["evidence"]:
        ecrivain.writerow([p["evidence_id"], p["platform"], p["label"], p["post_url"], p["post_id"],
                           p["detected_at"], p["views"], p["shares"], p["videos_count"],
                           str(p["estimated_impact_low_euros"]).replace(".", ","), str(p["estimated_impact_high_euros"]).replace(".", ","),
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

def creer_pdf_rapport(data, audit, streams_caches, manque_bas, manque_haut):
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
        ["Écoutes non déclarées", nombre(streams_caches)],
        ["Redevances non perçues (estimation)", fourchette(manque_bas, manque_haut)],
        ["Usages non autorisés détectés", str(resume["total_incidents"])],
        ["Audience cumulée des usages (vues)", nombre(resume["total_views"])],
        ["Impact estimé des usages", fourchette(resume["estimated_impact_low_euros"], resume["estimated_impact_high_euros"])],
        ["Total estimé à récupérer", fourchette(manque_bas + resume["estimated_impact_low_euros"], manque_haut + resume["estimated_impact_high_euros"])],
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
                           nombre(p["views"]), Paragraph(fourchette(p["estimated_impact_low_euros"], p["estimated_impact_high_euros"]), petit)])
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
    b = BAREME_TRAQY
    taux_ecoute = taux_streaming(data)
    contenu += [Spacer(1, 16), Paragraph(f"Méthode de calcul – {audit['rate_card']}", styles["Heading3"])]
    methode = Table([
        ["Type d'usage", "Règle appliquée (bas – haut)"],
        ["Écoutes non déclarées", f"Écoutes × {taux(taux_ecoute[0])} – {taux(taux_ecoute[1])} par écoute"],
        ["Fuite d'un titre non commercialisé", f"Vues × {taux(b['fuite'][0])} – {taux(b['fuite'][1])}"],
        ["Usage sur YouTube (Content ID)", f"Vues × {taux(b['youtube'][0])} – {taux(b['youtube'][1])}"],
        ["Usage sur TikTok", f"Vidéos × {taux(b['tiktok'][0])} – {taux(b['tiktok'][1])}"],
        ["Usage sur Instagram / Facebook", f"Utilisations × {taux(b['meta'][0])} – {taux(b['meta'][1])}"],
        ["Usage sur X", "Aucune rémunération publique connue : preuve seule"],
        [f"Publicité non autorisée ({LIBELLES_NOTORIETE[data.artist_tier.value]})",
         f"Forfait de {fourchette(*b['pub'][data.artist_tier.value])} par usage"],
    ], colWidths=[200, 270], repeatRows=1)
    methode.setStyle(style_tableau)
    contenu += [methode, Spacer(1, 20), Paragraph(
        f"Fourchettes estimées à partir des données communiquées. Sources du barème : {SOURCES_BAREME} "
        "Document confidentiel.", styles["Italic"])]
    doc.build(contenu)
    return tampon.getvalue()

def calculer_redevances(data):
    streams_caches = max(0, data.actual_streams - data.reported_streams)
    taux_bas, taux_haut = taux_streaming(data)
    return streams_caches, round(streams_caches * taux_bas, 2), round(streams_caches * taux_haut, 2)

@app.post("/api/v1/audit")
def audit_complet(data: AuditPackRequest):
    audit = calculer_audit_social(data)
    streams_caches, manque_bas, manque_haut = calculer_redevances(data)
    audit["royalties"] = {
        "hidden_streams_detected": streams_caches,
        "missing_money_low_euros": manque_bas,
        "missing_money_high_euros": manque_haut,
    }
    return audit

@app.post("/api/v1/audit-pack")
def audit_pack(data: AuditPackRequest):
    audit = calculer_audit_social(data)
    streams_caches, manque_bas, manque_haut = calculer_redevances(data)
    zip_memoire = io.BytesIO()
    with zipfile.ZipFile(zip_memoire, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Rapport_Audit_Traqy.pdf", creer_pdf_rapport(data, audit, streams_caches, manque_bas, manque_haut))
        archive.writestr("Dossier_Preuves_Traqy.csv", creer_csv_preuves(audit))
        archive.writestr("Metadonnees_Oeuvre_Traqy.xml", creer_xml_metadonnees(data, audit))
    return Response(
        content=zip_memoire.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="Pack_Audit_{audit["audit_id"]}.zip"'},
    )