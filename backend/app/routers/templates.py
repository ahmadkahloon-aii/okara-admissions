"""Templates router: register Meta-approved templates used for campaigns."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Template, User
from ..auth import get_current_user
from ..schemas import TemplateIn, TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Template).order_by(Template.created_at.desc()).all()


@router.post("", response_model=TemplateOut)
def create_template(body: TemplateIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if db.query(Template).filter(Template.name == body.name).first():
        raise HTTPException(400, "A template with this name already exists.")
    t = Template(**body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    t = db.query(Template).get(template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    db.delete(t)
    db.commit()
    return {"deleted": True}
