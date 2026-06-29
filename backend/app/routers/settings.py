"""Settings router: read/update API keys + business config; test connections."""
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth import get_current_user
from ..config import all_settings, set_setting, get_setting
from ..schemas import SettingsUpdate
from ..services import whatsapp

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"settings": all_settings(db, reveal_secrets=False)}


@router.put("")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    for key, value in body.settings.items():
        # ignore masked placeholders so we don't overwrite secrets with ****
        if value and value.startswith("********"):
            continue
        set_setting(db, key, value)
    return {"settings": all_settings(db, reveal_secrets=False), "saved": True}


@router.post("/test/whatsapp")
def test_whatsapp(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not whatsapp.is_configured(db):
        return {"ok": False, "detail": "Missing WhatsApp token or phone number id."}
    version = get_setting(db, "GRAPH_API_VERSION", "v21.0")
    phone_id = get_setting(db, "WHATSAPP_PHONE_NUMBER_ID")
    token = get_setting(db, "WHATSAPP_TOKEN")
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(f"https://graph.facebook.com/{version}/{phone_id}",
                           headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        if r.status_code >= 400:
            return {"ok": False, "detail": data.get("error", data)}
        return {"ok": True, "detail": {"verified_name": data.get("verified_name"),
                                       "display_phone_number": data.get("display_phone_number")}}
    except Exception as e:  # noqa
        return {"ok": False, "detail": str(e)}


@router.post("/test/openai")
def test_openai(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    key = get_setting(db, "OPENAI_API_KEY")
    if not key:
        return {"ok": False, "detail": "No OpenAI API key set."}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        model = get_setting(db, "OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Reply with the word OK."}],
            max_tokens=5)
        return {"ok": True, "detail": resp.choices[0].message.content.strip()}
    except Exception as e:  # noqa
        return {"ok": False, "detail": str(e)}
