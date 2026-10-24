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
    iswc: Optional[str] = None             # œuvre enregistrée, quand le catalogue le dit


class Solde(BaseModel):
    """Solde d'un compte chez un éditeur ou un distributeur, sur une période (positif : en faveur du client)."""
    payeur: Optional[str] = None
    compte: str
    periode: Optional[str] = None
    debut: Optional[date] = None
    fin: Optional[date] = None
    ouverture: Optional[float] = None
    royalties: Optional[float] = None
    cloture: Optional[float] = None
    devise: Optional[str] = None
    fichier: str
    ligne: int


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
    frais = "frais"
    avance = "avance"


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
    contrat: Optional[str] = None          # numéro de contrat indiqué dans le relevé
    taux_partage: Optional[str] = None     # taux de partage indiqué dans le relevé
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


class Gravite(str, Enum):
    bloquant = "bloquant"
    important = "important"
    a_completer = "à compléter"


class Manque(BaseModel):
    """Contrôle des manques : ce qui manque dans les fichiers déposés, et ce qu'il faut demander au client."""
    gravite: Gravite
    sujet: str
    constat: str
    action: str
    nombre: int = 0
    montant: Optional[float] = None        # argent concerné, quand il est connu
    exemples: List[str] = Field(default_factory=list)


class Fuite(BaseModel):
    """Droits non perçus : ce qui n'a pas été versé, combien (quand c'est chiffrable) et à qui le réclamer."""
    regle: str
    oeuvre: Optional[str] = None
    iswc: Optional[str] = None
    isrc: Optional[str] = None
    payeur: Optional[str] = None
    montant: Optional[float] = None        # None : non chiffré
    estimation: bool = True                # False : montant lu tel quel dans un relevé
    methode: str
    action: str
    preuves: List[str] = Field(default_factory=list)


class Import(BaseModel):
    oeuvres: List[Oeuvre] = Field(default_factory=list)
    enregistrements: List[Enregistrement] = Field(default_factory=list)
    parts: List[Part] = Field(default_factory=list)
    revenus: List[Revenu] = Field(default_factory=list)
    soldes: List[Solde] = Field(default_factory=list)
    fichiers: List[BilanFichier] = Field(default_factory=list)
    manques: List[Manque] = Field(default_factory=list)
    fuites: List[Fuite] = Field(default_factory=list)
    resume: Dict[str, int] = Field(default_factory=dict)
