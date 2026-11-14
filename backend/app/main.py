from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel, Field
from . import rag
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
                interaction_pairs=len(s.pairs), rag_ready=rag.is_ready())

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
