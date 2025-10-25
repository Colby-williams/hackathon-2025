# E‑Bike Rentals (Hackathon Demo)
Campus micromobility demo built by a team of beginning sophomores. Front end uses a Google Maps view; back end is a tiny Flask API with an in‑memory datastore (perfect for demos — restarting the server resets everything).

- Live site (static marketing pages): https://colby-williams.github.io/hackathon-2025/index.html
  - Note: GitHub Pages is static only. The interactive Map requires the Flask API running (locally or on a host like Render/Railway). For a zero‑CORS setup, serve the pages with Flask.
- Tech stack: HTML/CSS/JS + Flask (Python 3), Google Maps JavaScript API.


> Security note: This README includes a Google Maps key for hackathon convenience: `AIzaSyDVLbb9n_X7BXgErxe1QB4m9Dyv8vodwm8`.
> If this repo is public, rotate/restrict the key immediately after the event.
## Features

> AI assistance disclosure: Most JavaScript was generated with OpenAI GPT‑5; the team validated and refined the code.

- Simple sign‑in (demo users) with HTTP‑only session cookie.
- Live map with available vehicles: bike, snow‑bike, e‑bike, scooter.
- Start/end a ride; cost calculated per minute (rounded up).
- Wallet with deposits; rentals are blocked when your balance is negative (HTTP 402).
- Battery model for e‑bike/scooter + “Recharge” action when empty.
- In‑memory data for hackathon simplicity (no database).

Demo users you can try on the Map page:
- u123 / pass123 (starts with $20.00)
- u124 / pass124 (starts with $10.00)
- u125 / pass125 (starts with $5.00)

## How we built it
- Step 1 — Planning and wireframes: We started by discussing the core flow (sign in → find a vehicle → start ride → end ride → pay) and sketching wireframes for the Home, About, Services/Products, Contact, and Map pages.
- Step 2 — Split the work and build in parallel:
  - Colby Williams — site‑wide styling (styles.css), layout, responsive tweaks, and shared components (nav, footer).
  - Emma Kohler — content and styling for the About, Services/Products, and Contact pages; copywriting and small accessibility fixes.
  - Tanner Brown — Google Cloud setup (project + Maps JavaScript API), API key management, and the embedded map in map.html (markers and basic UI).
  - John Zhou — rental domain logic and state model: user accounts and sign‑in, wallet/deposit flow, per‑minute pricing, battery consumption for e‑bikes/scooters with “Recharge,” and negative‑balance blocking.
- Step 3 — Integration and testing: We wired the map to the Flask endpoints, verified log‑in, rentals, wallet deposits, and ride cost calculations, then fixed small UI/logic mismatches.
- Step 4 — AI‑assisted implementation and polish: With OpenAI GPT‑5, we generated most of the JavaScript (map markers, InfoWindows, UI event handlers/modals, fetch calls to the Flask API, and basic error handling). We then reviewed, edited, and tested the code; GPT‑5 also helped prettify CSS/markup and draft this README.

## Project structure (key files)
- app.py — Flask server and API (also serves index.html, map.html, and /config.js).
- index.html, about.html, services.html, contact.html — marketing/landing pages.
- map.html — the interactive rentals map (loads Google Maps + calls the API).
- script.js, styles.css — shared UI code and styles.
- config.js — local dev fallback for the Google Maps key (avoid committing real keys!).

There are also a few “.bak” files with older versions of map.html and app.py and extra stylesheets.

## Quick start (local)
Prereqs: Python 3.10+ and pip.

1) Clone the repo and open the folder in a terminal.

2) Install Flask:
```bash
pip install "flask==3.0.3"
```

3) Provide a Google Maps API key as an environment variable (this is what the app serves at /config.js).
For the hackathon, you can use this key:
- AIzaSyDVLbb9n_X7BXgErxe1QB4m9Dyv8vodwm8

IMPORTANT: Do not commit real keys in public repos. If this README is public, assume the key is compromised and rotate/restrict it after the event. 
Consider restricting the key by HTTP referrer or IP in the Google Cloud Console.

- macOS/Linux:
```bash
export GOOGLE_MAPS_KEY="AIzaSyDVLbb9n_X7BXgErxe1QB4m9Dyv8vodwm8"
```
- Windows PowerShell:
```powershell
$env:GOOGLE_MAPS_KEY="AIzaSyDVLbb9n_X7BXgErxe1QB4m9Dyv8vodwm8"
```

4) Run the server:
```bash
python app.py
```
By default it will listen on http://127.0.0.1:5000.

5) Open the app:
- Home: http://127.0.0.1:5000/
- Map:  http://127.0.0.1:5000/map

Tip: If you see “Google Maps API key missing” on the map page, the key was not supplied. See step 3.

## Environment variables
- GOOGLE_MAPS_KEY — required for the Map (Google Maps JS). The Flask route /config.js exposes it to the browser.
- Optional for deployment: PORT — some hosts inject this; see “Deploying” below.

Security note: Do not commit real API keys. Prefer using environment variables. If you keep a local config.js for convenience, make sure it uses a placeholder and is listed in .gitignore when you push.

Example .gitignore additions:
```
# never commit secrets
.env
config.js
```

## Deploying the whole app (front end + API)
The simplest way is to deploy the Flask app so it serves both the pages and the API from the same origin (no CORS headaches). Two options are shown below.

Before deploying, we recommend making app.py read the host/port from the environment so platforms can bind correctly. Change the last line to:

```python
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
```

Also add a minimal requirements.txt at the repo root:
```
flask==3.0.3
```
(Optionally add gunicorn if you prefer a production server on Linux hosts: `gunicorn==23.0.0` and use `gunicorn app:app` as the start command.)

### Option A: Render
1) Push your repo to GitHub.
2) On render.com, “New +” → “Web Service” → Connect your repo.
3) Environment:
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`  (or `gunicorn app:app` if you added gunicorn)
4) Add environment variables:
   - `GOOGLE_MAPS_KEY=your-real-key`
5) Deploy. Render will set `PORT` automatically; the `app.run(..., port=int(os.getenv("PORT", "5000")))` change ensures it binds.
6) Visit the Render URL. Both “/” and “/map” should work.

### Option B: Railway
1) Push your repo to GitHub and create a new Railway project from it.
2) Add variables in the project settings:
   - `GOOGLE_MAPS_KEY=your-real-key`
3) Add a service with:
   - Build: `pip install -r requirements.txt`
   - Start: `python app.py` (or `gunicorn app:app`)
4) Deploy. Railway injects `PORT`; the modified app.py will bind correctly.

Note on GitHub Pages: You can keep your static marketing pages on Pages, but the Map will need to call the API on a different origin. That introduces CORS. For beginners we suggest serving everything via Flask instead. If you must split them, enable CORS in Flask (`pip install flask-cors`) and configure allowed origins.

## Using the app
- Open /map, sign in with one of the demo users.
- Click a green marker to see a vehicle’s details.
- Rent Now starts a ride; End Ride ends it (the cost is deducted from your wallet).
- If your balance is negative you’ll be prompted to deposit before renting.
- E‑bikes/scooters have a battery % that drains with time; recharge sets it back to 100%.

## API overview (for teammates and judges)
All endpoints are relative to the Flask server.

- Auth
  - POST /login  — body: `{ "username": "u123", "password": "pass123" }`
  - POST /logout
  - GET  /me     — returns `{ authenticated, user_id?, name?, balance_cents? }`

- Wallet
  - GET  /wallet
  - POST /wallet/deposit — body: `{ "amount_dollars": 5 }` or `{ "amount_cents": 500 }`

- Bikes
  - GET  /bikes — returns each bike with availability, pricing, and (for electric) battery_percent.

- Rentals
  - POST /rentals/start — body: `{ "bike_id": "b3" }`. Blocks with HTTP 402 if your balance is negative.
  - GET  /rentals/{id}  — live status (duration and estimated cost).
  - POST /rentals/{id}/end — body: `{ "lat": <number>, "lng": <number> }` — ends the ride and deducts the cost.

- Battery
  - POST /bikes/{bike_id}/recharge — sets battery_percent to 100 for e‑bikes/scooters (demo‑only).

- Misc
  - GET /config.js — exposes `window.CONFIG = { GOOGLE_MAPS_KEY: "..." }` from the env var.
  - GET /health

In this demo everything is in memory. Restarting the server clears rides, resets balances, and logs you out.

## Troubleshooting
- Blank or error on the map: the Google Maps key is missing/invalid, billing is off, or referrers don’t match. Make sure GOOGLE_MAPS_KEY is set in the server environment.
- CORS errors in the browser console: you’re loading the HTML from a different origin than the Flask API. Easiest fix: let Flask serve all pages; otherwise add `flask-cors` and allow your front‑end origin.
- “Battery empty. Please recharge first.”: recharge the bike in the InfoWindow or via POST /bikes/{id}/recharge.
- “Your balance is negative.” (HTTP 402): deposit funds in the Account modal or POST /wallet/deposit.

## Acknowledgements
- Built with help from OpenAI GPT-5 (AI pair-programming and README drafting), October 2025.
- Most of the JavaScript for the map UI and API calls was generated with OpenAI GPT‑5 and then reviewed/modified by the team.


## Team
- Emma Kohler
- John Zhou
- Colby Williams
- Tanner Brown

## Ethics & Academic Honesty
- AI assistance: Most of the JavaScript (map UI and API calls) and some copy were generated with OpenAI GPT‑5. The team reviewed, edited, and tested all AI‑assisted code, and made final design/implementation decisions.
- Attribution: We disclose AI use in this README (and can tag AI‑assisted commits in messages if requested by judges).
- Originality: Code and assets are either written by the team, generated for us by GPT‑5, or otherwise appropriately licensed. We avoided copying from closed‑source or non‑permissive sources.
- Data & privacy: This demo uses only mock users and in‑memory state. Please don’t enter personal data.
- Security & keys: A Google Maps API key appears in this README for hackathon convenience. Restrict it by referrer/IP and rotate it after the event. Don’t commit secrets to public repos; prefer environment variables.
- Licensing & terms: Google Maps JavaScript API is used under Google’s terms; usage may incur charges if quotas are exceeded.
- Academic honesty: If your course or hackathon requires disclosure of AI‑generated work, this section is intended to satisfy that requirement.

## Notes for judges
- This is a hackathon demo intended for learning. It uses an in‑memory store, no HTTPS termination, and no real payment provider. Don’t use it in production without proper auth, storage, and security hardening.
