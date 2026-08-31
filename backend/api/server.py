from fastapi import FastAPI
from backend.core.system_info import get_system_telemetry
from backend.core.intent_router import route_command

app = FastAPI(title="DRAX AI Server API", version="2.0")

@app.get("/")
def home():
    return {
        "status": "DRAX AI ONLINE",
        "system": get_system_telemetry()
    }

@app.post("/command")
def execute_command(cmd: str):
    response = route_command(cmd)
    return {"command": cmd, "response": response}
