import os
import json
import win32com.client

print("🚀 app_scanner.py STARTED")  # <-- FORCE PRINT

START_MENU_PATHS = [
    os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
]

OUTPUT_FILE = "backend/data/app_index.json"


def scan_start_menu():
    print("🔍 scan_start_menu() CALLED")

    shell = win32com.client.Dispatch("WScript.Shell")
    apps = {}
    total_lnk = 0

    for base_path in START_MENU_PATHS:
        print("➡ Scanning:", base_path)

        if not os.path.exists(base_path):
            print("❌ Path does not exist")
            continue

        for root, _, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith(".lnk"):
                    total_lnk += 1
                    shortcut_path = os.path.join(root, file)

                    try:
                        shortcut = shell.CreateShortcut(shortcut_path)
                        target = shortcut.Targetpath

                        if target:
                            app_name = os.path.splitext(file)[0].lower()
                            apps[app_name] = target

                    except Exception as e:
                        print("⚠ Error reading shortcut:", shortcut_path, e)

    print(f"🔎 Total .lnk found: {total_lnk}")
    print(f"📦 Apps indexed: {len(apps)}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2)

    print("✅ App index written to", OUTPUT_FILE)


# 🔥 THIS IS THE MOST IMPORTANT LINE
if __name__ == "__main__":
    scan_start_menu()
