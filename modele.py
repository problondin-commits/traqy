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
    autres_revenus = "autres_revenus"      # merchandising et autres recettes d'un relevé distributeur
    retenue = "retenue"                    # sommes dues à un tiers (ex. royautés d'artiste, taux négatif)
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


class RevenuPays(BaseModel):
    """Revenus d'un relevé regroupés par pays (pour la carte). Ils doublent les lignes de revenus : ne jamais les additionner."""
    pays: str                              # code pays à deux lettres (FR, BE…)
    categorie: Categorie
    periode: Optional[str] = None
    contrat: Optional[str] = None
    quantite: Optional[float] = None
    montant: float
    fichier: str


class DetailPays(BaseModel):
    """Détail des recettes d'un pays, tous relevés confondus, pour la fiche pays de la carte.
    dimension : « titre » ou « plateforme ». Seules les 10 premières valeurs de chaque pays sont gardées."""
    pays: str
    dimension: str
    valeur: str
    montant: float
    quantite: Optional[float] = None


class Avance(BaseModel):
    """Avance versée sur un contrat (ex. coproduction). Son montant est déclaré par le client : les relevés
    ne montrent que le recoupement, période par période (lignes « Advance » négatives)."""
    contrat: str
    projet: Optional[str] = None           # album ou projet couvert par le contrat
    montant: float
    devise: Optional[str] = "EUR"
    date_versement: Optional[date] = None
    versee_au_client: Optional[bool] = None   # True : l'avance a été versée en argent au client (elle n'a pas payé de frais)
    fichier: str
    ligne: int


class Contrat(BaseModel):
    """Fiche d'un contrat, déclarée par le client (fichier .json déposé avec ses relevés) :
    les clauses utiles, les avances (minimums garantis) et la façon de les reconnaître dans les relevés.
    - albums : [{contrat, titre, rang}] : un compte (numéro de contrat des relevés) par album couvert
    - clauses : [{article, titre, texte}] : résumé fidèle des clauses, cité tel quel à l'écran
    - avances : [{nom, album, contrat, montant, motifs, recoupe_avant_releves, source_avant_releves}] :
      « motifs » = morceaux de libellé des lignes « Advance » qui remboursent cette avance, sur n'importe quel compte
    - resultats_anterieurs : [{contrat, montant, jusqu_au, source}] : résultat d'un compte avant le premier relevé détaillé
    - avances_non_remboursables : l'avance ne se compense que sur le résultat (ex. « compensables mais non remboursables »)
    - seuil_accord_depenses : au-delà de ce montant HT, une dépense exige l'accord écrit du client"""
    nom: str
    parties: Optional[str] = None
    date_signature: Optional[date] = None
    albums: List[dict] = Field(default_factory=list)
    clauses: List[dict] = Field(default_factory=list)
    avances: List[dict] = Field(default_factory=list)
    resultats_anterieurs: List[dict] = Field(default_factory=list)
    avances_non_remboursables: bool = False
    seuil_accord_depenses: Optional[float] = None
    avertissement: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    fichier: str = ""


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
    id: Optional[int] = None               # numéro dans la base, une fois enregistrée
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
    decision: Optional[str] = None         # choix du client : « validée » (à réclamer) ou « écartée »


class Import(BaseModel):
    import_id: Optional[int] = None        # numéro dans la base, une fois enregistré
    client: Optional[str] = None
    oeuvres: List[Oeuvre] = Field(default_factory=list)
    enregistrements: List[Enregistrement] = Field(default_factory=list)
    parts: List[Part] = Field(default_factory=list)
    revenus: List[Revenu] = Field(default_factory=list)
    soldes: List[Solde] = Field(default_factory=list)
    avances: List[Avance] = Field(default_factory=list)
    revenus_pays: List[RevenuPays] = Field(default_factory=list)
    detail_pays: List[DetailPays] = Field(default_factory=list)
    contrats: List[Contrat] = Field(default_factory=list)
    fichiers: List[BilanFichier] = Field(default_factory=list)
    manques: List[Manque] = Field(default_factory=list)
    fuites: List[Fuite] = Field(default_factory=list)
    resume: Dict[str, int] = Field(default_factory=dict)
