"""Runtime configuration. Secrets and business config live in the DB (Setting table)
so they can be edited from the dashboard; bootstrap defaults come from the environment."""
import os
from sqlalchemy.orm import Session
from .models import Setting

# settings that the dashboard manages. (key, is_secret, default_env)
MANAGED_SETTINGS = [
    ("WHATSAPP_TOKEN", True, "WHATSAPP_TOKEN"),
    ("WHATSAPP_PHONE_NUMBER_ID", False, "WHATSAPP_PHONE_NUMBER_ID"),
    ("WHATSAPP_BUSINESS_ACCOUNT_ID", False, "WHATSAPP_BUSINESS_ACCOUNT_ID"),
    ("WHATSAPP_VERIFY_TOKEN", True, "WHATSAPP_VERIFY_TOKEN"),
    ("WHATSAPP_APP_SECRET", True, "WHATSAPP_APP_SECRET"),
    ("GRAPH_API_VERSION", False, "GRAPH_API_VERSION"),
    ("OPENAI_API_KEY", True, "OPENAI_API_KEY"),
    ("OPENAI_MODEL", False, "OPENAI_MODEL"),
    ("OPENAI_EMBED_MODEL", False, "OPENAI_EMBED_MODEL"),
    ("OPENAI_TTS_MODEL", False, "OPENAI_TTS_MODEL"),
    ("OPENAI_TTS_VOICE", False, "OPENAI_TTS_VOICE"),
    ("OPENAI_STT_MODEL", False, "OPENAI_STT_MODEL"),
    ("VOICE_REPLIES", False, "VOICE_REPLIES"),            # on | off : AI replies to voice with voice
    ("AI_PROVIDER", False, "AI_PROVIDER"),                 # openai | none
    ("BUSINESS_NAME", False, "BUSINESS_NAME"),
    ("DEFAULT_LANGUAGE", False, "DEFAULT_LANGUAGE"),
]

DEFAULTS = {
    "GRAPH_API_VERSION": "v21.0",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_EMBED_MODEL": "text-embedding-3-small",
    "OPENAI_TTS_MODEL": "tts-1",
    "OPENAI_TTS_VOICE": "alloy",
    "OPENAI_STT_MODEL": "whisper-1",
    "VOICE_REPLIES": "on",
    "AI_PROVIDER": "openai",
    "BUSINESS_NAME": "Superior University Okara Campus",
    "DEFAULT_LANGUAGE": "en",
}


def ensure_settings(db: Session):
    """Create any missing managed settings, seeding from env or defaults."""
    for key, is_secret, env_key in MANAGED_SETTINGS:
        existing = db.query(Setting).filter(Setting.key == key).first()
        if not existing:
            value = os.getenv(env_key, DEFAULTS.get(key, ""))
            db.add(Setting(key=key, value=value, is_secret=is_secret))
    db.commit()


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row and row.value:
        return row.value
    return os.getenv(key, DEFAULTS.get(key, default))


def set_setting(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        is_secret = any(k == key and s for k, s, _ in MANAGED_SETTINGS)
        db.add(Setting(key=key, value=value, is_secret=is_secret))
    db.commit()


def all_settings(db: Session, reveal_secrets: bool = False) -> list:
    ensure_settings(db)
    out = []
    for row in db.query(Setting).order_by(Setting.key).all():
        value = row.value
        if row.is_secret and not reveal_secrets and value:
            value = "********" + value[-4:] if len(value) > 4 else "********"
        out.append({"key": row.key, "value": value, "is_secret": row.is_secret,
                    "configured": bool(row.value)})
    return out


# JWT / app secret (process-level, from env)
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production-please")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
