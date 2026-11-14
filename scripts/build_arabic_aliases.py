"""
build_arabic_aliases.py - يولّد data/processed/arabic_brand_aliases.csv:
كتابات عربية (من الملف المصري) لعلامات تجارية موجودة فعلاً في AMMPS (المغرب).

قاعدة القبول (حتى لا نربط اسماً عربياً بدواء مختلف):
  1) الاسم التجاري اللاتيني المصري (قبل أول رقم/وحدة) يطابق حرفياً علامة في AMMPS، و
  2) المادة الفعالة المصرية تشبه (تشابه >= 85) مادة فعالة في AMMPS لنفس العلامة.
الأسعار المصرية لا تُستعمل. الأسماء العربية هنا نقحرة مصرية: قد تختلف عن نطق المغاربة، لذلك
المطابقة الحرفية فقط تُنفَّذ تلقائياً، والتشابه بالهيكل الصامت يسأل «واش كتقصد؟».

Usage: python scripts/build_arabic_aliases.py
"""
import collections, re, sys
from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "backend"))
from drug_linker import normalize as ar_norm, skeleton, clean_brand, strip_prefix_ar  # noqa: E402
from app.catalog import norm as lat_norm  # noqa: E402

def first_actives(sci: str) -> list[str]:
    parts = re.split(r"[+/]", str(sci))
    return [lat_norm(re.sub(r"\(.*?\)", "", p)) for p in parts if p.strip()]

def main():
    E = pd.read_csv(ROOT / "data/raw/egypt/egyptian-drugs.csv")
    A = pd.read_csv(ROOT / "data/processed/ammps_clean.csv")
    A["brand_n"] = A.nom.map(lat_norm)
    A["acts"] = A.substances.map(lambda s: {lat_norm(re.sub(r"\(.*?\)", "", a)) for a in str(s).split("//")})
    brand_acts, family = collections.defaultdict(set), collections.defaultdict(set)
    for r in A.itertuples():
        brand_acts[r.brand_n] |= r.acts
        f = r.brand_n.split(" ")[0]
        if len(f) >= 5 and f != r.brand_n: family[f].add(r.brand_n); brand_acts[f] |= r.acts
    keys = set(brand_acts)

    stats = collections.Counter(); cand = collections.defaultdict(collections.Counter); meta = {}
    for r in E.itertuples():
        base = lat_norm(clean_brand(str(r.commercial_name_en)).strip(" .("))
        if len(base) < 4 or not isinstance(r.commercial_name_ar, str): stats["skip_short_or_no_ar"] += 1; continue
        if base not in keys: stats["brand_not_in_ammps"] += 1; continue
        n = len(base.split())
        ar = " ".join(r.commercial_name_ar.split()[:n])          # نفس عدد كلمات العلامة اللاتينية
        if not re.search(r"[؀-ۿ]", ar): stats["no_arabic"] += 1; continue
        eg = first_actives(r.scientific_name) if isinstance(r.scientific_name, str) else []
        score = max((fuzz.ratio(x, y) for x in eg for y in brand_acts[base]), default=0)
        if score < 85: stats["active_disagree"] += 1; continue
        cand[(base, ar_norm(ar))][ar] += 1
        meta[(base, ar_norm(ar))] = dict(egypt_name_en=r.commercial_name_en, egypt_active=r.scientific_name, active_score=score)
        stats["accepted_rows"] += 1

    by_alias = collections.defaultdict(set)
    for (base, an) in cand: by_alias[an].add(base)
    rows = []
    for (base, an), forms in cand.items():
        if len(an) < 4: stats["alias_too_short"] += 1; continue
        if len(by_alias[an]) > 1: stats["ambiguous_alias_dropped"] += 1; continue   # نفس الاسم العربي لعلامتين مختلفتين
        rows.append(dict(alias_ar=forms.most_common(1)[0][0], alias_norm=" ".join(strip_prefix_ar(t) for t in an.split()),
                         skeleton=skeleton(an), brand_key=base, n_egypt_rows=sum(forms.values()), **meta[(base, an)]))
    out = pd.DataFrame(rows).sort_values(["brand_key", "alias_norm"])
    out.to_csv(ROOT / "data/processed/arabic_brand_aliases.csv", index=False, encoding="utf-8-sig")
    print(dict(stats)); print(f"{len(out)} aliases for {out.brand_key.nunique()} AMMPS brands (of {A.brand_n.nunique()} brands)")
    print(out.head(12)[["alias_ar", "brand_key", "active_score"]].to_string(index=False))

if __name__ == "__main__":
    main()
