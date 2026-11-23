# 💊 SmartDwa — Moroccan Darija Medical Assistant (RAG + FastAPI + Streamlit + Docker)

An intelligent medical guidance and pharmacy over-the-counter assistant tailored for Moroccan Darija, combining Retrieval-Augmented Generation (RAG), structured medication/interaction logic, a [FastAPI](http://localhost:8000/docs) backend, a [Streamlit](http://localhost:8501/) chat interface, and containerized deployment via [Docker](https://github.com/soufian-haskouk/SmartDwa-AI-Assistant-Darija/blob/temp-backup/docker-compose.yml).

---

## ✨ Key Capabilities

* **Darija Medical & Pharmacy Guidance:** Designed to assist with Moroccan Darija queries around over-the-counter guidance, active substances, dosages, red-flag safety checks, and drug interactions (`interaction_pairs.csv`, `backend/app/safety/redflags.py`).
* **AMMPS Catalog & Pricing:** Full normalization of AMMPS medication rows (9,755 rows) with search by brand name or active substance (`catalog.py`, `/catalog/search`) and Arabic alias mapping (`build_arabic_aliases.py`).
* **RAG & RCP Pipeline:** Section extraction from RCP documents (`build_rcp_sections.py`), chunking, BM25/TF-IDF + RRF retrieval (`build_rag_index.py`, `eval_rag.py`), plus optional dense embedding support (`--embedder e5`) and optional LLM mode (`USE_LLM=true` for Ollama / Atlas-Chat).
* **Backend & UI:** [FastAPI](http://localhost:8000/docs) endpoints (`/health`, `/link`, `/chat`, `/admin/reload`, `/catalog/search`) paired with a [Streamlit](http://localhost:8501/) conversational interface.

---

## 📁 Project Structure

```text
.
├── backend/            # FastAPI app, safety guards/redflags, catalog & RAG logic
├── data/               # Raw datasets, processed tables, RAG artifacts, and models
├── docs/               # Guides and documentation (including DOCKER_GUIDE.md & intent guide)
├── eval/               # Evaluation scripts and datasets
├── ml/                 # Intent / NLP / model experiments and helpers
├── scripts/            # Data preparation, RCP builders, RAG index & evaluation scripts
├── tests/              # Unit and integration tests (pytest)
├── ui/                 # Streamlit frontend application
├── docker-compose.yml  # Multi-service Docker configuration
└── .env / env templates