"""واجهة الـ RAG للـ orchestrator.
retrieve_for(text, own_ids) -> passages (list[dict]) ؛ pair_passages(a, b) -> مقتطف من §4.5 لـ a يذكر b."""
import os
from pathlib import Path
from .. import config
from . import lexicon
from .retriever import Retriever

INDEX_DIR = Path(os.getenv("RAG_DIR", config.DATA_DIR / "rag"))
_R = None
_TERMS = None

def _terms():
    """أسماء/فئات كل مادة بالفرنسية من extract_rcp_sections.TERMS (لترجيح chunks تذكر دواءً آخر)."""
    global _TERMS
    if _TERMS is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ers", config.ROOT / "scripts" / "extract_rcp_sections.py")
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        _TERMS = {k: " ".join(t for t, _ in v) for k, v in m.TERMS.items()}
    return _TERMS

def is_ready() -> bool:
    return (INDEX_DIR / "chunks.jsonl").exists()

def get() -> Retriever:
    global _R
    if _R is None:
        dense = None
        if os.getenv("RAG_DENSE", "false").lower() == "true":
            from .embedders import E5Embedder
            dense = E5Embedder()
        _R = Retriever(INDEX_DIR, dense)
    return _R

def reset():
    global _R; _R = None

def _pack(h):
    return dict(source=h["source"], section=h["section"], category=h["category"], product=h["product"],
                substance_id=h["substance_id"], text=h["text"], score=h["score"])

def retrieve(query: str, substance_ids: list[str], k: int = 2, intent: str | None = None) -> list[dict]:
    """سؤال حول دواء واحد، أو عدة أدوية: لكل دواء A نبحث في §4.5 عن مقطع يذكر الأدوية الأخرى."""
    if not is_ready() or not substance_ids:
        return []
    R, out = get(), []
    if len(substance_ids) >= 2:
        for a in substance_ids:
            terms = [t for b in substance_ids if b != a for t in _terms().get(b, b.lower()).split(" ") if len(t) > 3]
            hits = R.search(query, [a], k=3, boost_terms=" ".join(terms), sections=("4.5",))
            # لا نعرض مقطعاً كدليل إلا إذا ذكر فعلاً الدواء الآخر (اسماً أو فئةً)؛ وإلا نتركه فارغاً بدل تضليل المستخدم
            rel = [h for h in hits if any(t in lexicon.normalize(h["text"]) for t in map(lexicon.normalize, terms))]
            out += rel[:1]
    else:
        a = substance_ids[0]
        prior = lexicon.section_prior(query, False)
        if intent == "contraindication": prior["4.3"] += 0.5          # النية المتنبَّأ بها تحدد القسم المرجَّح
        elif intent == "interaction": prior["4.5"] += 0.5
        out = R.search(query, [a], k=k, prior=prior)
    return [_pack(h) for h in out]
