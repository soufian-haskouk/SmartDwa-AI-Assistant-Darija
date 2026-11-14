"""تدريب وتقييم مصنّف النية: baseline قواعد vs LogReg vs LinearSVC vs شبكة عصبية (MLP) على TF-IDF حروف+كلمات.
الاختيار على val (قوالب لم تُرَ)، والاختبار النهائي على gold المكتوب يدوياً مرة واحدة. يكتب النموذج والتقرير.

Usage: python ml/train_intent.py --medqa path/to/MedQA_MA.csv
"""
import argparse, json, random, sys, time
from pathlib import Path
import numpy as np, pandas as pd, joblib, sklearn
from scipy.sparse import hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "ml")]
from app.intent_text import norm_text          # noqa: E402
from app.intent import rule_intent, LABELS     # noqa: E402
import intent_data as D                         # noqa: E402


def feats():
    return FeatureUnion([
        ("w", TfidfVectorizer(preprocessor=norm_text, analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("c", TfidfVectorizer(preprocessor=norm_text, analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, max_features=150000)),
    ])


def models():
    return {
        "LogReg": Pipeline([("f", feats()), ("m", LogisticRegression(C=12, max_iter=2000, class_weight="balanced"))]),
        "LinearSVC (calibrated)": Pipeline([("f", feats()), ("m", CalibratedClassifierCV(LinearSVC(C=0.7, class_weight="balanced"), cv=3))]),
        "MLP (1 hidden layer, 128)": Pipeline([("f", feats()), ("m", MLPClassifier((128,), early_stopping=True, max_iter=60, random_state=0))]),
    }


def metrics(y, p):
    return dict(acc=accuracy_score(y, p), macro_f1=f1_score(y, p, average="macro", labels=LABELS, zero_division=0))


def noisy(texts, seed=3):
    rng = random.Random(seed); out = []
    for t in texts:
        out.append(D.noise(D.noise(t, rng), rng))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--medqa", required=True); ap.add_argument("--out", default=str(ROOT / "data/models"))
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    df, gold = D.build(a.medqa), D.load_gold()
    df = df[~df.text.isin(set(gold.text))]                     # صفر تسرب بين التدريب والاختبار
    tr, va = df[df.split == "train"], df[df.split == "val"]
    R = {}; fitted = {}
    # --- baseline قواعد
    for name, d in (("val", va), ("gold", gold)):
        R.setdefault("Rules (expert)", {})[name] = metrics(d.label, [rule_intent(t)[0] for t in d.text])
    for name, m in models().items():
        t0 = time.time(); m.fit(tr.text, tr.label); fitted[name] = m
        R[name] = {"val": metrics(va.label, m.predict(va.text)), "gold": metrics(gold.label, m.predict(gold.text)),
                   "gold_noisy": metrics(gold.label, m.predict(noisy(gold.text))), "train_s": round(time.time() - t0, 1)}
    R["Rules (expert)"]["gold_noisy"] = metrics(gold.label, [rule_intent(t)[0] for t in noisy(gold.text)])

    best = fitted["LogReg"]                                     # الخدمة تحتاج احتمالات معايَرة بسهولة؛ LR مفسَّر وخفيف
    P = best.predict_proba(gold.text); cls = list(best.classes_)
    pred = np.array(cls)[P.argmax(1)]; conf = P.max(1)
    rep = classification_report(gold.label, pred, labels=LABELS, zero_division=0, digits=3)
    cm = pd.DataFrame(confusion_matrix(gold.label, pred, labels=LABELS), index=LABELS, columns=LABELS)
    # منحنى العتبة (قيم تُقاس على gold؛ العتبة المعتمدة 0.55 محافظة وليست مضبوطة بدقة)
    thr = []
    for t in (0.3, 0.45, 0.55, 0.65, 0.8):
        m = conf >= t; thr.append((t, m.mean(), accuracy_score(gold.label[m], pred[m]) if m.any() else float("nan")))
    em = gold.label.eq("emergency").values
    emerg_recall_model = float((pred[em] == "emergency").mean())
    from app.intent import IntentClassifier
    joblib.dump(best, out / "intent.joblib", compress=3)
    json.dump(dict(sklearn=sklearn.__version__, labels=LABELS, threshold=0.55, n_train=int(len(tr)), n_val=int(len(va)), n_gold=int(len(gold)),
                   gold_macro_f1=R["LogReg"]["gold"]["macro_f1"], model="tfidf(word1-2+char_wb2-5)+LogReg"),
              open(out / "intent.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    clf = IntentClassifier(out / "intent.joblib")
    full = [clf.predict(t) for t in gold.text]                  # النظام الكامل: نموذج + عتبة + fallback قواعد + OR طوارئ
    pf = [x["label"] for x in full]; R["System (model+threshold+rules fallback)"] = {"gold": metrics(gold.label, pf)}
    sys_em = float(np.mean([p == "emergency" for p, e in zip(pf, em) if e]))
    errs = gold.assign(pred=pred, conf=conf.round(2))[pred != gold.label.values]

    L = ["# تقرير مصنّف النية — SmartDwa", "", f"- التدريب: **{len(tr)}** جملة (قوالب اصطناعية + {int((tr.source=='medqa').sum())} سؤالاً طبياً عاماً من MedQA_MA كفئة out_of_scope)",
         f"- التحقق val: **{len(va)}** (قوالب محجوزة لم يرها النموذج) — اختيار النموذج يتم هنا فقط",
         f"- الاختبار gold: **{len(gold)}** جملة مكتوبة يدوياً (ملف `ml/gold_intent.psv`)، صفر تداخل مع التدريب/val. ⚠️ الوسوم وضعها الذكاء الاصطناعي (`label_ai`) وتحتاج مراجعة بشرية قبل الاعتماد الأكاديمي.", "",
         "## 1) مقارنة النماذج (Macro-F1 / Accuracy)", "", "| النموذج | val F1 | gold F1 | gold Acc | gold مع ضجيج إضافي F1 |", "|---|---|---|---|---|"]
    for n, r in R.items():
        L.append(f"| {n} | {r.get('val',{}).get('macro_f1',float('nan')):.3f} | {r['gold']['macro_f1']:.3f} | {r['gold']['acc']:.3f} | {r.get('gold_noisy',{}).get('macro_f1',float('nan')):.3f} |")
    L += ["", "> قراءة (مهمة): **val منخفض عمداً** لأنه يتكوّن من قوالب صياغة لم يرها النموذج (≈25 قالباً لكل فئة فقط) ⇒ يكشف أن النموذج تعلّم جزئياً صياغات القوالب. أما gold فمكتوب بيد واحدة (بأسلوب قريب من القوالب)، فرقمه **متفائل** ولا يُعتبر تقديراً للأداء مع مستخدمين حقيقيين. الحل الحقيقي: بيانات حقيقية أكثر تنوعاً + نموذج Transformer (انظر `ml/colab_finetune_intent.py`).", "",
          "## 2) النموذج المعتمد (LogReg) على gold — تفصيل لكل فئة", "", "```", rep, "```", "", "## 3) مصفوفة الالتباس (صفوف = الحقيقة، أعمدة = التنبؤ)", "", "```", cm.to_string(), "```", "",
          "## 4) الثقة والعتبة", "", "| العتبة | تغطية | دقة ضمن المغطّى |", "|---|---|---|"]
    L += [f"| {t} | {c:.2f} | {a_:.3f} |" for t, c, a_ in thr]
    L += ["", f"- العتبة المعتمدة في الخدمة 0.55 (محافظة؛ تحت العتبة تُستعمل القواعد).", f"- Recall فئة الطوارئ على gold: النموذج وحده **{emerg_recall_model:.2f}**، النظام الكامل (نموذج + قواعد guards) **{sys_em:.2f}**.", "",
          "## 5) أخطاء النموذج على gold", "", "| الجملة | الحقيقة | التنبؤ | الثقة |", "|---|---|---|---|"]
    L += [f"| {r.text} | {r.label} | {r.pred} | {r.conf} |" for r in errs.itertuples()]
    L += ["", "## 6) حدود صريحة", "- بيانات التدريب اصطناعية في معظمها؛ لا تعكس بالضرورة كلام الصيادلة والزبائن الحقيقي. الحل: جمع أسئلة حقيقية (log التطبيق بعد موافقة) وإعادة التدريب.",
          "- gold صغير (176) ⇒ هامش خطأ كبير (±5–7 نقاط)، ومكتوب بأسلوب كاتب واحد.", "- فئة out_of_scope تعتمد على MedQA (أسئلة طبية عامة) + محادثة عادية؛ قد تخطئ في أسئلة صيدلانية غير مألوفة.",
          "- baseline القواعد كُتب بعد الاطلاع على أسلوب gold (دون ضبط تكراري عليه) ⇒ قد يكون متفائلاً قليلاً لصالح القواعد.", "- النموذج يصنّف النية فقط؛ الحقائق (أسعار/تداخلات/موانع) تأتي من AMMPS وRCP وليس منه."]
    (ROOT / "eval").mkdir(exist_ok=True); (ROOT / "eval/intent_eval_report.md").write_text("\n".join(L), encoding="utf-8")
    gold.assign(pred=pred, conf=conf.round(3)).to_csv(ROOT / "eval/intent_gold_predictions.csv", index=False, encoding="utf-8-sig")
    print(json.dumps({k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.get("gold", {}).items()} for k, v in R.items()}, ensure_ascii=False, indent=1))
    print("emergency recall model/system:", emerg_recall_model, sys_em)


if __name__ == "__main__":
    main()
