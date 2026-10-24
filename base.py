"""
Traqy · Base de données PostgreSQL (Supabase, Francfort).

L'adresse de connexion est lue dans le fichier secret .env (DATABASE_URL), jamais écrite dans le code.
Les tables sont rangées dans le schéma « traqy », qui n'est pas exposé par l'interface publique de Supabase.
Chaque import est enregistré en entier (catalogue, revenus, soldes, bilans, manques, fuites) et rattaché à un client.
Les colonnes des tables sont tirées directement du modèle interne (modele.py) : les deux restent toujours alignés.
"""
import os
import typing
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, MetaData, Table, Text,
                        create_engine, insert, select, text)
from sqlalchemy.dialects.postgresql import JSONB

from modele import BilanFichier, Enregistrement, Fuite, Import, Manque, Oeuvre, Part, Revenu, Solde

load_dotenv(Path(__file__).with_name(".env"))
SCHEMA = "traqy"
meta = MetaData(schema=SCHEMA)

clients = Table("clients", meta,
                Column("id", Integer, primary_key=True),
                Column("nom", Text, nullable=False, unique=True),
                Column("cree_le", DateTime(timezone=True), nullable=False))
imports = Table("imports", meta,
                Column("id", Integer, primary_key=True),
                Column("client_id", Integer, ForeignKey(f"{SCHEMA}.clients.id", ondelete="CASCADE"), nullable=False, index=True),
                Column("cree_le", DateTime(timezone=True), nullable=False),
                Column("resume", JSONB))


def type_sql(annotation):
    """Type Python du modèle -> type de colonne PostgreSQL."""
    args = [a for a in typing.get_args(annotation) if a is not type(None)]
    t = args[0] if typing.get_origin(annotation) is typing.Union and args else annotation
    if typing.get_origin(t) in (list, dict):
        return JSONB
    if isinstance(t, type) and issubclass(t, Enum):
        return Text
    return {str: Text, int: Integer, float: Float, bool: Boolean, date: Date}.get(t, JSONB)

def table_depuis(nom, modele):
    colonnes = [Column("id", Integer, primary_key=True),
                Column("import_id", Integer, ForeignKey(f"{SCHEMA}.imports.id", ondelete="CASCADE"), nullable=False, index=True)]
    colonnes += [Column(champ, type_sql(info.annotation)) for champ, info in modele.model_fields.items() if champ != "id"]
    return Table(nom, meta, *colonnes)

# Contenu d'un import : nom de la table, modèle, champ de l'objet Import
CONTENU = [("oeuvres", Oeuvre, "oeuvres"), ("enregistrements", Enregistrement, "enregistrements"), ("parts", Part, "parts"),
           ("revenus", Revenu, "revenus"), ("soldes", Solde, "soldes"), ("bilans_fichiers", BilanFichier, "fichiers"),
           ("manques", Manque, "manques"), ("fuites", Fuite, "fuites")]
TABLES = {nom: table_depuis(nom, modele) for nom, modele, _ in CONTENU}


_moteur = None

def adresse():
    """Adresse de la base, nettoyée (tolère « DATABASE_URL= » collé devant, des guillemets ou des espaces)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("DATABASE_URL="):
        url = url[len("DATABASE_URL="):]
    return url.strip().strip("'\"").strip()

def configuree():
    return bool(adresse())

def verifier():
    with moteur().connect() as c:
        c.execute(text("select 1"))

def moteur():
    """Connexion unique, créée au premier usage. Les tables manquantes sont créées à ce moment-là."""
    global _moteur
    if _moteur is None:
        url = adresse().replace("postgresql://", "postgresql+psycopg://", 1)
        _moteur = create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2)
        with _moteur.begin() as c:
            c.execute(text(f"create schema if not exists {SCHEMA}"))
            meta.create_all(c)
            completer_colonnes(c)
    return _moteur

def completer_colonnes(c):
    """Ajoute aux tables existantes les colonnes apparues depuis dans modele.py (les données déjà là sont gardées)."""
    for t in TABLES.values():
        existantes = set(c.execute(text("select column_name from information_schema.columns "
                                        "where table_schema = :s and table_name = :t"), {"s": SCHEMA, "t": t.name}).scalars())
        for col in t.columns:
            if col.name not in existantes:
                c.execute(text(f'alter table {SCHEMA}.{t.name} add column "{col.name}" {col.type.compile(dialect=c.dialect)}'))

def enregistrer_import(nom_client, imp):
    """Enregistre un import complet pour ce client (créé s'il n'existe pas). Renvoie le numéro de l'import."""
    maintenant = datetime.now(timezone.utc)
    with moteur().begin() as c:
        client_id = c.execute(select(clients.c.id).where(clients.c.nom == nom_client)).scalar()
        if client_id is None:
            client_id = c.execute(insert(clients).values(nom=nom_client, cree_le=maintenant).returning(clients.c.id)).scalar()
        import_id = c.execute(insert(imports).values(client_id=client_id, cree_le=maintenant, resume=imp.resume)
                              .returning(imports.c.id)).scalar()
        for nom, _, champ in CONTENU:
            lignes = [dict(e.model_dump(mode="json", exclude={"id"}), import_id=import_id) for e in getattr(imp, champ)]
            for ligne in lignes:   # les dates restent des dates, pas du texte
                for k, v in ligne.items():
                    if isinstance(TABLES[nom].c[k].type, Date) and v:
                        ligne[k] = date.fromisoformat(v)
            if lignes:
                c.execute(insert(TABLES[nom]), lignes)
    return import_id

def lire_import(import_id):
    """Relit un import enregistré, dans le modèle interne. None s'il n'existe pas."""
    with moteur().connect() as c:
        entete = c.execute(select(imports, clients.c.nom).join(clients).where(imports.c.id == import_id)).mappings().first()
        if entete is None:
            return None
        imp = Import(resume=entete["resume"] or {}, import_id=import_id, client=entete["nom"])
        for nom, modele, champ in CONTENU:
            t = TABLES[nom]
            lignes = c.execute(select(t).where(t.c.import_id == import_id).order_by(t.c.id)).mappings().all()
            garder = lambda k: k != "import_id" and (k != "id" or "id" in modele.model_fields)
            setattr(imp, champ, [modele(**{k: v for k, v in l.items() if garder(k)}) for l in lignes])
    return imp

DECISIONS = ("validée", "écartée")

def decider_fuite(fuite_id, decision):
    """Enregistre le choix du client sur une alerte (None pour annuler). Renvoie False si l'alerte n'existe pas."""
    t = TABLES["fuites"]
    with moteur().begin() as c:
        return c.execute(t.update().where(t.c.id == fuite_id).values(decision=decision)).rowcount == 1

def lister_imports(nom_client=None):
    requete = (select(imports.c.id, imports.c.cree_le, imports.c.resume, clients.c.nom.label("client"))
               .join(clients).order_by(imports.c.id.desc()))
    if nom_client:
        requete = requete.where(clients.c.nom == nom_client)
    with moteur().connect() as c:
        return [dict(l) for l in c.execute(requete).mappings().all()]

def supprimer_client(nom_client):
    """Efface un client et tous ses imports (utilisé par les tests)."""
    with moteur().begin() as c:
        c.execute(clients.delete().where(clients.c.nom == nom_client))
