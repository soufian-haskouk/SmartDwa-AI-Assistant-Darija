"""
Phase 3 evaluation of drug_linker.py  ->  eval/linker_eval_report.md  +  eval/linker_test_cases.csv

 A. Synthetic typos on real CNOPS brand names + DCI names   (robustness to spelling noise; OPTIMISTIC: same vocabulary)
 B. Hand-written realistic cases (Latin / Arabic script / Arabizi / sentences / negatives / out-of-scope drug)
    -> written by the assistant, NOT by a native speaker: the project owner must review and extend them.
 C. False-positive check on a random sample of MedQA_MA questions.

'actionable' hit = confidence high/medium AND not ambiguous AND in scope.  Anything else => the bot must ask "did you mean X?".
"""
import argparse, random, sys, os, collections
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from drug_linker import DrugLinker, normalize

CASES = [  # (id, kind, text, expected in-scope substance ids)
 ("L01","latin_brand","doliprane",["PARACETAMOL"]), ("L02","latin_brand","dolipran 1000",["PARACETAMOL"]),
 ("L03","latin_typo","dolyprane",["PARACETAMOL"]), ("L04","latin_brand","Brufen 400",["IBUPROFENE"]),
 ("L05","latin_typo","brufenn",["IBUPROFENE"]), ("L06","latin_brand","augmentin",["AMOXICILLINE"]),
 ("L07","latin_typo","agmentin",["AMOXICILLINE"]), ("L08","latin_brand","glucophage 850",["METFORMINE"]),
 ("L09","latin_typo","gloucophage",["METFORMINE"]), ("L10","latin_typo","voltaren",["DICLOFENAC"]),
 ("L11","latin_brand","cataflam",["DICLOFENAC"]), ("L12","latin_typo","ventolin",["SALBUTAMOL"]),
 ("L13","latin_typo","soluprd",["PREDNISOLONE"]), ("L14","latin_brand","zyrtec",["CETIRIZINE"]),
 ("L15","latin_brand","mopral",["OMEPRAZOLE"]), ("L16","latin_brand","zithromax",["AZITHROMYCINE"]),
 ("L17","latin_brand","aspegic",["ACIDE ACETYLSALICYLIQUE"]), ("L18","latin_typo","asprin",["ACIDE ACETYLSALICYLIQUE"]),
 ("L19","latin_brand","amlor",["AMLODIPINE"]), ("L20","latin_dci","ibuprofene",["IBUPROFENE"]),
 ("A01","arabic","دوليبران",["PARACETAMOL"]), ("A02","arabic","الدوليبران",["PARACETAMOL"]),
 ("A03","arabic","باراسيتامول",["PARACETAMOL"]), ("A04","arabic","بروفين",["IBUPROFENE"]),
 ("A05","arabic","اوجمنتين",["AMOXICILLINE"]), ("A06","arabic","الاموكسيسيلين",["AMOXICILLINE"]),
 ("A07","arabic","ميتفورمين",["METFORMINE"]), ("A08","arabic","كليكوفاج",["METFORMINE"]),
 ("A09","arabic","فولتارين",["DICLOFENAC"]), ("A10","arabic","فنتولين",["SALBUTAMOL"]),
 ("A11","arabic","اسبرين",["ACIDE ACETYLSALICYLIQUE"]), ("A12","arabic","ديكلوفيناك",["DICLOFENAC"]),
 ("A13","arabic","اوميبرازول",["OMEPRAZOLE"]), ("A14","arabic","سيتيريزين",["CETIRIZINE"]),
 ("A15","arabic","بريدنيزولون",["PREDNISOLONE"]), ("A16","arabic","فوروسيميد",["FUROSEMIDE"]),
 ("Z01","arabizi","bruffen",["IBUPROFENE"]), ("Z02","arabizi","agmentine",["AMOXICILLINE"]),
 ("Z03","arabizi","diclofinac",["DICLOFENAC"]), ("Z04","arabizi","omeprazol",["OMEPRAZOLE"]),
 ("Z05","arabizi","cetirizin",["CETIRIZINE"]), ("Z06","arabizi","metphormin",["METFORMINE"]),
 ("S01","sentence","واش نقدر ناخد الدوليبران مع الأوجمنتين؟",["PARACETAMOL","AMOXICILLINE"]),
 ("S02","sentence","كنت كنستعمل ventoline وولا مزيان",["SALBUTAMOL"]),
 ("S03","sentence","شنو الفرق بين البروفين والدوليبران؟",["IBUPROFENE","PARACETAMOL"]),
 ("S04","sentence","bghit n3ref wach nakhod aspirine w ibuprofen f nafs lwa9t",["ACIDE ACETYLSALICYLIQUE","IBUPROFENE"]),
 ("S05","sentence","كنت كنشرب الميتفورمين وعندي مشكل فالمعدة",["METFORMINE"]),
 ("S06","sentence","بنتي عندها السخانة و3ندي غير الباراسيتامول",["PARACETAMOL"]),
 ("S07","sentence","واش ممكن نخلط الأسبرين مع الكلاريتين؟",["ACIDE ACETYLSALICYLIQUE","LORATADINE"]),
 ("S08","sentence","doliprane ou ibuprofene pour mal de tête?",["PARACETAMOL","IBUPROFENE"]),
 ("S09","sentence","Quelle est la dose de Voltarène pour un adulte",["DICLOFENAC"]),
 ("S10","sentence","واش نقدر ناخد الباروكستين مع الدوليبران؟",["PARACETAMOL"]),   # paroxetine is out of scope
 ("N01","negative","راسي كيضرني بزاف شنو ندير؟",[]), ("N02","negative","كيفاش نتعالج من الحمى؟",[]),
 ("N03","negative","واش الدواء ديال الضغط خاصو الماء؟",[]), ("N04","negative","نسيت نخد الدوا ديالي البارح",[]),
 ("N05","negative","عندي حساسية من البنسلين",[]), ("N06","negative","j'ai mal à la gorge depuis deux jours",[]),
 ("N07","negative","فين نلقى صيدلية قريبة؟",[]), ("N08","negative","شحال ثمن الكشف عند الطبيب",[]),
 ("N09","negative","كنحس بدوخة منين كنوقف",[]), ("N10","negative","عندي الجلدة كتحكني",[]),
]

def actionable(h): return (not h["out_of_scope"]) and h["confidence"] in ("high", "medium") and not h["ambiguous"]

def typo(w, rng, n_edits):
    w = list(w)
    for _ in range(n_edits):
        if len(w) < 5: break
        op = rng.choice(["del", "swap", "dup", "vowel"]); i = rng.randrange(1, len(w) - 1)
        if op == "del": del w[i]
        elif op == "swap": w[i], w[i + 1] = w[i + 1], w[i]
        elif op == "dup": w.insert(i, w[i])
        else:
            vs = "aeiou"; j = [k for k, c in enumerate(w) if c in vs]
            if j: w[rng.choice(j)] = rng.choice(vs)
    return "".join(w)

def main(a):
    L = DrugLinker(a.alias, common_words_file=a.common)
    al = L.df
    out = ["# Drug linker evaluation (Phase 3)\n"]

    # ---------- A. synthetic typos
    rng = random.Random(42)
    src = al[(al.alias_type.isin(["brand", "dci"])) & (~al.alias.str.contains(" ")) & (al.norm.str.len() >= 6) & (al.lang != "ar")]
    rows = []
    for _, r in src.iterrows():
        gold = set(r.substance_id.split("|"))
        for ne in (0, 1, 2):
            q = typo(r.norm, rng, ne) if ne else r.norm
            res = L.link_term(q, k=3)
            pred = [x["substance_id"] for x in res if x["score"] >= L.th]
            top1 = pred[0] if pred else None
            rows.append(dict(edits=ne, top1=top1 in gold, top3=bool(gold & set(pred[:3])),
                             found=bool(pred), wrong_top1=bool(pred) and top1 not in gold))
    d = pd.DataFrame(rows).groupby("edits").mean(numeric_only=True).round(3)
    n = len(src)
    out += [f"## A. Synthetic typos ({n} CNOPS brand/DCI names, Latin, length>=6)\n",
            "| edits | Top-1 | Top-3 | found anything | wrong Top-1 |", "|---|---|---|---|---|"]
    out += [f"| {e} | {r.top1:.1%} | {r.top3:.1%} | {r.found:.1%} | {r.wrong_top1:.1%} |" for e, r in d.iterrows()]
    out += ["\nCaveat: the noisy words come from the same vocabulary the linker knows, so this is an upper bound.\n"]

    # ---------- B. hand-written cases
    known = set(al.norm)
    recs = []
    for cid, kind, text, exp in CASES:
        hits = L.find_drugs(text)
        act = sorted({h["substance_id"] for h in hits if actionable(h)})
        anyin = sorted({h["substance_id"] for h in hits if not h["out_of_scope"]})
        wrong_act = [s for s in act if s not in exp]
        recs.append(dict(id=cid, kind=kind, text=text, expected="|".join(exp), actionable="|".join(act), any_in_scope="|".join(anyin),
                         exact_actionable=set(act) == set(exp), exact_lenient=set(anyin) == set(exp),
                         wrong_actionable=len(wrong_act), needs_confirmation=any((not actionable(h)) and not h["out_of_scope"] for h in hits),
                         hits=" ; ".join(f"{h['span']}->{h['substance_id'][:12]}({h['confidence']}{',amb' if h['ambiguous'] else ''}{',OUT' if h['out_of_scope'] else ''})" for h in hits)))
    B = pd.DataFrame(recs); B.to_csv(os.path.join(a.out_dir, "linker_test_cases.csv"), index=False, encoding="utf-8-sig")
    g = B.groupby("kind").agg(n=("id", "count"), strict=("exact_actionable", "mean"), lenient=("exact_lenient", "mean"),
                              wrong_actionable=("wrong_actionable", "sum"), confirm=("needs_confirmation", "sum")).round(3)
    out += [f"## B. Hand-written cases ({len(B)})\n", "strict = only actionable hits count; lenient = low-confidence/ambiguous hits count too.\n",
            "| kind | n | strict exact | lenient exact | wrong actionable hits | needs confirmation |", "|---|---|---|---|---|---|"]
    out += [f"| {k} | {r.n} | {r.strict:.0%} | {r.lenient:.0%} | {r.wrong_actionable} | {r.confirm} |" for k, r in g.iterrows()]
    tot = B.agg({"exact_actionable": "mean", "exact_lenient": "mean", "wrong_actionable": "sum"})
    out += [f"\n**Overall:** strict {tot.exact_actionable:.0%}, lenient {tot.exact_lenient:.0%}, wrong actionable hits: {int(tot.wrong_actionable)}\n"]
    bad = B[~B.exact_lenient]
    if len(bad):
        out += ["### Cases not matched even leniently\n", "| id | text | expected | got |", "|---|---|---|---|"]
        out += [f"| {r.id} | {r.text} | {r.expected} | {r.hits} |" for r in bad.itertuples()]
    out += ["\nCaveat: these cases were written by an AI, not by a native Darija speaker. Review them and add real user messages.\n"]

    # ---------- C. false positives on MedQA_MA
    q = pd.read_csv(a.medqa, on_bad_lines="skip").sample(a.n_fp, random_state=7)
    nq = nin = nact = namb = nlow = nout = 0
    for t in q["Question"].astype(str):
        hs = L.find_drugs(t)
        nq += 1 if hs else 0
        for h in hs:
            if h["out_of_scope"]: nout += 1; continue
            nin += 1; nact += actionable(h); namb += h["ambiguous"]; nlow += (h["confidence"] == "low")
    out += [f"## C. MedQA_MA sample ({a.n_fp} patient questions)\n",
            f"- questions with any drug hit: {nq} ({nq / a.n_fp:.1%})", f"- in-scope hits: {nin} (actionable {nact}, ambiguous {namb}, low-confidence {nlow})",
            f"- out-of-scope drug hits (handled safely): {nout}",
            "",
            "**Manual review (done by the AI assistant on the seed=7 sample of 4000, so a Moroccan reader should re-check):**",
            "- all 22 *actionable* in-scope hits were genuine drug mentions;",
            "- of the 35 non-actionable (need confirmation) hits: 5 clearly false (e.g. a hair-removal 'flash', marjoram, sulpiride, glibenclamide, 'baby'), 4 undecidable, ~26 plausible real mentions (mostly Arabic spellings of brands).",
            "- Lesson: ordinary words collide with brand names by sound, so Arabic-script matches that are not exact DCI/CNOPS names must be confirmed with the user.\n"]
    open(os.path.join(a.out_dir, "linker_eval_report.md"), "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(out))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", default="data/processed/alias_table.csv"); ap.add_argument("--common", default="data/processed/common_words.txt")
    ap.add_argument("--medqa", required=True); ap.add_argument("--out-dir", default="eval"); ap.add_argument("--n-fp", type=int, default=4000)
    main(ap.parse_args())
