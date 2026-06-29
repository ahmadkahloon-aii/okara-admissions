"""Retrieval over the knowledge base. Uses OpenAI embeddings when available,
otherwise a keyword-overlap fallback so the assistant still works without a key."""
import math
import re
from sqlalchemy.orm import Session
from ..models import KBChunk
from ..config import get_setting


def _openai_client(db: Session):
    key = get_setting(db, "OPENAI_API_KEY")
    provider = get_setting(db, "AI_PROVIDER", "openai")
    if provider != "openai" or not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:  # noqa
        return None


def embed_text(db: Session, text: str):
    client = _openai_client(db)
    if not client:
        return None
    model = get_setting(db, "OPENAI_EMBED_MODEL", "text-embedding-3-small")
    try:
        resp = client.embeddings.create(model=model, input=text[:8000])
        return resp.data[0].embedding
    except Exception:  # noqa
        return None


def chunk_markdown(md: str):
    """Split KB markdown into retrievable chunks by heading."""
    chunks = []
    current_title = "Knowledge Base"
    buf = []
    for line in md.splitlines():
        if re.match(r"^#{1,3}\s+", line):
            if buf and any(b.strip() for b in buf):
                chunks.append((current_title, "\n".join(buf).strip()))
            current_title = re.sub(r"^#{1,3}\s+", "", line).strip()
            buf = [line]
        else:
            buf.append(line)
    if buf and any(b.strip() for b in buf):
        chunks.append((current_title, "\n".join(buf).strip()))
    # split very long chunks further on blank lines / Q. markers
    out = []
    for title, content in chunks:
        if len(content) <= 1200:
            out.append((title, content))
            continue
        parts = re.split(r"\n(?=Q\.\s)", content)
        acc = ""
        for part in parts:
            if len(acc) + len(part) > 1200 and acc:
                out.append((title, acc.strip()))
                acc = part
            else:
                acc += "\n" + part
        if acc.strip():
            out.append((title, acc.strip()))
    return out


def reindex(db: Session, md: str) -> int:
    """Rebuild the KB index from markdown. Returns chunk count."""
    db.query(KBChunk).delete()
    db.commit()
    count = 0
    for title, content in chunk_markdown(md):
        emb = embed_text(db, f"{title}\n{content}")
        db.add(KBChunk(title=title, content=content, embedding=emb))
        count += 1
    db.commit()
    return count


def _cosine(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _keyword_score(query, text):
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    t = re.findall(r"[a-z0-9]+", text.lower())
    if not q or not t:
        return 0.0
    tset = set(t)
    overlap = sum(1 for w in q if w in tset)
    return overlap / len(q)


def retrieve(db: Session, query: str, k: int = 4) -> list:
    chunks = db.query(KBChunk).all()
    if not chunks:
        return []
    q_emb = embed_text(db, query)
    scored = []
    for c in chunks:
        if q_emb and c.embedding:
            score = _cosine(q_emb, c.embedding)
        else:
            score = _keyword_score(query, c.title + " " + c.content)
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"title": c.title, "content": c.content, "score": round(s, 3)} for s, c in scored[:k]]
