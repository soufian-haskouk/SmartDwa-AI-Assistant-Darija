"""Questions de santé générale (hors médicaments).

1) `is_first_aid` : conduite à tenir devant une personne en détresse (crise, malaise, étouffement, brûlure, hémorragie…) → message FIXE d'urgence, jamais de génération
   (la relecture des générations Atlas a montré des erreurs de premiers secours que les règles lexicales ne détectent pas). Toujours actif, sans modèle.
2) `answer_general` : générateur Atlas-Chat-2B + LoRA, derrière USE_HEALTH_GENERATOR (faux par défaut), toujours suivi du garde-fou (safety_rules v2) et d'un message de repli fixe.
Le générateur ne touche jamais aux faits sur les médicaments (prix AMMPS, RCP §4.3/§4.5)."""
import logging, re
import httpx
from . import config
from .intent_text import norm_text
from .safety import safety_rules as SR

log = logging.getLogger("smartdwa.health")

# même consigne que pendant l'entraînement (colab_chat2/sft_*.csv, colonne instruction)
INSTRUCTION = "أجب عن سؤال المريض بطريقة بسيطة وآمنة. لا تعطِ جرعات ولا تشخيصاً ولا وصف دواء، ولا تطلب صوراً أو معلومات شخصية، وانصح بسؤال الصيدلي أو الطبيب عند الحاجة."
FALLBACK = "ما نقدرش نجاوب على هاد السؤال بشكل آمن. سول الطبيب أو الصيدلي، وإلا كانت الحالة مستعجلة عيّط للإسعاف."
FIRST_AID_TEXT = ("هادي حالة ما نقدرش نعطي فيها تعليمات إسعافات أولية من هنا، حيت الغلط فيها خطير. " + config.EMERGENCY_TEXT)

# conduite à tenir / détresse (darija, arabe, français, anglais), appliqué au texte normalisé (norm_text)
_FA = [r"الرعاد|الصرع|تشنج|convuls|seizure|epilep|crise d", r"سخف|غمي عليه|غمات|فقد(ان|ت)? الوعي|طاح.*(ما|بلا) (كيجاوب|حركه)|evanoui|malaise|faint|unconscious",
       r"تخنق|اختنق|اختناق|لقمه|etouff|chok", r"(حرق|حرقه|احترق|brul)\w*.*(جلد|ما|ماء|نار|burn)|burn|brulure|حروق|الحروق", r"نزيف|الدم (ما )?(بغاش|كيوقفش|كيسيل)|(نوقف|وقف|نحبس|حبس)\w* (ال)?دم|hemorrag|bleeding|saign",
       r"انعاش|massage cardiaque|\bcpr\b|توقف القلب|arret cardiaque|cardiac arrest|ما كيتنفسش|ne respire|not breathing", r"لدغه|عضه|morsure|piqure|snake|bite",
       r"عظم (مكسور|مكسر)|كسر\w* فـ?(الرجل|اليد|العظم)|fracture|broken bone", r"سكته|جلطه|avc|stroke|اسعاف(ات)? اوليه|premiers? secours|first aid"]
_FA = re.compile("|".join(_FA))
_CONDUITE = re.compile(r"كيفاش|كيف|شنو ندير|شنو خاصني|واش خاصني|comment|que faire|what (do|should)|how (to|do)|نتعامل|نتصرف|نعاون|ندير ليه|نسعف|aider")

def is_first_aid(text: str) -> bool:
    t = norm_text(text)
    return bool(_FA.search(t)) and bool(_CONDUITE.search(t) or re.search(r"قدامي|عندي واحد|شي حد|شخص|مريض|ولدي|بنتي|بابا|ماما|someone|person|quelqu", t))

_HEALTH_AR = ("عندي|كنحس|كيضرني|كيضرو|ضرني|وجع|الم |سخانه|كحه|دوخه|ورم|حكه|اسهال|غثيان|قيء|صداع|راسي|كرشي|دايخ"
              "|صحه|صحتي|مرض|امراض|مريض|علاج|نصيحه|نزله|زكام|رشح|برد|حمي|سخون|عطس|حساسيه|اكزيما|جلد|بشره|عيني|اذني|سنان|ضرس|حلق|بلعوم"
              "|صدر|ضغط|سكر|كولسترول|فيتامين|كالسيوم|حديد|انيميا|فقر الدم|نعاس|ارق|نوم|تعب|عياء|ارهاق|قلق|توتر|اكتئاب|حامل|حمل|رضاع|رضيع"
              "|طفل|ولدي|بنتي|حميه|رجيم|وزن|سمنه|قولون|معده|حموضه|امساك|بواسير|كلي|مثانه|بول|حصي|ظهر|ركبه|مفاصل|عضلات|رقبه|كتف|التواء|جرح"
              "|لسعه|دوخ|ننعس|كينعس|خفقان|قلب|تنفس|ربو|بلغم|حنجره|شقيقه|مناعه|التهاب|عدوي|فيروس|بكتيريا|تحليل|صيام|رمضان|الراس")
_HEALTH_LAT = ("douleur|mal (a|au|aux)|fievre|toux|symptom|diarrh|vertige|migraine|sante|maladie|traitement|rhume|grippe|allerg|eczema|peau|yeux|dent|gorge"
               "|tension|diabet|sucre|cholesterol|vitamine|fatigue|sommeil|insomnie|stress|anxiete|enceinte|grossesse|allaitement|bebe|enfant|regime|poids"
               "|estomac|digest|constipation|rein|genou|articulation|muscle|blessure|plaie|immun|infection"
               "|pain|fever|cough|headache|rash|health|disease|\\bcold\\b|\\bflu\\b|skin|tooth|throat|blood pressure|diabetes|sugar|vitamin|sleep|insomnia|anxiety"
               "|pregnan|baby|child|diet|weight|stomach|kidney|knee|joint|injury|wound|infection")
_HEALTH = re.compile(_HEALTH_AR + "|" + _HEALTH_LAT)

def looks_like_health_question(text: str) -> bool:
    """heuristique provisoire : sera remplacée par l'intention `symptoms_query` du classifieur v3 quand celui-ci sera branché"""
    return bool(_HEALTH.search(norm_text(text)))

_KA_RE = re.compile(r"^(0|[1-9]\d{0,3}(s|m|h))$")      # 0 | 30s | 5m | 30m | 2h ... (valeurs d'Ollama)
_KA_MAX_S = 24 * 3600
_runtime = {"keep_alive": config.HEALTH_GEN_KEEPALIVE if _KA_RE.match(config.HEALTH_GEN_KEEPALIVE) else "30m"}

def _ka_seconds(v: str) -> int:
    return 0 if v == "0" else int(v[:-1]) * {"s": 1, "m": 60, "h": 3600}[v[-1]]

def get_keep_alive() -> str:
    return _runtime["keep_alive"]

def set_keep_alive(v: str) -> str:
    """change la durée à chaud (sans redémarrage) ; valide le format ; revient à la valeur de .env au redémarrage du backend"""
    v = str(v).strip().lower()
    if not _KA_RE.match(v) or _ka_seconds(v) > _KA_MAX_S:
        raise ValueError("format invalide : utiliser 0, 30s, 5m, 30m, 2h ... (maximum 24h)")
    _runtime["keep_alive"] = v
    return v

def generate(question: str) -> str | None:
    """appelle le serveur (API Ollama /api/chat) ; None si indisponible"""
    try:
        hdr = {"Authorization": f"Bearer {config.HEALTH_GEN_TOKEN}"} if config.HEALTH_GEN_TOKEN else {}
        r = httpx.post(f"{config.OLLAMA_URL}/api/chat", timeout=config.HEALTH_GEN_TIMEOUT, headers=hdr, json={
            "model": config.HEALTH_GEN_MODEL, "stream": False, "keep_alive": get_keep_alive(),
            "options": {"temperature": 0, "repeat_penalty": 1.1, "num_predict": 120},
            "messages": [{"role": "user", "content": INSTRUCTION + "\n\n" + question}]})
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as e:
        log.warning("health generator unavailable: %s", type(e).__name__); return None

def answer_general(question: str) -> dict:
    """renvoie {answer, used, blocked_reason}. Le garde-fou s'applique à CHAQUE réponse générée."""
    raw = generate(question)
    if not raw: return dict(answer=FALLBACK, used=False, blocked_reason="generator_unavailable")
    why = SR.safety_reason_v2(question, raw)
    if not why and len(raw) < 30: why = "too_short"
    if why:
        log.info("health answer blocked: %s", why); return dict(answer=FALLBACK, used=False, blocked_reason=why)
    return dict(answer=raw, used=True, blocked_reason="")
