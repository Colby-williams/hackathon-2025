# app.py
# Micromobility rental backend (Flask, in-memory) with:
# - Username/password login via HTTP-only session cookie
# - Vehicle types: bike, snow-bike, e-bike, scooter (per-minute prices)
# - User wallet/balance: /wallet (GET), /wallet/deposit (POST)
# - Block starting a rental if the user's balance is negative (HTTP 402)
# - Ride cost is deducted from balance when ending a ride
# - API: /login, /logout, /me, /wallet, /wallet/deposit, /bikes, /rentals/start, /rentals/{id}, /rentals/{id}/end
# - Static helpers: serves index.html at "/", map.html at "/map", and /config.js exposes GOOGLE_MAPS_KEY
#
# Run:
#   pip install "flask==3.0.3"
#   export GOOGLE_MAPS_KEY="YOUR_REAL_KEY"    # or PowerShell: $env:GOOGLE_MAPS_KEY="YOUR_REAL_KEY"
#   python app.py
#
# Note: In-memory store for hackathons. Any server restart clears rentals and balances.

from __future__ import annotations

import os
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Literal

from flask import Flask, jsonify, request, send_from_directory, abort, make_response

app = Flask(__name__, static_url_path="", static_folder=".")

# -------- Demo users (plaintext + balances; demo-only) --------
USERS: Dict[str, dict] = {
    "u123": {"password": "pass123", "name": "Alice",   "balance_cents": 2000},  # $20.00
    "u124": {"password": "pass124", "name": "Bob",     "balance_cents": 1000},  # $10.00
    "u125": {"password": "pass125", "name": "Charlie", "balance_cents":  500},  # $5.00
}
SESSIONS: Dict[str, str] = {}  # sid -> user_id
BLOCK_NEGATIVE_BALANCE_ON_START = True  # prevent renting when balance < 0

def get_current_user_id() -> Optional[str]:
    sid = request.cookies.get("sid")
    if not sid:
        return None
    return SESSIONS.get(sid)

def require_login() -> str:
    uid = get_current_user_id()
    if not uid:
        abort(401, description="Not logged in")
    return uid

# -------- Models --------
VehicleType = Literal["bike", "snow-bike", "e-bike", "scooter"]

@dataclass
class Bike:
    id: str
    vehicle_type: VehicleType
    lat: float
    lng: float
    is_available: bool = True
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Rental:
    id: str
    user_id: str
    bike_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    cost_cents: Optional[int] = None

# -------- Pricing --------
PRICING = {
    "bike":      {"unlock_cents": 0, "per_minute_cents": 50},   # $0.50/min
    "snow-bike": {"unlock_cents": 0, "per_minute_cents": 50},   # $0.50/min
    "e-bike":    {"unlock_cents": 0, "per_minute_cents": 100},  # $1.00/min
    "scooter":   {"unlock_cents": 0, "per_minute_cents": 100},  # $1.00/min
}
MAX_RIDE_MINUTES = 240  # optional cap

# -------- Seed bikes --------
bikes: Dict[str, Bike] = {
    "b1":  Bike(id="b1",  vehicle_type="bike",      lat=43.81488858304542, lng=-111.79005227761711),
    "b2":  Bike(id="b2",  vehicle_type="e-bike",    lat=43.8201,           lng=-111.7859),
    "b3":  Bike(id="b3",  vehicle_type="scooter",   lat=43.825,            lng=-111.789),
    "b4":  Bike(id="b4",  vehicle_type="snow-bike", lat=43.8185,           lng=-111.783),
    "b5":  Bike(id="b5",  vehicle_type="bike",      lat=43.8212,           lng=-111.7871),
    "b6":  Bike(id="b6",  vehicle_type="e-bike",    lat=43.8239,           lng=-111.7842),
    "b7":  Bike(id="b7",  vehicle_type="scooter",   lat=43.8197,           lng=-111.7863),
    "b8":  Bike(id="b8",  vehicle_type="bike",      lat=43.8225,           lng=-111.7888),
    "b9":  Bike(id="b9",  vehicle_type="snow-bike", lat=43.8176,           lng=-111.7899),
    "b10": Bike(id="b10", vehicle_type="e-bike",    lat=43.8246,           lng=-111.7827),
    "b11": Bike(id="b11", vehicle_type="bike",      lat=43.8208,           lng=-111.7909),
    "b12": Bike(id="b12", vehicle_type="scooter",   lat=43.8231,           lng=-111.7879),
}
rentals: Dict[str, Rental] = {}
bike_locks: Dict[str, threading.Lock] = {bid: threading.Lock() for bid in bikes}

# -------- Helpers --------
def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: datetime | None) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()

def compute_cost_cents(vehicle_type: str, start: datetime, end: datetime) -> int:
    p = PRICING.get(vehicle_type, {"unlock_cents": 0, "per_minute_cents": 50})
    elapsed_seconds = max(0, int((end - start).total_seconds()))
    minutes = max(1, (elapsed_seconds + 59) // 60)  # round up, min 1 minute
    return int(p["unlock_cents"] + minutes * p["per_minute_cents"])

def rental_to_dict(r: Rental, include_balance: bool = False) -> dict:
    b = bikes.get(r.bike_id)
    vtype = b.vehicle_type if b else "bike"
    p = PRICING.get(vtype, {"unlock_cents": 0, "per_minute_cents": 50})
    end = r.ended_at or utcnow()
    duration_seconds = max(0, int((end - r.started_at).total_seconds()))
    current_cost_estimate_cents = compute_cost_cents(vtype, r.started_at, utcnow()) if r.ended_at is None else r.cost_cents
    out = {
        "id": r.id,  # frontend should not display this publicly
        "user_id": r.user_id,
        "bike_id": r.bike_id,
        "vehicle_type": vtype,
        "started_at": iso(r.started_at),
        "ended_at": iso(r.ended_at),
        "duration_seconds": duration_seconds,
        "cost_cents": r.cost_cents,
        "current_cost_estimate_cents": current_cost_estimate_cents,
        "per_minute_cents": p["per_minute_cents"],
        "unlock_cents": p["unlock_cents"],
    }
    if include_balance:
        uid = r.user_id
        out["user_balance_cents"] = USERS.get(uid, {}).get("balance_cents", 0)
    return out

def active_rental_for_bike(bike_id: str) -> Optional[Rental]:
    for r in rentals.values():
        if r.bike_id == bike_id and r.ended_at is None:
            return r
    return None

def active_rental_for_user(user_id: str) -> Optional[Rental]:
    for r in rentals.values():
        if r.user_id == user_id and r.ended_at is None:
            return r
    return None

# -------- Static helpers --------
@app.route("/")
def root():
    try:
        return send_from_directory(".", "index.html")
    except Exception:
        return "<h3>Place index.html next to app.py</h3>", 200, {"Content-Type": "text/html"}

@app.route("/map")
def map_page():
    try:
        return send_from_directory(".", "map.html")
    except Exception:
        return "<h3>Place map.html next to app.py</h3>", 200, {"Content-Type": "text/html"}

@app.get("/config.js")
def serve_config_js():
    key = os.getenv("GOOGLE_MAPS_KEY", "")
    js = f'window.CONFIG = {{ "GOOGLE_MAPS_KEY": {json.dumps(key)} }};'
    return js, 200, {"Content-Type": "application/javascript; charset=utf-8"}

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": iso(utcnow())})

# -------- Auth --------
@app.post("/login")
def login():
    body = request.get_json(force=True, silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()
    user = USERS.get(username)
    if not user or user["password"] != password:
        abort(401, description="Invalid username or password")
    sid = str(uuid.uuid4())
    SESSIONS[sid] = username
    resp = make_response(jsonify({
        "ok": True,
        "user_id": username,
        "name": user.get("name"),
        "balance_cents": user.get("balance_cents", 0),
    }))
    resp.set_cookie("sid", sid, httponly=True, samesite="Lax")
    return resp

@app.post("/logout")
def logout():
    sid = request.cookies.get("sid")
    if sid and sid in SESSIONS:
        del SESSIONS[sid]
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie("sid")
    return resp

@app.get("/me")
def me():
    uid = get_current_user_id()
    if not uid:
        return jsonify({"authenticated": False})
    user = USERS.get(uid, {})
    return jsonify({
        "authenticated": True,
        "user_id": uid,
        "name": user.get("name"),
        "balance_cents": user.get("balance_cents", 0),
    })

# -------- Wallet --------
@app.get("/wallet")
def get_wallet():
    uid = require_login()
    bal = USERS.get(uid, {}).get("balance_cents", 0)
    return jsonify({"user_id": uid, "balance_cents": bal})

@app.post("/wallet/deposit")
def wallet_deposit():
    uid = require_login()
    body = request.get_json(force=True, silent=True) or {}
    amt_cents = body.get("amount_cents")
    amt_dollars = body.get("amount_dollars")
    if amt_cents is None and amt_dollars is None:
        abort(400, description="Provide amount_cents or amount_dollars")
    if amt_cents is None:
        try:
            amt_cents = int(round(float(amt_dollars) * 100))
        except Exception:
            abort(400, description="Invalid amount_dollars")
    try:
        amt_cents = int(amt_cents)
    except Exception:
        abort(400, description="Invalid amount_cents")
    if amt_cents <= 0:
        abort(400, description="Deposit must be > 0")
    USERS[uid]["balance_cents"] = USERS[uid].get("balance_cents", 0) + amt_cents
    return jsonify({"ok": True, "user_id": uid, "balance_cents": USERS[uid]["balance_cents"]})

# -------- Bikes --------
@app.get("/bikes")
def list_bikes():
    out = []
    for b in bikes.values():
        active = active_rental_for_bike(b.id)
        p = PRICING.get(b.vehicle_type, {"unlock_cents": 0, "per_minute_cents": 50})
        out.append({
            "id": b.id,
            "vehicle_type": b.vehicle_type,
            "lat": b.lat,
            "lng": b.lng,
            "is_available": b.is_available,
            "last_seen_at": iso(b.last_seen_at),
            "rented_by_user_id": active.user_id if active else None,
            "current_rental_id": active.id if active else None,
            "per_minute_cents": p["per_minute_cents"],
            "unlock_cents": p["unlock_cents"],
        })
    return jsonify(out)

# -------- Rentals --------
@app.post("/rentals/start")
def start_rental():
    user_id = require_login()
    body = request.get_json(force=True, silent=True) or {}
    bike_id = body.get("bike_id")
    if not bike_id:
        abort(400, description="bike_id is required")

    if BLOCK_NEGATIVE_BALANCE_ON_START:
        bal = USERS.get(user_id, {}).get("balance_cents", 0)
        if bal < 0:
            abort(402, description="Your balance is negative. Please deposit funds to rent.")

    bike = bikes.get(bike_id)
    if not bike:
        abort(404, description="Bike not found")
    if active_rental_for_user(user_id):
        abort(409, description="User already has an active rental")

    lock = bike_locks[bike.id]
    with lock:
        if not bike.is_available:
            abort(409, description="Bike not available")

        bike.is_available = False
        bike.last_seen_at = utcnow()

        rid = str(uuid.uuid4())
        rental = Rental(
            id=rid,
            user_id=user_id,
            bike_id=bike.id,
            started_at=utcnow(),
        )
        rentals[rid] = rental
        return jsonify(rental_to_dict(rental)), 201

@app.get("/rentals/<rental_id>")
def get_rental(rental_id: str):
    rental = rentals.get(rental_id)
    if not rental:
        abort(404, description="Rental not found")

    if rental.ended_at is None:
        elapsed_min = (utcnow() - rental.started_at).total_seconds() / 60
        if elapsed_min > MAX_RIDE_MINUTES:
            _end_rental_internal(rental, lat=None, lng=None)

    return jsonify(rental_to_dict(rentals[rental_id]))

@app.post("/rentals/<rental_id>/end")
def end_rental(rental_id: str):
    user_id = require_login()
    body = request.get_json(force=True, silent=True) or {}
    lat = body.get("lat")
    lng = body.get("lng")

    rental = rentals.get(rental_id)
    if not rental:
        abort(404, description="Rental not found")
    if rental.user_id != user_id:
        abort(403, description="Cannot end someone else's rental")
    if rental.ended_at is not None:
        return jsonify(rental_to_dict(rental, include_balance=True))

    out = _end_rental_internal(rental, lat=lat, lng=lng)

    # Deduct cost from user's balance
    cost = rental.cost_cents or 0
    USERS[user_id]["balance_cents"] = USERS[user_id].get("balance_cents", 0) - cost
    out["user_balance_cents"] = USERS[user_id]["balance_cents"]
    return jsonify(out)

def _end_rental_internal(rental: Rental, lat: Optional[float], lng: Optional[float]) -> dict:
    bike = bikes.get(rental.bike_id)
    if not bike:
        abort(500, description="Bike missing")

    end_time = utcnow()
    cost = compute_cost_cents(bike.vehicle_type, rental.started_at, end_time)
    rental.ended_at = end_time
    rental.cost_cents = cost

    if lat is not None and lng is not None:
        try:
            bike.lat = float(lat)
            bike.lng = float(lng)
        except Exception:
            pass
    bike.is_available = True
    bike.last_seen_at = utcnow()
    return rental_to_dict(rental)

# -------- Debug --------
@app.post("/debug/reset")
def reset_state():
    rentals.clear()
    for b in bikes.values():
        b.is_available = True
        b.last_seen_at = utcnow()
    # Reset balances to starters
    for uid, u in USERS.items():
        u["balance_cents"] = 2000 if uid == "u123" else 1000 if uid == "u124" else 500
    SESSIONS.clear()
    return jsonify({"ok": True, "message": "State reset"}), 200

if __name__ == "__main__":
    if not os.getenv("GOOGLE_MAPS_KEY"):
        print("NOTE: GOOGLE_MAPS_KEY env var is not set. /config.js will return an empty key.")
        print("      Set it with: export GOOGLE_MAPS_KEY='YOUR_REAL_KEY' (macOS/Linux)")
        print("                 or: $env:GOOGLE_MAPS_KEY='YOUR_REAL_KEY' (Windows PowerShell)")
    app.run(host="127.0.0.1", port=5000, debug=True)