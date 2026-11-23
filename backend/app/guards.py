"""حواجز بسيطة قبل أي شيء: طوارئ + أسئلة الجرعات. (مؤقتاً قواعد كلمات؛ سيعوضها intent classifier لاحقاً.)"""
import re

EMERGENCY = [r"جرعة زايدة", r"سوبردوز", r"overdose", r"surdosage", r"ما قادرش نتنفس", r"ضيق شديد في التنفس",
             r"فقد(ت|ان) الوعي", r"تسمم", r"empoisonn", r"suicid", r"بغيت نموت", r"نتحر",
             # أفكار انتحارية / إيذاء النفس (دارجة، عربية، فرنسية، إنجليزية)
             r"(بغيت|باغي|بغا|حاب|نبغي|ودي|عندي بغيت)\s*(ن|أن)?(موت|مووت)", r"(نقتل|نقتّل|نقتل|اقتل)\s*(راسي|نفسي|روحي|راسو)",
             r"(ما|مابقيتش|ما بقيتش|ما بقيت)\s*(ب?غيت|باغي|باغيا|حاب)?ش?\s*(ن)?عيش", r"ما (ب?غيتش|باغيش|حابش) (ن)?عيش",
             r"(تعبت|مللت|عييت|سئمت|زهقت)\s*(من|ف)\s*(ال)?(حياة|حياتي|دنيا|عيشة)", r"(ننهي|نسالي|نقطع|نوقف|نسلي|ننهى)\s*(مع\s*)?(ال)?حياتي",
             r"(نشنق|نذبح|نحرق|نرمي|نجرح|نأذي|نآذي|نؤذي)\s*(راسي|روحي|نفسي)", r"(انهاء|إنهاء|نهاية)\s*حياتي", r"انتحار|أريد أن أموت|اريد ان اموت|أفكر في الانتحار|افكر في الانتحار",
             r"me tuer", r"mettre fin (a|à) (mes jours|ma vie)", r"en finir (avec la vie|avec moi)", r"envie de mourir", r"(plus|pas) envie de vivre", r"je veux mourir",
             r"je (vais|voudrais) me (suicider|faire du mal)", r"kill myself", r"end my (own )?life", r"want to die", r"don'?t want to (live|be alive)", r"hurt myself", r"self[- ]harm", r"automutil"]
DOSE = [r"جرعة", r"الجرعة", r"قداش (نشرب|ناخد|ناخذ|نتناول|ندير)", r"كم (حبة|مرة|ملغ)", r"شحال (ناخد|نشرب|ندير)",
        r"dose", r"posologie", r"combien (de|je)", r"dosage", r"how (much|many)", r"قداش من حبة", r"شحال من حبة"]

def _hit(text, pats):
    t = text.lower()
    return any(re.search(p, t) for p in pats)

def is_emergency(text): return _hit(text, EMERGENCY)
def asks_dose(text): return _hit(text, DOSE)
