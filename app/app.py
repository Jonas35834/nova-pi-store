import json
import os
import re
import subprocess
import threading

from flask import Flask, jsonify, render_template


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APPS_FILE = os.path.join(
    BASE_DIR,
    "apps.json"
)


app = Flask(__name__)


state = {
    "running": False,
    "app": None,
    "action": None,
    "output": "",
    "success": None
}


state_lock = threading.Lock()


# ============================================================
# APP-DATEN
# ============================================================

def load_apps():

    with open(
        APPS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)["apps"]


def find_app(app_id):

    for item in load_apps():

        if item["id"] == app_id:
            return item

    return None


# ============================================================
# APT / DPKG
# ============================================================

def valid_package_name(package):

    return bool(
        re.fullmatch(
            r"[a-zA-Z0-9.+_-]+",
            package
        )
    )


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


def get_installed_version(package):

    result = subprocess.run(
        [
            "dpkg-query",
            "-W",
            "-f=${Version}",
            package
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    version = result.stdout.strip()

    if not version:
        return None

    return version


def get_candidate_version(package):

    result = subprocess.run(
        [
            "apt-cache",
            "policy",
            package
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    for line in result.stdout.splitlines():

        line = line.strip()

        if line.startswith("Candidate:"):

            version = line.split(
                ":",
                1
            )[1].strip()

            if version and version != "(none)":
                return version

    return None


def has_update(package):

    installed = get_installed_version(
        package
    )

    candidate = get_candidate_version(
        package
    )

    if not installed or not candidate:
        return False

    result = subprocess.run(
        [
            "dpkg",
            "--compare-versions",
            candidate,
            "gt",
            installed
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return result.returncode == 0


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


def app_has_update(item):

    if not app_is_installed(item):
        return False

    packages = item.get(
        "packages",
        []
    )

    return any(
        has_update(package)
        for package in packages
    )


def get_app_versions(item):

    packages = item.get(
        "packages",
        []
    )

    versions = []

    for package in packages:

        installed = get_installed_version(
            package
        )

        candidate = get_candidate_version(
            package
        )

        versions.append({
            "package": package,
            "installed": installed,
            "candidate": candidate
        })

    return versions


# ============================================================
# APP STATUS
# ============================================================

def prepare_app(item):

    result = dict(item)

    result["installed"] = app_is_installed(
        item
    )

    result["update_available"] = (
        app_has_update(item)
        if result["installed"]
        else False
    )

    result["versions"] = get_app_versions(
        item
    )

    return result


# ============================================================
# INSTALL / REMOVE / UPDATE
# ============================================================

def run_worker(
    app_id,
    action
):

    global state

    with state_lock:

        item = find_app(app_id)

        if item is None:

            state["output"] = (
                "App nicht gefunden."
            )

            state["success"] = False
            state["running"] = False

            return

        state["running"] = True
        state["app"] = app_id
        state["action"] = action
        state["output"] = ""
        state["success"] = None


    try:

        if item.get("type") != "apt":

            raise Exception(
                "Dieser App-Typ wird noch nicht unterstützt."
            )


        packages = item.get(
            "packages",
            []
        )


        if not packages:

            raise Exception(
                "Keine Pakete definiert."
            )


        for package in packages:

            if not valid_package_name(
                package
            ):

                raise Exception(
                    f"Ungültiger Paketname: {package}"
                )


        # ----------------------------------------------------
        # INSTALL
        # ----------------------------------------------------

        if action == "install":

            command = [
                "sudo",
                "/usr/local/bin/"
                "nova-pi-store-install"
            ]

            command.extend(packages)


        # ----------------------------------------------------
        # REMOVE
        # ----------------------------------------------------

        elif action == "remove":

            command = [
                "sudo",
                "/usr/local/bin/"
                "nova-pi-store-remove"
            ]

            command.extend(packages)


        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------

        elif action == "update":

            command = [
                "sudo",
                "/usr/local/bin/"
                "nova-pi-store-update"
            ]

            command.extend(packages)


        else:

            raise Exception(
                "Unbekannte Aktion."
            )


        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )


        if process.stdout:

            for line in process.stdout:

                with state_lock:

                    state["output"] += line


        process.wait()


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
# WEBSEITE
# ============================================================

@app.route("/")
def index():

    apps = [
        prepare_app(item)
        for item in load_apps()
    ]

    return render_template(
        "index.html",
        apps=apps
    )


# ============================================================
# API: APPS
# ============================================================

@app.route("/api/apps")
def api_apps():

    apps = [
        prepare_app(item)
        for item in load_apps()
    ]

    return jsonify(apps)


# ============================================================
# API: ACTION
# ============================================================

@app.route(
    "/api/<action>/<app_id>",
    methods=["POST"]
)
def action(
    action,
    app_id
):

    if action not in (
        "install",
        "remove",
        "update"
    ):

        return jsonify({
            "success": False,
            "error": "Ungültige Aktion."
        }), 400


    with state_lock:

        if state["running"]:

            return jsonify({
                "success": False,
                "error": (
                    "Es läuft bereits "
                    "eine Aktion."
                )
            }), 409


    item = find_app(app_id)


    if item is None:

        return jsonify({
            "success": False,
            "error": "App nicht gefunden."
        }), 404


    thread = threading.Thread(
        target=run_worker,
        args=(
            app_id,
            action
        ),
        daemon=True
    )

    thread.start()


    return jsonify({
        "success": True
    })


# ============================================================
# API: STATUS
# ============================================================

@app.route("/api/status")
def status():

    with state_lock:

        return jsonify({
            "running": state["running"],
            "app": state["app"],
            "action": state["action"],
            "output": state["output"],
            "success": state["success"]
        })


# ============================================================
# API: SYSTEM
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
# START
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
