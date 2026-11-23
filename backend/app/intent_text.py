"""تطبيع النص لمصنّف النية (يُستعمل وقت التدريب ووقت الخدمة؛ يجب أن يبقى مطابقاً)."""
import re, unicodedata

_AR_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_DIAC = re.compile(r"[ً-ٰٟـ]")
_VAR = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "پ": "ب", "گ": "ك", "ڤ": "ف"})
_REP = re.compile(r"(.)\1{2,}")


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))     # é,è,ô -> e,e,o
    s = _DIAC.sub("", s).translate(_AR_DIG).translate(_VAR)
    s = _REP.sub(r"\1\1", s)
    s = re.sub(r"[؟?!.,;:()\[\]«»\"“”…،]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
