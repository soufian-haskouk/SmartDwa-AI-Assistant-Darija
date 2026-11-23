"""Données du classifieur d'intention v5 : v4 + gabarits ciblés (faiblesses vues sur test_free v4) + test_free réinjecté en train (free_dev) + NOUVEAU test_fresh.

Ce qui change vs v4 :
  - V5_EXTRA : gabarits ciblés sur les confusions observées (out_of_scope↔symptoms_query/price/drug_info, « شحال » prix vs dosage,
    urgences manquées : douleur thoracique arabizi, convulsions, étouffement, inconscience, ingestion accidentelle).
  - test_free (v4, 407 phrases) devient du DÉVELOPPEMENT : phrases + variantes bruitées en train (split « train », source « free_dev »).
  - test_fresh (ml/test_v5_intent.psv, ~300 phrases) : écrit APRÈS v4, jamais vu à l'entraînement ni pour étendre le lexique RED avant mesure.
⚠️ Honnêteté : tout reste écrit par l'IA. Seules de vraies questions (real_questions.csv → split test_real) donnent un chiffre indépendant.
"""
import random, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))
import intent_data as D1
import intent_v2_data as V2
import intent_v4_data as V4

LABELS = V2.LABELS
# --- lexique RED v5 = RED v4 + motifs ajoutés APRÈS la mesure sur test_fresh (couverture mesurée AVANT : 16/30 urgences ; voir RED_COVERAGE_FRESH_BEFORE).
# ⚠️ Conséquence : la couverture sur test_fresh n'est plus une mesure honnête après cet ajout (circulaire) ; seule la couverture AVANT compte.
RED_COVERAGE_FRESH_BEFORE = "16/30"
RED5_EXTRA = [
    r"ضيق\s*(ف|في)?\s*(ال)?(نفس|صدر|تنفس)", r"(ألم|وجع|الم)\s*\S{0,8}\s*(ف|في)?(ال)?صدر", r"ضغط\s*(ف|في)?(ال)?صدر", r"معرفتش نتنفس|ما قادرش نهضر",
    r"نأذي راسي|نؤذي راسي|نأذي نفسي", r"ما بقات كتعطيني جواب",
    r"ma (bqatch|b9atch|bqat) kat?3tini|mghmd|tghtat|tkhnak|tkhnk|ytnfs|kaytqay", r"f sder|wja3 f sder|sder w", r"ndkhel nafas|ma9drach (nd?khel|nteneffes)|lwn dyali tbddl",
    r"(khda|khdit|khdat|shrb|chrb)\b.{0,30}(b ?ghalat|kamel|toute)", r"nsali m3a nafsi|nsali 7yati",
    r"étouff", r"blood everywhere|won'?t stop|not breathing|isn'?t breathing|stopped breathing|crushing",
]
_RED_V4_FIXED = re.compile(V4.RED.pattern.replace("كنزيف|نزيف", "كنزيف|نزيف(?!\\s*(ديال|د|من)?\\s*(ال)?[اأ]نف)"), re.I)
RED = re.compile(_RED_V4_FIXED.pattern + "|" + "|".join(RED5_EXTRA), re.I)


def policy_violations(df):
    m = df.text.map(lambda t: bool(RED.search(str(t))))
    return df[m & (df.label != "emergency")]


def emergency_without_trigger(df):
    m = df.text.map(lambda t: bool(RED.search(str(t))))
    return df[(~m) & (df.label == "emergency")]

V5_EXTRA = {
"price": """شحال ثمن {d}|شحال كيسوا {d}|شحال ثمنو {d}|شحال كيتباع {d}|chhal taman {d}|ch7al ssi3r dial {d}|b9addach kayji {d}|b ch7al {d}|ch7al kaysswa {d}|taman {d} ?|{d} tarif|{d} prix ?|le prix du {d} SVP|combien je dois payer pour {d}|how much does a box of {d} cost|cost of {d} in Morocco|{d} price please|واش {d} ثمنو غالي|wach {d} ghali|بشحال {d}|ثمن {d} شحال دابا|{d} b ch7al""",
"dosage": """شحال من حبة ناخد من {d} فالنهار|كل شحال ساعة نشرب {d}|شحال نعطي ل بنتي من {d}|chhal men 7ba dial {d} nakhod|ch7al men nhar nkml {d}|fatni nakhod {d} chno ndir|wach 2 dial {d} f nafs lwa9t 3adi|combien de {d} par jour au maximum|combien de gouttes de {d}|{d} avant ou après le repas ?|how many {d} per day|how often can I take {d}|should I take {d} on an empty stomach|can I double my {d} dose|شحال من مرة فالنهار ناخد {d}|واش نقدر ناخد {d} مرتين فالنهار""",
"out_of_scope": """شحال الساعة دابا فباريس|فين نقدر نشري بيليه الطيارة|كيفاش نصاوب كلمة سر قوية|شكون هو أحسن لاعب فالعالم|شنو الطقس غدا ف {c}|بغيت وصفة ديال الحريرة|ch7al kaysswa lbenzin|kifach nbdl lmot de passe|chno a7ssan film|fin kayn a9reb stade|kifach nt3llm n9ra l'espagnol|quelle est la capitale de {c2}|comment installer WhatsApp sur mon PC|donne-moi une recette de tajine|combien coûte un loyer à {c}|quel est le meilleur laptop pour étudier|who is the president of France|write me a poem about the sea|how do I install Python|what's the best phone under 3000 dirhams|translate good morning to Arabic|merci beaucoup bye|شكرا ليك بزاف|مرحبا شنو أخبارك|واش تقدر تعاونني فالبرمجة|شكون صاوب الأنترنيت|ch7al l9ahwa f {c}|combien coûte un billet pour {c}|how much is a flight to {c}|how much is a taxi in {c}|كيفاش نشري تيليفون|wach kayn wifi hna""",
"symptoms_query": """شنو نديرو ملي كيجيني {sAR} كل صباح|كيفاش نتخلص من {sAR}|عندي {sAR} من أسبوع شنو السبب|كيفاش نعالج {mAR} بالأعشاب|واش {mAR} كتجي من التوتر|كنحس بتعب دايم شنو نديرو|شنو الأكل اللي مزيان لمرضى السكر|كيفاش نخفض الضغط بلا دوا|شنو علامات نقص الحديد|kifach n9der nnaam mzyan|3ndi {sAZ} mn jouj iyam chno ndir|chno homa a3rad {mAR}|wldi 3ndo {sAZ} chno ndir|j'ai souvent {sFR} que faire|comment calmer {sFR}|quels aliments éviter avec un reflux|comment faire baisser la fièvre d'un enfant|how to stop hiccups|why do I get {sEN} every afternoon|how can I lower my cholesterol naturally|what causes constant tiredness|is it normal to have mild {sEN} after eating|كيفاش نتفادى الإمساك|شنو أسباب الدوخة ملي كنوقف بسرعة|واش القهوة كتسبب الحموضة|كيفاش نعالج الجروح الصغيرة فالدار""",
"emergency": """عندي ألم فظيع فصدري ومعرفتش نتنفس|kan7ss b dik f sder w dra3i kayw3rni|ma9drach ndkhel nafas w lwn dyali tbddl|ولدي سقط ما بقاش كيتحرك|بنتي ما بقاتش كتعطيني جواب وعينيها مغمضين|mama tghtat b l7lib w tkhnak|wldi tghtat b chi 7aja w ma9drach ytnfs|wldi khda {dose} comprimés dial {d} b ghalat|شربت علبة كاملة ديال {d} ودابا كنحس بالنعاس القوي|جدتي خدات بزاف ديال {d} وبدا كيجيها الدم من الأنف بزاف|bba mghma 3lih w ma kayfi9ch|j'ai du mal à respirer et mon coeur bat très vite|ma fille s'est étouffée avec une cacahuète|il a pris toute la boîte de {d}|elle ne respire plus normalement|my husband has crushing chest pain|she can't breathe after the injection|he swallowed a handful of {d} tablets|my daughter fainted and isn't responding|my throat is closing|ولدي عندو حرارة بزاف وبدا كيتشنج|كنحس بتنميل فالدراع وضغط فصدري|wldi shrb dwa dial l7arara kamel w bda kaytqay|عندي ضيق ف التنفس بزاف وما قادرش نهضر|mon mari est tombé inconscient|my mother is not breathing|عندي أفكار باش نأذي راسي""",
}
# NB : les phrases ci-dessus sont des gabarits GÉNÉRIQUES ; test_fresh a été écrit à part, avec d'autres médicaments et tournures.


def frames_v5():
    out, mv = V4.frames_v4()
    for k, blob in V5_EXTRA.items():
        out[k] = list(dict.fromkeys(out[k] + V2._split(blob)))
    return out, mv


def _load_psv(path, split, source, idx):
    rows = []
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        if not l.strip() or l.startswith("#"): continue
        lab, txt = l.split("|", 1); lab = lab.strip()
        assert lab in LABELS, (lab, txt); rows.append((txt.strip(), lab, split, source, idx, source))
    return pd.DataFrame(rows, columns=["text", "label", "split", "source", "frame_idx", "frame"])


def build_v5(v4_csv, per_train=1600, per_eval=300, seed=17, split_seed=53, free_variants=4):
    rng = random.Random(seed); dp = D1.load_drug_pools(); P = V4.pools_v4()
    fr, moved = frames_v5()
    sp = V2.split_frames(fr, seed=split_seed)
    rows = []
    for split, n in (("train", per_train), ("val", per_eval), ("test", per_eval)):
        for lab in LABELS:
            fs = sp[split][lab]
            for _ in range(n):
                f = rng.choice(fs); s = V2.fill(f, rng, P, dp)
                s = re.sub(r"\s+", " ", D1.noise(rng.choice(D1.PREFIX) + s + rng.choice(D1.SUFFIX), rng)).strip()
                rows.append((s, lab, split, "template", fs.index(f), f))
    old = pd.read_csv(v4_csv, encoding="utf-8-sig")
    mq = old[old.source == "medqa"]
    medqa_dropped = int(mq.text.map(lambda t: bool(RED.search(str(t)))).sum())
    mq = mq[~mq.text.map(lambda t: bool(RED.search(str(t))))]
    for _, r in mq.iterrows(): rows.append((r.text, "symptoms_query", r.split, "medqa", -1, "medqa"))
    df = pd.DataFrame(rows, columns=["text", "label", "split", "source", "frame_idx", "frame"])
    gold = old[old.split == "test_gold"]
    free = V4.load_test_free()
    fresh = _load_psv(ROOT / "ml" / "test_v5_intent.psv", "test_fresh", "fresh_ai", -4)
    # free_dev : phrases originales + variantes bruitées -> TRAIN
    fd = []
    for _, r in free.iterrows():
        fd.append((r.text, r.label, "train", "free_dev", -3, "free_dev"))
        for _ in range(free_variants):
            s = re.sub(r"\s+", " ", D1.noise(r.text, rng)).strip()
            if s and s != r.text: fd.append((s, r.label, "train", "free_dev", -3, "free_dev"))
    fd = pd.DataFrame(fd, columns=df.columns)
    ban = set(gold.text) | set(fresh.text)
    df = df[~df.text.isin(ban)]
    prio = {"train": 0, "val": 1, "test": 2}
    df = df.assign(p=df.split.map(prio)).sort_values("p").drop_duplicates("text").drop(columns="p")
    fd = fd[~fd.text.isin(ban) & ~fd.text.isin(set(df[df.split != "train"].text))]
    out = pd.concat([df, fd, gold, fresh], ignore_index=True).drop_duplicates(["text", "split"])
    return out, dict(n_frames={k: len(v) for k, v in fr.items()}, free_dev_rows=len(fd), medqa_dropped_red_flag=medqa_dropped)
