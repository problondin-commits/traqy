"""
Traqy · Calculs des modules Valeur et Projection (repris de l'ancien Colab, résultats inchangés).

Valeur     : chiffre d'affaires réel d'un album depuis sa sortie, d'après les relevés du distributeur.
Projection : prolongation de la courbe jusqu'à la date de fin d'exploitation, avec un test à rebours.
Estimation : CA à partir des écoutes publiques, quand le client n'a pas encore de relevés.
             Aucun taux par défaut : le client saisit son taux. Le résultat est toujours une estimation.

Les contrats, taux de partage, frais et avances du client sont lus et renvoyés avec le reste.
"""
import hashlib
import io
import math
from datetime import date

import numpy as np
import pandas as pd

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
TYPES_VENTES = ["Digital Sales", "Physical Sales"]

class ErreurReleves(ValueError):
    """Relevés absents, illisibles ou sans ligne pour le produit demandé."""

def mois_fr(p):  # Period -> "février 2024"
    return f"{MOIS_LONG[p.month-1]} {p.year}"

def ajouter_mois(d, n):
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(y, m + 1, 1)


# --- Lecture des relevés ---------------------------------------------------------

def lire_releves(fichiers, controle):
    """fichiers : liste de (nom, contenu en octets). Ignore les doublons exacts, convertit les nombres (virgule décimale)."""
    fichiers = sorted(fichiers, key=lambda f: f[0])
    if not fichiers:
        raise ErreurReleves("Aucun relevé CSV reçu.")
    vus, frames = {}, []
    for nom, contenu in fichiers:
        h = hashlib.md5(contenu).hexdigest()
        if h in vus:
            controle.append(f"DOUBLON ignoré : {nom} identique à {vus[h]}")
            continue
        vus[h] = nom
        try:
            d = pd.read_csv(io.BytesIO(contenu), sep=";", encoding="utf-8-sig", dtype=str)
        except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError):
            raise ErreurReleves(f"Le fichier {nom} n'est pas un relevé CSV lisible (séparateur « ; », encodage UTF-8).")
        for c in ["Ventes", "Retours", "Ventes nettes", "Revenu", "Revenu net", "Montant"]:
            if c in d:
                d[c] = pd.to_numeric(d[c].str.replace(",", "."), errors="coerce")
        d["_fichier"] = nom
        frames.append(d)
        controle.append(f"Lu : {nom} ({len(d)} lignes)")
    D = pd.concat(frames, ignore_index=True)
    manquantes = [c for c in ["Type", "Titre du produit / Description", "Revenu"] if c not in D]
    if manquantes:
        raise ErreurReleves(f"Colonnes absentes des relevés : {', '.join(manquantes)}.")
    return D

def lister_produits(D, nombre=12):
    """Albums / produits trouvés dans les relevés, du plus gros au plus petit CA."""
    v = D[D["Type"].isin(TYPES_VENTES)]
    t = v.groupby("Titre du produit / Description")["Revenu"].sum().sort_values(ascending=False).head(nombre)
    return [{"produit": nom, "revenu": float(val)} for nom, val in t.items()]


# --- Test à rebours : la méthode est-elle fiable sur le passé de cet album ? ---------

def _decroissance(h, H, W):
    y = np.log(np.clip(h[-W:], 1, None)); b, a0 = np.polyfit(np.arange(W), y, 1); L = np.exp(a0 + b * (W - 1))
    return np.array([L * np.exp(b * k) for k in range(1, H + 1)])
def _puissance(h, H, W=9):
    c = len(h); p, a0 = np.polyfit(np.log(np.arange(c - W + 1, c + 1)), np.log(np.clip(h[-W:], 1, None)), 1)
    return np.exp(a0 + p * np.log(np.arange(c + 1, c + H + 1)))
def _plat(h, H, W=3):
    return np.full(H, h[-3:].mean())

def test_a_rebours(mm, fenetre, age_min=18):
    """Cache les derniers mois, les prévoit avec le passé seul, compare au réel."""
    m = mm.values.astype(float); n = len(m); lab = [str(p) for p in mm.index]
    M = [("Baisse régulière (méthode de cet audit)", lambda h, H: _decroissance(h, H, fenetre)),
         ("Baisse qui ralentit", _puissance), ("Niveau stable", _plat)]
    out = {"mois": n, "age_min": age_min, "ok": False}
    for H in (3, 6):
        pts = list(range(max(age_min, fenetre), n - H + 1))
        if len(pts) < 6: continue
        res = {}
        for nom, f in M:
            e = np.array([f(m[:c], H).sum() / m[c:c + H].sum() - 1 for c in pts])
            res[nom] = {"ecart_moyen": float(np.abs(e).mean()), "biais": float(e.mean()), "pire": float(e[np.abs(e).argmax()])}
        out["h%d" % H] = {"tests": len(pts), "methodes": res}
    if "h3" in out:
        out["ok"] = True; c = n - 3
        p = M[0][1](m[:c], 3).sum(); r = m[c:].sum()
        out["exemple"] = {"depuis": lab[c - 1], "prevu": float(p), "reel": float(r), "ecart": float(p / r - 1)}
    return out


# --- Estimation de la période AVANT les relevés (écoutes publiques Kworb) ------------
# Un seul montant, toujours présenté comme une estimation, non compté dans le total.
# Les 4 coefficients de fourchette du Colab (0,884 ; 1,064 ; 1,12 ; 0,87) sont retirés : aucune source.
SOURCE_KWORB = "Kworb (écoutes Spotify publiques, saisies à la main)"

def estimer_avant_releves(A, avant, total_pub, par_jour, date_pub):
    st = A[A["Type dexploitation"] == "Streaming"]
    sp = st[st["Plateforme"] == "Spotify"]
    if sp.empty or total_pub <= 0: return None
    ecoutes_rel = float(sp["Ventes nettes"].sum())
    fin_op = sp["mois_op"].max()
    jours_apres = max(0, (date.fromisoformat(date_pub) - ajouter_mois(date(fin_op.year, fin_op.month, 1), 1)).days) if date_pub else 0
    manque = total_pub - ecoutes_rel - par_jour * jours_apres
    if manque <= 0: return None
    pm = sp.groupby("mois")["Revenu"].sum().iloc[:12].sum() / sp.groupby("mois")["Ventes nettes"].sum().iloc[:12].sum()  # € par écoute, 12 premiers mois relevés
    part = float(sp["Revenu"].sum() / A["Revenu"].sum())  # part de Spotify dans le CA de l'album
    return {"nature": "estimation", "source": SOURCE_KWORB + (f", page du {date_pub}" if date_pub else ""),
            "montant": float(manque * pm / part), "ecoutes_manquantes": float(manque), "ecoutes_relevees": ecoutes_rel,
            "taux_1000": float(pm * 1000), "part_spotify": part,
            "mois": int(avant["mois"]), "moyenne_mois": float(manque / avant["mois"])}


# --- Valeur et Projection ----------------------------------------------------------

def calculer_valeur(D, produits, fin, aujourdhui, baisse_min=0.05, baisse_max=0.35, fenetre=12,
                    avec_video=False, sortie=None, ecoutes_publiques=0, ecoutes_jour=0, date_publique=None):
    """Renvoie (résultat, contrôles, contrats et frais)."""
    ctl, contrats = [], []
    today, fin = date.fromisoformat(aujourdhui), date.fromisoformat(fin)
    ctl.append(f"Types de lignes : {D['Type'].value_counts().to_dict()}")
    for t in ["Expense", "Advance", "Neighboring Rights"]:
        x = D[D["Type"] == t]
        if len(x):
            contrats.append(f"{t} : {x['Revenu'].sum():.2f} (somme brute, hors CA)")
    if "Numéro de contrat" in D:
        contrats.append(f"Contrats : {sorted(D['Numéro de contrat'].dropna().unique())}")
    if "Taux" in D:
        contrats.append(f"Taux de partage vus : {list(D['Taux'].dropna().unique()[:6])}")

    # 1) Périmètre : ventes numériques + physiques du produit audité
    ventes = D[D["Type"].isin(TYPES_VENTES)]
    A = ventes[ventes["Titre du produit / Description"].isin(produits)].copy()
    if not avec_video:
        A = A[A["Type de produit"].fillna("") != "videoOfficialContent"]
    if A.empty:
        raise ErreurReleves("Aucune ligne pour ce produit. Titres disponibles : " +
                            str(list(ventes["Titre du produit / Description"].value_counts().head(10).index)))
    hors = ventes.drop(A.index)
    contrats.append(f"CA hors périmètre (autres produits, vidéos) : {hors['Revenu'].sum():.2f}")

    A["mois"] = pd.to_datetime(A["Date de reporting"], format="%d/%m/%Y").dt.to_period("M")
    A["mois_op"] = pd.to_datetime(A["Date dopération"], format="%d/%m/%Y", errors="coerce").dt.to_period("M")
    mm = A.groupby("mois")["Revenu"].sum()
    # contrôle de continuité des mois
    idx = pd.period_range(mm.index.min(), mm.index.max(), freq="M")
    manquants = [str(p) for p in idx if p not in mm.index]
    if manquants:
        ctl.append(f"ATTENTION mois sans relevé : {manquants}. Demander les semestres manquants.")
    mm = mm.reindex(idx, fill_value=0.0)

    realise = float(A["Revenu"].sum())
    stream = A[A["Type dexploitation"] == "Streaming"]
    streams = float(stream["Ventes nettes"].sum())
    streamrev = float(stream["Revenu"].sum())
    phys = A[A["Type"] == "Physical Sales"]
    phys_units = {k: int(v) for k, v in phys.groupby("Type de produit")["Ventes nettes"].sum().items()}
    pays = stream.groupby("Pays")["Ventes nettes"].sum()
    part_fr = float(pays.get("FR", 0) / pays.sum() * 100) if pays.sum() else 0.0
    plat = {k: float(v) for k, v in stream.groupby("Plateforme")["Revenu"].sum().sort_values(ascending=False).head(4).items()}

    # 2) Date de sortie : premier mois d'opération qui atteint 25 % du mois record
    mo = A.groupby("mois_op")["Revenu"].sum().dropna()
    if sortie:
        sortie = pd.Period(sortie[:7], "M")
    else:
        sortie = mo[mo >= 0.25 * mo.max()].index.min()
    ctl.append(f"Sortie retenue : {sortie} (détectée sur les dates d'opération ; à confirmer avec le client)")

    # 3) Baisse mesurée sur les derniers mois complets
    y = mm.iloc[-fenetre:]
    t = np.arange(len(y))
    b, a0 = np.polyfit(t, np.log(y.clip(lower=1).values), 1)
    baisse = float(1 - np.exp(12 * b)); L = float(np.exp(a0 + b * (len(y) - 1)))
    ctl.append(f"Baisse annuelle mesurée sur {len(y)} mois : {baisse*100:.1f} % ; niveau mensuel de départ : {L:.0f}")

    # 4) Projection mois par mois, répartie par périodes
    dernier = mm.index.max()
    debut_gap = ajouter_mois(date(dernier.year, dernier.month, 1), 1)  # 1er du mois suivant le dernier relevé
    bornes = [debut_gap, today]
    k = 1
    while True:
        d = date(today.year + k, today.month, today.day)
        if d >= fin: bornes.append(fin); break
        bornes.append(d); k += 1
    def projeter(kmensuel):
        res = [0.0] * (len(bornes) - 1)
        n, m0 = 1, debut_gap
        while m0 < fin:
            m1 = ajouter_mois(m0, 1); val = L * np.exp(kmensuel * n)
            for i in range(len(bornes) - 1):
                lo, hi = max(m0, bornes[i]), min(m1, bornes[i + 1])
                if hi > lo: res[i] += val * (hi - lo).days / (m1 - m0).days
            n += 1; m0 = m1
        return res
    per = projeter(b)
    def plab(i):
        d0, d1 = bornes[i], bornes[i + 1]
        f = lambda d: f"{d.day} {MOIS[d.month-1]} {d.year}"
        if i == 0: return f"{MOIS[d0.month-1]} {d0.year} – {f(d1)} (non relevé)"
        return f"{f(d0)} – {f(d1)}"
    periodes = [{"label": plab(i), "valeur": float(v)} for i, v in enumerate(per)]
    def total_pour(baisse_ann):
        return realise + sum(projeter(np.log(1 - baisse_ann) / 12))
    lo_total, hi_total = total_pour(baisse_max), total_pour(baisse_min)

    R = dict(
        produit=list(produits), aujourdhui=today.isoformat(), fin=fin.isoformat(),
        dernier_releve=str(dernier), debut_releves=str(mm.index.min()),
        realise=realise, avenir=float(sum(per)), total=realise + float(sum(per)),
        gap=float(per[0]), periodes=periodes,
        baisse=baisse, niveau_depart=L,
        total_bas=lo_total, total_haut=hi_total, baisse_min=baisse_min, baisse_max=baisse_max,
        streams=streams, streamrev=streamrev, taux_1000=(streamrev / streams * 1000 if streams else 0),
        phys=float(phys["Revenu"].sum()), phys_units=phys_units,
        part_france=part_fr, plateformes=plat,
        ecoutes_dernier_mois=float(stream[stream["mois"] == dernier]["Ventes nettes"].sum()),
        sortie=str(sortie), sortie_fr=mois_fr(sortie),
        mois=[str(p) for p in mm.index], ca_mensuel=[float(v) for v in mm.values],
        pic=float(mm.max()), pic_mois=str(mm.idxmax()), dernier_mois_ca=float(mm.iloc[-1]),
        six_derniers=float(mm.iloc[-6:].sum()),
        annee=[{"annee": int(an), "valeur": float(v)} for an, v in mm.groupby(mm.index.year).sum().items()],
    )
    nb_avant = (mm.index.min() - sortie).n
    R["avant_releves"] = {"mois": int(nb_avant), "debut": str(sortie), "fin": str(mm.index.min() - 1)} if nb_avant >= 2 else None
    if R["avant_releves"]:
        ctl.append(f"ATTENTION : album sorti en {sortie}, relevés disponibles à partir de {mm.index.min()} : {nb_avant} mois non couverts.")
    R["estim_avant"] = estimer_avant_releves(A, R["avant_releves"], ecoutes_publiques, ecoutes_jour, date_publique) if R["avant_releves"] else None
    if R["estim_avant"]:
        e = R["estim_avant"]
        ctl.append(f"Estimation avant relevés ({e['source']}) : {e['ecoutes_manquantes']/1e6:.1f} M d'écoutes manquantes, {e['montant']:,.0f}, non comptée dans le total.")
    R["backtest"] = test_a_rebours(mm, fenetre)
    ctl.append("Test à rebours : " + ("effectué sur %d mois d'historique" % R["backtest"]["mois"] if R["backtest"]["ok"] else "non concluant (historique trop court)"))
    ctl.append(f"CA réalisé : {realise:,.0f} | à venir : {R['avenir']:,.0f} | total : {R['total']:,.0f}")
    ctl.append(f"Fourchette : {lo_total:,.0f} à {hi_total:,.0f}")
    return R, ctl, contrats


# --- Mode estimation (sans relevés) --------------------------------------------------

def estimer(albums, fin, aujourdhui, taux_1000, physique, baisse):
    """albums : liste de {album, ecoutes_cumulees, ecoutes_par_jour}. taux_1000 et physique sont saisis par le client."""
    lam = -math.log(1 - baisse)               # vitesse de décroissance par an
    r = taux_1000 / 1000 * (1 + physique)     # € par écoute, physique compris
    y0 = (date.fromisoformat(fin) - date.fromisoformat(aujourdhui)).days / 365.25
    cum = lambda t: (1 - math.exp(-lam * t)) / lam   # somme de la courbe de t=0 à t
    cuts = [c for c in [0, 1, 2, 3, 4, 5] if c < y0] + [y0]
    lignes = []
    for a in albums:
        done = a["ecoutes_cumulees"] * r
        rate = a["ecoutes_par_jour"] * 365   # écoutes par an, rythme actuel
        fut = rate * cum(y0) * r
        per = [rate * (cum(t) - cum(cuts[i])) * r for i, t in enumerate(cuts[1:])]
        lignes.append({"album": a["album"], "realise": done, "avenir": fut, "total": done + fut, "par_annee": per})
    return {
        "nature": "estimation",
        "albums": lignes,
        "realise": sum(l["realise"] for l in lignes),
        "avenir": sum(l["avenir"] for l in lignes),
        "total": sum(l["total"] for l in lignes),
    }
