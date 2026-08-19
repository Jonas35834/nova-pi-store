import json
import os
import re
import subprocess
import threading
from flask import Flask, jsonify, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_FILE = os.path.join(BASE_DIR, "apps.json")

app = Flask(__name__)

state = {
    "running": False,
    "app": None,
    "output": "",
    "success": None
}

state_lock = threading.Lock()


def load_apps():
    with open(APPS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)["apps"]


def find_app(app_id):
    for item in load_apps():
        if item["id"] == app_id:
            return item

    return None


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

    return result.stdout.strip() == "install ok installed"


def app_is_installed(item):
    packages = item.get("packages", [])

    if not packages:
        return False

    return all(
        is_installed(package)
        for package in packages
    )


def valid_package_name(package):
    return bool(
        re.fullmatch(
            r"[a-zA-Z0-9.+_-]+",
            package
        )
    )


def install_worker(app_id):

    global state

    with state_lock:

        item = find_app(app_id)

        if item is None:
            state["output"] = "App nicht gefunden."
            state["success"] = False
            state["running"] = False
            return

        state["running"] = True
        state["app"] = app_id
        state["output"] = ""
        state["success"] = None

    try:

        if item.get("type") != "apt":
            raise Exception(
                "Dieser App-Typ wird noch nicht unterstützt."
            )

        packages = item.get("packages", [])

        if not packages:
            raise Exception(
                "Keine Pakete definiert."
            )

        for package in packages:

            if not valid_package_name(package):
                raise Exception(
                    f"Ungültiger Paketname: {package}"
                )

        command = [
            "sudo",
            "/usr/local/bin/nova-pi-store-install"
        ]

        command.extend(packages)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

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


@app.route("/")
def index():

    apps = load_apps()

    for item in apps:
        item["installed"] = app_is_installed(item)

    return render_template(
        "index.html",
        apps=apps
    )


@app.route("/api/apps")
def api_apps():

    apps = load_apps()

    for item in apps:
        item["installed"] = app_is_installed(item)

    return jsonify(apps)


@app.route(
    "/api/install/<app_id>",
    methods=["POST"]
)
def install(app_id):

    if state["running"]:

        return jsonify({
            "success": False,
            "error": "Es läuft bereits eine Installation."
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


@app.route("/api/status")
def status():

    with state_lock:

        return jsonify({
            "running": state["running"],
            "app": state["app"],
            "output": state["output"],
            "success": state["success"]
        })


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


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
