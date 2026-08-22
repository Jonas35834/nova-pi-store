import os
import platform
import socket
import subprocess
import time
import json
import logging

import requests


# ============================================================
# CONFIG
# ============================================================

SERVER_URL = os.environ.get(
    "NOVA_PI_STORE_SERVER",
    "https://nova-pi-store.onrender.com"
).rstrip("/")

AGENT_ID_FILE = "/var/lib/nova-pi-store/agent-id"
TOKEN_FILE = "/var/lib/nova-pi-store/token"

POLL_INTERVAL = int(
    os.environ.get(
        "NOVA_PI_STORE_POLL_INTERVAL",
        "10"
    )
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("nova-pi-store-agent")


# ============================================================
# FILE HELPERS
# ============================================================

def ensure_directory():

    directory = "/var/lib/nova-pi-store"

    os.makedirs(
        directory,
        exist_ok=True
    )


def read_file(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return file.read().strip()

    except FileNotFoundError:

        return None


def write_file(path, value):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(value)

    try:

        os.chmod(
            path,
            0o600
        )

    except Exception:
        pass


# ============================================================
# AGENT ID
# ============================================================

def get_agent_id():

    return read_file(
        AGENT_ID_FILE
    )


def get_token():

    return read_file(
        TOKEN_FILE
    )


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def get_system_info():

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "architecture": platform.architecture()[0],
        "python": platform.python_version()
    }


# ============================================================
# REGISTER
# ============================================================

def register():

    system = get_system_info()

    payload = {
        "hostname": system["hostname"],
        "architecture": system["architecture"],
        "os": system["platform"],
        "version": system["release"]
    }

    try:

        response = requests.post(
            f"{SERVER_URL}/api/agent/register",
            json=payload,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            raise RuntimeError(
                data.get(
                    "error",
                    "Registrierung fehlgeschlagen"
                )
            )

        agent_id = data["agent_id"]
        token = data["token"]

        write_file(
            AGENT_ID_FILE,
            agent_id
        )

        write_file(
            TOKEN_FILE,
            token
        )

        logger.info(
            "Agent registriert: %s",
            agent_id
        )

        return agent_id, token

    except Exception as error:

        logger.error(
            "Registrierung fehlgeschlagen: %s",
            error
        )

        return None, None


# ============================================================
# HEARTBEAT
# ============================================================

def heartbeat(agent_id, token):

    system = get_system_info()

    payload = {
        "agent_id": agent_id,
        "hostname": system["hostname"],
        "system": system
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:

        response = requests.post(
            f"{SERVER_URL}/api/agent/heartbeat",
            json=payload,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        return True

    except Exception as error:

        logger.error(
            "Heartbeat fehlgeschlagen: %s",
            error
        )

        return False


# ============================================================
# PACKAGE COMMANDS
# ============================================================

def run_command(command):

    logger.info(
        "Befehl: %s",
        " ".join(command)
    )

    try:

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600
        )

        return {
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Befehl hat das Zeitlimit überschritten"
        }

    except Exception as error:

        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(error)
        }


# ============================================================
# TASK EXECUTION
# ============================================================

def execute_task(task):

    action = task.get("action")
    package = task.get("package")

    task_id = task["task_id"]

    logger.info(
        "Task %s: %s %s",
        task_id,
        action,
        package or ""
    )

    if action in [
        "install",
        "uninstall"
    ] and not package:

        return {
            "success": False,
            "error": "Kein Paket angegeben"
        }

    if action == "install":

        result = run_command([
            "sudo",
            "apt-get",
            "install",
            "-y",
            package
        ])

    elif action == "uninstall":

        result = run_command([
            "sudo",
            "apt-get",
            "remove",
            "-y",
            package
        ])

    elif action == "update":

        result = run_command([
            "sudo",
            "apt-get",
            "update"
        ])

        if result["success"]:

            result = run_command([
                "sudo",
                "apt-get",
                "upgrade",
                "-y"
            ])

    elif action == "refresh":

        result = run_command([
            "sudo",
            "apt-get",
            "update"
        ])

    elif action == "status":

        result = run_command([
            "dpkg-query",
            "-W",
            "-f=${Package} ${Version}\n"
        ])

    else:

        return {
            "success": False,
            "error": f"Unbekannte Aktion: {action}"
        }

    return result


# ============================================================
# SEND TASK RESULT
# ============================================================

def send_task_result(
    task_id,
    status,
    result,
    token
):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "status": status,
        "result": result
    }

    try:

        response = requests.post(
            f"{SERVER_URL}/api/tasks/{task_id}/result",
            json=payload,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        return True

    except Exception as error:

        logger.error(
            "Task-Ergebnis konnte nicht gesendet werden: %s",
            error
        )

        return False


# ============================================================
# GET TASKS
# ============================================================

def get_tasks(agent_id, token):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:

        response = requests.get(
            f"{SERVER_URL}/api/agent/{agent_id}/tasks",
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            return []

        return data.get(
            "tasks",
            []
        )

    except Exception as error:

        logger.error(
            "Tasks konnten nicht abgerufen werden: %s",
            error
        )

        return []


# ============================================================
# PROCESS TASKS
# ============================================================

def process_tasks(
    agent_id,
    token
):

    task_list = get_tasks(
        agent_id,
        token
    )

    for task in task_list:

        task_id = task["task_id"]

        send_task_result(
            task_id,
            "running",
            {
                "message": "Task gestartet"
            },
            token
        )

        result = execute_task(
            task
        )

        if result.get("success"):

            status = "success"

        else:

            status = "failed"

        send_task_result(
            task_id,
            status,
            result,
            token
        )


# ============================================================
# MAIN
# ============================================================

def main():

    ensure_directory()

    agent_id = get_agent_id()
    token = get_token()

    if not agent_id or not token:

        logger.info(
            "Kein Agent registriert."
        )

        agent_id, token = register()

        if not agent_id or not token:

            logger.error(
                "Agent konnte nicht registriert werden."
            )

            return 1

    logger.info(
        "Nova Pi Store Agent gestartet."
    )

    logger.info(
        "Server: %s",
        SERVER_URL
    )

    while True:

        heartbeat(
            agent_id,
            token
        )

        process_tasks(
            agent_id,
            token
        )

        time.sleep(
            POLL_INTERVAL
        )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )