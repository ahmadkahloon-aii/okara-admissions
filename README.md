# Superior University Okara — WhatsApp AI Admissions Platform

A complete, deployable WhatsApp + AI admissions automation system for the **Okara Campus, Fall 2026 intake**. Applicants chat on WhatsApp; the bot runs the full admissions journey (menus, eligibility, fees, scholarships, transport, application capture, appointments) and answers free-form questions with an AI counsellor grounded on a private knowledge base. Your team manages everything — leads, conversations, bulk template campaigns and API keys — from a branded web dashboard.

You only need to **add your WhatsApp and OpenAI keys** (from the dashboard Settings page). Nothing is hard-coded.

---

## What's inside

```
okara-admissions/
├── backend/      FastAPI + SQLite/Postgres — bot engine, AI, CRM, REST API, webhook
├── frontend/     React (Vite) dashboard — purple/gold branded console
├── docker-compose.yml
├── README.md
└── DEPLOYMENT.md  ← step-by-step go-live guide (read this)
```

### Key capabilities
- **WhatsApp Cloud API** integration: interactive menus (buttons + lists), free text, and approved-template sending.
- **AI counsellor** (OpenAI) with **tool-calling** into the eligibility / fee / scholarship engines and **RAG** over the knowledge base. Works offline with a deterministic fallback before keys are added.
- **Deterministic admissions flow** matching the approved conversation map — menus, eligibility check, application form, scholarship reveal, prospectus voucher and appointment booking.
- **Bulk campaigns**: pick a Meta-approved template, filter the audience (stage / status / source), preview, and send in the background.
- **CRM pipeline**: every applicant tracked through Lead → Qualified Lead → Prospectus → … → Current Student, with AI/Human status tags and manual takeover.
- **Editable knowledge base** from the dashboard, re-indexed on save.
- **Secure dashboard**: JWT login, API keys stored server-side and masked.

### The business logic is real
- Net first-semester fee uses the official formula `Admission + Misc + Tuition × (1 − waiver)`. Example: BS Computer Science at 78% → **PKR 117,500**.
- Scholarships return the single highest waiver (no stacking).
- Post-ADP fees for BS CS / BS AI are intentionally **"to confirm"** — the bot never quotes a number for them.
- All 23 Okara programs, fees, merit bands, categories and 6 transport routes are encoded in `backend/app/data/catalog.py`.

---

## Quick start (local, 5 minutes)

**1. Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # optional: edit JWT_SECRET / admin password
uvicorn app.main:app --reload --port 8000
```
Backend runs at `http://localhost:8000` (API docs at `/docs`). On first start it creates the database, a default admin, example templates and the KB index.

**2. Frontend**
```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:8000
npm run dev
```
Open the printed URL (default `http://localhost:5173`).

**3. Log in**
- Email: `admin@okara.superior.edu.pk`
- Password: `OkaraAdmin@2026`  *(change this immediately — see DEPLOYMENT.md)*

**4. Try it without WhatsApp**
Open any contact → use the **Simulate** button, or `POST /api/contacts/simulate`, to drive the whole bot flow locally before connecting WhatsApp.

---

## Going live

Connecting WhatsApp, OpenAI, the webhook and hosting (VPS for the backend, Hostinger/Vercel/Netlify for the dashboard) is covered step-by-step in **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

> Note: the FastAPI backend is a long-running service and **must** be hosted on a VPS or a platform like Railway/Render — it cannot run on static-only hosting. The React dashboard is a static build and can go on Hostinger, Vercel or Netlify.
