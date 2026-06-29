"""FastAPI application entry point for the Okara WhatsApp Admissions platform."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, SessionLocal
from .config import CORS_ORIGINS
from .seed import run_seed
from .routers import (webhook, auth, contacts, settings, templates,
                      campaigns, dashboard, knowledge)

app = FastAPI(title="Superior University Okara — WhatsApp Admissions Platform",
              version="1.0.0",
              description="WhatsApp + AI admissions automation for Superior University Okara Campus.")

origins = ["*"] if CORS_ORIGINS.strip() == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(settings.router)
app.include_router(templates.router)
app.include_router(campaigns.router)
app.include_router(dashboard.router)
app.include_router(knowledge.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {"service": "Okara WhatsApp Admissions Platform", "status": "running",
            "docs": "/docs", "webhook": "/webhook"}


@app.get("/health")
def health():
    return {"status": "ok"}
