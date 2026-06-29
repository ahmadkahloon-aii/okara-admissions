"""WhatsApp Cloud API client: send text, interactive menus, and approved templates."""
import hashlib
import hmac
import httpx
from sqlalchemy.orm import Session
from ..config import get_setting


def _base_url(db: Session) -> str:
    version = get_setting(db, "GRAPH_API_VERSION", "v21.0")
    phone_id = get_setting(db, "WHATSAPP_PHONE_NUMBER_ID")
    return f"https://graph.facebook.com/{version}/{phone_id}/messages"


def _headers(db: Session) -> dict:
    token = get_setting(db, "WHATSAPP_TOKEN")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def is_configured(db: Session) -> bool:
    return bool(get_setting(db, "WHATSAPP_TOKEN") and get_setting(db, "WHATSAPP_PHONE_NUMBER_ID"))


def verify_signature(db: Session, body: bytes, signature_header: str) -> bool:
    """Validate X-Hub-Signature-256 against the app secret. If no secret set, allow."""
    app_secret = get_setting(db, "WHATSAPP_APP_SECRET")
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _post(db: Session, payload: dict) -> dict:
    if not is_configured(db):
        return {"ok": False, "error": "WhatsApp not configured. Add the token and phone number id in Settings."}
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(_base_url(db), headers=_headers(db), json=payload)
        data = r.json() if r.content else {}
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "error": data}
        msg_id = ""
        try:
            msg_id = data["messages"][0]["id"]
        except (KeyError, IndexError):
            pass
        return {"ok": True, "message_id": msg_id, "raw": data}
    except Exception as e:  # noqa
        return {"ok": False, "error": str(e)}


def send_text(db: Session, to: str, text: str, preview_url: bool = False) -> dict:
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to,
               "type": "text", "text": {"body": text[:4096], "preview_url": preview_url}}
    return _post(db, payload)


def send_buttons(db: Session, to: str, body: str, buttons: list, header: str = None, footer: str = None) -> dict:
    """buttons: list of {"id": str, "title": str} (max 3, title <=20 chars)."""
    action = {"buttons": [{"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                          for b in buttons[:3]]}
    interactive = {"type": "button", "body": {"text": body[:1024]}, "action": action}
    if header:
        interactive["header"] = {"type": "text", "text": header[:60]}
    if footer:
        interactive["footer"] = {"text": footer[:60]}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "interactive", "interactive": interactive}
    return _post(db, payload)


def send_list(db: Session, to: str, body: str, button_text: str, sections: list,
              header: str = None, footer: str = None) -> dict:
    """sections: list of {"title": str, "rows": [{"id","title","description"?}]} (row title <=24 chars)."""
    norm_sections = []
    for s in sections:
        rows = []
        for row in s["rows"]:
            r = {"id": row["id"], "title": row["title"][:24]}
            if row.get("description"):
                r["description"] = row["description"][:72]
            rows.append(r)
        norm_sections.append({"title": s.get("title", "")[:24], "rows": rows})
    interactive = {"type": "list", "body": {"text": body[:1024]},
                   "action": {"button": button_text[:20], "sections": norm_sections}}
    if header:
        interactive["header"] = {"type": "text", "text": header[:60]}
    if footer:
        interactive["footer"] = {"text": footer[:60]}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "interactive", "interactive": interactive}
    return _post(db, payload)


def send_template(db: Session, to: str, template_name: str, language: str = "en_US",
                  body_params: list = None, header_param: dict = None) -> dict:
    """Send an approved template. body_params: list of strings for {{1}}, {{2}} ... """
    components = []
    if header_param:
        components.append({"type": "header", "parameters": [header_param]})
    if body_params:
        components.append({"type": "body",
                           "parameters": [{"type": "text", "text": str(p)} for p in body_params]})
    template = {"name": template_name, "language": {"code": language}}
    if components:
        template["components"] = components
    payload = {"messaging_product": "whatsapp", "to": to, "type": "template", "template": template}
    return _post(db, payload)


def mark_read(db: Session, message_id: str) -> dict:
    payload = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
    return _post(db, payload)
