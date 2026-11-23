"""
eval_rag.py - يقيس Recall@k للاسترجاع داخل مادة السؤال (نفترض أن الـ linker حدد المادة صحيحاً).
Hit = أحد أعلى k chunks هو من القسم المتوقع ونصّه يطابق gold_regex.
يقارن: عشوائي، BM25، TF-IDF حروف، هجين، هجين بلا قاموس (ablation)، هجين + ترجيح القسم. (+ dense إن وُجد --dense)
Usage: python scripts/eval_rag.py [--dense]
"""
import argparse, csv, random, re, sys, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.rag import lexicon  # noqa: E402
from app.rag.retriever import Retriever  # noqa: E402

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dense", action="store_true"); a = ap.parse_args()
    dense = None
    if a.dense:
        from app.rag.embedders import E5Embedder; dense = E5Embedder()
    R = Retriever(ROOT / "data" / "rag", dense)
    Q = list(csv.DictReader(open(ROOT / "eval" / "rag_questions.csv", encoding="utf-8")))
    def is_gold(c, q): return c["section"] == q["section"] and re.search(q["gold_regex"], lexicon.normalize(c["text"]))
    KS = (1, 3, 5)
    def run(name, fn):
        res = {k: [] for k in KS}; bylang = {}
        for q in Q:
            hits = fn(q, max(KS))
            for k in KS: res[k].append(any(is_gold(c, q) for c in hits[:k]))
            bylang.setdefault(q["lang"], []).append(any(is_gold(c, q) for c in hits[:3]))
        return name, {k: sum(v) / len(v) for k, v in res.items()}, {l: sum(v) / len(v) for l, v in bylang.items()}
    rnd = random.Random(0)
    def f_random(q, k):  # متوسط 200 تجربة
        pool = [c for c in R.chunks if c["substance_id"] == q["substance_id"]]; return rnd.sample(pool, min(k, len(pool)))
    def mk(mode, lex=True, prior=False):
        def f(q, k):
            text = q["question"]
            r = R
            if not lex:
                orig = lexicon.expand; lexicon.expand = lambda t: ""
            try:
                return r.search(text, [q["substance_id"]], k=k, mode=mode, prior=lexicon.section_prior(text, False) if prior else None)
            finally:
                if not lex: lexicon.expand = orig
        return f
    rows = []
    # العشوائي: متوسط 100 تجربة
    acc = {k: [] for k in KS}; lg = {}
    for _ in range(100):
        n, r, l = run("random", f_random)
        for k in KS: acc[k].append(r[k])
    rows.append(("عشوائي داخل المادة", {k: statistics.mean(v) for k, v in acc.items()}, None))
    for label, fn in [("BM25", mk("bm25")), ("TF-IDF حروف", mk("tfidf")), ("هجين (BM25+TF-IDF)", mk("hybrid")),
                      ("هجين بلا قاموس", mk("hybrid", lex=False)), ("هجين + ترجيح القسم", mk("hybrid", prior=True))] + \
                     ([("dense e5", mk("dense")), ("هجين + dense + ترجيح", mk("hybrid", prior=True))] if a.dense else []):
        _, r, l = run(label, fn); rows.append((label, r, l))
    n_chunks = {q["substance_id"]: sum(1 for c in R.chunks if c["substance_id"] == q["substance_id"]) for q in Q}
    out = ["# RAG retrieval evaluation", "", f"- أسئلة: {len(Q)} (كتبها الذكاء الاصطناعي؛ gold = مقطع من القسم المتوقع يطابق regex)",
           f"- chunks: {len(R.chunks)} | متوسط chunks لكل مادة: {statistics.mean(n_chunks.values()):.1f}",
           "- البحث داخل مادة السؤال (يُفترض أن الـ linker صحيح)", "",
           "| الطريقة | Recall@1 | Recall@3 | Recall@5 |", "|---|---|---|---|"]
    for label, r, _ in rows: out.append(f"| {label} | {r[1]:.0%} | {r[3]:.0%} | {r[5]:.0%} |")
    out += ["", "## Recall@3 حسب لغة السؤال", "", "| الطريقة | " + " | ".join(sorted({q['lang'] for q in Q})) + " |", "|---|" + "---|" * len({q['lang'] for q in Q})]
    for label, _, l in rows:
        if l: out.append(f"| {label} | " + " | ".join(f"{l[x]:.0%}" for x in sorted(l)) + " |")
    # الفاشلون في أفضل نظام
    best = mk("hybrid", prior=True); fails = []
    for q in Q:
        if not any(is_gold(c, q) for c in best(q, 3)): fails.append(f"- #{q['id']} [{q['lang']}] {q['question']}  (gold: {q['gold_regex']}, §{q['section']})")
    out += ["", f"## أسئلة فشلت في «هجين + ترجيح» عند k=3 ({len(fails)})", ""] + fails
    out += ["", "⚠️ الأسئلة والقاموس كلاهما من كتابة الذكاء الاصطناعي، فالنتائج تفاؤلية. أضف أسئلة حقيقية كتبها مستخدمون قبل اعتماد الأرقام."]
    (ROOT / "eval" / "rag_eval_report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))

if __name__ == "__main__":
    main()
