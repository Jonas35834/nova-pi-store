import os
import json
import secrets
import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(BASE_DIR, "app")

PORT = int(os.environ.get("PORT", "10000"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("nova-pi-store")


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    static_folder=APP_DIR,
    static_url_path=""
)

CORS(app)


# ============================================================
# IN-MEMORY DATA
# ============================================================

# Aktuell verbundene Raspberry Pis.
# Später kann das problemlos durch Firestore ersetzt werden.
agents = {}

# Kleine Aufgabenwarteschlange.
tasks = {}


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def generate_id(prefix):
    return f"{prefix}_{secrets.token_urlsafe(12)}"


def get_json():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {}

    return data


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def index():
    """
    Liefert die Weboberfläche.
    """

    index_file = os.path.join(APP_DIR, "index.html")

    if not os.path.exists(index_file):
        return jsonify({
            "error": "Frontend nicht gefunden"
        }), 404

    return send_from_directory(APP_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """
    Liefert CSS, JavaScript, Bilder usw.
    """

    file_path = os.path.join(APP_DIR, path)

    if os.path.isfile(file_path):
        return send_from_directory(APP_DIR, path)

    return jsonify({
        "error": "Datei nicht gefunden"
    }), 404


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():
    """
    Render Health Check.
    """

    return jsonify({
        "status": "ok",
        "service": "nova-pi-store",
        "time": now_iso()
    })


# ============================================================
# API INFO
# ============================================================

@app.route("/api")
def api_info():

    return jsonify({
        "name": "Nova Pi Store API",
        "version": "1.0.0",
        "status": "online",
        "time": now_iso()
    })


# ============================================================
# AGENT REGISTRATION
# ============================================================

@app.route("/api/agent/register", methods=["POST"])
def register_agent():

    data = get_json()

    hostname = str(data.get("hostname", "")).strip()
    architecture = str(data.get("architecture", "")).strip()
    os_name = str(data.get("os", "")).strip()
    version = str(data.get("version", "")).strip()

    if not hostname:
        return jsonify({
            "success": False,
            "error": "hostname fehlt"
        }), 400

    agent_id = data.get("agent_id")

    if not agent_id:
        agent_id = generate_id("agent")

    token = secrets.token_urlsafe(32)

    agents[agent_id] = {
        "agent_id": agent_id,
        "hostname": hostname,
        "architecture": architecture,
        "os": os_name,
        "version": version,
        "token": token,
        "registered_at": now_iso(),
        "last_seen": now_iso(),
        "status": "online"
    }

    logger.info(
        "Agent registriert: %s (%s)",
        agent_id,
        hostname
    )

    return jsonify({
        "success": True,
        "agent_id": agent_id,
        "token": token,
        "server_time": now_iso()
    })


# ============================================================
# AGENT HEARTBEAT
# ============================================================

@app.route("/api/agent/heartbeat", methods=["POST"])
def agent_heartbeat():

    data = get_json()

    agent_id = data.get("agent_id")

    if not agent_id:
        return jsonify({
            "success": False,
            "error": "agent_id fehlt"
        }), 400

    agent = agents.get(agent_id)

    if not agent:
        return jsonify({
            "success": False,
            "error": "Agent nicht registriert"
        }), 404

    agent["last_seen"] = now_iso()
    agent["status"] = "online"

    if "hostname" in data:
        agent["hostname"] = data["hostname"]

    if "system" in data:
        agent["system"] = data["system"]

    if "packages" in data:
        agent["packages"] = data["packages"]

    return jsonify({
        "success": True,
        "server_time": now_iso()
    })


# ============================================================
# AGENTS
# ============================================================

@app.route("/api/agents", methods=["GET"])
def get_agents():

    result = []

    for agent in agents.values():

        public_agent = dict(agent)

        # Token niemals an Frontend schicken
        public_agent.pop("token", None)

        result.append(public_agent)

    return jsonify({
        "success": True,
        "agents": result
    })


@app.route("/api/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id):

    agent = agents.get(agent_id)

    if not agent:
        return jsonify({
            "success": False,
            "error": "Agent nicht gefunden"
        }), 404

    public_agent = dict(agent)
    public_agent.pop("token", None)

    return jsonify({
        "success": True,
        "agent": public_agent
    })


# ============================================================
# TASKS
# ============================================================

@app.route("/api/tasks", methods=["GET"])
def get_tasks():

    return jsonify({
        "success": True,
        "tasks": list(tasks.values())
    })


@app.route("/api/tasks", methods=["POST"])
def create_task():

    data = get_json()

    agent_id = data.get("agent_id")
    action = data.get("action")

    if not agent_id:
        return jsonify({
            "success": False,
            "error": "agent_id fehlt"
        }), 400

    if not action:
        return jsonify({
            "success": False,
            "error": "action fehlt"
        }), 400

    if agent_id not in agents:
        return jsonify({
            "success": False,
            "error": "Agent nicht gefunden"
        }), 404

    allowed_actions = [
        "install",
        "uninstall",
        "update",
        "status",
        "refresh"
    ]

    if action not in allowed_actions:
        return jsonify({
            "success": False,
            "error": "Ungültige Aktion"
        }), 400

    task_id = generate_id("task")

    task = {
        "task_id": task_id,
        "agent_id": agent_id,
        "action": action,
        "package": data.get("package"),
        "created_at": now_iso(),
        "started_at": None,
        "finished_at": None,
        "status": "pending",
        "result": None
    }

    tasks[task_id] = task

    return jsonify({
        "success": True,
        "task": task
    }), 201


# ============================================================
# AGENT TASK QUEUE
# ============================================================

@app.route("/api/agent/<agent_id>/tasks", methods=["GET"])
def agent_tasks(agent_id):

    if agent_id not in agents:
        return jsonify({
            "success": False,
            "error": "Agent nicht gefunden"
        }), 404

    pending = []

    for task in tasks.values():

        if (
            task["agent_id"] == agent_id
            and task["status"] == "pending"
        ):
            pending.append(task)

    return jsonify({
        "success": True,
        "tasks": pending
    })


# ============================================================
# TASK RESULT
# ============================================================

@app.route("/api/tasks/<task_id>/result", methods=["POST"])
def task_result(task_id):

    task = tasks.get(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error": "Task nicht gefunden"
        }), 404

    data = get_json()

    status = data.get("status")

    if status not in [
        "running",
        "success",
        "failed"
    ]:
        return jsonify({
            "success": False,
            "error": "Ungültiger Status"
        }), 400

    task["status"] = status

    if status == "running":
        task["started_at"] = now_iso()

    if status in ["success", "failed"]:
        task["finished_at"] = now_iso()

    task["result"] = data.get("result")

    return jsonify({
        "success": True
    })


# ============================================================
# STORE
# ============================================================

@app.route("/api/store", methods=["GET"])
def store():

    apps_file = os.path.join(BASE_DIR, "apps.json")

    if not os.path.exists(apps_file):

        return jsonify({
            "success": True,
            "apps": []
        })

    try:

        with open(
            apps_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return jsonify({
                "success": True,
                "apps": data
            })

        if isinstance(data, dict):

            return jsonify({
                "success": True,
                "apps": data.get("apps", [])
            })

    except Exception as error:

        logger.exception("Fehler beim Laden von apps.json")

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    return jsonify({
        "success": True,
        "apps": []
    })


# ============================================================
# SYSTEM
# ============================================================

@app.route("/api/system")
def system():

    return jsonify({
        "service": "Nova Pi Store",
        "server": "Render",
        "time": now_iso(),
        "agents": len(agents),
        "tasks": len(tasks)
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "Route nicht gefunden"
    }), 404


@app.errorhandler(500)
def internal_error(error):

    logger.exception("Interner Serverfehler")

    return jsonify({
        "success": False,
        "error": "Interner Serverfehler"
    }), 500


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=True
    )
