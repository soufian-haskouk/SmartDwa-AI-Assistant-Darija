"""كتالوج الأسعار على كل صفوف AMMPS (9755): بحث بالاسم التجاري أو المادة الفعالة، حتى خارج الـ 20 مادة.
- exact  (اسم تجاري/مادة مطابقة حرفياً بعد التطبيع)  => نعرض الأسعار.
- fuzzy  (تشابه بخطأ إملائي)                          => نسأل «واش كتقصد X؟» ولا نعرض شيئاً تلقائياً.
الأسماء المكتوبة بالعربية غير مدعومة هنا (AMMPS بحروف لاتينية)؛ الـ linker يغطي كتابات الـ 20 مادة فقط."""
import re, sys, unicodedata
from collections import defaultdict
import pandas as pd
from rapidfuzz import fuzz, process
from rapidfuzz.distance import OSA
from . import config

sys.path.insert(0, str(config.ROOT / "scripts"))
from drug_linker import SUBST, normalize as ar_normalize, skeleton as ar_skeleton, strip_prefix_ar, AR_RANGE  # noqa: E402

EXTRA_SCOPE = {"ACIDE ACETYLSALICYLIQUE": ["ACETYLSALICYLATE"]}   # ملح lysine يُعدّ أسبرين (قرار سابق يحتاج تأكيد صيدلي)
TOKEN = re.compile(r"[A-Z0-9]+")

def norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s).upper()) if unicodedata.category(c) != "Mn")
    return " ".join(TOKEN.findall(s))

def _scope_rx():
    out = {}
    for sid, (names, _) in SUBST.items():
        pats = {norm(n) for n in names} | set(EXTRA_SCOPE.get(sid, []))
        out[sid] = re.compile(r"(?<![A-Z])(" + "|".join(re.escape(p) for p in pats if p) + r")")
    return out

def dose_nums(s: str) -> set[str]:
    """أرقام التركيز مع تحويل g إلى mg (1 G = 1000). مثال: '1 G' -> {'1','1000'}."""
    out = set()
    for num, unit in re.findall(r"(\d+(?:[.,]\d+)?)\s*(MG|G|ML|MCG|UI|µG)?\b", str(s).upper().replace("µ", "µ")):
        v = num.replace(",", ".")
        out.add(v.rstrip("0").rstrip(".") if "." in v else v)
        if unit == "G": out.add(str(int(round(float(v) * 1000))))
    return out

class Catalog:
    def __init__(self, df: pd.DataFrame, common_words: set[str] | None = None, ar_aliases: pd.DataFrame | None = None):
        self.df = df.reset_index(drop=True).copy()
        self.common = common_words or set()
        d = self.df
        d["brand_n"] = d["nom"].map(norm)
        d["acts"] = d["substances"].map(lambda s: [a.strip() for a in str(s).split("//") if a.strip()])
        d["acts_n"] = d["acts"].map(lambda L: sorted({k for a in L for k in {norm(a), norm(re.sub(r"\(.*?\)", "", a))} if k}))
        rx = _scope_rx()
        d["scope_ids"] = d["acts_n"].map(lambda L: [sid for sid, r in rx.items() if any(r.search(a) for a in L)])
        self.brand_idx, self.family_idx, self.act_idx = defaultdict(list), defaultdict(set), defaultdict(list)
        for i, r in d.iterrows():
            self.brand_idx[r.brand_n].append(i)
            first = r.brand_n.split(" ")[0]
            if len(first) >= 5 and first != r.brand_n: self.family_idx[first].add(r.brand_n)
            for a in r.acts_n: self.act_idx[a].append(i)
        self.fuzzy_keys = defaultdict(list)       # الحرف الأول -> مفاتيح أحادية الكلمة
        for k in set(self.brand_idx) | set(self.act_idx):
            if " " not in k and len(k) >= 6: self.fuzzy_keys[k[0]].append(k)
        self.max_n = 4
        # كتابات عربية للعلامات (arabic_brand_aliases.csv): مطابقة حرفية => تنفيذ، بالهيكل الصامت => تأكيد
        self.ar_exact, self.ar_skel = {}, defaultdict(set)   # skel -> {(alias_norm, brand)}
        if ar_aliases is not None:
            for r in ar_aliases.itertuples():
                self.ar_exact[r.alias_norm] = r.brand_key
                if len(str(r.skeleton)) >= 3: self.ar_skel[r.skeleton].add((r.alias_norm, r.brand_key))

    # ---------------------------------------------------------------- بحث في نص حر
    def find(self, text: str) -> list[dict]:
        toks = TOKEN.findall(norm(text))
        used, out = [False] * len(toks), []
        for n in range(min(self.max_n, len(toks)), 0, -1):
            for s in range(len(toks) - n + 1):
                if any(used[s:s + n]): continue
                g = " ".join(toks[s:s + n])
                if len(g) < 4: continue
                m = self._exact(g)
                if m:
                    out.append(m); 
                    for j in range(s, s + n): used[j] = True
        for s, t in enumerate(toks):                      # fuzzy للكلمات الأحادية غير المستعملة
            if used[s] or len(t) < 6 or t.lower() in self.common: continue
            cands = [k for k in self.fuzzy_keys.get(t[0], []) if abs(len(k) - len(t)) <= 2]
            maxd = 1 if len(t) <= 8 else 2             # عدد التعديلات المسموح (OSA: يشمل تبديل حرفين)
            best = process.extractOne(t, cands, scorer=OSA.distance, score_cutoff=maxd) if cands else None
            if best:
                m = self._exact(best[0]); m.update(exact=False, query=t, edits=int(best[1])); out.append(m)
        out += self._find_arabic(text, {m["key"] for m in out})
        return out

    def _find_arabic(self, text: str, have: set) -> list[dict]:
        if not self.ar_exact or not AR_RANGE.search(text): return []
        toks = [strip_prefix_ar(t) for t in ar_normalize(text).split()]
        used, res = [False] * len(toks), []
        for n in (3, 2, 1):
            for s in range(len(toks) - n + 1):
                if any(used[s:s + n]): continue
                part = toks[s:s + n]
                if not any(AR_RANGE.search(t) for t in part): continue
                g = " ".join(part)
                if len(g) < 4 or g in self.common: continue
                key, exact = self.ar_exact.get(g), True
                if key is None and n == 1 and not part[0] in self.common:
                    # تشابه بالهيكل الصامت + تقارب حروف فعلي (>=80) + طول >=5: حتى لا نسأل «واش كتقصد؟» عن كلمات عادية
                    cand = {(a, b) for a, b in self.ar_skel.get(ar_skeleton(g), ()) if len(g) >= 5 and fuzz.ratio(g, a) >= 80}
                    if len({b for _, b in cand}) == 1: key, exact = next(iter(cand))[1], False
                if key and key not in have:
                    m = self._exact(key)
                    if m:
                        m.update(exact=exact, query=g, via="arabic"); res.append(m); have.add(key)
                        for j in range(s, s + n): used[j] = True
        return res

    def _exact(self, key: str):
        if key in self.act_idx:
            return dict(kind="active", key=key, exact=True, rows=self.act_idx[key], query=key)
        if key in self.brand_idx:
            return dict(kind="brand", key=key, exact=True, rows=self.brand_idx[key], query=key)
        if key in self.family_idx:
            rows = [i for b in self.family_idx[key] for i in self.brand_idx[b]]
            return dict(kind="brand", key=key, exact=True, rows=rows, query=key)
        return None

    # ---------------------------------------------------------------- تقديم الصفوف
    def presentations(self, rows: list[int], limit=5, prefer_mono=True, dose_hint: str = "") -> dict:
        """dose_hint: نص السؤال؛ إن ذُكر رقم يطابق تركيز منتج (مثلاً 1000) نصفّي عليه. هذا اختيار منتج وليس نصيحة جرعة."""
        d = self.df.loc[rows]
        nums = {x for x in dose_nums(dose_hint) if len(x) >= 2}
        if nums:
            sel = d[d.dosage.map(lambda s: bool(nums & dose_nums(s)))]
            if len(sel): d = sel
        if prefer_mono and (d.n_actives == 1).any(): d = d[d.n_actives == 1]
        d = d.drop_duplicates(["nom", "dosage", "presentation"])
        avail = d[d.commercialise & d.ppv_dh.notna()].sort_values("ppv_dh")
        items = [dict(nom=r.nom, dosage=r.dosage, presentation=r.presentation, ppv_dh=float(r.ppv_dh),
                      ph_dh=None if pd.isna(r.ph_dh) else float(r.ph_dh)) for r in avail.head(limit).itertuples()]
        return dict(items=items, n_total=len(d), n_available=len(avail), n_not_marketed=int((~d.commercialise).sum()),
                    actives=sorted({a for L in d.acts for a in L})[:6])

    def brand_rows_for_span(self, sid: str, span: str) -> tuple[str, list[int]] | None:
        """علامة تجارية للمادة sid تطابق ما كتبه المستخدم بالهيكل الصامت (dolyprane/Doliprane/دوليبران -> DOLIPRANE).
        آمن لأن المادة محددة مسبقاً من الـ linker: نختار فقط علامة ضمن نفس المادة."""
        sk = ar_skeleton(span)
        if len(sk) < 4: return None
        if not hasattr(self, "_sk_brand"):
            self._sk_brand = defaultdict(set)
            for k in list(self.brand_idx) + list(self.family_idx): self._sk_brand[ar_skeleton(k)].add(k)
        for k in sorted(self._sk_brand.get(sk, ())):
            rows = self.brand_idx.get(k) or [i for b in self.family_idx.get(k, ()) for i in self.brand_idx[b]]
            rows = [i for i in rows if sid in self.df.scope_ids[i]]
            if rows: return k, rows
        return None

    def rows_for_substance(self, sid: str) -> list[int]:
        return [i for i, ids in self.df.scope_ids.items() if sid in ids]

    def in_scope(self, rows: list[int]) -> bool:
        return any(self.df.scope_ids[i] for i in rows)

    def display(self, m: dict) -> str:
        if m["kind"] == "brand":
            return self.df.nom[m["rows"][0]] if len(m["rows"]) == 1 or m["key"] in self.brand_idx else m["key"]
        return m["key"].title()
