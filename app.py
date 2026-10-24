import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

API = "http://127.0.0.1:8000"

def euros(montant):
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")

def nombre(valeur):
    return f"{valeur:,}".replace(",", " ")

def montant(valeur):
    return "Non calculé (taux non fourni)" if valeur is None else euros(valeur)

st.set_page_config(page_title="Traqy", layout="wide")

st.title("Traqy")
st.caption("Audit des redevances et détection des usages non autorisés")

# Paramètres de l'audit
st.sidebar.header("Paramètres de l'audit")
artiste = st.sidebar.text_input("Artiste", placeholder="Ex : Tiakola")
titre = st.sidebar.text_input("Titre", placeholder="Ex : Meuda")
isrc = st.sidebar.text_input("Code ISRC (facultatif)", placeholder="Ex : FR1232600001").strip().upper()
iswc = st.sidebar.text_input("Code ISWC (facultatif)", placeholder="Ex : T-123456789-0").strip().upper()
streams_reels = st.sidebar.number_input("Écoutes mesurées", min_value=0, value=0, step=1000)
streams_declares = st.sidebar.number_input("Écoutes déclarées", min_value=0, value=0, step=1000)
# Taux du client : laissés vides, les montants ne sont pas calculés (preuve seule)
st.sidebar.header("Vos taux (facultatif)")
st.sidebar.caption("Traqy n'applique aucun taux par défaut. Les montants obtenus sont des estimations.")
taux = st.sidebar.number_input("Redevance par écoute (€)", min_value=0.0, max_value=1.0, value=None, step=0.001, format="%.4f")
taux_client = {
    "leak_per_view": st.sidebar.number_input("Fuite : valeur par vue (€)", min_value=0.0, max_value=1.0, value=None, step=0.001, format="%.4f"),
    "youtube_per_view": st.sidebar.number_input("YouTube : valeur par vue (€)", min_value=0.0, max_value=1.0, value=None, step=0.001, format="%.4f"),
    "tiktok_per_video": st.sidebar.number_input("TikTok : valeur par vidéo (€)", min_value=0.0, max_value=100.0, value=None, step=0.001, format="%.4f"),
    "meta_per_use": st.sidebar.number_input("Instagram / Facebook : valeur par utilisation (€)", min_value=0.0, max_value=100.0, value=None, step=0.001, format="%.4f"),
    "commercial_fee": st.sidebar.number_input("Publicité non autorisée : forfait par usage (€)", min_value=0.0, value=None, step=100.0),
}

if artiste and titre:
    st.subheader(f"{artiste} – {titre}")
else:
    st.info("Renseignez l'artiste et le titre dans le panneau de gauche, puis lancez l'audit.")

# Tableau des usages non autorisés (une ligne par post)
TYPES = {
    "Version modifiée (Sped Up / Slowed)": "modified_version",
    "Utilisation commerciale (marque / publicité)": "unauthorized_commercial_use",
    "Fuite d'un titre non commercialisé": "leak",
    "Extrait non associé aux ayants droit": "unclaimed_content",
}
st.markdown("#### Usages non autorisés constatés")
st.caption("Cliquez dans la ligne vide du tableau pour ajouter un post (TikTok, YouTube, Instagram, Facebook, X). L'identifiant est facultatif : il est retrouvé automatiquement à partir du lien.")
vide = pd.DataFrame({
    "Plateforme": pd.Series(dtype="str"), "Type": pd.Series(dtype="str"), "Lien du post": pd.Series(dtype="str"),
    "Identifiant du post": pd.Series(dtype="str"), "Vues": pd.Series(dtype="int"), "Partages": pd.Series(dtype="int"),
    "Vidéos utilisant le son": pd.Series(dtype="int"),
})
incidents_saisis = st.data_editor(
    vide,
    num_rows="dynamic",
    use_container_width=True,
    key="incidents",
    column_config={
        "Plateforme": st.column_config.SelectboxColumn(options=["TikTok", "YouTube", "Instagram", "Facebook", "X"], required=True),
        "Type": st.column_config.SelectboxColumn(options=list(TYPES.keys()), required=True),
        "Lien du post": st.column_config.LinkColumn(required=True),
        "Identifiant du post": st.column_config.TextColumn(),
        "Vues": st.column_config.NumberColumn(min_value=0, default=0),
        "Partages": st.column_config.NumberColumn(min_value=0, default=0),
        "Vidéos utilisant le son": st.column_config.NumberColumn(min_value=1, default=1,
                                                                 help="TikTok, Instagram, Facebook : nombre de vidéos qui utilisent le son."),
    },
)

# Ayants droit de l'œuvre (pour le fichier de métadonnées)
ROLES = ["Auteur", "Compositeur", "Auteur-compositeur", "Arrangeur", "Éditeur"]
st.markdown("#### Ayants droit et répartition")
st.caption("Facultatif. Le total des parts doit faire 100 %. Le numéro IPI figure sur les relevés SACEM.")
ayants_saisis = st.data_editor(
    pd.DataFrame({
        "Nom": pd.Series(dtype="str"), "Rôle": pd.Series(dtype="str"),
        "IPI": pd.Series(dtype="str"), "Part (%)": pd.Series(dtype="float"),
    }),
    num_rows="dynamic",
    use_container_width=True,
    key="ayants",
    column_config={
        "Nom": st.column_config.TextColumn(required=True),
        "Rôle": st.column_config.SelectboxColumn(options=ROLES, required=True),
        "IPI": st.column_config.TextColumn(),
        "Part (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=0.01, required=True),
    },
)
ayants_valides = ayants_saisis.dropna(subset=["Nom", "Rôle", "Part (%)"])
total_parts = float(ayants_valides["Part (%)"].sum()) if len(ayants_valides) else 0.0
if len(ayants_valides) and abs(total_parts - 100) > 0.01:
    st.warning(f"Total des parts : {total_parts:g} %. Il doit être égal à 100 %.")

def entier(valeur):
    return 0 if pd.isna(valeur) else int(valeur)

def preparer_donnees():
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    incidents = []
    for ligne in incidents_saisis.dropna(subset=["Plateforme", "Type", "Lien du post"]).to_dict("records"):
        identifiant = ligne["Identifiant du post"]
        incidents.append({
            "platform": ligne["Plateforme"],
            "incident_type": TYPES[ligne["Type"]],
            "post_url": ligne["Lien du post"],
            "post_id": None if pd.isna(identifiant) or not str(identifiant).strip() else str(identifiant).strip(),
            "detected_at": maintenant,
            "views": entier(ligne["Vues"]),
            "shares": entier(ligne["Partages"]),
            "videos_count": max(1, entier(ligne["Vidéos utilisant le son"])),
        })
    return {
        "title": titre,
        "artist": artiste,
        "isrc": isrc or None,
        "actual_streams": int(streams_reels),
        "reported_streams": int(streams_declares),
        "royalty_rate": taux,
        "client_rates": taux_client,
        "incidents": incidents,
        "iswc": iswc or None,
        "rights_holders": [
            {"name": l["Nom"], "role": l["Rôle"], "share_percent": float(l["Part (%)"]),
             "ipi": None if pd.isna(l["IPI"]) or not str(l["IPI"]).strip() else str(l["IPI"]).replace(" ", "").strip()}
            for l in ayants_valides.to_dict("records")
        ],
    }

def appeler_api(chemin, donnees):
    try:
        reponse = requests.post(f"{API}{chemin}", json=donnees, timeout=30)
    except requests.exceptions.RequestException:
        st.error("Service d'audit indisponible. Vérifiez que l'API est démarrée.")
        st.stop()
    if reponse.status_code != 200:
        message = "Vérifiez l'ISRC, l'ISWC, les liens, les numéros IPI et la répartition."
        try:
            erreur = reponse.json()["detail"][0]["msg"]
            if erreur.startswith("Value error, "):
                message = erreur.replace("Value error, ", "")
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        st.error(f"Données refusées : {message}")
        st.stop()
    return reponse

if st.button("Lancer l'audit", type="primary", disabled=not (artiste and titre)):
    donnees = preparer_donnees()
    audit = appeler_api("/api/v1/audit", donnees).json()
    pack = appeler_api("/api/v1/audit-pack", donnees)
    nom_fichier = pack.headers.get("content-disposition", "").split('filename="')[-1].rstrip('"') or "Pack_Audit_Traqy.zip"
    st.session_state["resultat"] = {"audit": audit, "pack": pack.content, "nom_fichier": nom_fichier}

resultat = st.session_state.get("resultat")
if resultat:
    audit = resultat["audit"]
    finance = audit["royalties"]
    resume = audit["summary"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Écoutes non déclarées", nombre(finance["undeclared_streams"]))
    col2.metric("Usages non autorisés", resume["total_incidents"])
    col3.metric("Audience des usages (vues)", nombre(resume["total_views"]))
    col4, col5 = st.columns(2)
    col4.metric("Redevances non perçues (estimation)", montant(finance["unpaid_royalties_euros"]))
    col5.metric("Valeur des usages (estimation)", montant(resume["estimated_impact_euros"]))
    st.caption(f"Calcul : {audit['rates_source']}. Le détail des taux figure dans le rapport PDF.")

    st.markdown("#### Répartition par plateforme")
    st.table([{"Plateforme": p, "Incidents": n} for p, n in resume["incidents_by_platform"].items()])

    if audit["evidence"]:
        st.markdown("#### Dossier de preuves")
        st.table([
            {"Réf.": p["evidence_id"], "Plateforme": p["platform"], "Type": p["label"], "Lien": p["post_url"],
             "Identifiant": p["post_id"], "Vues": nombre(p["views"]), "Impact": montant(p["estimated_impact_euros"]),
             "Méthode": p["calculation_method"]}
            for p in audit["evidence"]
        ])

    st.download_button(
        "Télécharger le Pack d'Audit (PDF, preuves, métadonnées)",
        data=resultat["pack"],
        file_name=resultat["nom_fichier"],
        mime="application/zip",
        type="primary",
    )