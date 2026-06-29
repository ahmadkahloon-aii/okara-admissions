"""CRM helpers: lifecycle stages, tags, and lead detail capture."""
from sqlalchemy.orm import Session
from ..models import Contact, Message
from ..data import catalog


def get_or_create_contact(db: Session, wa_id: str, name: str = "", source: str = "whatsapp") -> Contact:
    c = db.query(Contact).filter(Contact.wa_id == wa_id).first()
    if not c:
        c = Contact(wa_id=wa_id, name=name or "", source=source, stage="Lead",
                    status_tag="AI-Handled", state="NEW", state_data={})
        db.add(c)
        db.commit()
        db.refresh(c)
    elif name and not c.name:
        c.name = name
        db.commit()
    return c


def log_message(db: Session, contact: Contact, direction: str, body: str,
                mtype: str = "text", payload: dict = None, wa_message_id: str = "",
                handled_by: str = "ai", status: str = "", media_b64: str = None,
                media_mime: str = "", transcription: str = "", media_id: str = "") -> Message:
    m = Message(contact_id=contact.id, direction=direction, type=mtype, body=body or "",
                payload=payload, wa_message_id=wa_message_id, handled_by=handled_by, status=status,
                media_b64=media_b64, media_mime=media_mime or "", transcription=transcription or "",
                media_id=media_id or "")
    db.add(m)
    db.commit()
    return m


def set_stage(db: Session, contact: Contact, stage: str):
    if stage in catalog.PIPELINE_STAGES:
        contact.stage = stage
        db.commit()


def set_status(db: Session, contact: Contact, status_tag: str):
    if status_tag in catalog.STATUS_TAGS:
        contact.status_tag = status_tag
        db.commit()


def set_state(db: Session, contact: Contact, state: str, data: dict = None):
    contact.state = state
    if data is not None:
        contact.state_data = data
    db.commit()


def update_state_data(db: Session, contact: Contact, **kwargs):
    data = dict(contact.state_data or {})
    data.update(kwargs)
    contact.state_data = data
    db.commit()


def apply_lead_details(db: Session, contact: Contact, details: dict):
    """Save captured form details and tag the program."""
    if details.get("name"):
        contact.name = details["name"]
    if details.get("cnic"):
        contact.cnic = details["cnic"]
    if details.get("father_name"):
        contact.father_name = details["father_name"]
    if details.get("contact_number"):
        contact.contact_number = details["contact_number"]
    if details.get("program"):
        contact.program_interest = details["program"]
        prog = catalog.program_by_name(details["program"]) or catalog.program_by_code(details["program"])
        if prog:
            contact.program_code = prog["code"]
            contact.program_tag = prog["code"]
    # capturing details qualifies the lead
    if contact.stage == "Lead":
        contact.stage = "Qualified Lead"
    db.commit()


def assign_to_human(db: Session, contact: Contact):
    contact.status_tag = "Human-Required"
    db.commit()
