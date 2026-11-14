"""Build the list of frequent tokens in patient-language questions (MedQA_MA 'Question' column).
These tokens are never matched approximately against drug names (exact alias matches are still allowed)."""
import sys, collections, re
import pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from drug_linker import normalize, strip_prefix_ar

def main(medqa_csv, out_txt, min_count=20):
    q = pd.read_csv(medqa_csv, on_bad_lines="skip")
    cnt = collections.Counter()
    for t in q["Question"].astype(str):
        for tok in set(normalize(t).split()):
            cnt[tok] += 1; cnt[strip_prefix_ar(tok)] += 1
    words = sorted(w for w, c in cnt.items() if c >= min_count and len(w) >= 3)
    open(out_txt, "w", encoding="utf-8").write("\n".join(words))
    print(f"{len(words)} common tokens (min_count={min_count}) -> {out_txt}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20)
