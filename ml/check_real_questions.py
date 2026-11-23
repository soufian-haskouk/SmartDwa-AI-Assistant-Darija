"""Valide real_questions.csv (vraies questions étiquetées à la main) avant de l'envoyer à Colab (évalué comme `test_real`).
Usage : python ml/check_real_questions.py real_questions.csv [--dataset colab_v5/intent_v5_dataset.csv]
Contrôles : colonnes text,label ; labels valides ; doublons ; fuite avec les données d'entraînement (phrase identique) ;
cohérence avec la politique P1 (drapeau rouge ⇒ emergency) ; répartition par classe ; nombre minimal (30 conseillé, 10 minimum technique).
Ne modifie JAMAIS le fichier. Code retour 1 s'il y a une erreur bloquante."""
import argparse, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))
import intent_v5_data as V5

ap = argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--dataset", default=str(ROOT / "colab_v5" / "intent_v5_dataset.csv")); a = ap.parse_args()
err, warn = [], []
try: df = pd.read_csv(a.csv, encoding="utf-8-sig")
except Exception as e: print("ERREUR : lecture impossible :", e); sys.exit(1)
if list(df.columns)[:2] != ["text", "label"]: err.append(f"colonnes attendues : text,label (trouvé : {list(df.columns)})")
else:
    df = df.dropna(subset=["text", "label"]).assign(text=lambda d: d.text.astype(str).str.strip(), label=lambda d: d.label.astype(str).str.strip())
    df = df[df.text != ""]
    bad = df[~df.label.isin(V5.LABELS)]
    for _, r in bad.iterrows(): err.append(f"label inconnu « {r.label} » pour : {r.text[:60]}")
    d = df[df.text.duplicated(keep=False)]
    if len(d): warn.append(f"{d.text.nunique()} phrase(s) en double (une seule sera utile) : {d.text.unique()[:3].tolist()}")
    try:
        tr = pd.read_csv(a.dataset, encoding="utf-8-sig"); leak = df[df.text.isin(set(tr.text))]
        if len(leak): err.append(f"{len(leak)} phrase(s) identique(s) à des données du dataset (fuite) : {leak.text.head(3).tolist()}")
    except FileNotFoundError: warn.append(f"dataset introuvable ({a.dataset}) : contrôle de fuite sauté")
    v = V5.policy_violations(df)
    for _, r in v.iterrows(): warn.append(f"drapeau rouge détecté mais label « {r.label} » (politique P1 ⇒ emergency) : {r.text[:70]}")
    miss = V5.emergency_without_trigger(df)
    if len(miss): warn.append(f"{len(miss)} emergency sans drapeau rouge détecté (OK si c'est voulu ; le lexique est limité)")
    n = len(df); cnt = df.label.value_counts().to_dict()
    if n < 10: err.append(f"seulement {n} lignes valides : minimum 10 (le notebook ignore sinon le fichier)")
    elif n < 30: warn.append(f"{n} lignes : < 30, le chiffre aura un intervalle de confiance très large (≈ ±{58.8/n**0.5:.0f} pts pour une acc. de 90 %)")
    print(f"{n} lignes valides | par classe : {cnt}")
    for lab in V5.LABELS:
        if cnt.get(lab, 0) == 0: warn.append(f"aucune question pour la classe {lab}")
    if n >= 10:
        p = 0.9; print(f"Intervalle de confiance 95 % approximatif pour une acc. de 90 % avec n={n} : ±{196*(p*(1-p)/n)**0.5:.1f} pts")
for w in warn: print("AVERTISSEMENT :", w)
for e in err: print("ERREUR :", e)
print("=> BLOQUANT" if err else "=> OK : fichier utilisable (renommer en real_questions.csv et l'uploader dans le notebook)")
sys.exit(1 if err else 0)
