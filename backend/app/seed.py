"""Idempotent seed: default admin user, example Meta templates, and KB index build."""
import os
from sqlalchemy.orm import Session
from .models import User, Template, KBChunk
from .auth import hash_password
from .config import ensure_settings
from .services import rag

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@okara.superior.edu.pk")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "OkaraAdmin@2026")

KB_PATH = os.path.join(os.path.dirname(__file__), "data", "knowledge_base.md")

EXAMPLE_TEMPLATES = [
    {"name": "okara_admissions_open_2026", "language": "en_US", "category": "MARKETING",
     "body_preview": "Assalam-o-Alaikum {{1}}! Admissions for Fall 2026 at Superior University Okara are now open. "
                     "Reply to explore programs, scholarships and eligibility.", "variables": 1},
    {"name": "okara_scholarship_reminder", "language": "en_US", "category": "MARKETING",
     "body_preview": "Hello {{1}}, merit scholarships up to 100% are available at Superior University Okara "
                     "for Fall 2026. Reply SCHOLARSHIP to check your maximum waiver.", "variables": 1},
    {"name": "okara_appointment_followup", "language": "en_US", "category": "UTILITY",
     "body_preview": "Hi {{1}}, this is a reminder about your admissions appointment at Superior University "
                     "Okara. Reply here if you need to reschedule.", "variables": 1},
]


def seed_admin(db: Session):
    if not db.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL.lower()).first():
        db.add(User(email=DEFAULT_ADMIN_EMAIL.lower(), name="Okara Admin",
                    hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD), role="admin"))
        db.commit()
        print(f"[seed] created admin user: {DEFAULT_ADMIN_EMAIL}")


def seed_templates(db: Session):
    for t in EXAMPLE_TEMPLATES:
        if not db.query(Template).filter(Template.name == t["name"]).first():
            db.add(Template(status="APPROVED", **t))
    db.commit()


def seed_kb(db: Session):
    """Build the KB index if empty."""
    if db.query(KBChunk).count() == 0 and os.path.exists(KB_PATH):
        with open(KB_PATH, "r", encoding="utf-8") as f:
            md = f.read()
        count = rag.reindex(db, md)
        print(f"[seed] indexed {count} KB chunks")


def run_seed(db: Session):
    ensure_settings(db)
    seed_admin(db)
    seed_templates(db)
    seed_kb(db)
