#!/usr/bin/env python3

import json
import os
import platform
import socket
import subprocess
import time

from simple_websocket import Client


# ============================================================
# KONFIGURATION
# ============================================================

SERVER = os.environ.get(
    "NOVA_PI_STORE_SERVER"
)

DEVICE_ID = os.environ.get(
    "NOVA_PI_STORE_DEVICE_ID"
)

DEVICE_TOKEN = os.environ.get(
    "NOVA_PI_STORE_TOKEN"
)


if not SERVER:

    raise RuntimeError(
        "NOVA_PI_STORE_SERVER fehlt."
    )


if not DEVICE_ID:

    raise RuntimeError(
        "NOVA_PI_STORE_DEVICE_ID fehlt."
    )


if not DEVICE_TOKEN:

    raise RuntimeError(
        "NOVA_PI_STORE_TOKEN fehlt."
    )


# ============================================================
# WEBSOCKET URL
# ============================================================

SERVER = SERVER.rstrip("/")


if SERVER.startswith(
    "https://"
):

    WS_URL = (
        "wss://"
        + SERVER[
            len("https://"):
        ]
        + "/ws/device"
    )

elif SERVER.startswith(
    "http://"
):

    WS_URL = (
        "ws://"
        + SERVER[
            len("http://"):
        ]
        + "/ws/device"
    )

else:

    WS_URL = (
        "wss://"
        + SERVER
        + "/ws/device"
    )


# ============================================================
# SYSTEM
# ============================================================

def get_system():

    try:

        hostname = socket.gethostname()


        uptime = subprocess.check_output(
            [
                "uptime",
                "-p"
            ],
            text=True
        ).strip()


        memory = subprocess.check_output(
            [
                "free",
                "-m"
            ],
            text=True
        )


        disk = subprocess.check_output(
            [
                "df",
                "-h",
                "/"
            ],
            text=True
        )


        return {

            "hostname": hostname,

            "platform": platform.platform(),

            "architecture": platform.machine(),

            "uptime": uptime,

            "memory": memory,

            "disk": disk

        }


    except Exception as error:

        return {

            "error": str(error)

        }


# ============================================================
# INSTALLIERTE APPS
# ============================================================

def get_installed_apps():

    try:

        output = subprocess.check_output(

            [

                "dpkg-query",

                "-W",

                "-f=${binary:Package}\n"

            ],

            text=True,

            stderr=subprocess.DEVNULL

        )


        return sorted(
            output.splitlines()
        )


    except Exception:

        return []


# ============================================================
# PAKETNAME PRÜFEN
# ============================================================

def valid_package(
    package
):

    if not isinstance(
        package,
        str
    ):

        return False


    if not package:

        return False


    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        ".+-_"
    )


    return all(
        char in allowed
        for char in package
    )


# ============================================================
# BEFEHL AUSFÜHREN
# ============================================================

def execute_command(
    message
):

    command = message.get(
        "command"
    )

    packages = message.get(
        "packages",
        []
    )


    # --------------------------------------------------------
    # System
    # --------------------------------------------------------

    if command == "system":

        return {

            "success": True,

            "system": get_system()

        }


    # --------------------------------------------------------
    # Apps
    # --------------------------------------------------------

    if command == "apps":

        return {

            "success": True,

            "apps": get_installed_apps()

        }


    # --------------------------------------------------------
    # Paketbefehle
    # --------------------------------------------------------

    if command in (
        "install",
        "remove",
        "update"
    ):

        if not isinstance(
            packages,
            list
        ):

            return {

                "success": False,

                "error":
                    "Pakete müssen eine Liste sein."

            }


        if not packages:

            return {

                "success": False,

                "error":
                    "Keine Pakete angegeben."

            }


        for package in packages:

            if not valid_package(
                package
            ):

                return {

                    "success": False,

                    "error":
                        f"Ungültiger Paketname: {package}"

                }


        if command == "install":

            cmd = [

                "sudo",

                "/usr/local/bin/"
                "nova-pi-store-install"

            ] + packages


        elif command == "remove":

            cmd = [

                "sudo",

                "/usr/local/bin/"
                "nova-pi-store-remove"

            ] + packages


        else:

            cmd = [

                "sudo",

                "/usr/local/bin/"
                "nova-pi-store-update"

            ] + packages


        try:

            result = subprocess.run(

                cmd,

                text=True,

                stdout=subprocess.PIPE,

                stderr=subprocess.STDOUT,

                timeout=600

            )


            return {

                "success":
                    result.returncode == 0,

                "output":
                    result.stdout,

                "returncode":
                    result.returncode

            }


        except subprocess.TimeoutExpired:

            return {

                "success": False,

                "error":
                    "Befehl wurde wegen Timeout beendet."

            }


    # --------------------------------------------------------
    # Neustart
    # --------------------------------------------------------

    if command == "reboot":

        subprocess.Popen(
            [
                "sudo",
                "/sbin/reboot"
            ]
        )


        return {

            "success": True

        }


    # --------------------------------------------------------
    # Herunterfahren
    # --------------------------------------------------------

    if command == "shutdown":

        subprocess.Popen(
            [
                "sudo",
                "/sbin/shutdown",
                "-h",
                "now"
            ]
        )


        return {

            "success": True

        }


    return {

        "success": False,

        "error":
            "Unbekannter Befehl."

    }


# ============================================================
# HAUPTSCHLEIFE
# ============================================================

def connect():

    print(
        "Verbinde mit:",
        WS_URL
    )


    ws = Client.connect(
        WS_URL,
        ping_interval=25
    )


    ws.send(
        json.dumps({

            "type":
                "authenticate",

            "device_id":
                DEVICE_ID,

            "token":
                DEVICE_TOKEN

        })
    )


    response = ws.receive()


    if not response:

        raise RuntimeError(
            "Server hat nicht geantwortet."
        )


    data = json.loads(
        response
    )


    if data.get(
        "type"
    ) != "authenticated":

        raise RuntimeError(
            "Authentifizierung fehlgeschlagen."
        )


    print(
        "Nova Pi Store Agent verbunden."
    )


    # --------------------------------------------------------
    # Initialdaten
    # --------------------------------------------------------

    ws.send(
        json.dumps({

            "type":
                "system",

            "system":
                get_system()

        })
    )


    ws.send(
        json.dumps({

            "type":
                "apps",

            "apps":
                get_installed_apps()

        })
    )


    last_heartbeat = 0


    while True:

        # ----------------------------------------------------
        # Heartbeat
        # ----------------------------------------------------

        if (
            time.time()
            - last_heartbeat
            > 20
        ):

            ws.send(
                json.dumps({

                    "type":
                        "heartbeat"

                })
            )


            last_heartbeat = time.time()


        # ----------------------------------------------------
        # Nachrichten
        # ----------------------------------------------------

        try:

            message = ws.receive()


        except Exception:

            break


        if message is None:

            break


        data = json.loads(
            message
        )


        message_type = data.get(
            "type"
        )


        # ----------------------------------------------------
        # Command
        # ----------------------------------------------------

        if message_type == "command":

            command_id = data.get(
                "id"
            )


            result = execute_command(
                data
            )


            ws.send(
                json.dumps({

                    "type":
                        "command_result",

                    "id":
                        command_id,

                    **result

                })
            )


            # Nach Paketänderungen aktualisieren

            if data.get(
                "command"
            ) in (
                "install",
                "remove",
                "update"
            ):

                ws.send(
                    json.dumps({

                        "type":
                            "apps",

                        "apps":
                            get_installed_apps()

                    })
                )


# ============================================================
# START
# ============================================================

def main():

    while True:

        try:

            connect()

        except Exception as error:

            print(
                "Verbindung verloren:",
                error
            )


        print(
            "Neue Verbindung in 5 Sekunden..."
        )


        time.sleep(5)


if __name__ == "__main__":

    main()
