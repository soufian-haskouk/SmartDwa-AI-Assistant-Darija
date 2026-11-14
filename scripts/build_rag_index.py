"""
build_rag_index.py - يبني data/rag/chunks.jsonl من rcp_sections (+ embeddings.npy اختيارياً).
Usage:
  python scripts/build_rag_index.py                 # chunks فقط (BM25 + TF-IDF يُبنيان عند تشغيل الـ backend)
  python scripts/build_rag_index.py --embedder e5   # + embeddings (يحتاج sentence-transformers وإنترنت)
"""
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.rag.chunking import build_all  # noqa: E402

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--embedder", choices=["none", "e5"], default="none"); a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("ers", ROOT / "scripts" / "extract_rcp_sections.py")
    ers = importlib.util.module_from_spec(spec); spec.loader.exec_module(ers)
    P = ROOT / "data" / "processed"; OUT = ROOT / "data" / "rag"; OUT.mkdir(parents=True, exist_ok=True)
    chunks = build_all(P / "rcp_sections", P / "rcp_extraction_report.csv", ers.FILES)
    with open(OUT / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks: f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(chunks)} chunks -> {OUT/'chunks.jsonl'}")
    if a.embedder == "e5":
        import numpy as np
        from app.rag.embedders import E5Embedder
        emb = E5Embedder().encode_docs([f"{c['substance_id']} {c['text']}" for c in chunks])
        np.save(OUT / "embeddings.npy", np.asarray(emb, dtype="float32")); print("embeddings saved", emb.shape)

if __name__ == "__main__":
    main()
