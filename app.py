import os
import json
import chromadb
from chromadb import PersistentClient
from chromadb.errors import NotFoundError
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import redis
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# ——— Logging Setup ———
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
logger.addHandler(ch)

# ——— Load Env Vars ———
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY")

# ——— FastAPI App ———
app = FastAPI()

# ——— Root Health Check ———
@app.get("/")
def read_root():
    return {"status": "ok", "message": "News-RAG backend is running!"}

# ——— CORS ———
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://news-rag-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ——— Redis Client ———
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger.info(f"Using Redis URL: {redis_url}")
redis_client = redis.from_url(redis_url, decode_responses=True)

# ——— ChromaDB Init ———
PERSIST_DIR = r"C:\news-chatbot\backend\data\processed\chroma_db"
try:
    chroma_client = PersistentClient(path=PERSIST_DIR)
    try:
        collection = chroma_client.get_collection("news_passages")
        logger.debug(f"Loaded 'news_passages' ({collection.count()} docs)")
    except NotFoundError:
        collection = chroma_client.create_collection("news_passages")
        logger.info("Created 'news_passages' collection")
except Exception as e:
    logger.error(f"ChromaDB init error: {e}")
    raise

# ——— Gemini Setup ———
genai.configure(api_key=GOOGLE_API_KEY)
logger.debug("Gemini configured")
for m in genai.list_models():
    logger.debug(f"Model available: {m.name}")

# ——— Pydantic Models ———
class MessageRequest(BaseModel):
    session_id: str
    message: str

class MessageResponse(BaseModel):
    response: str
    session_history: List[Dict[str, str]]

# ——— Helper: Generate LLM Response ———
def generate_llm_response(context: str, user_message: str) -> str:
    try:
        system_instruction = (
            "You are a helpful assistant. Answer user questions directly—"
            "do not list response-template options."
        )
        prompt = (
            f"SYSTEM: {system_instruction}\n\n"
            f"Context:\n{context}\n\n"
            f"User: {user_message}\n"
            "Assistant:"
        )
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)

        # check block feedback
        fb = getattr(resp, "prompt_feedback", None)
        if fb and fb.block_reason:
            return f"(Blocked by Gemini: {fb.block_reason})"

        # concatenate all parts
        full = ""
        for cand in getattr(resp, "candidates", []):
            for part in getattr(cand.content, "parts", []) or []:
                full += getattr(part, "text", "")
        return full.strip() or "(No response)"
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return f"(LLM error: {e})"

# ——— Chat Endpoint ———
@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    sid, user_msg = request.session_id, request.message
    logger.info(f"[CHAT] {sid=} {user_msg=!r}")

    # load history
    try:
        raw = redis_client.get(sid)
        history = json.loads(raw) if raw else []
    except Exception as e:
        logger.error(f"Redis load error: {e}")
        history = []

    # retrieve relevant docs
    try:
        res = collection.query(query_texts=[user_msg], n_results=5)
        docs = res["documents"][0]
    except Exception as e:
        logger.error(f"ChromaDB error: {e}")
        raise HTTPException(500, "Vector DB error")

    # build context
    convo = "\n".join(docs) + "\n" + "\n".join(
        f"User: {h['user']}\nBot: {h['bot']}" for h in history
    )

    # generate reply
    reply = generate_llm_response(convo, user_msg)

    # update history
    history.append({"user": user_msg, "bot": reply})
    try:
        redis_client.set(sid, json.dumps(history))
    except Exception as e:
        logger.error(f"Redis save error: {e}")

    return MessageResponse(response=reply, session_history=history)

# ——— Delete Session ———
@app.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    try:
        redis_client.delete(session_id)
        logger.info(f"Session {session_id} cleared")
    except Exception as e:
        logger.error(f"Redis delete error: {e}")
        raise HTTPException(500, "Could not clear session")

# ——— Debug Raw ———
@app.post("/debug_raw", response_model=Dict[str, Any])
async def debug_raw(request: MessageRequest):
    user_msg = request.message
    try:
        res = collection.query(query_texts=[user_msg], n_results=5)
        docs = res["documents"][0]
        prompt = f"Context:\n{docs}\n\nUser: {user_msg}\nBot:"
        resp = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return {"raw": str(resp), "attrs": dir(resp)}
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(500, "Debug error")
