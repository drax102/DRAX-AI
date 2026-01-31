def route(command: str):
    if command.startswith("open"):
        return "open_app"
    if "." in command:
        return "open_website"
    return "unknown"
