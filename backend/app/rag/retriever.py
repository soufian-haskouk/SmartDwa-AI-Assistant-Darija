"""استرجاع هجين داخل مادة (أو مواد) محددة: BM25 + TF-IDF بالحروف (n-grams) + (اختياري) embeddings، مدمجة بـ RRF."""
import json, re
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from . import lexicon

TOKEN = re.compile(r"[a-z0-9؀-ۿ]+")
STOP = set("de la le les des du un une et ou en au aux pour par sur dans avec a l d que qui est sont ce ces se sa son ses ne pas plus".split())

def tok(s: str) -> list[str]:
    return [t for t in TOKEN.findall(lexicon.normalize(s)) if len(t) > 1 and t not in STOP]

class Retriever:
    def __init__(self, index_dir: Path, dense_embedder=None):
        self.chunks = [json.loads(l) for l in open(index_dir / "chunks.jsonl", encoding="utf-8")]
        docs = [f"{c['substance_id']} {c['text']}" for c in self.chunks]
        self.bm25 = BM25Okapi([tok(d) for d in docs])
        self.tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, preprocessor=lexicon.normalize)
        self.X = self.tfidf.fit_transform(docs)
        self.dense, self.emb = dense_embedder, None
        if (index_dir / "embeddings.npy").exists() and dense_embedder is not None:
            self.emb = np.load(index_dir / "embeddings.npy")
        self.by_sid = {}
        for i, c in enumerate(self.chunks): self.by_sid.setdefault(c["substance_id"], []).append(i)

    # ---- مكونات الترتيب
    def _rank(self, scores: np.ndarray, cand: list[int]) -> dict[int, int]:
        order = sorted(cand, key=lambda i: -scores[i])
        return {i: r for r, i in enumerate(order)}

    def search(self, query: str, substance_ids: list[str] | None = None, k: int = 3, mode: str = "hybrid",
               boost_terms: str = "", prior: dict | None = None, sections: tuple | None = None) -> list[dict]:
        cand = [i for sid in (substance_ids or self.by_sid) for i in self.by_sid.get(sid, [])]
        if sections: cand = [i for i in cand if self.chunks[i]["section"] in sections]
        if not cand: return []
        q = " ".join([query, lexicon.expand(query), boost_terms]).strip()
        ranks = {}
        if mode in ("hybrid", "bm25"):
            ranks["bm25"] = self._rank(np.asarray(self.bm25.get_scores(tok(q))), cand)
        if mode in ("hybrid", "tfidf"):
            sim = (self.X @ self.tfidf.transform([q]).T).toarray().ravel()
            ranks["tfidf"] = self._rank(sim, cand)
        if mode in ("hybrid", "dense") and self.emb is not None and self.dense is not None:
            qv = self.dense.encode_query(q); ranks["dense"] = self._rank(self.emb @ qv, cand)
        if not ranks: return []
        fused = {i: sum(1.0 / (60 + r[i]) for r in ranks.values()) for i in cand}
        if prior:
            for i in fused: fused[i] *= prior.get(self.chunks[i]["section"], 1.0)
        top = sorted(fused, key=lambda i: -fused[i])[:k]
        return [dict(self.chunks[i], score=round(fused[i], 5)) for i in top]
