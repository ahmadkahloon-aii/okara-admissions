# Deployment Guide — Okara WhatsApp AI Admissions Platform

This walks you from zero to a live system. Follow the parts in order. Anything you don't set here can also be set later from the dashboard **Settings** page.

**Architecture recap**
- **Backend** (FastAPI) — a long-running service. Host on a **VPS** (Hostinger VPS, Contabo, DigitalOcean) or a platform like **Railway / Render**. It cannot run on static-only shared hosting.
- **Frontend** (React static build) — host on **Hostinger** (static), **Vercel**, or **Netlify**.
- The backend exposes a **`/webhook`** URL that Meta calls when a WhatsApp message arrives.

---

## Part 0 — What you'll need
- A **Meta (Facebook) account** and a **Meta Business** account.
- A phone number for WhatsApp (a test number is provided free by Meta to start).
- An **OpenAI account** with billing enabled (for the AI counsellor). Optional — the bot's menus and engines work without it; only free-text AI answers need it.
- A **domain or subdomain** for the backend with **HTTPS** (Meta requires HTTPS for webhooks). Railway/Render give you an HTTPS URL automatically.

---

## Part 1 — Get your WhatsApp Cloud API credentials

1. Go to **developers.facebook.com → My Apps → Create App**. Choose type **Business**. Name it (e.g. "Okara Admissions").
2. In the app dashboard, find **WhatsApp** and click **Set up**. This creates a test phone number and a temporary token.
3. From **WhatsApp → API Setup**, collect:
   - **Phone number ID** → this is `WHATSAPP_PHONE_NUMBER_ID`.
   - **WhatsApp Business Account ID** (WABA ID) → `WHATSAPP_BUSINESS_ACCOUNT_ID`.
   - A **temporary access token** (good for ~24h — fine for first testing).
4. **Create a permanent token** (so it doesn't expire):
   - Go to **business.facebook.com → Business Settings → Users → System Users**.
   - Create a **System User** (Admin role). Click **Add Assets** → assign your app and WhatsApp account with full control.
   - Click **Generate New Token** → select your app → choose permissions **`whatsapp_business_messaging`** and **`whatsapp_business_management`** → generate.
   - Copy the token → this is your permanent `WHATSAPP_TOKEN`. **Save it now; it won't be shown again.**
5. **App Secret** (used to verify that webhook calls really come from Meta):
   - App dashboard → **Settings → Basic → App Secret → Show**. Copy → `WHATSAPP_APP_SECRET`.
6. **Verify token** — you invent this. Any string, e.g. `okara-verify-2026`. You'll enter the same value in Meta and in the dashboard → `WHATSAPP_VERIFY_TOKEN`.

> For production you'll later **add your own business phone number** and verify your business in Meta to lift messaging limits. The test number can only message a few pre-approved recipients.

---

## Part 2 — Get your OpenAI key (optional but recommended)
1. Go to **platform.openai.com → API keys → Create new secret key**. Copy it → `OPENAI_API_KEY`.
2. Ensure billing is set up (Settings → Billing).
3. Defaults used by the app: chat model `gpt-4o-mini`, embeddings `text-embedding-3-small` (both cost-efficient). You can change these in Settings.

---

## Part 3 — Create message templates in Meta (for bulk campaigns)
Bulk/marketing messages and any message sent **outside the 24-hour customer service window** must use a **pre-approved template**.

1. Go to **business.facebook.com → WhatsApp Manager → Message Templates → Create Template**.
2. Choose category (**Marketing** for admissions promos, **Utility** for reminders), name it (lowercase + underscores, e.g. `okara_admissions_open_2026`), and language (e.g. English `en_US`).
3. Write the body. Use `{{1}}`, `{{2}}` for variables (e.g. `Assalam-o-Alaikum {{1}}! Admissions for Fall 2026 are open.`). Provide sample values and submit.
4. Wait for **Approved** status (usually minutes to a few hours).
5. You'll register this exact name in the dashboard later (Part 7). Three example templates are pre-loaded for reference — replace them with your real approved ones.

---

## Part 4 — Run locally first (recommended sanity check)
See the **Quick start** in `README.md`. Confirm you can log in and that the **Simulate** button on a contact drives the bot. Then proceed to hosting.

---

## Part 5 — Deploy the BACKEND

Pick ONE option.

### Option A — Railway (easiest, HTTPS included)
1. Push this project to a GitHub repo.
2. On **railway.app → New Project → Deploy from GitHub repo**, pick the repo.
3. Set **Root Directory** to `backend`. Railway detects the `Dockerfile`.
4. Add **Variables** (Settings → Variables):
   - `JWT_SECRET` = a long random string
   - `ADMIN_EMAIL`, `ADMIN_PASSWORD` = your first login
   - `CORS_ORIGINS` = your dashboard URL (e.g. `https://admissions.yoursite.com`) — or `*` while testing
   - (optional) `DATABASE_URL` for Postgres (add a Railway Postgres plugin and paste its URL, prefix `postgresql+psycopg2://`)
   - You may also set WhatsApp/OpenAI keys here, but it's easier to add them in the dashboard Settings later.
5. Railway gives you a public URL like `https://okara-backend.up.railway.app`. **This is your backend URL.** Your webhook is that URL + `/webhook`.

### Option B — Render
1. **render.com → New → Web Service** → connect the repo.
2. Root directory `backend`; Environment **Docker** (or Python with start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
3. Add the same environment variables as above. Render provides an HTTPS URL.

### Option C — Your own VPS (Hostinger VPS / Contabo / DigitalOcean)
1. SSH in. Install Docker, or Python 3.11+.
2. Copy the project up (git clone or scp).
3. **With Docker:**
   ```bash
   cd okara-admissions
   JWT_SECRET=... ADMIN_PASSWORD=... CORS_ORIGINS=https://your-dashboard docker compose up -d --build
   ```
   Backend listens on port 8000.
4. **Or without Docker:**
   ```bash
   cd backend && python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # edit it
   # run under a process manager so it stays up:
   pip install gunicorn
   gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```
5. **Put HTTPS in front** (required by Meta). Install Nginx + Certbot and reverse-proxy your domain to `127.0.0.1:8000`:
   ```nginx
   server {
     server_name api.yoursite.com;
     location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host;
                  proxy_set_header X-Forwarded-For $remote_addr; }
   }
   ```
   Then `sudo certbot --nginx -d api.yoursite.com`. Your backend URL becomes `https://api.yoursite.com`.

**Verify the backend is up:** open `https://<backend-url>/health` → should return `{"status":"ok"}`.

---

## Part 6 — Connect the webhook in Meta
1. In the **Meta App dashboard → WhatsApp → Configuration → Webhooks** (or **Edit** under Callback URL).
2. **Callback URL** = `https://<your-backend-url>/webhook`
3. **Verify token** = the exact `WHATSAPP_VERIFY_TOKEN` value.
   - ⚠️ The verify token must already be set in the backend **before** you click Verify. If you haven't set keys in the dashboard yet, set `WHATSAPP_VERIFY_TOKEN` as a backend environment variable for this step (it defaults to `okara-verify-2026` in `.env.example`).
4. Click **Verify and Save**. Meta calls your `/webhook` (GET) and expects the challenge echoed back — the app does this automatically.
5. Click **Manage** and **Subscribe** to the **`messages`** field (this is what delivers inbound messages and status updates).

> If verification fails: confirm the URL is HTTPS and public, `/health` works, and the verify token matches exactly.

---

## Part 7 — Deploy the FRONTEND (dashboard)

The dashboard is a static build that talks to your backend.

1. Set the backend URL. Create `frontend/.env`:
   ```
   VITE_API_URL=https://<your-backend-url>
   ```
2. Build:
   ```bash
   cd frontend && npm install && npm run build
   ```
   This produces `frontend/dist/` (static files).

**Host the `dist/` folder** — pick one:
- **Hostinger (static hosting / hPanel):** upload the **contents of `dist/`** into `public_html` (or a subdomain folder) via File Manager or FTP. Because the app uses hash routing, no special server rewrites are needed.
- **Vercel / Netlify:** "Import project" from GitHub, set **Root Directory** = `frontend`, **Build command** = `npm run build`, **Output dir** = `dist`, and add env var `VITE_API_URL`. Deploy.

3. **CORS:** make sure the backend's `CORS_ORIGINS` includes your dashboard's URL (set it in the backend env/host and redeploy), or keep `*` while testing.

---

## Part 8 — Enter your keys in the dashboard
1. Open the dashboard, log in.
2. Go to **Settings & Keys**. Fill in:
   - **WhatsApp:** Access Token, Phone Number ID, WhatsApp Business Account ID, Verify Token, App Secret. (Graph API Version default `v21.0` is fine.)
   - **AI Provider:** keep `openai`, paste your **OpenAI API Key**. (Leave models at defaults.)
   - **Business Identity:** name and default language.
3. Click **Save all changes**.
4. Click **Test connection** under WhatsApp (should show your verified number) and under AI (should reply "OK").

---

## Part 9 — Register templates & build the knowledge index
1. **Templates** page → register each **approved** Meta template by its exact name, language, and number of `{{n}}` variables.
2. **Knowledge Base** page → click **Re-index bundled KB**. With an OpenAI key set you'll get AI embeddings (semantic search); without it, a keyword fallback is used. Edit the facts anytime and click **Save edits & re-index**.

---

## Part 10 — Test end-to-end
1. **Simulated (no WhatsApp needed):** open/refresh **Leads & Contacts**, open a contact (or create one by simulating), and use **Simulate** to walk the flow: greeting → Programs → Eligibility → pick a program → check eligibility → apply. Confirm stages advance on the dashboard.
2. **Live WhatsApp:** from the phone that's allowed to message your test number, send "hi" to your WhatsApp number. You should get the main menu. Tap through programs, eligibility, fees, apply.
3. **Human takeover:** in a conversation, type a message and click **Send (live)** — it goes to the applicant and tags the lead **Human-Assigned**.

---

## Part 11 — Run a bulk campaign
1. **Bulk Campaigns** page → name it, pick an approved template, optionally fill `{{1}}` variables (separate multiple with `|`), and set an audience filter (stage / status / source).
2. **Preview audience** to see how many match.
3. **Send campaign** — it sends in the background; the history table updates sent/failed counts live.

> WhatsApp enforces messaging limits and an opt-in policy. Only message people who contacted you or opted in, and only with approved templates outside the 24-hour window. Start small while your number's quality rating builds up.

---

## Part 12 — Production checklist
- [ ] Change the **admin password** (set `ADMIN_PASSWORD` before first deploy, or create a new admin and rotate — the default exists only for first login).
- [ ] Set a strong, unique **`JWT_SECRET`**.
- [ ] Lock **`CORS_ORIGINS`** to your dashboard domain (not `*`).
- [ ] Use **Postgres** for anything beyond pilot scale: add a Postgres DB and set `DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db`. (On a fresh DB the app re-creates tables and re-seeds on startup.)
- [ ] Ensure the backend has **HTTPS** (Meta requirement) and stays up via a process manager / platform.
- [ ] Add your **own business phone number** in Meta and complete **business verification** to raise messaging limits.
- [ ] Back up the database (the SQLite file lives in the backend working dir / Docker volume `okara_data`).

---

## Troubleshooting
| Symptom | Fix |
|---|---|
| Webhook "Verify" fails in Meta | Backend not HTTPS/public, `/health` not returning ok, or verify token mismatch. Set `WHATSAPP_VERIFY_TOKEN` in backend env before verifying. |
| Bot doesn't reply on WhatsApp | Subscribe to the **`messages`** field (Part 6.5). Check the recipient is allowed (test number) and the token is permanent. Check backend logs. |
| Dashboard shows network/401 errors | Wrong `VITE_API_URL`, backend down, or CORS not allowing the dashboard domain. |
| "Configure WhatsApp in Settings before sending campaigns" | Add the token + phone number ID in Settings (Part 8). |
| AI gives generic answers | No OpenAI key set → it's using the keyword fallback. Add the key in Settings and re-index the KB. |
| Template send fails | The template name/language must match an **approved** template exactly, and the recipient must be reachable. |
| Fees for Post-ADP CS/AI show "being finalised" | Intentional — those are unconfirmed and must not be quoted. Update `backend/app/data/catalog.py` once confirmed. |

---

### Where the data lives (to customise)
- Programs, fees, scholarships, transport, office hours → `backend/app/data/catalog.py`
- AI knowledge / FAQ / guardrails → `backend/app/data/knowledge_base.md` (or edit live on the Knowledge Base page)
- Conversation flow / menus → `backend/app/services/conversation.py`
- AI behaviour & tools → `backend/app/services/openai_service.py`

You now have a complete, running WhatsApp AI admissions platform. 🎓
