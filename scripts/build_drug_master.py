"""
Phase 1 - build_drug_master.py
Links CNOPS (Moroccan market list) with BDPM (French reference) at the ACTIVE-SUBSTANCE level
for the 20 Level-A substances, and writes a coverage report.

Usage:
  python build_drug_master.py --cnops <cnops.xlsx> --bdpm-dir <folder with bdpm csv> --out data/processed
Expected BDPM files in --bdpm-dir (names may carry a prefix; matched by suffix):
  bdpm-compositions.csv, bdpm-specialites.csv, bdpm-conditions-prescription.csv
"""
import argparse, glob, os, re, unicodedata
import pandas as pd

# canonical DCI (normalized) -> (display name, therapeutic class, Arabic seed names TO REVIEW)
LEVEL_A = {
 "PARACETAMOL":              ("Paracétamol", "Antalgique/antipyrétique", ["باراسيتامول", "بارسيتامول"]),
 "IBUPROFENE":               ("Ibuprofène", "AINS", ["إيبوبروفين", "ايبوبروفين"]),
 "ACIDE ACETYLSALICYLIQUE":  ("Acide acétylsalicylique (aspirine)", "AINS/antiagrégant", ["أسبرين", "اسبيرين"]),
 "DICLOFENAC":               ("Diclofénac", "AINS", ["ديكلوفيناك"]),
 "OMEPRAZOLE":               ("Oméprazole", "Anti-ulcéreux (IPP)", ["أوميبرازول", "اوميبرازول"]),
 "DOMPERIDONE":              ("Dompéridone", "Digestif/antiémétique", ["دومبيريدون"]),
 "LOPERAMIDE":               ("Lopéramide", "Antidiarrhéique", ["لوبيراميد"]),
 "AMOXICILLINE":             ("Amoxicilline", "Antibiotique", ["أموكسيسيلين", "اموكسيسيلين"]),
 "AZITHROMYCINE":            ("Azithromycine", "Antibiotique", ["أزيثروميسين", "ازيترومايسين"]),
 "CLARITHROMYCINE":          ("Clarithromycine", "Antibiotique", ["كلاريثروميسين"]),
 "METFORMINE":               ("Metformine", "Antidiabétique", ["ميتفورمين"]),
 "LEVOTHYROXINE":            ("Lévothyroxine", "Thyroïde", ["ليفوثيروكسين"]),
 "AMLODIPINE":               ("Amlodipine", "Antihypertenseur", ["أملوديبين", "املوديبين"]),
 "BISOPROLOL":               ("Bisoprolol", "Bêtabloquant", ["بيزوبرولول"]),
 "ATORVASTATINE":            ("Atorvastatine", "Hypolipémiant", ["أتورفاستاتين"]),
 "FUROSEMIDE":               ("Furosémide", "Diurétique", ["فوروسيميد"]),
 "SALBUTAMOL":               ("Salbutamol", "Bronchodilatateur", ["سالبوتامول"]),
 "LORATADINE":               ("Loratadine", "Antihistaminique", ["لوراتادين"]),
 "CETIRIZINE":               ("Cétirizine", "Antihistaminique", ["سيتيريزين"]),
 "PREDNISOLONE":             ("Prednisolone", "Corticoïde", ["بريدنيزولون"]),
}

def norm(s) -> str:
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s).split())

_PATTERNS = {k: re.compile(r"(?<![A-Z0-9])" + re.escape(k) + r"(?![A-Z0-9])") for k in LEVEL_A}

def match_component(comp: str):
    """comp is a normalized single component; return canonical key or None.
    Word-boundary match anywhere, so salt forms ('FUMARATE DE BISOPROLOL') match
    while different molecules ('ESOMEPRAZOLE' vs 'OMEPRAZOLE') do not."""
    for key, pat in _PATTERNS.items():
        if pat.search(comp):
            return key
    return None

def components(dci: str):
    return [norm(x) for x in re.split(r"\s*/\s*|\s+\+\s+", str(dci)) if str(x).strip()]

def find(dirpath, suffix):
    hits = glob.glob(os.path.join(dirpath, f"*{suffix}"))
    if not hits: raise FileNotFoundError(f"{suffix} not found in {dirpath}")
    return hits[0]

def rx_flags(texts):
    t = " | ".join(sorted(set(texts))).lower()
    flags = []
    if re.search(r"liste i(?!i)", t): flags.append("liste I")
    if "liste ii" in t: flags.append("liste II")
    if "stup" in t: flags.append("stupéfiant")
    if "restreinte" in t: flags.append("prescription restreinte")
    return ", ".join(flags)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cnops", required=True)
    ap.add_argument("--bdpm-dir", required=True)
    ap.add_argument("--out", default="data/processed")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)

    # ---------- CNOPS ----------
    cn = pd.read_excel(a.cnops)
    cn["comps"] = cn["DCI1"].map(components)
    cn["targets"] = cn["comps"].map(lambda cs: sorted({k for c in cs if (k := match_component(c))}))
    cn = cn[cn["targets"].map(len) > 0].copy()
    cn["n_components"] = cn["comps"].map(len)
    cn["is_combination"] = cn["n_components"] > 1
    cn["PPV"] = pd.to_numeric(cn["PPV"], errors="coerce")

    # ---------- BDPM ----------
    comp = pd.read_csv(find(a.bdpm_dir, "compositions.csv"), sep=";", dtype=str)
    spec = pd.read_csv(find(a.bdpm_dir, "specialites.csv"), sep=";", dtype=str)
    cond = pd.read_csv(find(a.bdpm_dir, "conditions-prescription.csv"), sep=";", dtype=str)
    comp = comp[comp["nature_composant"].isin(["SA", "FT"])].copy()  # active substances only
    comp["key"] = comp["denomination_substance"].map(norm).map(match_component)
    comp = comp.dropna(subset=["key"])
    spec_i = spec.set_index("cis")
    rows = []
    for key, g in comp.groupby("key"):
        cis = g["cis"].unique()
        sp = spec[spec["cis"].isin(cis)]
        # mono-substance cis (single active substance) are the cleanest reference
        txt = cond[cond["cis"].isin(cis)]["condition_prescription_delivrance"].dropna().tolist()
        cis_with_cond = cond[cond["cis"].isin(cis)]["cis"].nunique()
        rows.append({
            "substance_id": key, "bdpm_cis": len(cis),
            "bdpm_commercialised": int((sp["etat_commercialisation"].str.contains("Commercialis", na=False)).sum()),
            "bdpm_routes": "; ".join(sp["voies_administration"].dropna().str.split(";").explode().str.strip().value_counts().head(4).index),
            "bdpm_forms_top": "; ".join(sp["forme_pharmaceutique"].dropna().value_counts().head(3).index),
            "bdpm_enhanced_surveillance": int((sp["surveillance_renforcee"] == "Oui").sum()),
            "fr_rx_flags_any": rx_flags(txt), "fr_pct_cis_with_rx_condition": round(100 * cis_with_cond / len(cis), 1),
        })
    ref = pd.DataFrame(rows)
    meta = pd.DataFrame([{"substance_id": k, "name": v[0], "class": v[1], "ar_names_seed": " | ".join(v[2])}
                         for k, v in LEVEL_A.items()])
    ref = meta.merge(ref, on="substance_id", how="left")

    # ---------- master (one row per CNOPS product x target substance) ----------
    m = cn.explode("targets").rename(columns={"targets": "substance_id"})
    m = m.merge(ref[["substance_id", "name", "class", "bdpm_cis", "fr_rx_flags_any", "fr_pct_cis_with_rx_condition"]], on="substance_id", how="left")
    keep = ["substance_id", "name", "class", "CODE", "NOM", "DCI1", "DOSAGE1", "UNITE_DOSAGE1", "FORME", "PRESENTATION",
            "PPV", "PRINCEPS_GENERIQUE", "TAUX_REMBOURSEMENT", "is_combination", "bdpm_cis", "fr_rx_flags_any", "fr_pct_cis_with_rx_condition"]
    m[keep].sort_values(["substance_id", "is_combination", "NOM"]).to_csv(
        os.path.join(a.out, "drug_master.csv"), index=False, encoding="utf-8-sig")
    ref.to_csv(os.path.join(a.out, "substances_reference.csv"), index=False, encoding="utf-8-sig")

    # ---------- coverage report ----------
    cov = []
    for key in LEVEL_A:
        s = m[m.substance_id == key]; mono = s[~s.is_combination]
        r = ref[ref.substance_id == key].iloc[0]
        cov.append({"substance": LEVEL_A[key][0], "cnops_rows_total": len(s), "cnops_rows_mono": len(mono),
                    "distinct_brands_mono": mono["NOM"].nunique(),
                    "princeps": int((mono.PRINCEPS_GENERIQUE == "P").sum()), "generics": int((mono.PRINCEPS_GENERIQUE == "G").sum()),
                    "ppv_min": mono.PPV.min(), "ppv_max": mono.PPV.max(),
                    "ppv_zero_rows": int((mono.PPV <= 0).sum()), "bdpm_cis": r.bdpm_cis,
                    "fr_rx_flags_any": r.fr_rx_flags_any, "fr_pct_rx": r.fr_pct_cis_with_rx_condition,
                    "warning": "FEW CNOPS ROWS (<5 mono)" if len(mono) < 5 else ""})
    cov = pd.DataFrame(cov); cov.to_csv(os.path.join(a.out, "coverage_report.csv"), index=False, encoding="utf-8-sig")
    print(cov.to_string(index=False))
    print(f"\nmaster rows: {len(m)} | CNOPS rows in source: {len(pd.read_excel(a.cnops))} | out: {a.out}")

if __name__ == "__main__":
    main()
