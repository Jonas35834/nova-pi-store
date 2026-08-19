import json
import subprocess
import threading
import os

from flask import Flask, render_template, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_FILE = os.path.join(BASE_DIR, "apps.json")

app = Flask(__name__)

install_state = {
    "running": False,
    "app": None,
    "output": "",
    "success": None
}

lock = threading.Lock()


def load_apps():
    with open(APPS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("apps", [])


def get_app(app_id):
    for item in load_apps():
        if item.get("id") == app_id:
            return item

    return None


def package_installed(package):
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    return result.stdout.strip() == "install ok installed"


def is_installed(app_info):
    packages = app_info.get("packages", [])

    if not packages:
        return False

    return all(package_installed(package) for package in packages)


def run_installation(app_id):
    global install_state

    with lock:
        try:
            app_info = get_app(app_id)

            if not app_info:
                install_state["success"] = False
                install_state["output"] = "App nicht gefunden."
                return

            install_state["running"] = True
            install_state["app"] = app_id
            install_state["output"] = ""
            install_state["success"] = None

            app_type = app_info.get("type")

            if app_type != "apt":
                install_state["output"] = (
                    "Dieser App-Typ wird momentan nicht unterstützt."
                )
                install_state["success"] = False
                return

            packages = app_info.get("packages", [])

            if not packages:
                install_state["output"] = "Keine Pakete angegeben."
                install_state["success"] = False
                return

            # Sicherheitsprüfung:
            # Nur Paketnamen mit erlaubten Zeichen.
            for package in packages:
                if not package.replace("-", "").replace(".", "").replace("+", "").isalnum():
                    install_state["output"] = (
                        f"Ungültiger Paketname: {package}"
                    )
                    install_state["success"] = False
                    return

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
                install_state["output"] += line

            process.wait()

            install_state["success"] = process.returncode == 0

        except Exception as error:
            install_state["output"] += (
                f"\nFehler: {error}\n"
            )
            install_state["success"] = False

        finally:
            install_state["running"] = False


@app.route("/")
def index():
    apps = load_apps()

    for item in apps:
        item["installed"] = is_installed(item)

    return render_template(
        "index.html",
        apps=apps
    )


@app.route("/api/apps")
def api_apps():
    apps = load_apps()

    for item in apps:
        item["installed"] = is_installed(item)

    return jsonify(apps)


@app.route("/api/install/<app_id>", methods=["POST"])
def install(app_id):

    if install_state["running"]:
        return jsonify({
            "success": False,
            "error": "Es läuft bereits eine Installation."
        }), 409

    app_info = get_app(app_id)

    if not app_info:
        return jsonify({
            "success": False,
            "error": "App nicht gefunden."
        }), 404

    thread = threading.Thread(
        target=run_installation,
        args=(app_id,),
        daemon=True
    )

    thread.start()

    return jsonify({
        "success": True
    })


@app.route("/api/status")
def status():
    return jsonify(install_state)


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

        memory = subprocess.check_output(
            ["free", "-m"],
            text=True
        )

        return jsonify({
            "hostname": hostname,
            "uptime": uptime,
            "memory": memory
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
