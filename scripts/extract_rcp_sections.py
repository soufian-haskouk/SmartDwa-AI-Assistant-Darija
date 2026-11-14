"""
Phase 5a - extract_rcp_sections.py
From the 20 RCP PDFs (one per Level-A substance) extract:
  4.3 Contre-indications   and   4.5 Interactions
then scan each 4.5 for mentions of the OTHER Level-A substances (by name or by drug class)
and write a CANDIDATE list. Nothing here is a validated rule: every row needs human review.

Usage:
  python extract_rcp_sections.py --pdf-dir data/raw/rcp --out data/processed
"""
import argparse, glob, json, os, re, subprocess, unicodedata
import pandas as pd

# file stem -> (substance_id, display name)
FILES = {
 "paracetamol":"PARACETAMOL","ibuprofene":"IBUPROFENE","acide_acetylsalicylique_aspirine":"ACIDE ACETYLSALICYLIQUE",
 "diclofenac":"DICLOFENAC","omeprazole":"OMEPRAZOLE","domperidone":"DOMPERIDONE","loperamide":"LOPERAMIDE",
 "amoxicilline":"AMOXICILLINE","azithromycine":"AZITHROMYCINE","clarithromycine":"CLARITHROMYCINE",
 "metformine":"METFORMINE","levothyroxine":"LEVOTHYROXINE","amlodipine":"AMLODIPINE","bisoprolol":"BISOPROLOL",
 "atorvastatine":"ATORVASTATINE","furosemide":"FUROSEMIDE","salbutamol":"SALBUTAMOL","loratadine":"LORATADINE",
 "cetirizine":"CETIRIZINE","prednisolone":"PREDNISOLONE",
}
# terms (accent-less, lowercase) that point to a target substance. kind = name | class
TERMS = {
 "PARACETAMOL":[("paracetamol","name")],
 "IBUPROFENE":[("ibuprofene","name"),("anti-inflammatoires non steroidiens","class"),("aines","class")],
 "ACIDE ACETYLSALICYLIQUE":[("acide acetylsalicylique","name"),("aspirine","name"),("salicyles","class"),("salicylates","class"),
                            ("anti-inflammatoires non steroidiens","class"),("aines","class")],
 "DICLOFENAC":[("diclofenac","name"),("anti-inflammatoires non steroidiens","class"),("aines","class")],
 "OMEPRAZOLE":[("omeprazole","name"),("inhibiteurs de la pompe a protons","class"),("inhibiteur de la pompe a protons","class"),("ipp","class")],
 "DOMPERIDONE":[("domperidone","name")],
 "LOPERAMIDE":[("loperamide","name")],
 "AMOXICILLINE":[("amoxicilline","name"),("penicillines","class"),("penicilline","class"),("beta-lactamines","class")],
 "AZITHROMYCINE":[("azithromycine","name"),("macrolides","class"),("macrolide","class")],
 "CLARITHROMYCINE":[("clarithromycine","name"),("macrolides","class"),("macrolide","class")],
 "METFORMINE":[("metformine","name"),("biguanides","class"),("antidiabetiques","class")],
 "LEVOTHYROXINE":[("levothyroxine","name"),("hormones thyroidiennes","class")],
 "AMLODIPINE":[("amlodipine","name"),("inhibiteurs calciques","class"),("antagonistes du calcium","class"),("dihydropyridines","class")],
 "BISOPROLOL":[("bisoprolol","name"),("beta-bloquants","class"),("beta-bloquant","class"),("betabloquants","class")],
 "ATORVASTATINE":[("atorvastatine","name"),("statines","class"),("statine","class"),("inhibiteurs de l'hmg","class")],
 "FUROSEMIDE":[("furosemide","name"),("diuretiques","class"),("diuretique","class")],
 "SALBUTAMOL":[("salbutamol","name"),("beta-2 mimetiques","class"),("beta2-mimetiques","class"),("beta-2-mimetiques","class")],
 "LORATADINE":[("loratadine","name"),("antihistaminiques","class")],
 "CETIRIZINE":[("cetirizine","name"),("antihistaminiques","class")],
 "PREDNISOLONE":[("prednisolone","name"),("corticoides","class"),("corticosteroides","class"),("glucocorticoides","class")],
}

def strip_acc(s):  # keep length 1:1 for index mapping
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def pdf_text(path):
    return subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True).stdout

HEAD = {
 "4.3": r"^\s*4\.3\.?\s*Contre[\s\-]?indications?",
 "4.4": r"^\s*4\.4\.?\s*Mises?\s+en\s+garde",
 "4.5": r"^\s*4\.5\.?\s*Interactions?",
 "4.6": r"^\s*4\.6\.?\s*(Fertilit|Grossesse)",
}
def section(text, key, next_key):
    starts = [m.start() for m in re.finditer(HEAD[key], text, re.I | re.M)]
    nexts = [m.start() for m in re.finditer(HEAD[next_key], text, re.I | re.M)]
    best = ""
    for s in starts:                      # table of contents also matches -> keep the LONGEST span
        e = next((n for n in nexts if n > s), None)
        if e and len(text[s:e]) > len(best):
            best = text[s:e]
    return re.sub(r"[ \t]+", " ", best).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", required=True); ap.add_argument("--out", default="data/processed")
    a = ap.parse_args()
    sec_dir = os.path.join(a.out, "rcp_sections"); os.makedirs(sec_dir, exist_ok=True)

    sections, report = {}, []
    for stem, sid in FILES.items():
        path = os.path.join(a.pdf_dir, stem + ".pdf")
        t = pdf_text(path)
        s43, s45 = section(t, "4.3", "4.4"), section(t, "4.5", "4.6")
        sections[sid] = {"4.3": s43, "4.5": s45}
        for k, v in (("4.3", s43), ("4.5", s45)):
            open(os.path.join(sec_dir, f"{stem}_{k}.txt"), "w", encoding="utf-8").write(v)
        report.append({"substance_id": sid, "file": stem + ".pdf", "chars_4_3": len(s43), "chars_4_5": len(s45),
                       "ok": len(s43) > 100 and len(s45) > 100})

    rows = []
    for src, secs in sections.items():
        raw = secs["4.5"]; low = strip_acc(raw).lower()
        for tgt, terms in TERMS.items():
            if tgt == src: continue
            seen = set()
            for term, kind in terms:
                for m in re.finditer(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", low):
                    a0, b0 = max(0, m.start() - 200), min(len(raw), m.end() + 250)
                    ex = re.sub(r"\s+", " ", raw[a0:b0]).strip()
                    key = (term, a0 // 400)
                    if key in seen: continue
                    seen.add(key)
                    rows.append({"source_rcp": src, "target": tgt, "match_type": kind, "matched_term": term,
                                 "excerpt": ex, "source_ref": f"RCP {src} §4.5", "review_status": "TO_REVIEW"})
    cand = pd.DataFrame(rows)
    cand.to_csv(os.path.join(a.out, "interaction_candidates.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(report).to_csv(os.path.join(a.out, "rcp_extraction_report.csv"), index=False)
    print(pd.DataFrame(report).to_string(index=False))
    print("\ncandidate rows:", len(cand), "| distinct (source,target) pairs:", cand[["source_rcp","target"]].drop_duplicates().shape[0])

if __name__ == "__main__":
    main()
