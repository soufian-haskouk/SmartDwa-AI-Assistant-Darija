"""
prepare_data.py - تطبيع ملف AMMPS الكامل (كل الصفوف، لا فقط العشرين مادة) مع كاش بالـ hash.

الفكرة: كلما أضفتَ صفوفاً أو حدّثتَ الملف الخام، يُعاد الحساب تلقائياً؛ وإن لم يتغير شيء يُتخطى.

Usage:
  python scripts/prepare_data.py                 # يتخطى إن لم يتغير الملف
  python scripts/prepare_data.py --force         # يعيد الحساب دائماً
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "ammps_medicaments.csv"
OUT = ROOT / "data" / "processed" / "ammps_clean.csv"
STATE = ROOT / "data" / "processed" / ".ammps_clean.state.json"


def parse_price(v):
    """'4.303.00 DH' -> 4303.0 ; '10,70 DH' -> 10.7 ; 'SANS PPV DH' -> None.
    القاعدة: آخر فاصل متبوع برقمين هو الفاصلة العشرية، وما قبله فواصل آلاف."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).upper().replace("DH", "").strip()
    if not s or "SANS" in s:
        return None
    s = s.replace(" ", "")
    m = re.fullmatch(r"(\d[\d.,]*?)[.,](\d{2})", s)
    if m:
        return float(m.group(1).replace(".", "").replace(",", "") + "." + m.group(2))
    if re.fullmatch(r"\d+", s):
        return float(s)
    return None


def split_actives(s):
    return [x.strip() for x in str(s).split("//") if x.strip()] if isinstance(s, str) else []


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(force=False):
    if not RAW.exists():
        sys.exit(f"missing {RAW}")
    digest = sha(RAW)
    if not force and OUT.exists() and STATE.exists():
        if json.loads(STATE.read_text()).get("sha256") == digest:
            print("ammps_clean.csv up to date (hash unchanged) - skipped")
            return
    df = pd.read_csv(RAW, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    out = pd.DataFrame({
        "nom": df["Nom"].astype(str).str.strip(),
        "dosage": df["Dosage"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip(),
        "substances": df["Substance_Active"].astype(str).str.strip(),
        "n_actives": df["Substance_Active"].map(lambda s: len(split_actives(s))),
        "presentation": df["Presentation"].astype(str).str.strip(),
        "ppv_dh": df["PPV"].map(parse_price),
        "ph_dh": df["PH"].map(parse_price),
        "commercialise": df["Status"].astype(str).str.strip().eq("Commercialisé"),
    })
    out.to_csv(OUT, index=False, encoding="utf-8")
    STATE.write_text(json.dumps({"sha256": digest, "rows": len(out)}))
    print(f"{len(out)} rows -> {OUT}  | priced: {out.ppv_dh.notna().sum()} | commercialise: {out.commercialise.sum()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    build(ap.parse_args().force)
