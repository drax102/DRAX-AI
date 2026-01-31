import json
import subprocess
import os

APP_INDEX_FILE = "backend/data/app_index.json"

STOP_WORDS = ["open", "launch", "start", "the", "app"]


def normalize(text: str):
    text = text.lower()
    for w in STOP_WORDS:
        text = text.replace(w, "")
    return text.strip()


def open_app(command: str):
    if not os.path.exists(APP_INDEX_FILE):
        return "App index not found. Run app_scanner.py first."

    with open(APP_INDEX_FILE, "r", encoding="utf-8") as f:
        apps = json.load(f)

    command = normalize(command)

    # 1️⃣ EXACT MATCH
    for app_name, target in apps.items():
        if command == app_name:
            return launch(target, app_name)

    # 2️⃣ CONTAINS MATCH
    for app_name, target in apps.items():
        if command in app_name:
            return launch(target, app_name)

    # 3️⃣ TOKEN MATCH
    for token in command.split():
        for app_name, target in apps.items():
            if token in app_name:
                return launch(target, app_name)

    return "Application not found"


def launch(target, app_name):
    try:
        # ✅ Microsoft Store / UWP apps
        if target.lower().startswith("shell:"):
            subprocess.Popen(
                ["cmd", "/c", "start", "", target],
                shell=True
            )

        # ✅ Normal desktop EXE
        else:
            subprocess.Popen([target], shell=False)

        return f"Opening {app_name}"

    except Exception as e:
        return f"Failed to open {app_name}: {e}"
