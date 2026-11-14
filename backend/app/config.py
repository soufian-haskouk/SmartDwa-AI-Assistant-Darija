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
