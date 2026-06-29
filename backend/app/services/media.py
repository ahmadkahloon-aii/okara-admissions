"""WhatsApp media handling: download inbound voice notes, upload + send outbound audio."""
import httpx
from sqlalchemy.orm import Session
from ..config import get_setting


def _token(db: Session) -> str:
    return get_setting(db, "WHATSAPP_TOKEN")


def _version(db: Session) -> str:
    return get_setting(db, "GRAPH_API_VERSION", "v21.0")


def download_media(db: Session, media_id: str):
    """Resolve a WhatsApp media id to raw bytes. Returns (bytes, mime) or (None, None)."""
    token = _token(db)
    if not token or not media_id:
        return None, None
    try:
        with httpx.Client(timeout=60) as client:
            meta = client.get(f"https://graph.facebook.com/{_version(db)}/{media_id}",
                              headers={"Authorization": f"Bearer {token}"})
            if meta.status_code >= 400:
                return None, None
            info = meta.json()
            url = info.get("url")
            mime = info.get("mime_type", "audio/ogg")
            if not url:
                return None, None
            blob = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if blob.status_code >= 400:
                return None, None
            return blob.content, mime
    except Exception:  # noqa
        return None, None


def upload_media(db: Session, audio_bytes: bytes, mime: str = "audio/ogg",
                 filename: str = "voice.ogg"):
    """Upload audio to WhatsApp; returns a media id or None."""
    token = _token(db)
    phone_id = get_setting(db, "WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_id or not audio_bytes:
        return None
    try:
        with httpx.Client(timeout=60) as client:
            r = client.post(
                f"https://graph.facebook.com/{_version(db)}/{phone_id}/media",
                headers={"Authorization": f"Bearer {token}"},
                data={"messaging_product": "whatsapp", "type": mime},
                files={"file": (filename, audio_bytes, mime)},
            )
        if r.status_code >= 400:
            return None
        return r.json().get("id")
    except Exception:  # noqa
        return None


def send_audio(db: Session, to: str, media_id: str) -> dict:
    """Send an audio message (OGG/Opus shows as a voice note)."""
    token = _token(db)
    phone_id = get_setting(db, "WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_id or not media_id:
        return {"ok": False, "error": "audio not configured"}
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual",
               "to": to, "type": "audio", "audio": {"id": media_id}}
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(f"https://graph.facebook.com/{_version(db)}/{phone_id}/messages",
                            headers={"Authorization": f"Bearer {token}",
                                     "Content-Type": "application/json"}, json=payload)
        data = r.json() if r.content else {}
        if r.status_code >= 400:
            return {"ok": False, "error": data}
        mid = ""
        try:
            mid = data["messages"][0]["id"]
        except (KeyError, IndexError):
            pass
        return {"ok": True, "message_id": mid}
    except Exception as e:  # noqa
        return {"ok": False, "error": str(e)}
