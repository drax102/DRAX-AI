
import subprocess, json

def run(cmd):
    try:
        with open("backend/data/app_index.json") as f:
            apps = json.load(f)
        for name, path in apps.items():
            if name in cmd:
                subprocess.Popen(path)
                return f"Opening {name}"
    except:
        pass
    return "App not found"
