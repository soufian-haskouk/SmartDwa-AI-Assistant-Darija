"""تقطيع نصوص RCP (§4.3 و§4.5) إلى chunks صغيرة قابلة للاسترجاع مع metadata للمصدر."""
import csv, re
from pathlib import Path

BULLETS = r"[·•●▪◦]"
SECTION_LABEL = {"4.3": "contre-indications", "4.5": "interactions médicamenteuses"}
CATEGORY = re.compile(r"(associations? (?:contre-?indiqu[ée]es?|d[ée]conseill[ée]es?)|pr[ée]cautions? d['’]emploi|[àa] prendre en compte)", re.I)
MIN_CH, MAX_CH = 220, 900

def clean(text: str) -> str:
    t = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    return re.sub(r"^4\.[35]\.?[^.]{0,120}?(?=[A-ZÉÀ·•])", "", t, count=1).strip() if t.startswith("4.") else t

def split_units(text: str) -> list[str]:
    t = clean(text)
    t = re.sub(rf"\s*{BULLETS}\s*", "\n", t)              # نقاط القوائم
    t = re.sub(r"\s\+\s(?=[A-ZÉÀ(])", "\n+ ", t)          # صيغة ANSM: «+ دواء»
    units = [u.strip(" \n") for u in t.split("\n")]
    return [u for u in units if len(u) > 2]

def split_long(u: str) -> list[str]:
    if len(u) <= MAX_CH:
        return [u]
    sents = re.split(r"(?<=[.;!?])\s+", u)
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > MAX_CH:
            out.append(cur); cur = cur.split(". ")[-1] + " " + s   # تداخل جملة واحدة
        else:
            cur = (cur + " " + s).strip()
    if cur: out.append(cur)
    return out

def make_chunks(text: str) -> list[tuple[str, str]]:
    """returns [(category, chunk_text)]"""
    chunks, cat, buf, buf_cat = [], "", "", ""
    def flush():
        nonlocal buf
        if buf.strip(): chunks.append((buf_cat, buf.strip()))
        buf = ""
    for u in (x for raw in split_units(text) for x in split_long(raw)):
        m = CATEGORY.search(u[:160])
        if m and len(u) < 160:                 # عنوان فئة (مثلاً «Associations déconseillées»)
            flush(); cat = m.group(1).capitalize(); continue
        if m: cat = m.group(1).capitalize()
        if buf and ((u.startswith("+ ") and len(buf) >= MIN_CH) or (len(buf) + len(u) + 1 > MAX_CH and len(buf) >= MIN_CH)):
            flush()
        if not buf: buf_cat = cat
        buf = (buf + " " + u).strip()
    flush()
    return chunks

def build_all(sections_dir: Path, report_csv: Path, files: dict) -> list[dict]:
    prod = {}
    if report_csv.exists():
        for r in csv.DictReader(open(report_csv, encoding="utf-8-sig")):
            prod[r["substance_id"]] = r["product"]
    out = []
    for stem, sid in files.items():
        for sec in ("4.3", "4.5"):
            p = sections_dir / f"{stem}_{sec}.txt"
            if not p.exists(): continue
            for i, (cat, txt) in enumerate(make_chunks(p.read_text(encoding="utf-8"))):
                out.append(dict(id=f"{stem}_{sec}_{i:02d}", substance_id=sid, stem=stem, section=sec, category=cat,
                                product=prod.get(sid, ""), source=f"RCP {sid} §{sec}", text=txt))
    return out
