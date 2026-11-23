"""مولّد بيانات مصنّف النية: قوالب اصطناعية متعددة اللغات (دارجة بالعربية/اللاتينية، فرنسية، إنجليزية)
+ أسماء أدوية حقيقية من AMMPS + ضجيج إملائي + أسئلة طبية عامة من MedQA_MA كفئة out_of_scope.
القوالب مقسّمة بين train و val (val يحتوي قوالب لم يرها النموذج إطلاقاً)؛ الاختبار النهائي = gold_intent.psv مكتوب يدوياً بشكل مستقل."""
import random, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LABELS = ["price", "interaction", "contraindication", "dosage", "side_effects", "alternative", "drug_info", "emergency", "out_of_scope"]

T = {
"price": """شحال ثمن {d}|بشحال كيتباع {d}|شحال كيسوا {d}؟|ثمن {d} شحال|بغيت نعرف الثمن ديال {d}|واش {d} غالي|شحال خاصني نخلص على {d}|chhal taman {d}|chhal kaysswa {d}|b chhal {d}|taman dial {d}|ch7al {d} f pharmacie|
prix de {d}|combien coûte {d}|{d} c'est combien ?|quel est le prix du {d}|le tarif de {d}|{d} prix au Maroc|how much is {d}|price of {d}|how much does {d} cost|cost of {d} in Morocco|شحال ثمنو هاد الدوا|chhal taman had dwa|combien ça coûte ce médicament|PPV ديال {d}|الأسعار ديال {d}|بغيت ثمن {d} و {d2}|prix {d} et {d2}|هل {d} رخيص|{d} rkhis wla ghali|سعر {d}|taman {d} 3afak|شحال كتسوا العلبة ديال {d}""",
"interaction": """واش نقدر نخلط {d} مع {d2}|واش {d} و {d2} كيتخلطو|واش نشرب {d} مع {d2}|واش كاين تفاعل بين {d} و {d2}|واش نقدر ناخد {d} و {d2} فنفس الوقت|{d} + {d2} خطير؟|واش ممكن نجمع {d} و {d2}|{d} مع {d2} واش مزيان|nakhod {d} m3a {d2}?|wach n9der nkhlet {d} w {d2}|{d} w {d2} kaytkhlto?|wach kayn interaction bin {d} w {d2}|n9der nchrb {d} m3a {d2} ?|
puis-je prendre {d} avec {d2}|{d} et {d2} ensemble possible ?|interaction entre {d} et {d2}|peut-on associer {d} et {d2}|est-ce dangereux de mélanger {d} et {d2}|{d} avec {d2} c'est dangereux ?|can I take {d} with {d2}|is it safe to take {d} and {d2} together|{d} and {d2} interaction|can I mix {d} and {d2}|{d} plus {d2} ok?|واش {d} كيتعاون مع الكحول|puis-je boire de l'alcool avec {d}|can I drink alcohol with {d}|واش نشرب القهوة مع {d}|واش كاين مشكل ملي نخلط جوج دوايات|est-ce que je peux associer deux médicaments""",
"contraindication": """واش الحامل تقدر تاخد {d}|واش {d} مزيان للحامل|واش مرضعة تقدر تستعمل {d}|موانع الاستعمال ديال {d}|شكون ما يمكنش ياخد {d}|واش {d} ممنوع فالربو|واش مريض السكر يقدر ياخد {d}|واش نخدم {d} وأنا عندي مشكل فالكلى|واش {d} خطير على الكبد|{d} والحمل|{d} للأطفال واش مسموح|واش {d} ممنوع على مرضى الضغط|wach 7amila t9der takhod {d}|{d} w l7aml|wach {d} mamnou3 l rbou|moussahil {d} f l'allaitement|wach {d} yssir l diabetique|wach {d} khatir 3la lkoulya|
{d} est-il contre-indiqué pendant la grossesse|{d} et allaitement|contre-indications de {d}|puis-je prendre {d} si j'ai de l'asthme|{d} en cas d'insuffisance rénale|{d} chez la femme enceinte|qui ne doit pas prendre {d}|{d} est-il dangereux pour les reins|{d} possible avec un ulcère de l'estomac|can pregnant women take {d}|is {d} safe during pregnancy|contraindications of {d}|{d} while breastfeeding|can I take {d} if I have asthma|who should not take {d}|is {d} safe for kidney disease|{d} and high blood pressure safe ?|واش هاد الدوا خطير على الحامل|ما كيمشيش هاد الدوا مع مرضى القلب""",
"dosage": """شحال ناخد ديال {d}|قداش من حبة ناخد من {d}|شحال من مرة فاليوم نشرب {d}|كل شحال ساعة ناخد {d}|شحال الجرعة ديال {d}|قداش الجرعة القصوى ديال {d}|شحال ندير للطفل من {d}|شحال من ملعقة ديال {d}|شحال من يوم نكمل {d}|واش 2 حبات ديال {d} بزاف|9addach nakhod men {d}|chhal men 7ba dial {d}|chhal mn mra f nhar {d}|9ddach men sachet dial {d}|kol chhal sa3a nakhod {d}|chhal ndir l tfl men {d}|
posologie de {d}|quelle dose de {d}|combien de comprimés de {d} par jour|combien de fois par jour prendre {d}|{d} dose maximale par jour|dose de {d} pour un enfant de {n} kg|toutes les combien d'heures prendre {d}|pendant combien de jours prendre {d}|how many {d} can I take a day|{d} dosage for adults|how often can I take {d}|what is the maximum dose of {d}|how many mg of {d}|{d} dose for a child|how many tablets of {d} per day|واش ناخد {n}00 ملغ ديال {d}|واش {n} حبات ديال {d} فاليوم مزيان""",
"side_effects": """شنو هي الأعراض الجانبية ديال {d}|واش {d} كيسبب النعاس|واش {d} كيضر المعدة|شنو كيوقع ملي نشرب {d}|آثار جانبية ديال {d}|واش {d} كيسبب الإسهال|واش {d} كيدير الدوخة|مضاعفات {d} شنو هي|واش {d} كيعطي حساسية|chno homa l a3rad dial {d}|kaydir lia {d} l ma3da|wach {d} kay3ss|{d} kaysbb lia ta3ab|wach {d} kaydir noum|chno kaysra ila khdit {d}|
effets indésirables de {d}|effets secondaires du {d}|{d} peut-il donner des nausées|{d} provoque-t-il de la somnolence|est-ce que {d} est mauvais pour l'estomac|les risques de {d} à long terme|{d} donne des maux de tête ?|side effects of {d}|does {d} cause drowsiness|{d} adverse reactions|is it normal to feel dizzy after {d}|can {d} upset my stomach|{d} long term risks|واش عادي نحس بالغثيان من {d}|بدات كيجيني الدوخة من ملي خديت {d}""",
"alternative": """شنو البديل ديال {d}|bdil {d}|بديل رخيص لـ {d}|واش كاين دوا بحال {d} وأرخص|شنو نشري بلاصة {d}|{d} ما لقيتوش فالصيدلية شنو نبدلو بيه|واش كاين جنريك ديال {d}|نفس الدوا ديال {d} بعلامة أخرى|{d} مقطوع شنو كنعوض بيه|واش {d} و {d2} نفس الدوا|bdil rkhis dial {d}|chno nchri blast {d}|wach kayn generique dial {d}|{d} makaynch chno nbdl bih|
générique de {d}|remplaçant de {d}|alternative à {d}|y a-t-il un équivalent moins cher à {d}|{d} en rupture quoi prendre à la place|médicament équivalent à {d}|même principe actif que {d}|cheaper alternative to {d}|generic version of {d}|substitute for {d}|what can I take instead of {d}|another brand of {d}|is {d2} the same as {d}|{d} is out of stock any alternative""",
"drug_info": """شنو هو {d}|علاش كيتستعمل {d}|{d} فاش كيفيد|واش {d} كيعالج {m}|شنو هي المادة الفعالة ديال {d}|{d} من أي عائلة دوا|كيفاش كيخدم {d}|{d} كيتاخد بالفم ولا بالحقن|شنو كيدير {d}|ach howa {d}|{d} 3lach kaytsta3ml|ach kaydir {d}|chno hiya lmadda l fa3ala dyal {d}|kifach kaykhdem {d}|
c'est quoi {d}|à quoi sert {d}|{d} sert à quoi|quel est le principe actif de {d}|{d} est un antibiotique ?|pour quelle maladie prend-on {d}|forme et présentation de {d}|dans quelle famille est {d}|what is {d} used for|what is {d}|what does {d} do|is {d} an antibiotic|active ingredient of {d}|how does {d} work|what class of drug is {d}""",
"emergency": """شربت بزاف ديال {d} بلا ما نقصد|{d} ولدي بلعو كامل|ولدي بلع علبة ديال {d}|كنحس بضيق فالنفس من ملي خديت {d}|وجهي تنفخ من ملي خديت {d}|تسمم بـ {d} شنو ندير|جرعة زايدة ديال {d}|مات ليا الجسم من بعد {d}|بغيت نموت|بغيت ننهي حياتي|ما بقيتش قادر نتنفس|غمات عليا من بعد {d}|لساني تنفخ بعد {d}|نبزق الدم من ملي خديت {d}|wldi bela3 {d} kamel|khdit bzaf dial {d} w ana mkhlou3|ma 9drach nteneffess men b3d {d}|bghit nmout|sm3ni rassi ghadi nghma bs7 khdit {d}|
j'ai avalé trop de {d}|mon enfant a avalé {d}|surdosage de {d} que faire|overdose de {d}|j'ai du mal à respirer après {d}|il est inconscient après {d}|empoisonnement au {d}|mon visage gonfle après {d}|convulsions après {d}|je veux mourir|i took too much {d}|overdose of {d} what to do|my child swallowed {d} pills|i can't breathe after taking {d}|he fainted after {d}|swollen tongue after {d}|i want to die""",
"out_of_scope": """شنو هي أعراض {m}|كيفاش نعالج {m} بلا دوا|واش عندي {m}|شنو السبب ديال {m}|{m} كيتعدى؟|فين نلقى طبيب ديال {m}|c'est quoi {m}|quels sont les symptômes de {m}|comment guérir {m}|j'ai peut-être {m} que faire|how to treat {m} naturally|what causes {m}|symptoms of {m}|do I have {m}|salam|salam labas|labas 3lik|bonjour|hello|merci|choukran bzaf|شكرا بزاف|شكون نتا|شنو سميتك|chkoun nta|qui es-tu|who are you|what's your name|tell me a joke|شحال الساعة|what is the weather today|quel temps fait-il|أحسن مطعم فـ {c}|فين نلقى صيدلية ديال الليل فـ {c}|pharmacie de garde à {c}|horaires des pharmacies à {c}|comment devenir pharmacien|كيفاش نصاوب الكسكس|فين نشري تيليفون|best football team|كيفاش نكتب CV|translate this sentence|3awnni f l math|kifach ndir kiik|how to cook pasta|شنو هي عاصمة {c2}|capital of {c2}"""}
SYMP = ["السكري", "الربو", "الصداع النصفي", "الاكتئاب", "ارتفاع الضغط", "السرطان", "الأنيميا", "التهاب المفاصل", "الإكزيما", "الحساسية", "diabète", "hypertension", "migraine", "asthme", "anémie", "eczéma", "dépression", "cancer", "arthrose", "diabetes", "anxiety", "psoriasis", "angine", "insomnie", "kidney stones", "الأرق", "حصى الكلي", "الزكام", "الحمى", "ألم الظهر"]
INDIC = ["الصداع", "الحمى", "الألم", "الإسهال", "الغثيان", "الالتهاب", "السعال", "الحساسية", "الربو", "الضغط", "السكر", "الروماتيزم", "التهاب الحلق"]
CITIES = ["الدار البيضاء", "الرباط", "مراكش", "طنجة", "فاس", "Casablanca", "Rabat", "Marrakech", "Agadir", "Tanger"]
CAPS = ["فرنسا", "إسبانيا", "France", "Spain", "Japan", "Brazil", "اليابان", "البرازيل"]
PREFIX = ["", "", "", "", "salam ", "سلام ", "bonjour ", "عافاك ", "3afak ", "svp ", "hello ", "ila 9derti ", "من فضلك ", "بغيت نسول: ", "wach t9der tjawbni: ", "salut, ", "السلام عليكم "]
SUFFIX = ["", "", "", "", " svp", " عافاك", " 3afak", " merci", " شكرا", " please", " ؟", "?", " ...", " بسرعة", " stp"]


def split_templates(seed=0, val_frac=0.25):
    rng = random.Random(seed)
    tr, va = {}, {}
    for k, blob in T.items():
        ts = [t.strip() for t in re.split(r"\|\s*", blob.replace("\n", "|")) if t.strip()]
        rng.shuffle(ts)
        nv = max(3, int(len(ts) * val_frac))
        va[k], tr[k] = ts[:nv], ts[nv:]
    return tr, va


def load_drug_pools():
    a = pd.read_csv(ROOT / "data/processed/ammps_clean.csv")
    brands = a.nom.str.split().str[0].str.title().drop_duplicates().tolist()
    brands = [b for b in brands if 4 <= len(b) <= 14 and b.isalpha()]
    actives = sorted({s.split("//")[0].strip().title() for s in a.substances.dropna() if len(s.split("//")[0].strip()) > 4})
    ar = pd.read_csv(ROOT / "data/processed/arabic_brand_aliases.csv", encoding="utf-8-sig").alias_ar.dropna().tolist()
    known = ["Doliprane", "Efferalgan", "Dafalgan", "Augmentin", "Clamoxyl", "Voltarène", "Ibuprofène", "Aspirine", "Spasfon", "Smecta",
             "Levothyrox", "Zithromax", "Abilify", "Ventoline", "Daflon", "Mopral", "Xanax", "Prednisolone", "Metformine", "Paracétamol", "Amoxicilline"]
    ar_common = ["دوليبران", "الباراسيتامول", "الأسبرين", "الإيبوبروفين", "الأموكسيسيلين", "أوغمنتين", "فولتارين", "سمكتا", "سبازفون"]
    return brands, actives, ar, known, ar_common


def noise(s, rng):
    """ضجيج واقعي: خطأ إملائي، حذف علامات، توحيد الهمزات/التاء المربوطة، تطويل حروف."""
    if rng.random() < 0.25:
        w = s.split(); idx = [i for i, x in enumerate(w) if re.fullmatch(r"[A-Za-zÀ-ÿ]{5,}", x)]
        if idx:
            i = rng.choice(idx); x = list(w[i]); p = rng.randrange(1, len(x) - 1); op = rng.choice("dsi")
            if op == "d": del x[p]
            elif op == "s": x[p], x[p + 1 if p + 1 < len(x) else p - 1] = x[p + 1 if p + 1 < len(x) else p - 1], x[p]
            else: x.insert(p, x[p])
            w[i] = "".join(x); s = " ".join(w)
    if rng.random() < 0.3: s = s.replace("؟", "").replace("?", "")
    if rng.random() < 0.2: s = s.translate(str.maketrans("أإآة", "ااا" + "ه"))
    if rng.random() < 0.3: s = s.lower()
    return s


def fill(t, rng, pools, drugless=0.08):
    brands, actives, ar, known, ar_common = pools
    def pick():
        r = rng.random()
        return rng.choice(known) if r < .4 else rng.choice(brands) if r < .65 else rng.choice(actives) if r < .8 else rng.choice(ar + ar_common)
    d, d2 = pick(), pick()
    if "{d}" in t and rng.random() < drugless:           # أسئلة بلا اسم دواء ("هاد الدوا") حتى لا يصير اسم الدواء شرطاً للتصنيف
        d = rng.choice(["هاد الدوا", "had dwa", "ce médicament", "this medicine", "الدوا اللي عطاوني", "le médicament que j'ai"])
    return (t.replace("{d}", d).replace("{d2}", d2).replace("{n}", str(rng.randint(1, 9)))
             .replace("{m}", rng.choice(SYMP if "out" in "x" else SYMP + INDIC)).replace("{c}", rng.choice(CITIES)).replace("{c2}", rng.choice(CAPS)))


def load_medqa(path, n, seed, avoid, names=frozenset()):
    """أسئلة طبية عامة (دارجة) كفئة out_of_scope؛ نستبعد كل سؤال فيه اسم دواء معروف أو كلمة نية (لتقليل ضجيج التسمية)."""
    d = pd.read_csv(path, usecols=["Question"]).Question.astype(str)
    d = d[(d.str.len() >= 8) & (d.str.len() <= 160)].drop_duplicates()
    d = d[~d.str.contains(avoid, regex=True, case=False)]
    tok = re.compile(r"[\w']+", re.U)
    d = d[[not any(w.lower() in names for w in tok.findall(q)) for q in d]]
    return d.sample(min(n, len(d)), random_state=seed).tolist()


def build(medqa_path, n_per_intent=1400, seed=7):
    rng = random.Random(seed); pools = load_drug_pools()
    tr_t, va_t = split_templates(seed)
    brands, actives, ar, known, ar_common = pools
    names = {x.lower() for x in brands + actives + known} | set(ar + ar_common)
    cues = (r"ثمن|شحال|سعر|prix|جرعة|dose|posolog|قداش|حبة|حبوب|دوا|دواء|أدوية|médicament|مضاد|antibio|حامل|grossesse|عرض جانبي|effets|بديل|مرضع|تفاعل|"
            r"سوبردوز|تسمم|انتحر|نموت|overdose|surdosage|suicid")
    mq = load_medqa(medqa_path, 4500, seed, cues, {n.lower() for n in names})
    rows = []
    for split, T_ in (("train", tr_t), ("val", va_t)):
        n = n_per_intent if split == "train" else n_per_intent // 4
        for lab in LABELS:
            for _ in range(n):
                s = fill(rng.choice(T_[lab]), rng, pools)
                s = noise(rng.choice(PREFIX) + s + rng.choice(SUFFIX), rng).strip()
                rows.append((s, lab, split, "template"))
    cut = int(len(mq) * .8)
    for q in mq[:cut]: rows.append((q, "out_of_scope", "train", "medqa"))
    for q in mq[cut:]: rows.append((q, "out_of_scope", "val", "medqa"))
    df = pd.DataFrame(rows, columns=["text", "label", "split", "source"]).drop_duplicates("text")
    return df


def load_gold():
    r = [l.rstrip("\n").split("|", 1) for l in open(Path(__file__).parent / "gold_intent.psv", encoding="utf-8") if "|" in l]
    return pd.DataFrame(r, columns=["label", "text"])[["text", "label"]]
