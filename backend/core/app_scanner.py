import os
import json
import subprocess
import winreg
import threading

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

OUTPUT_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "app_index.json"))

START_MENU_PATHS = [
    os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
]

# Standard Built-in Windows Apps
BUILTIN_APPS = {
    "notepad": r"C:\Windows\System32\notepad.exe",
    "calculator": r"C:\Windows\System32\calc.exe",
    "calc": r"C:\Windows\System32\calc.exe",
    "paint": r"C:\Windows\System32\mspaint.exe",
    "file explorer": r"C:\Windows\explorer.exe",
    "explorer": r"C:\Windows\explorer.exe",
    "cmd": r"C:\Windows\System32\cmd.exe",
    "command prompt": r"C:\Windows\System32\cmd.exe",
    "powershell": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "task manager": r"C:\Windows\System32\Taskmgr.exe",
    "control panel": r"C:\Windows\System32\control.exe",
}


def scan_start_menu(apps: dict):
    """Fast scan of Windows Start Menu shortcuts (.lnk files)."""
    if win32com is None or pythoncom is None:
        return

    try:
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        for base_path in START_MENU_PATHS:
            if not os.path.exists(base_path):
                continue
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        try:
                            full_path = os.path.join(root, file)
                            shortcut = shell.CreateShortcut(full_path)
                            target = shortcut.Targetpath
                            if target and os.path.exists(target):
                                name = os.path.splitext(file)[0].lower()
                                apps[name] = target
                        except Exception:
                            pass
        pythoncom.CoUninitialize()
    except Exception as e:
        print(f"Start menu scan notice: {e}")


def scan_registry(apps: dict):
    """Fast scan of registered Windows App Paths from Registry."""
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
    ]

    for root_key, reg_path in reg_paths:
        try:
            key = winreg.OpenKey(root_key, reg_path)
            subkeys_count = winreg.QueryInfoKey(key)[0]
            for i in range(subkeys_count):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    path, _ = winreg.QueryValueEx(subkey, "")
                    if path and os.path.exists(path):
                        clean_name = subkey_name.lower().replace(".exe", "")
                        apps[clean_name] = path
                except Exception:
                    pass
        except Exception:
            pass


def scan_uwp_apps(apps: dict):
    """Fast scan of UWP Microsoft Store apps via PowerShell Get-StartApps."""
    try:
        cmd = 'powershell -NoProfile -Command "Get-StartApps | ConvertTo-Json"'
        output = subprocess.check_output(cmd, shell=True, timeout=5).decode('utf-8', errors='ignore')
        data = json.loads(output)
        if isinstance(data, list):
            for item in data:
                name = item.get("Name", "").lower()
                app_id = item.get("AppID", "")
                if name and app_id:
                    apps[name] = f"shell:AppsFolder\\{app_id}"
    except Exception as e:
        print(f"UWP Store scan notice: {e}")


def run_scan():
    """Performs ultra-fast background app index build and saves to JSON."""
    apps = dict(BUILTIN_APPS)

    t1 = threading.Thread(target=scan_start_menu, args=(apps,))
    t2 = threading.Thread(target=scan_registry, args=(apps,))
    t3 = threading.Thread(target=scan_uwp_apps, args=(apps,))

    t1.start(); t2.start(); t3.start()
    t1.join(); t2.join(); t3.join()

    out_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2, ensure_ascii=False)

    print(f"DRAX App Scanner indexed {len(apps)} applications successfully.")
    return apps


if __name__ == "__main__":
    run_scan()