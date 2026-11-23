import os
from pathlib import Path

ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
PROCESSED = DATA_DIR / "processed"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "atlas-chat-2b")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"   # false = جواب جاهز بدون نموذج لغوي
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))

# أرقام الطوارئ: مأخوذة من README مشروع DwaTalk، تحقّق منها قبل التسليم.
EMERGENCY_TEXT = ("⚠️ هادي حالة مستعجلة. عيّط دابا على: السامو 141، الوقاية المدنية 15، "
                  "أو مركز محاربة السموم 0801 000 180. ما تستناش.")

# تاريخ استخراج AMMPS (حسب صاحب المشروع). غيّره عند كل استخراج جديد.
AMMPS_DATE = os.getenv("AMMPS_DATE", "2026-11-10")

# ---- مولّد الأسئلة الصحية العامة (Atlas-Chat-2B + LoRA) : مغلق افتراضياً ----
# يتكلم مع خادم متوافق مع واجهة Ollama (/api/chat). لا يُستعمل أبداً للأدوية (الحقائق من AMMPS/RCP) ولا للإسعافات الأولية (رسالة ثابتة).
USE_HEALTH_GENERATOR = os.getenv("USE_HEALTH_GENERATOR", "false").lower() == "true"
HEALTH_GEN_MODEL = os.getenv("HEALTH_GEN_MODEL", "smartdwa-atlas")
HEALTH_GEN_TIMEOUT = float(os.getenv("HEALTH_GEN_TIMEOUT", "90"))
HEALTH_GEN_KEEPALIVE = os.getenv("HEALTH_GEN_KEEPALIVE", "30m")   # durée pendant laquelle Ollama garde le modèle en RAM après la dernière requête (ex. 5m, 30m, 1h, 0 = décharger tout de suite)
HEALTH_GEN_TOKEN = os.getenv("HEALTH_GEN_TOKEN", "")      # seulement si Ollama est derrière le proxy à jeton du notebook Colab (tunnel)

# ---- classifieur d'intention XLM-R distant (même tunnel Colab que le générateur) : fermé par défaut ----
# INTENT_BACKEND=local : sklearn + règles (comportement historique). remote : XLM-R via POST {INTENT_URL}/intent ; en cas d'échec -> repli sklearn/règles.
INTENT_BACKEND = os.getenv("INTENT_BACKEND", "local").lower()
INTENT_URL = os.getenv("INTENT_URL", "").rstrip("/")
INTENT_TOKEN = os.getenv("INTENT_TOKEN", "") or HEALTH_GEN_TOKEN
INTENT_TIMEOUT = float(os.getenv("INTENT_TIMEOUT", "8"))
INTENT_MIN_CONF = float(os.getenv("INTENT_MIN_CONF", "0.5"))
