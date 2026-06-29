"""Campaigns router: build an audience and send a Meta-approved template in bulk."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import Campaign, Contact, Template, User
from ..auth import get_current_user
from ..schemas import CampaignIn, CampaignOut
from ..services import whatsapp, crm

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _audience_query(db: Session, flt: dict):
    q = db.query(Contact)
    if flt.get("stage"):
        q = q.filter(Contact.stage == flt["stage"])
    if flt.get("status_tag"):
        q = q.filter(Contact.status_tag == flt["status_tag"])
    if flt.get("program_code"):
        q = q.filter(Contact.program_code == flt["program_code"])
    if flt.get("source"):
        q = q.filter(Contact.source == flt["source"])
    return q


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@router.post("/preview")
def preview_audience(body: CampaignIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    count = _audience_query(db, body.audience_filter).count()
    sample = [{"name": c.name, "wa_id": c.wa_id}
              for c in _audience_query(db, body.audience_filter).limit(5).all()]
    return {"audience_size": count, "sample": sample}


def _run_campaign(campaign_id: int):
    """Background worker: send the template to every audience member."""
    db = SessionLocal()
    try:
        camp = db.query(Campaign).get(campaign_id)
        if not camp:
            return
        camp.status = "running"
        db.commit()
        contacts = _audience_query(db, camp.audience_filter or {}).all()
        camp.total = len(contacts)
        db.commit()
        for c in contacts:
            res = whatsapp.send_template(db, c.wa_id, camp.template_name, camp.language,
                                         body_params=camp.variables or None)
            if res.get("ok"):
                camp.sent += 1
                crm.log_message(db, c, "out", f"[template: {camp.template_name}]",
                                mtype="template", wa_message_id=res.get("message_id", ""),
                                handled_by="system", status="sent")
                if c.source == "broadcast" and c.stage == "Lead":
                    pass
            else:
                camp.failed += 1
                crm.log_message(db, c, "out", f"[template failed: {camp.template_name}]",
                                mtype="template", handled_by="system", status="failed",
                                payload={"error": res.get("error")})
            db.commit()
        camp.status = "completed"
        camp.completed_at = dt.datetime.utcnow()
        db.commit()
    except Exception as e:  # noqa
        camp = db.query(Campaign).get(campaign_id)
        if camp:
            camp.status = "failed"
            db.commit()
        print("Campaign error:", e)
    finally:
        db.close()


@router.post("", response_model=CampaignOut)
def create_and_send(body: CampaignIn, background: BackgroundTasks,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not whatsapp.is_configured(db):
        raise HTTPException(400, "Configure WhatsApp in Settings before sending campaigns.")
    if not db.query(Template).filter(Template.name == body.template_name).first():
        raise HTTPException(400, "Register the template first under Templates.")
    camp = Campaign(name=body.name, template_name=body.template_name, language=body.language,
                    audience_filter=body.audience_filter, variables=body.variables,
                    status="queued", created_by=user.id)
    db.add(camp)
    db.commit()
    db.refresh(camp)
    background.add_task(_run_campaign, camp.id)
    return camp


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    camp = db.query(Campaign).get(campaign_id)
    if not camp:
        raise HTTPException(404, "Campaign not found")
    return camp
