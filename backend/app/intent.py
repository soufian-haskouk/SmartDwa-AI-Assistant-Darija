"""مصنّف النية (Intent Classifier): نموذج ML مدرَّب (TF-IDF حروف+كلمات + Logistic Regression) مع fallback لقواعد خبير.

سياسة الاستعمال (neuro-symbolic):
  - النموذج يقرر "ماذا يريد المستخدم" (price / interaction / ...)؛ الحقائق تبقى من AMMPS/RCP لا من النموذج.
  - ثقة < العتبة  -> نستعمل القواعد (rule_intent) بدل النموذج.
  - الطوارئ: النموذج OR قواعد الـ guards (نفضّل recall على precision لأن الخطأ المفقود أخطر).
"""
import json, logging, os, re
from pathlib import Path

from . import config, guards
from .intent_text import norm_text

log = logging.getLogger("smartdwa.intent")
LABELS = ["price", "interaction", "contraindication", "dosage", "side_effects", "alternative", "drug_info", "emergency", "out_of_scope"]
MODEL_DIR = Path(os.getenv("MODEL_DIR", config.DATA_DIR / "models"))

# ------------------------------------------------------------------ قواعد الخبير (baseline + fallback)
_R = {
    "price": r"ثمن|تمن|taman|prix|tarif|ppv|cout|coute|combien|chhal|ch7al|شحال|بشحال|كيسوا|kaysswa|kaytsewa|kaysa|how much|price|cost|غالي|رخيص|expensive|cheap|سعر|اسعار|الاسعار",
    "interaction": r"مع|m3a|avec|together|ensemble|mix|melang|خلط|نخلط|تفاعل|interaction|associer|combine|combiner|ونجمع|نجمع|كحول|alcool|alcohol|\bet\b.*\bet\b",
    "contraindication": r"حامل|حمل|grossesse|enceinte|pregnan|allait|مرضع|breastfeed|contre.?indi|contraindic|موانع|ممنوع|mamnou3|ربو|asthm|كلي|kidney|renal|rénal|لكبد|foie",
    "dosage": r"جرعه|dose|posolog|9add?ach|قداش|كم حبه|combien de comprim|how many|how often|كل شحال|chhal (men|mn|ndir|nakhod|ناخد)|شحال (من|ناخد|ندير|نشرب|نتناول)|maximum|ملغ|\bmg\b",
    "side_effects": r"اعراض|عرض جانبي|اثار جانبيه|effets?\s+(secondaire|ind)|side effect|a3rad|مضاعفات|adverse|nausee|somnolence|دوخه|نعاس|غثيان|ils?\s+provoque|kaydir lia|يسبب|كيسبب|kaysbb",
    "alternative": r"بديل|bdil|alternativ|generique|générique|remplacant|remplaçant|substitut|equivalent|instead|cheaper|نعوض|بلاصه|blast|رخص|rkhis|اخر بحال|مقطوع",
    "drug_info": r"شنو هو|chno howa|ach howa|c.?est quoi|what is|à quoi sert|a quoi sert|sert a|علاش كيتستعمل|علاش|ach kaydir|principe actif|active ingredient|الماده الفعاله|يعالج|used for|كيفاش كيخدم|how does",
}
_R = {k: re.compile(v) for k, v in _R.items()}
_PRIORITY = ["dosage", "side_effects", "alternative", "contraindication", "price", "interaction", "drug_info"]


def rule_intent(text: str, has_drug: bool = True) -> tuple[str, float]:
    """قواعد خبير: guards للطوارئ والجرعة (كما في النظام الأصلي) ثم كلمات مفتاحية؛ بلا نتيجة -> drug_info إن وُجد دواء وإلا out_of_scope."""
    if guards.is_emergency(text): return "emergency", 1.0
    t = norm_text(text)
    if guards.asks_dose(text): return "dosage", 1.0
    for k in _PRIORITY:
        if _R[k].search(t): return k, 0.5
    return ("drug_info" if has_drug else "out_of_scope"), 0.3


# ------------------------------------------------------------------ النموذج
class IntentClassifier:
    def __init__(self, path: Path | None = None):
        self.pipe, self.meta, self.error = None, {}, None
        path = path or (MODEL_DIR / "intent.joblib")
        try:
            import joblib, sklearn
            self.meta = json.loads((path.with_suffix(".json")).read_text(encoding="utf-8"))
            if self.meta.get("sklearn") != sklearn.__version__:
                self.error = f"sklearn version mismatch (trained {self.meta.get('sklearn')} vs {sklearn.__version__}); retrain: docker compose run --rm ml-train"
                log.warning(self.error); return
            self.pipe = joblib.load(path)
        except FileNotFoundError:
            self.error = "model file not found (rules fallback only)"
        except Exception as e:                       # نموذج تالف/غير متوافق: لا نكسر الخدمة
            self.error = f"{type(e).__name__}: {e}"; log.warning("intent model not loaded: %s", self.error)

    @property
    def ready(self): return self.pipe is not None
    @property
    def threshold(self): return float(self.meta.get("threshold", 0.55))

    def predict(self, text: str, has_drug: bool = True) -> dict:
        rl, rc = rule_intent(text, has_drug)
        out = dict(label=rl, confidence=rc, source="rules", rules_label=rl, top=[], model_label=None)
        if guards.is_emergency(text):                # الطوارئ: القواعد تغلب دائماً
            out.update(label="emergency", confidence=1.0, source="rules"); return out
        if not self.ready: return out
        p = self.pipe.predict_proba([text])[0]
        order = p.argsort()[::-1]
        cls = list(self.pipe.classes_)
        top = [(cls[i], round(float(p[i]), 3)) for i in order[:3]]
        out.update(top=top, model_label=top[0][0])
        if top[0][1] >= self.threshold:
            out.update(label=top[0][0], confidence=top[0][1], source="model")
        # الطوارئ: إن اقترح النموذج emergency بثقة معتدلة (>=0.35) نقبل (تفضيل recall)
        elif dict(top).get("emergency", 0) >= 0.35:
            out.update(label="emergency", confidence=dict(top)["emergency"], source="model")
        return out
