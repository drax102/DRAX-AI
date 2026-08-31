"""
builtins.py — Standard Windows built-in application definitions.
"""

BUILTIN_APPS = [
    {
        "name": "notepad",
        "display_name": "Notepad",
        "aliases": ["text editor", "notes", "notepad"],
        "type": "executable",
        "target": "notepad.exe",
        "source": "builtin",
    },
    {
        "name": "calculator",
        "display_name": "Calculator",
        "aliases": ["calc", "calculator"],
        "type": "executable",
        "target": "calc.exe",
        "source": "builtin",
    },
    {
        "name": "paint",
        "display_name": "Paint",
        "aliases": ["mspaint", "draw", "paint"],
        "type": "executable",
        "target": "mspaint.exe",
        "source": "builtin",
    },
    {
        "name": "command prompt",
        "display_name": "Command Prompt",
        "aliases": ["cmd", "terminal", "command line"],
        "type": "executable",
        "target": "cmd.exe",
        "source": "builtin",
    },
    {
        "name": "powershell",
        "display_name": "Windows PowerShell",
        "aliases": ["powershell", "posh"],
        "type": "executable",
        "target": "powershell.exe",
        "source": "builtin",
    },
    {
        "name": "task manager",
        "display_name": "Task Manager",
        "aliases": ["taskman", "processes", "task manager"],
        "type": "executable",
        "target": "taskmgr.exe",
        "source": "builtin",
    },
    {
        "name": "file explorer",
        "display_name": "File Explorer",
        "aliases": ["explorer", "my computer", "files", "file explorer"],
        "type": "executable",
        "target": "explorer.exe",
        "source": "builtin",
    },
    {
        "name": "control panel",
        "display_name": "Control Panel",
        "aliases": ["control panel", "settings legacy"],
        "type": "executable",
        "target": "control.exe",
        "source": "builtin",
    },
]
