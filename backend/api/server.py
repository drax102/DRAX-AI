
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def home():
    return {"status":"Drax AI running"}
