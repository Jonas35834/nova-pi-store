import os
import json
import secrets
import threading
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth

from simple_websocket import Server, ConnectionClosed


# ============================================================
# FLASK
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
# FIREBASE
# ============================================================

firebase_file = os.environ.get(
    "FIREBASE_SERVICE_ACCOUNT_FILE"
)

if not firebase_file:

    raise RuntimeError(
        "FIREBASE_SERVICE_ACCOUNT_FILE fehlt."
    )


if not firebase_admin._apps:

    firebase_admin.initialize_app(
        credentials.Certificate(
            firebase_file
        )
    )


# ============================================================
# GERÄTE
# ============================================================

devices = {}

devices_lock = threading.Lock()


# ============================================================
# WEBSOCKET-VERBINDUNGEN
# ============================================================

connections = {}

connections_lock = threading.Lock()


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def now():

    return int(
        time.time()
    )


def get_firebase_user():

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith(
        "Bearer "
    ):

        return None


    token = authorization[
        7:
    ].strip()


    if not token:

        return None


    try:

        return auth.verify_id_token(
            token
        )

    except Exception:

        return None


def require_user():

    user = get_firebase_user()

    if user is None:

        return None, (
            jsonify({
                "success": False,
                "error": "Nicht authentifiziert."
            }),
            401
        )

    return user, None


# ============================================================
# STARTSEITE
# ============================================================

@app.get("/")
def index():

    return jsonify({
        "name": "Nova Pi Store API",
        "version": "1.0.0",
        "status": "online"
    })


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({
        "success": True,
        "status": "online",
        "time": now()
    })


# ============================================================
# ME
# ============================================================

@app.get("/api/me")
def me():

    user, error = require_user()

    if error:

        return error


    return jsonify({
        "success": True,
        "uid": user["uid"],
        "email": user.get("email")
    })


# ============================================================
# GERÄT REGISTRIEREN
# ============================================================

@app.post("/api/devices/register")
def register_device():

    user, error = require_user()

    if error:

        return error


    data = request.get_json(
        silent=True
    ) or {}


    name = data.get(
        "name",
        "Raspberry Pi"
    ).strip()


    if not name:

        name = "Raspberry Pi"


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

        "last_seen": None,

        "system": {},

        "apps": []

    }


    with devices_lock:

        devices[
            device_id
        ] = device


    return jsonify({

        "success": True,

        "device": {

            "id": device_id,

            "name": name,

            "token": device_token

        }

    })


# ============================================================
# GERÄTE AUFLISTEN
# ============================================================

@app.get("/api/devices")
def list_devices():

    user, error = require_user()

    if error:

        return error


    result = []


    with devices_lock:

        for device in devices.values():

            if device["uid"] != user["uid"]:

                continue


            result.append({

                "id": device["id"],

                "name": device["name"],

                "online": device["online"],

                "last_seen": device["last_seen"],

                "system": device["system"],

                "apps": device["apps"]

            })


    return jsonify({

        "success": True,

        "devices": result

    })


# ============================================================
# EIN GERÄT
# ============================================================

@app.get("/api/devices/<device_id>")
def get_device(device_id):

    user, error = require_user()

    if error:

        return error


    with devices_lock:

        device = devices.get(
            device_id
        )


        if device is None:

            return jsonify({

                "success": False,

                "error": "Gerät nicht gefunden."

            }), 404


        if device["uid"] != user["uid"]:

            return jsonify({

                "success": False,

                "error": "Kein Zugriff."

            }), 403


        return jsonify({

            "success": True,

            "device": {

                "id": device["id"],

                "name": device["name"],

                "online": device["online"],

                "last_seen": device["last_seen"],

                "system": device["system"],

                "apps": device["apps"]

            }

        })


# ============================================================
# PI WEBSOCKET
# ============================================================

@app.route(
    "/ws/device",
    websocket=True
)
def device_websocket():

    ws = Server.accept(
        request.environ
    )


    device_id = None


    try:

        # ----------------------------------------------------
        # Erste Nachricht
        # ----------------------------------------------------

        raw = ws.receive()


        if not raw:

            ws.close()

            return ""


        data = json.loads(
            raw
        )


        if data.get("type") != "authenticate":

            ws.send(
                json.dumps({
                    "type": "error",
                    "error": "Authentifizierung erforderlich."
                })
            )

            ws.close()

            return ""


        device_id = data.get(
            "device_id"
        )

        token = data.get(
            "token"
        )


        if not device_id or not token:

            ws.send(
                json.dumps({
                    "type": "error",
                    "error": "Gerätedaten fehlen."
                })
            )

            ws.close()

            return ""


        # ----------------------------------------------------
        # Gerät prüfen
        # ----------------------------------------------------

        with devices_lock:

            device = devices.get(
                device_id
            )


            if device is None:

                ws.send(
                    json.dumps({
                        "type": "error",
                        "error": "Gerät nicht gefunden."
                    })
                )

                ws.close()

                return ""


            if not secrets.compare_digest(
                device["token"],
                token
            ):

                ws.send(
                    json.dumps({
                        "type": "error",
                        "error": "Ungültiger Token."
                    })
                )

                ws.close()

                return ""


            device["online"] = True

            device["last_seen"] = now()


        # ----------------------------------------------------
        # Verbindung speichern
        # ----------------------------------------------------

        with connections_lock:

            connections[
                device_id
            ] = ws


        ws.send(
            json.dumps({
                "type": "authenticated"
            })
        )


        # ----------------------------------------------------
        # Nachrichten vom Pi
        # ----------------------------------------------------

        while True:

            raw = ws.receive()


            if raw is None:

                break


            try:

                message = json.loads(
                    raw
                )

            except Exception:

                continue


            message_type = message.get(
                "type"
            )


            # ------------------------------------------------
            # Heartbeat
            # ------------------------------------------------

            if message_type == "heartbeat":

                with devices_lock:

                    if device_id in devices:

                        devices[
                            device_id
                        ]["online"] = True

                        devices[
                            device_id
                        ]["last_seen"] = now()


                ws.send(
                    json.dumps({
                        "type": "heartbeat_ack"
                    })
                )


            # ------------------------------------------------
            # Systeminformationen
            # ------------------------------------------------

            elif message_type == "system":

                with devices_lock:

                    if device_id in devices:

                        devices[
                            device_id
                        ]["system"] = message.get(
                            "system",
                            {}
                        )


            # ------------------------------------------------
            # Apps
            # ------------------------------------------------

            elif message_type == "apps":

                with devices_lock:

                    if device_id in devices:

                        devices[
                            device_id
                        ]["apps"] = message.get(
                            "apps",
                            []
                        )


            # ------------------------------------------------
            # Command Result
            # ------------------------------------------------

            elif message_type == "command_result":

                # Die Website bekommt das Ergebnis
                # über die REST-Abfrage bzw. zukünftige
                # Erweiterung.

                pass


    except ConnectionClosed:

        pass

    except Exception as error:

        print(
            "WebSocket error:",
            error
        )

    finally:

        if device_id:

            with connections_lock:

                if connections.get(
                    device_id
                ) is ws:

                    del connections[
                        device_id
                    ]


            with devices_lock:

                if device_id in devices:

                    devices[
                        device_id
                    ]["online"] = False


    return ""


# ============================================================
# BEFEHL AN PI
# ============================================================

@app.post(
    "/api/devices/<device_id>/command"
)
def send_command(device_id):

    user, error = require_user()

    if error:

        return error


    data = request.get_json(
        silent=True
    ) or {}


    command = data.get(
        "command"
    )


    allowed_commands = {

        "install",

        "remove",

        "update",

        "system",

        "apps",

        "reboot",

        "shutdown"

    }


    if command not in allowed_commands:

        return jsonify({

            "success": False,

            "error": "Unbekannter Befehl."

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


        if device["uid"] != user["uid"]:

            return jsonify({

                "success": False,

                "error": "Kein Zugriff."

            }), 403


    with connections_lock:

        ws = connections.get(
            device_id
        )


    if ws is None:

        return jsonify({

            "success": False,

            "error": "Raspberry Pi ist offline."

        }), 409


    message = {

        "type": "command",

        "id": secrets.token_urlsafe(
            16
        ),

        "command": command,

        "packages": data.get(
            "packages",
            []
        )

    }


    try:

        ws.send(
            json.dumps(
                message
            )
        )

    except Exception:

        return jsonify({

            "success": False,

            "error": "Befehl konnte nicht gesendet werden."

        }), 500


    return jsonify({

        "success": True,

        "command_id": message["id"]

    })


# ============================================================
# START
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

        port=port,

        debug=False

    )
