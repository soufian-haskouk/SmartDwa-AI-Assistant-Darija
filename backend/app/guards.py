"""حواجز بسيطة قبل أي شيء: طوارئ + أسئلة الجرعات. (مؤقتاً قواعد كلمات؛ سيعوضها intent classifier لاحقاً.)"""
import re

EMERGENCY = [r"جرعة زايدة", r"سوبردوز", r"overdose", r"surdosage", r"ما قادرش نتنفس", r"ضيق شديد في التنفس",
             r"فقد(ت|ان) الوعي", r"تسمم", r"empoisonn", r"suicid", r"بغيت نموت", r"نتحر"]
DOSE = [r"جرعة", r"الجرعة", r"قداش (نشرب|ناخد|ناخذ|نتناول|ندير)", r"كم (حبة|مرة|ملغ)", r"شحال (ناخد|نشرب|ندير)",
        r"dose", r"posologie", r"combien (de|je)", r"dosage", r"how (much|many)", r"قداش من حبة", r"شحال من حبة"]

def _hit(text, pats):
    t = text.lower()
    return any(re.search(p, t) for p in pats)

def is_emergency(text): return _hit(text, EMERGENCY)
def asks_dose(text): return _hit(text, DOSE)
