"""Mode intent distant (XLM-R) : toujours testé avec un serveur SIMULÉ (aucun vrai modèle ici)."""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ["PROJECT_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT / "backend"))
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import config, health
from app import intent as intent_mod
from app.safety import redflags


def chat(msg):
    with TestClient(app) as c:
        return c.post("/chat", json={"message": msg}).json()


class Resp:
    def __init__(self, top): self._t = top
    def raise_for_status(self): pass
    def json(self): return {"top": self._t}


@pytest.fixture
def remote(monkeypatch):
    monkeypatch.setattr(config, "INTENT_BACKEND", "remote"); monkeypatch.setattr(config, "INTENT_URL", "https://fake.example")
    monkeypatch.setattr(config, "INTENT_TOKEN", "tok")
    calls = []
    def install(top=None, exc=None):
        import httpx
        def post(url, json=None, headers=None, timeout=None):
            calls.append((url, json, headers, timeout))
            if exc: raise exc
            return Resp(top)
        monkeypatch.setattr(httpx, "post", post)
        return calls
    return install


def test_default_is_local_and_no_network(monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("appel réseau en mode local"))
    assert config.INTENT_BACKEND == "local"
    chat("شحال ثمن doliprane")


def test_remote_used_with_token_and_url(remote):
    calls = remote(top=[["price", 0.97], ["drug_info", 0.02]])
    r = chat("شحال ثمن doliprane")
    assert r["intent"]["source"] == "remote_model" and r["intent"]["label"] == "price"
    assert calls and calls[0][0] == "https://fake.example/intent" and calls[0][2]["Authorization"] == "Bearer tok"


def test_remote_low_confidence_falls_back_to_rules(remote):
    remote(top=[["alternative", 0.30], ["price", 0.25]])
    r = chat("شحال ثمن doliprane")
    assert r["intent"]["source"] == "rules"


def test_remote_down_falls_back_to_local(remote):
    import httpx
    remote(exc=httpx.ConnectError("down"))
    r = chat("شحال ثمن doliprane")
    assert r["route"] == "price" and r["intent"]["source"] != "remote_model"


def test_remote_garbage_labels_fall_back(remote):
    remote(top=[["hacked", 0.99]])
    assert chat("شحال ثمن doliprane")["intent"]["source"] != "remote_model"


@pytest.mark.parametrize("q", ["ma9drach ndkhel nafas w lwn dyali tbddl", "bnti ma bqatch kat3tini jawab w 3inha mghmdin", "عندي ضيق ف التنفس بزاف وما قادرش نهضر", "my mother is not breathing", "ma fille s'est étouffée avec une cacahuète"])
def test_red_flag_guard_beats_model_and_skips_network(q, remote):
    calls = remote(top=[["out_of_scope", 0.99]])
    r = chat(q)
    assert r["route"] == "emergency" and "141" in r["answer"] and not calls


def test_model_emergency_with_moderate_prob_accepted(remote):
    remote(top=[["symptoms_query", 0.45], ["emergency", 0.40]])
    assert chat("ولدي ما بغاش ياكل من البارح")["route"] == "emergency"


def test_symptoms_query_goes_to_general_health_when_generator_on(remote, monkeypatch):
    remote(top=[["symptoms_query", 0.95]])
    monkeypatch.setattr(config, "USE_HEALTH_GENERATOR", True)
    monkeypatch.setattr(health, "answer_general", lambda t: dict(answer="جواب تجريبي", used=True, blocked_reason=None))
    r = chat("كيفاش نخفض الضغط بلا دوا")
    assert r["route"] == "general_health"


def test_symptoms_query_generator_off_gives_safe_message(remote):
    remote(top=[["symptoms_query", 0.95]])
    r = chat("كيفاش نخفض الضغط بلا دوا")
    assert r["route"] == "not_a_drug_question"


def test_out_of_scope_remote(remote):
    remote(top=[["out_of_scope", 0.98]])
    assert chat("شكون هو أحسن لاعب فالعالم")["route"] == "not_a_drug_question"


def test_red_flag_module_negatives():
    for q in ["شحال ثمن Doliprane", "عندي تنميل فاليدين شنو نديرو", "واش Kardegic كيسبب النزيف ديال الأنف", "how to stop hiccups"]:
        assert not redflags.is_red_flag(q), q


def test_health_reports_backend():
    with TestClient(app) as c:
        h = c.get("/health").json()
        assert h["intent_backend"] == "local"
