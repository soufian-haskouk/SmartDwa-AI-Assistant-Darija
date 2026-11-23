from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from . import config, health as health_mod, rag
from .data_store import DataStore
from .linking import load_linker
from .orchestrator import Orchestrator

state = {}

@asynccontextmanager
async def lifespan(app):
    store = DataStore()
    state["store"], state["orch"] = store, Orchestrator(load_linker(), store)
    if rag.is_ready():
        rag.get()   # يبني BM25/TF-IDF مرة واحدة عند الإقلاع
    yield

app = FastAPI(title="SmartDwa API", version="0.1", lifespan=lifespan)

class Msg(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

@app.get("/health")
def health():
    s = state["store"]
    return dict(status="ok", rag_chunks=len(rag.get().chunks) if rag.is_ready() else 0, drugs_master=len(s.master), ammps_rows=len(s.ammps), catalog_brands=len(s.catalog.brand_idx) if s.catalog else 0,
                interaction_pairs=len(s.pairs), rag_ready=rag.is_ready(),
                intent_model_ready=state["orch"].intent.ready, intent_model_error=state["orch"].intent.error,
                intent_backend=config.INTENT_BACKEND, intent_remote_error=state["orch"].intent.remote_error)

@app.post("/link")
def link(m: Msg):
    return state["orch"].link(m.message)

@app.post("/chat")
def chat(m: Msg):
    return state["orch"].chat(m.message)

@app.get("/catalog/search")
def catalog_search(q: str):
    cat = state["store"].catalog
    if cat is None:
        return []
    return [dict(kind=m["kind"], key=m["key"], exact=m["exact"], in_scope=cat.in_scope(m["rows"]),
                 **cat.presentations(m["rows"])) for m in cat.find(q)]

@app.post("/admin/reload")
def reload_data():
    state["store"].reload()
    return dict(status="reloaded", ammps_rows=len(state["store"].ammps))


class KeepAlive(BaseModel):
    value: str = Field(description="0, 30s, 5m, 30m, 2h ... (maximum 24h)")

@app.get("/admin/keepalive")
def get_keepalive():
    return dict(keep_alive=health_mod.get_keep_alive())

@app.post("/admin/keepalive")
def set_keepalive(k: KeepAlive):
    try:
        return dict(keep_alive=health_mod.set_keep_alive(k.value))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
