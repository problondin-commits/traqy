"""
Traqy · Modèle de données interne unique.

Tous les fichiers déposés (catalogues, relevés) sont traduits dans ce modèle,
quel que soit leur format d'origine : œuvre, enregistrement, ayant droit et part, revenu, période.
"""
from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Oeuvre(BaseModel):
    """Œuvre musicale (composition), identifiée par son ISWC ou son code SACEM."""
    titre: str
    iswc: Optional[str] = None
    code_sacem: Optional[str] = None
    artiste: Optional[str] = None


class Enregistrement(BaseModel):
    """Enregistrement (master), identifié par son ISRC."""
    titre: str
    isrc: str
    projet: Optional[str] = None
    artiste: Optional[str] = None


class Part(BaseModel):
    """Part d'un ayant droit sur une œuvre, en % (DEP : exécution, DR : reproduction, PHONO : clé phonographique)."""
    titre: str
    iswc: Optional[str] = None
    ayant_droit: str
    role: Optional[str] = None
    ipi: Optional[str] = None
    part_dep: Optional[float] = None
    part_dr: Optional[float] = None
    part_phono: Optional[float] = None
    societe: Optional[str] = None


class Categorie(str, Enum):
    streaming = "streaming"
    ventes_numeriques = "ventes_numeriques"
    ventes_physiques = "ventes_physiques"
    droits_auteur = "droits_auteur"
    droits_voisins = "droits_voisins"
    synchro = "synchro"
    reseaux_sociaux = "reseaux_sociaux"
    retenue = "retenue"


class Revenu(BaseModel):
    """Une ligne de revenu d'un relevé, avec sa période."""
    categorie: Categorie
    titre: Optional[str] = None
    artiste: Optional[str] = None
    isrc: Optional[str] = None
    iswc: Optional[str] = None
    code_sacem: Optional[str] = None
    periode: Optional[str] = None          # libellé d'origine, gardé tel quel
    debut: Optional[date] = None           # période lue dans le libellé, quand c'est possible
    fin: Optional[date] = None
    payeur: Optional[str] = None           # distributeur, société de gestion, marque…
    plateforme: Optional[str] = None
    pays: Optional[str] = None
    quantite: Optional[float] = None       # écoutes, ventes ou vues
    montant: Optional[float] = None
    devise: Optional[str] = None
    beneficiaire: Optional[str] = None
    fichier: str
    ligne: int


class BilanFichier(BaseModel):
    """Première vérification à l'import : le fichier est-il lisible et reconnu ?"""
    fichier: str
    format: Optional[str] = None
    statut: str                            # importé, ignoré ou refusé
    lignes_importees: int = 0
    lignes_ignorees: int = 0
    messages: List[str] = Field(default_factory=list)


class Import(BaseModel):
    oeuvres: List[Oeuvre] = Field(default_factory=list)
    enregistrements: List[Enregistrement] = Field(default_factory=list)
    parts: List[Part] = Field(default_factory=list)
    revenus: List[Revenu] = Field(default_factory=list)
    fichiers: List[BilanFichier] = Field(default_factory=list)
    resume: Dict[str, int] = Field(default_factory=dict)
