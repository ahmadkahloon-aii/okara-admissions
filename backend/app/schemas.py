"""Pydantic schemas for API requests/responses."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import datetime as dt


class LoginIn(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    class Config:
        from_attributes = True


class SettingIn(BaseModel):
    key: str
    value: str


class SettingsUpdate(BaseModel):
    settings: Dict[str, str]


class ContactOut(BaseModel):
    id: int
    wa_id: str
    name: str
    cnic: str
    father_name: str
    program_interest: str
    program_code: str
    contact_number: str
    percentage: Optional[float]
    language: str
    source: str
    stage: str
    status_tag: str
    program_tag: str
    scholarship_note: str
    state: str
    last_inbound_at: Optional[dt.datetime]
    created_at: dt.datetime
    class Config:
        from_attributes = True


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    stage: Optional[str] = None
    status_tag: Optional[str] = None
    assigned_to: Optional[int] = None
    program_code: Optional[str] = None


class MessageOut(BaseModel):
    id: int
    direction: str
    type: str
    body: str
    status: str
    handled_by: str
    created_at: dt.datetime
    class Config:
        from_attributes = True


class SendMessageIn(BaseModel):
    text: str
    handled_by: str = "human"


class SendVoiceIn(BaseModel):
    text: str
    language: Optional[str] = None  # en | ur (hint only)


class SimulateIn(BaseModel):
    wa_id: str = "test-user"
    text: Optional[str] = None
    interactive_id: Optional[str] = None
    source: str = "whatsapp"


class ImportContactIn(BaseModel):
    wa_id: str
    name: str = ""
    program: str = ""
    percentage: Optional[float] = None
    source: str = "broadcast"
    stage: str = "Lead"


class TemplateIn(BaseModel):
    name: str
    language: str = "en_US"
    category: str = "MARKETING"
    body_preview: str = ""
    variables: int = 0
    header_type: str = "none"


class TemplateOut(TemplateIn):
    id: int
    status: str
    class Config:
        from_attributes = True


class CampaignIn(BaseModel):
    name: str
    template_name: str
    language: str = "en_US"
    audience_filter: Dict[str, Any] = {}
    variables: List[str] = []


class CampaignOut(BaseModel):
    id: int
    name: str
    template_name: str
    language: str
    status: str
    total: int
    sent: int
    failed: int
    created_at: dt.datetime
    class Config:
        from_attributes = True


class KBReindexIn(BaseModel):
    content: Optional[str] = None  # if omitted, use bundled knowledge_base.md
