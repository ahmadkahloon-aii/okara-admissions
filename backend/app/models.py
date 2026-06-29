"""ORM models for the admissions platform."""
import datetime as dt
from sqlalchemy import (Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON)
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return dt.datetime.utcnow()


class User(Base):
    """Dashboard user (admin / counsellor)."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, default="")
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="admin")  # admin | counsellor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class Setting(Base):
    """Key/value settings (API keys, business config) editable from the dashboard."""
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, default="")
    is_secret = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Contact(Base):
    """A WhatsApp lead / applicant."""
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    wa_id = Column(String, unique=True, index=True, nullable=False)  # WhatsApp phone number id (E.164 w/o +)
    name = Column(String, default="")
    cnic = Column(String, default="")
    father_name = Column(String, default="")
    program_interest = Column(String, default="")
    program_code = Column(String, default="")
    contact_number = Column(String, default="")
    percentage = Column(Float, nullable=True)
    language = Column(String, default="en")  # en | ur
    source = Column(String, default="whatsapp")  # whatsapp | meta_ad | broadcast
    stage = Column(String, default="Lead")
    status_tag = Column(String, default="AI-Handled")
    program_tag = Column(String, default="")
    scholarship_note = Column(String, default="")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    state = Column(String, default="NEW")        # conversation FSM state
    state_data = Column(JSON, default=dict)        # transient slot data
    last_inbound_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), index=True)
    direction = Column(String)  # in | out
    type = Column(String, default="text")  # text | interactive | template | image | audio | system
    body = Column(Text, default="")
    payload = Column(JSON, nullable=True)
    wa_message_id = Column(String, default="")
    status = Column(String, default="")  # sent | delivered | read | failed
    handled_by = Column(String, default="ai")  # ai | human | system
    media_id = Column(String, default="")        # WhatsApp media id (audio/image)
    media_b64 = Column(Text, nullable=True)        # stored audio bytes (base64) for playback
    media_mime = Column(String, default="")        # e.g. audio/ogg
    transcription = Column(Text, default="")        # speech-to-text of a voice note / text spoken
    created_at = Column(DateTime, default=utcnow, index=True)

    contact = relationship("Contact", back_populates="messages")


class Template(Base):
    """Meta-approved message template registered in the dashboard."""
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)   # exact Meta template name
    language = Column(String, default="en")
    category = Column(String, default="MARKETING")
    body_preview = Column(Text, default="")
    variables = Column(Integer, default=0)               # number of {{n}} body variables
    header_type = Column(String, default="none")         # none | text | image
    status = Column(String, default="APPROVED")
    created_at = Column(DateTime, default=utcnow)


class Campaign(Base):
    """A bulk template send."""
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    template_name = Column(String, nullable=False)
    language = Column(String, default="en")
    audience_filter = Column(JSON, default=dict)   # {stage, program_code, status_tag}
    variables = Column(JSON, default=list)          # default body variable values
    status = Column(String, default="draft")        # draft | running | completed | failed
    total = Column(Integer, default=0)
    sent = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), index=True)
    name = Column(String, default="")
    contact_number = Column(String, default="")
    program = Column(String, default="")
    slot = Column(String, default="")        # e.g. "2026-07-10 11:00"
    status = Column(String, default="requested")  # requested | confirmed | done | cancelled
    note = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class KBChunk(Base):
    """A chunk of the knowledge base with its embedding for RAG."""
    __tablename__ = "kb_chunks"
    id = Column(Integer, primary_key=True)
    title = Column(String, default="")
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # list[float] or null (keyword fallback)
    created_at = Column(DateTime, default=utcnow)
