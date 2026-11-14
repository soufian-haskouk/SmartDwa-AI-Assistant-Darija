"""
build_rcp_sections.py - يستخرج البندين 4.3 (موانع الاستعمال) و4.5 (التداخلات) من RCP لكل مادة،
من PDF (data/raw/rcp/<stem>.pdf) أو من صفحة BDPM المحفوظة HTML (data/raw/rcp_html/<stem>.html).

على عكس extract_rcp_sections.py لا يمسّ interaction_candidates.csv (حتى لا يُستبدل بنتائج ناقصة)،
ويقبل مواد ناقصة ويبلّغ عنها. الناتج: data/processed/rcp_sections/<stem>_4.3.txt و_4.5.txt + rcp_extraction_report.csv

Usage: python scripts/build_rcp_sections.py
"""
import csv, html, re, subprocess, sys
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ers", ROOT / "scripts" / "extract_rcp_sections.py")
ers = importlib.util.module_from_spec(spec); spec.loader.exec_module(ers)   # نعيد استعمال FILES و section()

PDF_DIR, HTML_DIR = ROOT / "data/raw/rcp", ROOT / "data/raw/rcp_html"
OUT = ROOT / "data/processed/rcp_sections"

def html_text(path):
    t = Path(path).read_text(encoding="utf-8", errors="ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"</(p|div|h\d|li|tr|table)>|<br\s*/?>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = t.replace("\xa0", " ")
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    notes = {}
    src_csv = HTML_DIR / "sources.csv"
    if src_csv.exists():
        for r in csv.DictReader(open(src_csv, encoding="utf-8")): notes[r["stem"]] = r
    rows = []
    for stem, sid in ers.FILES.items():
        pdf, htm = PDF_DIR / f"{stem}.pdf", HTML_DIR / f"{stem}.html"
        if pdf.exists():   text, kind = ers.pdf_text(str(pdf)), "pdf"
        elif htm.exists(): text, kind = html_text(htm), "html"
        else:
            rows.append(dict(substance_id=sid, source="MISSING", product="", chars_4_3=0, chars_4_5=0, ok=False, note=""))
            continue
        s43, s45 = ers.section(text, "4.3", "4.4"), ers.section(text, "4.5", "4.6")
        (OUT / f"{stem}_4.3.txt").write_text(s43, encoding="utf-8")
        (OUT / f"{stem}_4.5.txt").write_text(s45, encoding="utf-8")
        n = notes.get(stem, {})
        rows.append(dict(substance_id=sid, source=kind, product=n.get("product", "RCP PDF (utilisateur)"),
                         chars_4_3=len(s43), chars_4_5=len(s45), ok=len(s43) > 100 and len(s45) > 100, note=n.get("note", "")))
    with open(ROOT / "data/processed/rcp_extraction_report.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows: print(f"{r['substance_id']:26s} {r['source']:8s} 4.3={r['chars_4_3']:6d} 4.5={r['chars_4_5']:6d} {'OK' if r['ok'] else '--'}  {r['product'][:50]}")
    print(f"\nOK: {sum(r['ok'] for r in rows)}/20 | missing: {[r['substance_id'] for r in rows if r['source']=='MISSING']}")

if __name__ == "__main__":
    main()
