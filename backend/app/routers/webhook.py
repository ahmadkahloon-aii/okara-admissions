"""WhatsApp Cloud API webhook: GET verification + POST message receipt."""
import base64
import datetime as dt
from fastapi import APIRouter, Request, Depends, Response, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_setting
from ..services import whatsapp, crm, conversation, media, voice, openai_service

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
def verify(request: Request,
           hub_mode: str = Query(None, alias="hub.mode"),
           hub_challenge: str = Query(None, alias="hub.challenge"),
           hub_verify_token: str = Query(None, alias="hub.verify_token"),
           db: Session = Depends(get_db)):
    """Meta calls this to verify the webhook. Echo the challenge if the token matches."""
    verify_token = get_setting(db, "WHATSAPP_VERIFY_TOKEN")
    if hub_mode == "subscribe" and hub_verify_token and hub_verify_token == verify_token:
        return Response(content=hub_challenge or "", media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


def _parse_inbound(message: dict) -> dict:
    """Normalise a WhatsApp inbound message into our internal shape."""
    mtype = message.get("type", "text")
    out = {"type": mtype, "text": None, "interactive_id": None, "interactive_title": None,
           "wa_message_id": message.get("id", "")}
    if mtype == "text":
        out["text"] = message.get("text", {}).get("body", "")
    elif mtype == "interactive":
        inter = message.get("interactive", {})
        if inter.get("type") == "button_reply":
            out["interactive_id"] = inter["button_reply"]["id"]
            out["interactive_title"] = inter["button_reply"].get("title", "")
        elif inter.get("type") == "list_reply":
            out["interactive_id"] = inter["list_reply"]["id"]
            out["interactive_title"] = inter["list_reply"].get("title", "")
    elif mtype == "button":  # template quick-reply button
        out["text"] = message.get("button", {}).get("text", "")
    elif mtype in ("audio", "voice"):
        node = message.get("audio") or message.get("voice") or {}
        out["type"] = "audio"
        out["media_id"] = node.get("id", "")
        out["text"] = ""  # filled in after transcription
    elif mtype in ("image", "video", "document"):
        out["type"] = mtype
        out["text"] = message.get(mtype, {}).get("caption", "") or f"[{mtype} received]"
    else:
        out["text"] = "[unsupported message]"
    return out


@router.post("")
async def receive(request: Request, db: Session = Depends(get_db)):
    """Receive inbound messages and run the conversation engine."""
    raw = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not whatsapp.verify_signature(db, raw, signature):
        return Response(content="invalid signature", status_code=403)

    data = await request.json()
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                # status callbacks (delivered / read / failed)
                for st in value.get("statuses", []):
                    _handle_status(db, st)
                # contact profile names
                profiles = {c["wa_id"]: c.get("profile", {}).get("name", "")
                            for c in value.get("contacts", [])}
                for message in value.get("messages", []):
                    wa_id = message.get("from")
                    if not wa_id:
                        continue
                    name = profiles.get(wa_id, "")
                    # detect Click-to-WhatsApp ad referral -> land on Programs menu
                    referral = message.get("referral") or value.get("referral")
                    source = "meta_ad" if referral else "whatsapp"
                    contact = crm.get_or_create_contact(db, wa_id, name, source=source)
                    contact.last_inbound_at = dt.datetime.utcnow()
                    db.commit()
                    inbound = _parse_inbound(message)
                    # mark read (best effort)
                    if inbound.get("wa_message_id"):
                        whatsapp.mark_read(db, inbound["wa_message_id"])
                    # ad referral: jump straight into programs menu on first touch
                    if referral and contact.state in ("NEW", "MAIN_MENU"):
                        conversation.show_programs_menu(
                            db, contact, intro="Welcome! Here are our programs - tap to explore:")
                    elif inbound.get("type") == "audio":
                        _handle_voice(db, contact, inbound)
                    else:
                        conversation.handle(db, contact, inbound)
    except Exception as e:  # noqa - never 500 to Meta, or it retries forever
        print("Webhook processing error:", e)
    return {"status": "ok"}


def _handle_voice(db: Session, contact, inbound: dict):
    """Inbound voice note: download, transcribe, run the engine, and reply with voice."""
    audio_bytes, mime = media.download_media(db, inbound.get("media_id"))
    if audio_bytes:
        inbound["media_b64"] = base64.b64encode(audio_bytes).decode("ascii")
        inbound["media_mime"] = mime
        txt = openai_service.transcribe(db, audio_bytes, mime, contact.language)
        inbound["transcription"] = txt or ""
        inbound["text"] = txt or ""

    if not inbound.get("text"):
        # couldn't transcribe (no OpenAI key, or download failed): store + escalate
        crm.log_message(db, contact, "in", "[voice note received]", mtype="audio",
                        payload={k: v for k, v in inbound.items() if k != "media_b64"},
                        media_b64=inbound.get("media_b64"), media_mime=inbound.get("media_mime", ""),
                        media_id=inbound.get("media_id", ""))
        crm.assign_to_human(db, contact)
        conversation._dispatch(db, contact, "text",
                               text=("I've received your voice note. A counsellor will listen and reply "
                                     "shortly \u2014 or please type your question and I can help right away."))
        return

    outs = conversation.handle(db, contact, inbound)
    # reply to a voice note with voice (for plain-text answers; menus stay as buttons)
    if get_setting(db, "VOICE_REPLIES", "on") == "on":
        for o in outs:
            if o.get("kind") == "text" and o.get("text"):
                voice.send_voice_note(db, contact, o["text"])


def _handle_status(db: Session, st: dict):
    from ..models import Message
    msg_id = st.get("id")
    status = st.get("status")
    if not msg_id:
        return
    m = db.query(Message).filter(Message.wa_message_id == msg_id).first()
    if m:
        m.status = status or m.status
        db.commit()
