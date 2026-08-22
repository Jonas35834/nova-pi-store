import copy
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
import urllib.error

from flask import Flask, jsonify, render_template


# ============================================================
# Konfiguration
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# GitHub-Pages-Version von apps.json
APPS_URL = (
    "https://jonas35834.github.io/"
    "nova-pi-store/apps.json"
)

# Wie lange die App-Liste lokal zwischengespeichert wird
APPS_CACHE_SECONDS = 60


# ============================================================
# Flask
# ============================================================

app = Flask(__name__)


# ============================================================
# App-Cache
# ============================================================

apps_cache = {
    "apps": None,
    "timestamp": 0,
    "error": None
}

apps_cache_lock = threading.Lock()


# ============================================================
# Installationsstatus
# ============================================================

state = {
    "running": False,
    "app": None,
    "output": "",
    "success": None
}

state_lock = threading.Lock()


# ============================================================
# Apps von GitHub laden
# ============================================================

def load_apps_from_github():

    request = urllib.request.Request(
        APPS_URL,
        headers={
            "User-Agent": "Nova-Pi-Store"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=10
    ) as response:

        data = response.read().decode("utf-8")

    parsed = json.loads(data)

    if not isinstance(parsed, dict):
        raise Exception(
            "Ungültiges apps.json Format."
        )

    apps = parsed.get("apps")

    if not isinstance(apps, list):
        raise Exception(
            "apps.json enthält keine gültige 'apps'-Liste."
        )

    return apps


# ============================================================
# Apps laden
# ============================================================

def load_apps():

    now = time.time()

    with apps_cache_lock:

        cached_apps = apps_cache["apps"]
        cached_time = apps_cache["timestamp"]

        # Cache noch gültig
        if (
            cached_apps is not None
            and now - cached_time < APPS_CACHE_SECONDS
        ):

            return copy.deepcopy(cached_apps)


    # GitHub aktualisieren
    try:

        apps = load_apps_from_github()

        with apps_cache_lock:

            apps_cache["apps"] = apps
            apps_cache["timestamp"] = time.time()
            apps_cache["error"] = None

        return copy.deepcopy(apps)


    except Exception as error:

        print(
            "Fehler beim Laden von apps.json:",
            error
        )

        # Wenn bereits ein alter Cache existiert,
        # diesen weiterverwenden
        with apps_cache_lock:

            if apps_cache["apps"] is not None:

                apps_cache["error"] = str(error)

                return copy.deepcopy(
                    apps_cache["apps"]
                )

        # Noch kein Cache vorhanden
        raise


# ============================================================
# App suchen
# ============================================================

def find_app(app_id):

    for item in load_apps():

        if item.get("id") == app_id:

            return item

    return None


# ============================================================
# Paket installiert?
# ============================================================

def is_installed(package):

    result = subprocess.run(
        [
            "dpkg-query",
            "-W",
            "-f=${Status}",
            package
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    return (
        result.stdout.strip()
        == "install ok installed"
    )


# ============================================================
# App installiert?
# ============================================================

def app_is_installed(item):

    packages = item.get(
        "packages",
        []
    )

    if not packages:

        return False

    return all(
        is_installed(package)
        for package in packages
    )


# ============================================================
# Paketname prüfen
# ============================================================

def valid_package_name(package):

    return bool(
        re.fullmatch(
            r"[a-zA-Z0-9.+_-]+",
            package
        )
    )


# ============================================================
# Installations-Worker
# ============================================================

def install_worker(app_id):

    global state

    with state_lock:

        item = find_app(app_id)

        if item is None:

            state["output"] = (
                "App nicht gefunden.\n"
            )

            state["success"] = False
            state["running"] = False

            return

        state["running"] = True
        state["app"] = app_id
        state["output"] = ""
        state["success"] = None


    try:

        # ------------------------------------------------------
        # Nur APT-Apps erlauben
        # ------------------------------------------------------

        if item.get("type") != "apt":

            raise Exception(
                "Dieser App-Typ wird noch "
                "nicht unterstützt."
            )


        # ------------------------------------------------------
        # Pakete
        # ------------------------------------------------------

        packages = item.get(
            "packages",
            []
        )

        if not packages:

            raise Exception(
                "Keine Pakete definiert."
            )


        # ------------------------------------------------------
        # Paketnamen prüfen
        # ------------------------------------------------------

        for package in packages:

            if not valid_package_name(
                package
            ):

                raise Exception(
                    "Ungültiger Paketname: "
                    + str(package)
                )


        # ------------------------------------------------------
        # Installation
        # ------------------------------------------------------

        command = [
            "sudo",
            "/usr/local/bin/"
            "nova-pi-store-install"
        ]

        command.extend(packages)


        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )


        # ------------------------------------------------------
        # Ausgabe lesen
        # ------------------------------------------------------

        if process.stdout:

            for line in process.stdout:

                with state_lock:

                    state["output"] += line


        process.wait()


        # ------------------------------------------------------
        # Ergebnis
        # ------------------------------------------------------

        with state_lock:

            state["success"] = (
                process.returncode == 0
            )


    except Exception as error:

        with state_lock:

            state["output"] += (
                "\nFEHLER: "
                + str(error)
                + "\n"
            )

            state["success"] = False


    finally:

        with state_lock:

            state["running"] = False


# ============================================================
# Startseite
# ============================================================

@app.route("/")
def index():

    try:

        apps = load_apps()

    except Exception as error:

        return (
            "Nova Pi Store konnte die App-Liste "
            "nicht laden: "
            + str(error),
            503
        )


    for item in apps:

        item["installed"] = (
            app_is_installed(item)
        )


    return render_template(
        "index.html",
        apps=apps
    )


# ============================================================
# API: Apps
# ============================================================

@app.route("/api/apps")
def api_apps():

    try:

        apps = load_apps()

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 503


    for item in apps:

        item["installed"] = (
            app_is_installed(item)
        )


    return jsonify({
        "success": True,
        "apps": apps
    })


# ============================================================
# API: Apps aktualisieren
# ============================================================

@app.route("/api/apps/refresh", methods=["POST"])
def refresh_apps():

    try:

        apps = load_apps_from_github()

        with apps_cache_lock:

            apps_cache["apps"] = apps
            apps_cache["timestamp"] = time.time()
            apps_cache["error"] = None

        return jsonify({
            "success": True,
            "count": len(apps)
        })


    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 503


# ============================================================
# API: Repository-Status
# ============================================================

@app.route("/api/repository")
def repository_status():

    with apps_cache_lock:

        timestamp = apps_cache["timestamp"]
        error = apps_cache["error"]
        cached = apps_cache["apps"] is not None


    if timestamp:

        age = int(
            time.time() - timestamp
        )

    else:

        age = None


    return jsonify({
        "url": APPS_URL,
        "cached": cached,
        "cache_age_seconds": age,
        "cache_seconds": APPS_CACHE_SECONDS,
        "error": error
    })


# ============================================================
# API: Installation
# ============================================================

@app.route(
    "/api/install/<app_id>",
    methods=["POST"]
)
def install(app_id):

    with state_lock:

        if state["running"]:

            return jsonify({
                "success": False,
                "error": (
                    "Es läuft bereits "
                    "eine Installation."
                )
            }), 409


    item = find_app(app_id)


    if item is None:

        return jsonify({
            "success": False,
            "error": "App nicht gefunden."
        }), 404


    thread = threading.Thread(
        target=install_worker,
        args=(app_id,),
        daemon=True
    )

    thread.start()


    return jsonify({
        "success": True
    })


# ============================================================
# API: Status
# ============================================================

@app.route("/api/status")
def status():

    with state_lock:

        return jsonify({
            "running": state["running"],
            "app": state["app"],
            "output": state["output"],
            "success": state["success"]
        })


# ============================================================
# API: System
# ============================================================

@app.route("/api/system")
def system():

    try:

        hostname = subprocess.check_output(
            ["hostname"],
            text=True
        ).strip()


        uptime = subprocess.check_output(
            ["uptime", "-p"],
            text=True
        ).strip()


        return jsonify({
            "hostname": hostname,
            "uptime": uptime
        })


    except Exception as error:

        return jsonify({
            "error": str(error)
        })


# ============================================================
# Start
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
