"""قاموس بذري (seed) لترجمة كلمات الأسئلة (دارجة/عربية/أرابيزي/إنجليزية) إلى مصطلحات RCP الفرنسية.
⚠️ كتبه الذكاء الاصطناعي ويحتاج مراجعة ناطق بالدارجة. الهدف فقط توسيع الاستعلام للبحث النصي (BM25)."""
import re, unicodedata

# كل مفتاح: regex على النص المطبَّع (بلا تشكيل/لهجات) ← مصطلحات فرنسية تضاف للاستعلام
LEX = [
 (r"حامل|حمل|الحمل|hamla|hamil|7amla|enceinte|pregnan", "grossesse enceinte trimestre"),
 (r"رضاع|ترضع|ترضيع|allait|breast|lactat|reda3a", "allaitement"),
 (r"كبد|الكبد|kabd|kbed|foie|liver|hepat", "hépatique foie insuffisance hépatique"),
 (r"كلي|الكلى|كلاوي|klawi|kalawi|rein|kidney|renal|rénal", "rénale rein insuffisance rénale"),
 (r"ربو|الربو|asthm|rabw|rabou", "asthme bronchospasme"),
 (r"حساسي|الحساسية|7asasiya|hassasiya|allerg|hypersensib", "hypersensibilité allergie"),
 (r"قلب|القلب|galb|qalb|coeur|cœur|cardiaq|heart|cardiac", "cardiaque insuffisance cardiaque rythme QT"),
 (r"ضغط|tension|hypertens|ضغط الدم", "hypertension hypotension pression artérielle"),
 (r"سكر|السكري|diab|sokkar|sukkar", "diabète glycémie"),
 (r"طفل|اطفال|الأطفال|drari|derri|enfant|child|bébé|nourrisson|pediatr", "enfant nourrisson pédiatrique âge ans"),
 (r"شيخ|كبار السن|ancien|elderly|âgé|vieux", "sujet âgé"),
 (r"كحول|الكحول|شراب|alcool|alcohol|khamr", "alcool"),
 (r"معدة|المعدة|قرحة|ma3da|ulc|stomach|gastr|estomac", "ulcère gastroduodénal gastro-intestinal hémorragie digestive"),
 (r"نزيف|(?<!\S)دم(?!\S)|(?<!\S)الدم(?!\S)|saign|bleed|hemorr|hémorr|anticoag|مميع", "hémorragie saignement anticoagulants antivitamines K"),
 (r"مضاد حيوي|antibio|antibiot", "antibiotique macrolides pénicillines"),
 (r"فيتامين|vitamin", "vitamine"),
 (r"عصير|pamplemousse|grapefruit|جريب", "jus de pamplemousse"),
 (r"قيء|غثيان|ترجيع|vomi|nausea|nausée", "nausées vomissements"),
 (r"إسهال|اسهال|diarrh|ishal", "diarrhée"),
 (r"غدة|الغدة|thyro|thyroid", "thyroïde hyperthyroïdie hypothyroïdie"),
 (r"ممنوع|منوع|ما يتاخدش|ما نقدرش|interdit|contre-?indiqu|contraindic|forbidden|mamnou3", "contre-indiqué contre-indication"),
 (r"تداخل|تتداخل|(?<!\S)مع(?!\S)|m3a|ma3a|مخلط|نخلط|خلط|avec|with|interact|ensemble|together|combin", "association interaction"),
 (r"سرطان|cancer|chimio", "cytotoxique méthotrexate"),
 (r"مرض نفسي|اكتئاب|dépress|antidépress|depress", "antidépresseurs"),
 (r"صرع|epilep|épilep|convuls", "épilepsie anticonvulsivants"),
 (r"تعفن|infection|عدوى|virus|فيروس", "infection"),
 (r"لقاح|vaccin", "vaccins"),
 (r"جرعة زايدة|surdos|overdose", "surdosage"),
]
# مؤشرات نية القسم (ليست فلتراً بل ترجيح)
INTERACTION_HINT = re.compile(r"تداخل|(?<!\S)مع(?!\S)|m3a|ma3a|avec|with|interact|نخلط|خلط|ensemble|together|combin|association")
CONTRA_HINT = re.compile(r"ممنوع|منوع|ما يتاخدش|ما نقدرش|contre-?indiqu|contraindic|interdit|forbidden|حامل|حمل|hamla|enceinte|pregnan|allerg|حساسي|كبد|كلي|طفل|رضاع|ربو|asthm|hepat|renal|rénal|عندي|مرضى|patient")

def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[ً-ٟـ]", "", s)                 # تشكيل وتطويل
    s = s.translate(str.maketrans("أإآٱ", "اااا")).replace("ى", "ي").replace("ة", "ه")
    return s

def _npat(p: str) -> str:
    """تطبيع نمط regex مع الحفاظ على رموز مثل \\S و\\d (لا تُحوَّل إلى أحرف صغيرة)."""
    return re.sub(r"(\\[A-Za-z])|(.)", lambda m: m.group(1) or normalize(m.group(2)), p, flags=re.S)

def expand(text: str) -> str:
    n = normalize(text)
    extra = []
    for pat, fr in LEX:
        if re.search(_npat(pat), n):
            extra.append(fr)
    return " ".join(extra)

def section_prior(text: str, has_other_drug: bool) -> dict:
    n = normalize(text)
    p = {"4.3": 1.0, "4.5": 1.0}
    if has_other_drug or INTERACTION_HINT.search(n): p["4.5"] += 0.25
    if CONTRA_HINT.search(n): p["4.3"] += 0.25
    return p
