# Frontend deployment — two options

## Option 1 (easiest): single-file dashboard  ✅ recommended if the build showed a blank page
Use **`okara-dashboard.html`** in this folder. It is the entire dashboard compiled into one
self-contained file (React + styles all inlined, no separate asset files, no build step).

**Deploy:**
1. Upload `okara-dashboard.html` anywhere — Hostinger `public_html` (rename to `index.html` if you
   want it at the domain root), a subfolder, Netlify drop, or even open it locally.
2. Open it in a browser. On the login screen, set **Backend API URL** to your backend's address
   (e.g. `https://your-backend.up.railway.app`). It's remembered in the browser.
3. Log in with your admin credentials.

Why this fixes the blank page: a normal Vite build loads `/assets/*.js` from the domain root. If the
files sit in a subfolder, those requests 404 and nothing renders. The single file has no external
assets, so it can't mis-path.

**Rebuild it** after changing any React source:
```bash
cd frontend
npm install
node build_single.cjs      # regenerates okara-dashboard.html
```

## Option 2: standard Vite build
```bash
cd frontend
npm install
# set the backend URL for the build:
echo "VITE_API_URL=https://your-backend-url" > .env
npm run build               # outputs frontend/dist/
```
`vite.config.js` now uses `base: './'` so the build also works when hosted in a subfolder.
Upload the **contents of `dist/`** to your host.

---

In both options, make sure the backend's `CORS_ORIGINS` allows the dashboard's URL (or keep it `*`
while testing). The app uses hash routing, so no server rewrite rules are needed.
