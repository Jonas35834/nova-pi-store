import os
import secrets
import time
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS

import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    }
)


# ============================================================
# Firebase Admin
# ============================================================

firebase_initialized = False


def init_firebase():

    global firebase_initialized

    if firebase_initialized:
        return

    # --------------------------------------------------------
    # Render Secret File
    # --------------------------------------------------------

    service_account_path = os.environ.get(
        "FIREBASE_SERVICE_ACCOUNT"
    )

    if not service_account_path:

        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT "
            "ist nicht gesetzt."
        )

    credential = credentials.Certificate(
        service_account_path
    )

    firebase_admin.initialize_app(
        credential
    )

    firebase_initialized = True


init_firebase()


# ============================================================
# Geräte
# ============================================================

devices = {}

devices_lock = threading.Lock()


# ============================================================
# Authentifizierung
# ============================================================

def get_user():

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith(
        "Bearer "
    ):

        return None


    token = authorization[7:].strip()


    if not token:
        return None


    try:

        decoded = auth.verify_id_token(
            token
        )

        return decoded

    except Exception:

        return None


# ============================================================
# Test
# ============================================================

@app.get("/")
def index():

    return jsonify({
        "name": "Nova Pi Store Backend",
        "status": "online"
    })


# ============================================================
# Health
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({
        "success": True,
        "status": "online",
        "timestamp": int(time.time())
    })


# ============================================================
# Benutzer
# ============================================================

@app.get("/api/me")
def me():

    user = get_user()

    if user is None:

        return jsonify({
            "success": False,
            "error": "Nicht authentifiziert."
        }), 401


    return jsonify({
        "success": True,
        "uid": user["uid"],
        "email": user.get("email")
    })


# ============================================================
# Pi registrieren
# ============================================================

@app.post("/api/devices/register")
def register_device():

    user = get_user()

    if user is None:

        return jsonify({
            "success": False,
            "error": "Nicht authentifiziert."
        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    name = data.get(
        "name",
        "Raspberry Pi"
    )


    device_id = secrets.token_urlsafe(
        24
    )

    device_token = secrets.token_urlsafe(
        48
    )


    device = {
        "id": device_id,
        "uid": user["uid"],
        "name": name,
        "token": device_token,
        "online": False,
        "last_seen": None
    }


    with devices_lock:

        devices[device_id] = device


    return jsonify({
        "success": True,
        "device": {
            "id": device_id,
            "name": name,
            "token": device_token
        }
    })


# ============================================================
# Geräte des Benutzers
# ============================================================

@app.get("/api/devices")
def list_devices():

    user = get_user()

    if user is None:

        return jsonify({
            "success": False,
            "error": "Nicht authentifiziert."
        }), 401


    with devices_lock:

        result = []

        for device in devices.values():

            if device["uid"] != user["uid"]:
                continue


            result.append({
                "id": device["id"],
                "name": device["name"],
                "online": device["online"],
                "last_seen": device["last_seen"]
            })


    return jsonify({
        "success": True,
        "devices": result
    })


# ============================================================
# Pi Heartbeat
# ============================================================

@app.post("/api/device/heartbeat")
def heartbeat():

    data = request.get_json(
        silent=True
    ) or {}


    device_id = data.get(
        "device_id"
    )

    token = data.get(
        "token"
    )


    if not device_id or not token:

        return jsonify({
            "success": False,
            "error": "Gerätedaten fehlen."
        }), 400


    with devices_lock:

        device = devices.get(
            device_id
        )


        if device is None:

            return jsonify({
                "success": False,
                "error": "Gerät nicht gefunden."
            }), 404


        if not secrets.compare_digest(
            device["token"],
            token
        ):

            return jsonify({
                "success": False,
                "error": "Ungültiger Gerätetoken."
            }), 403


        device["online"] = True

        device["last_seen"] = int(
            time.time()
        )


    return jsonify({
        "success": True
    })


# ============================================================
# Server starten
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
