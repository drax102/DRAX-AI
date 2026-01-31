
import webbrowser, re

def run(cmd):
    cmd = cmd.replace(" dot ", ".")
    m = re.search(r"[a-zA-Z0-9-]+\.(com|in|io|org)", cmd)
    if m:
        webbrowser.open("https://" + m.group())
        return "Opening website"
    return "No website found"
