# Phase 3 - drug name linking (alias table + matcher)

Files
- scripts/drug_linker.py        build alias table + `DrugLinker` (normalise, consonant skeleton, edit distance, n-gram scan)
- scripts/build_common_words.py frequent tokens of patient language (blocked from approximate matching)
- scripts/eval_linker.py        evaluation -> eval/linker_eval_report.md, eval/linker_test_cases.csv
- data/processed/alias_table.csv, common_words.txt

Rebuild
    python scripts/build_common_words.py <MedQA_MA.csv> data/processed/common_words.txt 100
    python scripts/drug_linker.py build --master data/processed/drug_master.csv --egypt <egyptian.csv> --cnops <cnops.xlsx> --out data/processed/alias_table.csv
    python scripts/eval_linker.py --medqa <MedQA_MA.csv>
Use
    from drug_linker import DrugLinker
    L = DrugLinker("data/processed/alias_table.csv", common_words_file="data/processed/common_words.txt")
    L.find_drugs("واش نقدر ناخد الدوليبران مع الأوجمنتين؟")
Each hit: substance_id, score, confidence (high/medium/low), ambiguous, out_of_scope, alternatives.

Dialogue rule for Phase 8: act only on confidence high/medium AND not ambiguous AND not out_of_scope;
otherwise ask "did you mean X?"; out_of_scope -> "this drug is not in my knowledge base, ask a pharmacist".

Known limits
- Arabic DCI spellings in alias_table are seeds written by the assistant (source=manual-seed-REVIEW): review them.
- Egyptian brand names are country-specific: uncorroborated ones are always low confidence.
- CNOPS list is from 2014; brand names introduced since are unknown to the linker.
- Test cases were written by an AI, not by a native speaker; add real messages.
