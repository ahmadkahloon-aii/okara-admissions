"""High-level voice helpers: turn text into a WhatsApp voice note and log it."""
import base64
from sqlalchemy.orm import Session
from . import media, openai_service, crm


def send_voice_note(db: Session, contact, text: str, handled_by: str = "ai") -> dict:
    """Synthesize `text` to speech, send it as a WhatsApp voice note, and log it.
    Returns {ok, error?}. Requires the OpenAI key (TTS) and WhatsApp config."""
    if not text or not text.strip():
        return {"ok": False, "error": "empty text"}
    audio, mime = openai_service.synthesize(db, text)
    if not audio:
        return {"ok": False, "error": "Voice generation unavailable (add the OpenAI key in Settings)."}
    media_id = media.upload_media(db, audio, mime)
    if not media_id:
        return {"ok": False, "error": "Could not upload audio to WhatsApp (check the WhatsApp token)."}
    res = media.send_audio(db, contact.wa_id, media_id)
    b64 = base64.b64encode(audio).decode("ascii")
    crm.log_message(db, contact, "out", text, mtype="audio", handled_by=handled_by,
                    wa_message_id=res.get("message_id", ""),
                    status="sent" if res.get("ok") else "failed",
                    media_b64=b64, media_mime=mime, transcription=text, media_id=media_id)
    return {"ok": res.get("ok", False), "error": res.get("error")}
