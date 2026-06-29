"""Knowledge base router: view chunks, reindex (re-embed) the KB, and test retrieval."""
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import KBChunk, User
from ..auth import get_current_user
from ..schemas import KBReindexIn
from ..services import rag

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base.md")


def _load_bundled() -> str:
    with open(os.path.abspath(KB_PATH), "r", encoding="utf-8") as f:
        return f.read()


@router.get("")
def list_chunks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chunks = db.query(KBChunk).all()
    return {"count": len(chunks),
            "embedded": sum(1 for c in chunks if c.embedding),
            "chunks": [{"id": c.id, "title": c.title,
                        "preview": c.content[:160], "has_embedding": bool(c.embedding)}
                       for c in chunks]}


@router.get("/raw")
def raw_kb(user: User = Depends(get_current_user)):
    return {"content": _load_bundled()}


@router.post("/reindex")
def reindex(body: KBReindexIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    content = body.content if body.content else _load_bundled()
    if body.content:  # persist edited KB back to disk
        with open(os.path.abspath(KB_PATH), "w", encoding="utf-8") as f:
            f.write(body.content)
    count = rag.reindex(db, content)
    embedded = db.query(KBChunk).filter(KBChunk.embedding.isnot(None)).count()
    return {"reindexed": count, "embedded": embedded,
            "mode": "embeddings" if embedded else "keyword-fallback"}


@router.get("/search")
def search(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"results": rag.retrieve(db, q, k=4)}
