"""Dashboard router: pipeline funnel, counts and recent activity."""
import datetime as dt
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Contact, Message, Campaign, Appointment, User
from ..auth import get_current_user
from ..data import catalog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_contacts = db.query(Contact).count()
    by_stage = {s: 0 for s in catalog.PIPELINE_STAGES}
    for stage, count in db.query(Contact.stage, func.count(Contact.id)).group_by(Contact.stage):
        by_stage[stage] = count
    by_status = {}
    for tag, count in db.query(Contact.status_tag, func.count(Contact.id)).group_by(Contact.status_tag):
        by_status[tag] = count
    by_program = []
    for code, count in (db.query(Contact.program_code, func.count(Contact.id))
                        .filter(Contact.program_code != "")
                        .group_by(Contact.program_code)
                        .order_by(func.count(Contact.id).desc()).limit(10)):
        by_program.append({"program_code": code, "count": count})
    by_source = {}
    for src, count in db.query(Contact.source, func.count(Contact.id)).group_by(Contact.source):
        by_source[src] = count

    since = dt.datetime.utcnow() - dt.timedelta(days=7)
    msgs_in = db.query(Message).filter(Message.direction == "in", Message.created_at >= since).count()
    msgs_out = db.query(Message).filter(Message.direction == "out", Message.created_at >= since).count()

    return {
        "total_contacts": total_contacts,
        "needs_human": by_status.get("Human-Required", 0),
        "pipeline": [{"stage": s, "count": by_stage[s]} for s in catalog.PIPELINE_STAGES],
        "by_status": by_status,
        "by_program": by_program,
        "by_source": by_source,
        "messages_7d": {"in": msgs_in, "out": msgs_out},
        "campaigns": db.query(Campaign).count(),
        "appointments": db.query(Appointment).count(),
    }


@router.get("/appointments")
def appointments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Appointment).order_by(Appointment.created_at.desc()).limit(100).all()
    return [{"id": a.id, "name": a.name, "contact_number": a.contact_number,
             "program": a.program, "slot": a.slot, "status": a.status,
             "created_at": a.created_at} for a in rows]
