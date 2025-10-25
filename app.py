# app.py
# Micromobility rental backend (Flask, in-memory) with:
# - Vehicle types: bike, snow-bike, e-bike, scooter
# - Per-type pricing (per-minute + optional unlock fee)
# - Endpoints: /bikes, /rentals/start, /rentals/{id}, /rentals/{id}/end, /users/{user}/active_rental
# - /config.js served from env GOOGLE_MAPS_KEY for your index.html to load Google Maps
#
# Run:
#   pip install "flask==3.0.3"
#   export GOOGLE_MAPS_KEY="YOUR_REAL_KEY"    # or PowerShell: $env:GOOGLE_MAPS_KEY="YOUR_REAL_KEY"
#   python app.py
# Place index.html next to this file. Include <script src="config.js"></script> in your page.

from __future__ import annotations

import os
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Literal

from flask import Flask, jsonify, request, send_from_directory, abort

app = Flask(__name__, static_url_path="", static_folder=".")

# ---------------- Models ----------------

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

# ---------------- Pricing (per vehicle type) ----------------
# Requested: bikes $0.50/min; e-bikes & scooters $1.00/min. Snow-bikes -> $0.50/min.
PRICING = {
    "bike":      {"unlock_cents": 0, "per_minute_cents": 50},
    "snow-bike": {"unlock_cents": 0, "per_minute_cents": 50},
    "e-bike":    {"unlock_cents": 0, "per_minute_cents": 100},
    "scooter":   {"unlock_cents": 0, "per_minute_cents": 100},
}

MAX_RIDE_MINUTES = 240  # 4 hours cap (optional)

# ---------------- Seed data ----------------

bikes: Dict[str, Bike] = {
    "b1": Bike(id="b1", vehicle_type="bike",      lat=43.81488858304542, lng=-111.79005227761711),
    "b2": Bike(id="b2", vehicle_type="e-bike",    lat=43.8201,           lng=-111.7859),
    "b3": Bike(id="b3", vehicle_type="scooter",   lat=43.825,            lng=-111.789),
    "b4": Bike(id="b4", vehicle_type="snow-bike", lat=43.8185,           lng=-111.783),
    "b5": Bike(id="b5", vehicle_type="bike",      lat=43.8212,           lng=-111.7871),
    "b6": Bike(id="b6", vehicle_type="e-bike",    lat=43.8239,           lng=-111.7842),
}
rentals: Dict[str, Rental] = {}
bike_locks: Dict[str, threading.Lock] = {bid: threading.Lock() for bid in bikes}

# ---------------- Helpers ----------------

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

def rental_to_dict(r: Rental) -> dict:
    b = bikes.get(r.bike_id)
    vtype = b.vehicle_type if b else "bike"
    p = PRICING.get(vtype, {"unlock_cents": 0, "per_minute_cents": 50})
    end = r.ended_at or utcnow()
    duration_seconds = max(0, int((end - r.started_at).total_seconds()))
    current_cost_estimate_cents = compute_cost_cents(vtype, r.started_at, utcnow()) if r.ended_at is None else r.cost_cents
    return {
        "id": r.id,
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

# ---------------- Routes ----------------

@app.route("/")
def index():
    try:
        return send_from_directory(".", "index.html")
    except Exception:
        html = """
        <!doctype html><meta charset="utf-8">
        <title>Micromobility Backend</title>
        <div style="font-family:system-ui,sans-serif;margin:24px;max-width:720px">
          <h2>Micromobility Backend is running</h2>
          <p>Place <code>index.html</code> next to <code>app.py</code> to serve your map UI.</p>
          <p>Your Google Maps key is served at <code>/config.js</code>
             (set env <code>GOOGLE_MAPS_KEY</code>).</p>
          <ul>
            <li><a href="/bikes">/bikes</a></li>
            <li><a href="/health">/health</a></li>
          </ul>
        </div>
        """
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.get("/config.js")
def serve_config_js():
    key = os.getenv("GOOGLE_MAPS_KEY", "")
    js = f'window.CONFIG = {{ "GOOGLE_MAPS_KEY": {json.dumps(key)} }};'
    return js, 200, {"Content-Type": "application/javascript; charset=utf-8"}

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": iso(utcnow())})

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

@app.get("/users/<user_id>/active_rental")
def get_user_active_rental(user_id: str):
    r = active_rental_for_user(user_id)
    if not r:
        return jsonify({"active": False})
    return jsonify({"active": True, "rental": rental_to_dict(r)})

@app.post("/rentals/start")
def start_rental():
    # Body: { "user_id": "u123", "bike_id": "b1" }
    body = request.get_json(force=True, silent=True) or {}
    user_id = body.get("user_id")
    bike_id = body.get("bike_id")
    if not user_id or not bike_id:
        abort(400, description="user_id and bike_id are required")

    bike = bikes.get(bike_id)
    if not bike:
        abort(404, description="Bike not found")

    # One active rental per user
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

    # Optional auto-end if beyond cap
    if rental.ended_at is None:
        elapsed_min = (utcnow() - rental.started_at).total_seconds() / 60
        if elapsed_min > MAX_RIDE_MINUTES:
            _end_rental_internal(rental, lat=None, lng=None)

    return jsonify(rental_to_dict(rentals[rental_id]))

@app.post("/rentals/<rental_id>/end")
def end_rental(rental_id: str):
    # Body: { "lat": 43.82, "lng": -111.78 }
    body = request.get_json(force=True, silent=True) or {}
    lat = body.get("lat")
    lng = body.get("lng")

    rental = rentals.get(rental_id)
    if not rental:
        abort(404, description="Rental not found")
    if rental.ended_at is not None:
        return jsonify(rental_to_dict(rental))  # idempotent

    out = _end_rental_internal(rental, lat=lat, lng=lng)
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

@app.post("/debug/reset")
def reset_state():
    rentals.clear()
    for b in bikes.values():
        b.is_available = True
        b.last_seen_at = utcnow()
    return jsonify({"ok": True, "message": "State reset"}), 200

if __name__ == "__main__":
    if not os.getenv("GOOGLE_MAPS_KEY"):
        print("NOTE: GOOGLE_MAPS_KEY env var is not set. /config.js will return an empty key.")
        print("      Set it with: export GOOGLE_MAPS_KEY='YOUR_REAL_KEY' (macOS/Linux)")
        print("                 or: $env:GOOGLE_MAPS_KEY='YOUR_REAL_KEY' (Windows PowerShell)")
    app.run(host="127.0.0.1", port=5000, debug=True)