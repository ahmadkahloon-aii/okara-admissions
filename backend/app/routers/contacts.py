"""Contacts / leads router: list, detail, conversation, manual reply, simulator."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import Contact, Message, User
from ..auth import get_current_user
from ..schemas import ContactOut, ContactUpdate, MessageOut, SendMessageIn, SimulateIn, ImportContactIn, SendVoiceIn
from ..services import whatsapp, crm, conversation, voice
from ..data import catalog

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(q: str = "", stage: str = "", status_tag: str = "", program_code: str = "",
                  source: str = "", limit: int = Query(100, le=500),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Contact)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Contact.name.ilike(like), Contact.wa_id.ilike(like),
                                 Contact.contact_number.ilike(like), Contact.cnic.ilike(like)))
    if stage:
        query = query.filter(Contact.stage == stage)
    if status_tag:
        query = query.filter(Contact.status_tag == status_tag)
    if program_code:
        query = query.filter(Contact.program_code == program_code)
    if source:
        query = query.filter(Contact.source == source)
    return query.order_by(Contact.updated_at.desc()).limit(limit).all()


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Contact).get(contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    return c


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    c = db.query(Contact).get(contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("stage") and data["stage"] not in catalog.PIPELINE_STAGES:
        raise HTTPException(400, "Invalid stage")
    if data.get("status_tag") and data["status_tag"] not in catalog.STATUS_TAGS:
        raise HTTPException(400, "Invalid status tag")
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{contact_id}/messages")
def conversation_messages(contact_id: int, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    c = db.query(Contact).get(contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    msgs = (db.query(Message).filter(Message.contact_id == contact_id)
            .order_by(Message.created_at.asc()).all())
    return [{"id": m.id, "direction": m.direction, "type": m.type, "body": m.body,
             "status": m.status, "handled_by": m.handled_by,
             "created_at": m.created_at.isoformat() if m.created_at else None,
             "has_audio": bool(m.media_b64), "transcription": m.transcription or ""} for m in msgs]


@router.get("/audio/{message_id}")
def message_audio(message_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Return a stored voice note as a data URL the dashboard can play."""
    m = db.query(Message).get(message_id)
    if not m or not m.media_b64:
        raise HTTPException(404, "No audio for this message")
    mime = m.media_mime or "audio/ogg"
    return {"audio": f"data:{mime};base64,{m.media_b64}", "transcription": m.transcription or ""}


@router.post("/{contact_id}/send_voice")
def send_voice(contact_id: int, body: SendVoiceIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Counsellor sends a voice note (text is spoken via TTS, English or Urdu)."""
    c = db.query(Contact).get(contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    if body.language in ("en", "ur"):
        c.language = body.language
        db.commit()
    res = voice.send_voice_note(db, c, body.text, handled_by="human")
    if not res.get("ok"):
        detail = res.get("error") or "Voice send failed"
        raise HTTPException(400, detail if isinstance(detail, str) else str(detail))
    c.status_tag = "Human-Assigned"
    c.assigned_to = user.id
    db.commit()
    return {"ok": True}


@router.post("/{contact_id}/send", response_model=MessageOut)
def send_manual(contact_id: int, body: SendMessageIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Counsellor sends a manual WhatsApp message (takes over from AI)."""
    c = db.query(Contact).get(contact_id)
    if not c:
        raise HTTPException(404, "Contact not found")
    res = whatsapp.send_text(db, c.wa_id, body.text)
    c.status_tag = "Human-Assigned"
    c.assigned_to = user.id
    db.commit()
    m = crm.log_message(db, c, "out", body.text, handled_by="human",
                        wa_message_id=res.get("message_id", ""),
                        status="sent" if res.get("ok") else "failed")
    return m


@router.post("/import")
def import_contacts(items: list[ImportContactIn], db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Bulk upsert contacts from an uploaded list (does NOT trigger the bot).
    Imported contacts can then be targeted by bulk campaigns."""
    created = updated = skipped = 0
    for it in items:
        wa = "".join(ch for ch in (it.wa_id or "") if ch.isdigit())
        if not wa:
            skipped += 1
            continue
        c = db.query(Contact).filter(Contact.wa_id == wa).first()
        is_new = c is None
        if is_new:
            c = Contact(wa_id=wa, source=(it.source or "broadcast"), stage="Lead",
                        status_tag="AI-Handled", state="NEW", state_data={})
            db.add(c)
        if it.name:
            c.name = it.name
        if it.source:
            c.source = it.source
        if it.stage in catalog.PIPELINE_STAGES:
            c.stage = it.stage
        if it.percentage is not None:
            c.percentage = it.percentage
        if it.program:
            prog = catalog.program_by_name(it.program) or catalog.program_by_code(it.program)
            c.program_interest = prog["name"] if prog else it.program
            if prog:
                c.program_code = prog["code"]
                c.program_tag = prog["code"]
        db.commit()
        created += 1 if is_new else 0
        updated += 0 if is_new else 1
    return {"created": created, "updated": updated, "skipped": skipped, "total": len(items)}


@router.post("/simulate")
def simulate(body: SimulateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Drive the conversation engine without a live WhatsApp connection (for testing the flow)."""
    contact = crm.get_or_create_contact(db, body.wa_id, source=body.source)
    import datetime as _dt
    contact.last_inbound_at = _dt.datetime.utcnow()
    db.commit()
    inbound = {"type": "interactive" if body.interactive_id else "text",
               "text": body.text, "interactive_id": body.interactive_id}
    outbound = conversation.handle(db, contact, inbound)
    # strip non-serialisable delivery internals for the response
    clean = []
    for o in outbound:
        clean.append({"kind": o.get("kind"), "text": o.get("text"),
                      "buttons": o.get("buttons"), "sections": o.get("sections"),
                      "button": o.get("button")})
    return {"contact_id": contact.id, "state": contact.state, "stage": contact.stage,
            "outbound": clean}
