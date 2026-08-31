import os
import sys
import time
import subprocess

try:
    import psutil
except ImportError:
    psutil = None


def get_system_telemetry():
    """Returns a dictionary of current CPU, RAM, OS status."""
    if psutil:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        ram_used = mem.percent
        ram_gb = f"{mem.used / (1024**3):.1f}/{mem.total / (1024**3):.1f} GB"
    else:
        cpu = 0.0
        ram_used = 0.0
        ram_gb = "N/A"

    return {
        "cpu_usage": cpu,
        "ram_usage": ram_used,
        "ram_formatted": ram_gb,
        "os_name": sys.platform.upper(),
        "status": "ONLINE // READY"
    }


def get_system_status_speech():
    """Returns a spoken summary of system health for DRAX."""
    telemetry = get_system_telemetry()
    cpu = telemetry["cpu_usage"]
    ram = telemetry["ram_usage"]
    ram_fmt = telemetry["ram_formatted"]
    return f"DRAX System Status: CPU load is at {cpu:.1f} percent. RAM utilization is {ram:.1f} percent ({ram_fmt}). All core systems are nominal."


def change_volume(action: str):
    """Adjusts Windows master volume using ncom / keypress or powershell."""
    try:
        if "up" in action or "increase" in action:
            cmd = "powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]175)\""
            subprocess.Popen(cmd, shell=True)
            return "Increasing master volume."
        elif "down" in action or "decrease" in action:
            cmd = "powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]174)\""
            subprocess.Popen(cmd, shell=True)
            return "Decreasing master volume."
        elif "mute" in action:
            cmd = "powershell -c \"(New-Object -ComObject WScript.Shell).SendKeys([char]173)\""
            subprocess.Popen(cmd, shell=True)
            return "Toggling volume mute."
    except Exception as e:
        print("Volume control error:", e)
    return "Volume adjusted."
