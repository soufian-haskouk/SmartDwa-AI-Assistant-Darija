"""Fine-tuning Transformer لمصنّف النية على Google Colab (GPU مجاني). ⚠️ لم يُجرَّب في بيئة التطوير (لا يوجد torch هناك) — شغّله وراجع الأخطاء.

الخطوات في Colab:
  !pip -q install transformers datasets accelerate scikit-learn pandas
  ارفع إلى Colab: ml/intent_data.py, ml/gold_intent.psv, backend/app/intent_text.py, data/processed/ammps_clean.csv,
  data/processed/arabic_brand_aliases.csv, MedQA_MA.csv  (مع نفس بنية المجلدات: ROOT/ml, ROOT/data/processed, ...)
  !python ml/colab_finetune_intent.py --medqa MedQA_MA.csv --model SI2M-Lab/DarijaBERT   # أو xlm-roberta-base / aubmindlab/bert-base-arabertv2
ثم حمّل مجلد النتيجة وقارن macro-F1 على gold بجدول eval/intent_eval_report.md (نفس gold بدون تسرّب).
"""
import argparse, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))
import intent_data as D
from datasets import Dataset
from sklearn.metrics import classification_report, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

ap = argparse.ArgumentParser(); ap.add_argument("--medqa", required=True); ap.add_argument("--model", default="xlm-roberta-base")
ap.add_argument("--epochs", type=int, default=3); ap.add_argument("--out", default="intent_transformer"); a = ap.parse_args()
L = D.LABELS; l2i = {l: i for i, l in enumerate(L)}
df, gold = D.build(a.medqa), D.load_gold(); df = df[~df.text.isin(set(gold.text))]
tok = AutoTokenizer.from_pretrained(a.model)
def enc(d):
    ds = Dataset.from_dict({"text": d.text.tolist(), "label": [l2i[x] for x in d.label]})
    return ds.map(lambda b: tok(b["text"], truncation=True, max_length=64), batched=True)
tr, va, go = enc(df[df.split == "train"]), enc(df[df.split == "val"]), enc(gold)
model = AutoModelForSequenceClassification.from_pretrained(a.model, num_labels=len(L), id2label=dict(enumerate(L)), label2id=l2i)
metric = lambda p: {"macro_f1": f1_score(p.label_ids, p.predictions.argmax(-1), average="macro")}
args = TrainingArguments(a.out, num_train_epochs=a.epochs, per_device_train_batch_size=32, learning_rate=3e-5, eval_strategy="epoch",
                         save_strategy="no", report_to=[], fp16=True, warmup_ratio=0.1, weight_decay=0.01)
t = Trainer(model=model, args=args, train_dataset=tr, eval_dataset=va, tokenizer=tok, compute_metrics=metric); t.train()
p = t.predict(go); pred = p.predictions.argmax(-1)
print("GOLD macro-F1:", f1_score(p.label_ids, pred, average="macro"))
print(classification_report(p.label_ids, pred, target_names=L, digits=3))
t.save_model(a.out); tok.save_pretrained(a.out)
