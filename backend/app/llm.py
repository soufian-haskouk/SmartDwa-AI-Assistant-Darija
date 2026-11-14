"""طبقة توليد اختيارية عبر Ollama (Atlas-Chat). تُستعمل فقط لإعادة صياغة حقائق جاهزة، لا لإنتاج معلومة طبية."""
import httpx
from . import config

SYSTEM = ("أنت مساعد صيدلي تعليمي كتجاوب بالدارجة المغربية البسيطة. جاوب فقط بالمعلومات الموجودة في «الحقائق». "
          "إلا ما لقيتيش الجواب فيها قول: ما عنديش هاد المعلومة، سول الصيدلي. ما تعطيش جرعات ولا تشخيص. جواب قصير.")

def rewrite_in_darija(question: str, facts: str) -> str | None:
    if not config.USE_LLM:
        return None
    try:
        r = httpx.post(f"{config.OLLAMA_URL}/api/chat", timeout=config.LLM_TIMEOUT, json={
            "model": config.OLLAMA_MODEL, "stream": False, "options": {"temperature": 0.2},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"الحقائق:\n{facts}\n\nالسؤال: {question}"}]})
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception:
        return None  # نرجع للجواب الجاهز
