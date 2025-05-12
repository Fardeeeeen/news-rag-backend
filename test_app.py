# test_app.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI()

class MessageRequest(BaseModel):
    session_id: str
    message: str

@app.get("/ping")
def ping():
    return {"pong": True}

@app.post("/debug_raw")
async def debug_raw(req: MessageRequest) -> Dict[str, Any]:
    print("DEBUG_RAW hit!")
    return {"msg": "debug ok"}
