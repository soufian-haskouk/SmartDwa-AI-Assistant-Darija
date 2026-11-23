import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ["PROJECT_ROOT"] = str(ROOT)
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from app.main import app

def client():
    return TestClient(app)

def test_health():
    with client() as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["drugs_master"] > 2000 and h["interaction_pairs"] == 29

def test_emergency_and_dose_refusal():
    with client() as c:
        assert c.post("/chat", json={"message": "عندي جرعة زايدة ديال باراسيتامول"}).json()["route"] == "emergency"
        assert c.post("/chat", json={"message": "شحال ناخد من دوليبران"}).json()["route"] == "refuse_dose"

def test_interaction_route():
    with client() as c:
        r = c.post("/chat", json={"message": "can I take clarithromycin with domperidone"}).json()
        assert r["route"] == "interaction" and r["interactions"], r
        assert "RCP" in " ".join(r["sources"])

def test_single_drug_prices_and_unknown():
    with client() as c:
        r = c.post("/chat", json={"message": "شنو هو ibuprofen"}).json()
        assert r["route"] == "drug_info" and r["presentations"]
        assert c.post("/chat", json={"message": "واش كاين شي دوا للحساسية"}).json()["route"] in ("clarify", "not_a_drug_question")

def test_rag_passages_mention_other_drug():
    with client() as c:
        h = c.get("/health").json()
        assert h["rag_ready"] and h["rag_chunks"] > 200
        r = c.post("/chat", json={"message": "ibuprofen m3a aspirine wach khatir"}).json()
        assert r["passages"] and all(p["source"].startswith("RCP") for p in r["passages"])
        assert any("acétylsalicylique" in p["text"] or "AINS" in p["text"] for p in r["passages"])

def test_rag_single_drug_section_prior():
    from app import rag
    hits = rag.retrieve("paracetamol insuffisance hépatique ممنوع", ["PARACETAMOL"], k=1)
    assert hits and hits[0]["section"] == "4.3"

def test_price_only_out_of_scope_brand():
    with client() as c:
        r = c.post("/chat", json={"message": "بشحال Abilify 10"}).json()
        assert r["route"] == "price_only" and r["presentations"][0]["ppv_dh"] == 1200.0
        assert "خارج النطاق" in r["answer"]            # لا معلومات سلامة

def test_typo_asks_confirmation_not_price():
    with client() as c:
        r = c.post("/chat", json={"message": "abilifi"}).json()
        assert r["route"] == "confirm" and not r["presentations"]

def test_dose_hint_selects_product_gram_to_mg():
    with client() as c:
        r = c.post("/chat", json={"message": "doliprane 1000 prix"}).json()
        assert r["presentations"] and all(p["dosage"] == "1 G" for p in r["presentations"])

def test_out_of_scope_companion_warns_first():
    with client() as c:
        r = c.post("/chat", json={"message": "paracetamol m3a abilify"}).json()
        assert r["answer"].startswith("⚠️") and "ABILIFY" in r["answer"]

def test_catalog_endpoint_and_performance():
    import time
    with client() as c:
        t = time.time(); m = c.get("/catalog/search", params={"q": "omeprazole"}).json()
        assert m and m[0]["in_scope"] and time.time() - t < 1

def test_arabic_brand_out_of_scope_gives_price():
    with client() as c:
        r = c.post("/chat", json={"message": "بشحال دوا أبيليفي"}).json()
        assert r["route"] == "price_only" and r["presentations"][0]["ppv_dh"] == 1200.0

def test_arabic_spelling_variant_asks_confirmation():
    with client() as c:
        r = c.post("/chat", json={"message": "شحال كيسوا أبيليفاي"}).json()
        assert r["route"] == "confirm" and "ABILIFY" in r["answer"] and not r["presentations"]

def test_arabic_aliases_file_is_conservative():
    import pandas as pd
    a = pd.read_csv(ROOT / "data/processed/arabic_brand_aliases.csv", encoding="utf-8-sig")
    assert len(a) > 300 and a.active_score.min() >= 85 and a.alias_norm.is_unique

def test_brand_misspelling_and_arabic_use_same_brand_as_correct_spelling():
    with client() as c:
        ref = c.post("/chat", json={"message": "Doliprane"}).json()["presentations"]
        for q in ["dolyprane", "شحال تمن دوليبران"]:
            r = c.post("/chat", json={"message": q}).json()
            assert r["presentations"] and r["presentations"][0]["nom"].startswith("DOLIPRANE"), q
        assert ref and ref[0]["nom"].startswith("DOLIPRANE")


def _chat(c, q): return c.post("/chat", json={"message": q}).json()


def test_intent_routing():
    with client() as c:
        r = _chat(c, "شحال ثمن Doliprane"); assert r["intent"]["label"] == "price" and r["presentations"] and not r["passages"]
        r = _chat(c, "chno kaydir lia ibuprofene f l ma3da"); assert r["route"] in ("side_effects_unavailable", "emergency") and not r["presentations"]
        r = _chat(c, "شنو البديل ديال Doliprane"); assert r["route"] == "alternative" and r["presentations"]
        r = _chat(c, "واش الحامل تقدر تاخد ibuprofène"); assert r["route"] == "contraindication"
        r = _chat(c, "كيفاش نعالج الصداع النصفي بلا دوا"); assert r["route"] in ("not_a_drug_question", "clarify")
        r = _chat(c, "ma petite fille a avalé toute la boîte de Doliprane"); assert r["route"] == "emergency"
        r = _chat(c, "شحال من حبة ناخد من Doliprane"); assert r["route"] == "refuse_dose"


def test_intent_model_present_and_sane():
    from app.intent import IntentClassifier
    m = IntentClassifier(); assert m.ready, m.error
    assert m.predict("bghit nmout")["label"] == "emergency"
