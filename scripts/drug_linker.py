"""
Phase 3 - drug_linker.py
Entity linking of drug mentions (Latin / Arabic script / Arabizi, with typos) to the 20 Level-A substances.

Two parts:
  1) build_alias_table(): CNOPS brand names + DCI names (FR/EN/AR seeds) + Egyptian Arabic brand spellings
  2) DrugLinker: normalisation + consonant-skeleton ("phonetic key") + fuzzy matching, n-gram scan of a sentence.

CLI:
  python drug_linker.py build --master data/processed/drug_master.csv --egypt <egyptian csv> --out data/processed/alias_table.csv
  python drug_linker.py query  --alias data/processed/alias_table.csv "واش الدوليبران كيتاخد مع الحليب"
"""
import argparse, re, unicodedata, collections
import pandas as pd
from rapidfuzz import fuzz, process
from rapidfuzz.distance import OSA

# ----------------------------------------------------------------- substances (FR display, EN names, AR seeds TO REVIEW)
SUBST = {
 "PARACETAMOL": (["paracetamol", "paracétamol", "acetaminophen"], ["باراسيتامول", "بارسيتامول", "باراسيتمول"]),
 "IBUPROFENE": (["ibuprofene", "ibuprofène", "ibuprofen"], ["ايبوبروفين", "إيبوبروفين", "ايبوبروفان"]),
 "ACIDE ACETYLSALICYLIQUE": (["acide acetylsalicylique", "acide acétylsalicylique", "aspirine", "aspirin", "acetylsalicylic acid"], ["اسبرين", "أسبرين", "اسبيرين", "أسبيرين"]),
 "DICLOFENAC": (["diclofenac", "diclofénac"], ["ديكلوفيناك", "ديكلوفيناك"]),
 "OMEPRAZOLE": (["omeprazole", "oméprazole"], ["اوميبرازول", "أوميبرازول", "اوميبرازول"]),
 "DOMPERIDONE": (["domperidone", "dompéridone"], ["دومبيريدون"]),
 "LOPERAMIDE": (["loperamide", "lopéramide"], ["لوبيراميد"]),
 "AMOXICILLINE": (["amoxicilline", "amoxicillin", "amoxycillin"], ["اموكسيسيلين", "أموكسيسيلين", "اموكسيسلين"]),
 "AZITHROMYCINE": (["azithromycine", "azithromycin"], ["ازيترومايسين", "أزيثروميسين", "ازيثروميسين"]),
 "CLARITHROMYCINE": (["clarithromycine", "clarithromycin"], ["كلاريثروميسين", "كلاريترومايسين"]),
 "METFORMINE": (["metformine", "metformin"], ["ميتفورمين", "ميتفورمين"]),
 "LEVOTHYROXINE": (["levothyroxine", "lévothyroxine", "thyroxine"], ["ليفوثيروكسين", "ليفوتيروكسين"]),
 "AMLODIPINE": (["amlodipine"], ["املوديبين", "أملوديبين"]),
 "BISOPROLOL": (["bisoprolol"], ["بيسوبرولول", "بيزوبرولول"]),
 "ATORVASTATINE": (["atorvastatine", "atorvastatin"], ["اتورفاستاتين", "أتورفاستاتين"]),
 "FUROSEMIDE": (["furosemide", "furosémide", "frusemide"], ["فوروسيميد"]),
 "SALBUTAMOL": (["salbutamol", "albuterol"], ["سالبوتامول"]),
 "LORATADINE": (["loratadine"], ["لوراتادين"]),
 "CETIRIZINE": (["cetirizine", "cétirizine"], ["سيتيريزين", "سيتريزين"]),
 "PREDNISOLONE": (["prednisolone"], ["بريدنيزولون", "بريدنيسولون"]),
}
EN_FIRSTWORD = {}  # english first word (upper) -> substance_id, used to read the Egyptian file
for sid, (names, _) in SUBST.items():
    for n in names:
        EN_FIRSTWORD[unicodedata.normalize("NFD", n).encode("ascii", "ignore").decode().upper().split()[0]] = sid
EN_FIRSTWORD.update({"ACETYLSALICYLIC": "ACIDE ACETYLSALICYLIQUE", "ASPIRIN": "ACIDE ACETYLSALICYLIQUE", "ACETAMINOPHEN": "PARACETAMOL"})

# ----------------------------------------------------------------- normalisation
_TASHKEEL = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
AR_RANGE = re.compile(r"[\u0600-\u06FF]")
UNITS = {"MG", "G", "ML", "MCG", "UI", "L", "KG", "MCG/ML", "MG/ML", "CP", "COMP", "GEL", "AMP", "SACHET", "SACHETS", "B", "BT", "FL"}

def strip_latin(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return s

def norm_ar(s: str) -> str:
    s = _TASHKEEL.sub("", s)
    s = re.sub("[أإآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    s = re.sub("ئ|ؤ", "ء", s)
    return s

_AR_PUNCT = re.compile(r"[\u060C\u061B\u061F\u066A-\u066D\u06D4]")   # ، ؛ ؟ ٪ ... (they sit inside the Arabic block!)

def normalize(s: str) -> str:
    """lowercase, no accents/tashkeel, punctuation -> space. Arabic letters are kept."""
    s = _AR_PUNCT.sub(" ", str(s))
    s = norm_ar(strip_latin(s) if not AR_RANGE.search(s) else _keep_ar(s))
    s = re.sub(r"[^a-z0-9\u0600-\u06FF ]", " ", s)
    return " ".join(s.split())

def _keep_ar(s):  # strip accents only on latin chars, keep arabic
    return "".join(c if AR_RANGE.match(c) else strip_latin(c) for c in s)

# consonant-skeleton classes: merge letters that Arabic/Latin/Arabizi spellings confuse
_LAT = [("ph", "F"), ("th", "T"), ("ch", "S"), ("sh", "S"), ("ck", "K"), ("kh", "K"), ("qu", "K"), ("x", "KS")]
_LATMAP = {"b": "B", "p": "B", "f": "F", "v": "F", "t": "T", "d": "D", "k": "K", "q": "K", "g": "K", "c": "K",
           "s": "S", "z": "S", "j": "K", "l": "L", "m": "M", "n": "N", "r": "R", "h": "", "w": "", "y": "",
           "a": "", "e": "", "i": "", "o": "", "u": ""}
_ARMAP = {"ب": "B", "ت": "T", "ث": "T", "ج": "K", "ح": "", "خ": "K", "د": "D", "ذ": "D", "ر": "R", "ز": "S", "س": "S",
          "ش": "S", "ص": "S", "ض": "D", "ط": "T", "ظ": "S", "ع": "", "غ": "K", "ف": "F", "ق": "K", "ك": "K",
          "ل": "L", "م": "M", "ن": "N", "ه": "", "و": "", "ي": "", "ا": "", "ء": "", "گ": "K", "پ": "B", "ڤ": "F"}

def strip_prefix_ar(tok: str) -> str:
    for p in ("ال", "لل", "وال", "بال", "فال"):
        if tok.startswith(p) and len(tok) - len(p) >= 3:
            return tok[len(p):]
    return tok

def skeleton(s: str) -> str:
    """consonant skeleton key, e.g. DOLIPRANE / dolyprane / دوليبران -> DLBRN"""
    parts = []
    for tok in normalize(s).split():
        tok = strip_prefix_ar(tok)
        if AR_RANGE.search(tok):
            parts.append("".join(_ARMAP.get(c, "") for c in tok))
            continue
        tok = re.sub(r"(?<=[a-z])7(?=[a-z])|^7(?=[a-z])", "h", tok)      # arabizi digits inside words
        tok = re.sub(r"(?<=[a-z])9(?=[a-z])|^9(?=[a-z])", "q", tok)
        tok = re.sub(r"(?<=[a-z])5(?=[a-z])", "kh", tok)
        tok = re.sub(r"[0-9]", "", tok)
        for a, b in _LAT:
            tok = tok.replace(a, b.lower())
        tok = re.sub(r"c(?=[ei])", "s", tok)
        tok = re.sub(r"g(?=[ei])", "k", tok)
        parts.append("".join(_LATMAP.get(c, c.upper()) for c in tok))
    return re.sub(r"(.)\1+", r"\1", "".join(parts))

# ----------------------------------------------------------------- alias table
def clean_brand(nom: str) -> str:
    toks = []
    for t in re.split(r"\s+", str(nom).upper().strip()):
        if re.search(r"\d", t) or t in UNITS: break
        toks.append(t)
    return " ".join(toks).strip()

def build_alias_table(master_csv, egypt_csv, out_csv, cnops_xlsx=None):
    m = pd.read_csv(master_csv)
    rows = []
    # (a) DCI names
    for sid, (names, ar) in SUBST.items():
        for n in names: rows.append(dict(alias=n, alias_type="dci", lang="fr/en", substance_id=sid, is_combination=False, source="manual"))
        for n in ar:    rows.append(dict(alias=n, alias_type="dci", lang="ar", substance_id=sid, is_combination=False, source="manual-seed-REVIEW"))
    # (b) CNOPS brands
    m["brand"] = m["NOM"].map(clean_brand)
    for brand, g in m[m.brand.str.len() >= 3].groupby("brand"):
        sids = sorted(set(g.substance_id)); comb = bool(g.is_combination.any())
        rows.append(dict(alias=brand, alias_type="brand", lang="fr", substance_id="|".join(sids), is_combination=comb, source="cnops"))
        first = brand.split()[0]
        if " " in brand and len(first) >= 5 and first not in {"AMOXICILLINE", "PARACETAMOL", "IBUPROFENE", "DICLOFENAC"}:
            rows.append(dict(alias=first, alias_type="brand_first_token", lang="fr", substance_id="|".join(sids), is_combination=comb, source="cnops"))
    # (c) Egyptian brands (mono-ingredient only): Latin + Arabic spelling pairs
    e = pd.read_csv(egypt_csv, on_bad_lines="skip")
    def sci_first(s):
        s = re.sub(r"\(.*?\)", " ", str(s).upper())
        comps = [c.strip() for c in re.split(r"[+,]", s) if c.strip()]
        if len(comps) != 1: return None
        w = re.sub(r"[^A-Z]", " ", comps[0]).split()
        return EN_FIRSTWORD.get(w[0]) if w else None
    e["sid"] = e["scientific_name"].map(sci_first)
    e = e.dropna(subset=["sid"])
    def first_tok(s, ar=False):
        for t in str(s).split():
            if re.search(r"\d", t): break
            t = re.sub(r"[^A-Za-z\u0600-\u06FF]", "", t)
            if len(t) >= 3: return t
        return ""
    e["en1"] = e.commercial_name_en.map(first_tok); e["ar1"] = e.commercial_name_ar.map(first_tok)
    cnops_map = collections.defaultdict(set)                      # normalised CNOPS brand (and first token) -> substances
    for r in rows:
        if r["source"] == "cnops":
            for sid in r["substance_id"].split("|"): cnops_map[normalize(r["alias"])].add(sid)
    cnt = collections.Counter(zip(e.en1.str.upper(), e.ar1, e.sid))
    for (en, ar, sid), c in cnt.items():
        src = "egypt+cnops" if sid in cnops_map.get(normalize(en), set()) else "egypt"   # brand names differ by country!
        if en and len(en) >= 4:
            rows.append(dict(alias=en, alias_type="brand_egypt", lang="en", substance_id=sid, is_combination=False, source=src))
        if ar and AR_RANGE.search(ar) and len(ar) >= 3:
            rows.append(dict(alias=ar, alias_type="brand_egypt", lang="ar", substance_id=sid, is_combination=False, source=src))
    # (d) OUT-OF-SCOPE drugs (everything else in CNOPS): lets the linker say "known drug, but not in my knowledge base"
    if cnops_xlsx:
        full = pd.read_excel(cnops_xlsx)
        lvl = set(SUBST)
        def is_lvl(dci):
            n = normalize(dci).upper()
            return any(re.search(r"(?<![A-Z0-9])" + re.escape(k) + r"(?![A-Z0-9])", n) for k in lvl)
        other = full[~full["DCI1"].astype(str).map(is_lvl)].copy()
        for dci in other["DCI1"].dropna().astype(str).str.strip().unique():
            n = normalize(dci)
            if len(n) >= 5 and "/" not in dci:
                rows.append(dict(alias=dci.upper(), alias_type="dci_other", lang="fr", substance_id="OUT:" + n.upper(), is_combination=False, source="cnops-out"))
        other["brand"] = other["NOM"].map(clean_brand)
        for brand, g in other[other.brand.str.len() >= 4].groupby("brand"):
            sid = "OUT:" + normalize(str(g["DCI1"].iloc[0])).upper()
            rows.append(dict(alias=brand, alias_type="brand_other", lang="fr", substance_id=sid, is_combination=False, source="cnops-out"))
    df = pd.DataFrame(rows)
    df["norm"] = df.alias.map(normalize); df["skel"] = df.alias.map(skeleton)
    order = {"dci": 0, "brand": 1, "brand_first_token": 2, "dci_other": 3, "brand_other": 4, "brand_egypt": 5}
    df["_rank"] = df.alias_type.map(order) * 10 + df.source.map({"manual": 0, "cnops": 0, "cnops-out": 0, "egypt+cnops": 1, "manual-seed-REVIEW": 1}).fillna(2)
    df = df[df.norm.str.len() >= 3].sort_values("_rank", kind="stable").drop_duplicates(subset=["norm", "substance_id"]).drop(columns="_rank").reset_index(drop=True)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    return df

# ----------------------------------------------------------------- linker
class DrugLinker:
    FUZZY_TYPES = {"dci", "brand", "brand_first_token", "dci_other", "brand_other"}      # egyptian brands: exact (norm / skeleton) only
    def __init__(self, alias_csv, threshold=0.88, common_words_file=None):
        self.df = pd.read_csv(alias_csv, dtype=str, keep_default_na=False)
        self.th = threshold
        self.common = set()
        if common_words_file:
            self.common = {w.strip() for w in open(common_words_file, encoding="utf-8") if w.strip()}
        self.by_norm = collections.defaultdict(list); self.by_skel = collections.defaultdict(list)
        for i, r in self.df.iterrows():
            self.by_norm[r.norm].append(i)
            if len(r.skel) >= 4: self.by_skel[r.skel].append(i)
        fz = self.df[self.df.alias_type.isin(self.FUZZY_TYPES)]
        self.fz_idx = list(fz.index)
        self.fz_norm = [self.df.norm[i] for i in self.fz_idx]
        self.fz_skel = [self.df.skel[i] for i in self.fz_idx]

    def _score_candidate(self, q_norm, q_skel, approx=True):
        """list of (score, row_index). Skeleton equality is weak evidence (vowels are dropped), so:
        same-script skeleton matches must also look similar as plain strings; cross-script (Arabic<->Latin) gets a flat 0.92."""
        q_ar = bool(AR_RANGE.search(q_norm))
        best = [(1.0, i) for i in self.by_norm.get(q_norm, [])]
        if not approx:
            return best
        if len(q_skel) >= 5:
            pen = 0.0
            for i in self.by_skel.get(q_skel, []):
                a_norm = self.df.norm[i]
                if q_ar != bool(AR_RANGE.search(a_norm)):
                    sc = 0.92
                else:
                    r = fuzz.ratio(q_norm, a_norm) / 100
                    if r < 0.65: continue
                    sc = 0.80 + 0.15 * r
                best.append((sc - pen, i))
        L = len(q_norm)
        allowed = 0 if L < 5 else 1 if L <= 8 else 2        # typos tolerated grow with word length
        if allowed:
            for choice, d, pos in process.extract(q_norm, self.fz_norm, scorer=OSA.distance, limit=5, score_cutoff=allowed):
                if abs(len(choice) - L) > allowed: continue
                sc = (0.94 if L >= 6 else 0.91) if d == 1 else 0.90
                best.append((sc, self.fz_idx[pos]))
        if L >= 4:
            for choice, sc, pos in process.extract(q_norm, self.fz_norm, scorer=fuzz.ratio, limit=5, score_cutoff=88):
                best.append((sc / 100 * 0.98, self.fz_idx[pos]))
        if len(q_skel) >= 5:
            for choice, sc, pos in process.extract(q_skel, self.fz_skel, scorer=fuzz.ratio, limit=5, score_cutoff=85):
                best.append((sc / 100 * 0.90, self.fz_idx[pos]))
        return best

    def link_term(self, term, k=3, approx=None):
        """link a short drug-name string; returns top-k distinct substance ids with scores.
        approx=None -> approximate matching only for a single word that is not a common word of patient language."""
        qn, qs = normalize(term), skeleton(term)
        qn = " ".join(strip_prefix_ar(t) for t in qn.split())
        if approx is None:
            approx = (" " not in qn) and (qn not in self.common) and (normalize(term) not in self.common)
        cands = self._score_candidate(qn, qs, approx=approx)
        agg = {}
        for sc, i in cands:
            r = self.df.loc[i]
            for sid in r.substance_id.split("|"):
                if sid not in agg or sc > agg[sid][0]:
                    agg[sid] = (sc, r.alias, r.alias_type, r.source, r.is_combination == "True")
        res = sorted(((v[0], sid, v[1], v[2], v[3], v[4]) for sid, v in agg.items()), key=lambda t: -t[0])[:k]
        return [dict(score=round(a[0], 3), substance_id=a[1], matched_alias=a[2], alias_type=a[3], source=a[4], is_combination=a[5]) for a in res]

    @staticmethod
    def confidence(score):
        return "high" if score >= 0.97 else "medium" if score >= 0.93 else "low"

    def find_drugs(self, text, max_n=3):
        """scan a sentence with 1..max_n word windows; non-overlapping best matches above threshold.
        Each hit has: confidence (high/medium/low), ambiguous (runner-up within 0.02 and a different substance),
        out_of_scope (known drug but not one of the 20)."""
        toks = re.findall(r"[A-Za-z0-9\u00C0-\u017F\u0600-\u06FF'’\-]+", text)
        cands = []
        for n in range(1, max_n + 1):
            for s in range(0, len(toks) - n + 1):
                span = " ".join(toks[s:s + n])
                if len(normalize(span)) < 4: continue
                res = self.link_term(span, k=2)
                if res and res[0]["score"] >= self.th:
                    cands.append((res[0]["score"], n, s, s + n, span, res))
        cands.sort(key=lambda x: (-x[0], -x[1]))
        used, out = set(), []
        for sc, n, a, b, span, res in cands:
            if used & set(range(a, b)): continue
            used |= set(range(a, b))
            top = res[0]
            amb = len(res) > 1 and res[1]["score"] >= self.th and (top["score"] - res[1]["score"]) < 0.02 and res[1]["substance_id"] != top["substance_id"]
            conf = "low" if top["source"] == "egypt" else self.confidence(top["score"])   # country-specific brand names: always confirm
            out.append(dict(span=span, confidence=conf, ambiguous=amb,
                            out_of_scope=top["substance_id"].startswith("OUT:"),
                            alternatives=[r["substance_id"] for r in res[1:] if r["score"] >= self.th], **top, _pos=a))
        out.sort(key=lambda r: r["_pos"])
        for r in out: r.pop("_pos")
        return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd")
    b = sp.add_parser("build"); b.add_argument("--master"); b.add_argument("--egypt"); b.add_argument("--out"); b.add_argument("--cnops")
    q = sp.add_parser("query"); q.add_argument("--alias"); q.add_argument("text")
    a = ap.parse_args()
    if a.cmd == "build":
        df = build_alias_table(a.master, a.egypt, a.out, a.cnops); print(df.alias_type.value_counts()); print("aliases:", len(df))
    elif a.cmd == "query":
        for r in DrugLinker(a.alias).find_drugs(a.text): print(r)
