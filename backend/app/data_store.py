"""تحميل الجداول مرة واحدة عند التشغيل (الأداء) مع إمكانية إعادة التحميل بعد تحديث البيانات."""
import pandas as pd
from . import config
from .catalog import Catalog

class DataStore:
    def __init__(self):
        self.reload()

    def reload(self):
        P = config.PROCESSED
        self.master = pd.read_csv(P / "drug_master.csv", encoding="utf-8-sig")
        self.pairs = pd.read_csv(P / "interaction_pairs.csv", encoding="utf-8-sig")
        self.pairs_idx = {r.pair: r for r in self.pairs.itertuples(index=False)}
        ammps = P / "ammps_clean.csv"
        self.ammps = pd.read_csv(ammps) if ammps.exists() else pd.DataFrame()
        cw = P / "common_words.txt"
        common = set(cw.read_text(encoding="utf-8").split()) if cw.exists() else set()
        aa = P / "arabic_brand_aliases.csv"
        ar = pd.read_csv(aa, encoding="utf-8-sig") if aa.exists() else None
        self.catalog = Catalog(self.ammps, common, ar) if len(self.ammps) else None   # فهرسة مرة واحدة في الذاكرة

    def interaction(self, a: str, b: str):
        key = " | ".join(sorted([a, b]))
        r = self.pairs_idx.get(key)
        if r is None:
            return None
        lvl = None if pd.isna(r.engine_level_max) else int(r.engine_level_max)
        return dict(pair=key, level=lvl, needs_review=bool(r.needs_review),
                    dose_dependent=bool(r.dose_dependent), sources=str(r.sources))

    def presentations(self, substance_id: str, only_available=True, limit=8):
        m = self.master[(self.master.substance_id == substance_id) & (self.master.source == "ammps")]
        if only_available:
            m = m[m.statut_commercialisation.fillna("").str.startswith("Commercialis")]
        m = m.dropna(subset=["PPV"]).sort_values("PPV")
        return [dict(nom=r.NOM, dosage=" ".join(str(r.DOSAGE1).split()), forme=str(r.FORME), ppv_dh=float(r.PPV))
                for r in m.head(limit).itertuples()]

    def display_name(self, substance_id: str) -> str:
        r = self.master[self.master.substance_id == substance_id]
        return str(r.iloc[0]["name"]) if len(r) else substance_id.title()
