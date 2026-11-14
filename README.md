# SmartDwa — مساعد صيدلي بالدارجة (RAG + FastAPI + Streamlit + Docker)

## التشغيل  (التفاصيل لأول مرة على Windows: DOCKER_GUIDE.md)
```
docker compose up --build        # backend :8000  +  Streamlit :8501
```
افتح http://localhost:8501 . وثائق الـ API: http://localhost:8000/docs

## تحديث بيانات AMMPS (يُعاد الحساب فقط إذا تغيّر الملف)
ضع الملف الجديد في `data/raw/ammps_medicaments.csv` ثم:
```
docker compose run --rm prepare      # يحدّث data/processed/ammps_clean.csv (كل الصفوف، أسعار منظّفة)
curl -X POST localhost:8000/admin/reload
```

## الحالة
| الجزء | الحالة |
|---|---|
| FastAPI: /health /link /chat /admin/reload | ✅ يعمل (4 اختبارات) |
| Streamlit chat | ✅ |
| Linker (20 مادة) + حواجز (طوارئ/جرعات) + تداخلات من interaction_pairs.csv | ✅ |
| تطبيع AMMPS كامل (9755 صف) | ✅ |
| أسعار كل صفوف AMMPS (9755): بحث بالاسم التجاري/المادة، fuzzy يسأل ولا يعرض | ✅ `catalog.py` + `/catalog/search` |
| أسماء عربية للعلامات (519 اسماً / 515 علامة من الملف المصري CC0، بشرط تطابق المادة) | ✅ `build_arabic_aliases.py` |
| LLM (Ollama/Atlas-Chat) | ⏸ مطفأ افتراضياً: `USE_LLM=true` |
| RCP sections (20/20 مادة، §4.3 و§4.5) | ✅ `python scripts/build_rcp_sections.py` |
| RAG: chunking + BM25/TF-IDF + RRF، Recall@3 = 98% (أسئلة AI، تفاؤلي) | ✅ `python scripts/build_rag_index.py` ثم `scripts/eval_rag.py` |
| RAG dense (e5) | ⏳ كود جاهز لم يُجرَّب (لا إنترنت في بيئة التطوير): `--embedder e5` |
| Prolog / intent / بدائل | ⏳ |

اختبارات: `python -m pytest tests`
