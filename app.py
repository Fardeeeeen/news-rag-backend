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
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ——— Load Env Vars ———
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in environment variables")

# ——— FastAPI App ———
app = FastAPI()

# ——— CORS (allow your frontend origin) ———
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
        collection = chroma_client.get_collection(name="news_passages")
        logger.debug(f"Loaded collection 'news_passages' with {collection.count()} documents")
    except NotFoundError:
        collection = chroma_client.create_collection(name="news_passages")
        logger.info("Created new ChromaDB collection 'news_passages'")
except Exception as e:
    logger.error(f"Error initializing ChromaDB: {e}")
    raise

# ——— Gemini (Google Gen AI) Setup ———
genai.configure(api_key=GOOGLE_API_KEY)
logger.debug("Configured Gemini with API key")
for model in genai.list_models():
    logger.debug(f"Model: {model.name}")

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
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Context:\n{context}\n\nUser: {user_message}\nBot:"
        response = model.generate_content(prompt)

        # Check blocking
        fb = getattr(response, "prompt_feedback", None)
        if fb and fb.block_reason:
            return f"(Blocked by Gemini: {fb.block_reason})"

        # Extract text
        for candidate in getattr(response, "candidates", []):
            parts = getattr(candidate.content, "parts", None)
            if parts:
                return parts[0].text.strip()
        # Fallback
        return getattr(response, "text", "(No response)") or "(No response)"
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"(LLM error: {e})"

# ——— Chat Endpoint ———
@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    session_id = request.session_id
    user_msg = request.message
    logger.info(f"[CHAT] session={session_id} message={user_msg}")

    # Load session history
    try:
        raw = redis_client.get(session_id)
        history = json.loads(raw) if raw else []
    except Exception as e:
        logger.error(f"[CHAT] Redis error: {e}")
        history = []

    # Retrieve top-k passages
    try:
        results = collection.query(query_texts=[user_msg], n_results=5)
        docs = results["documents"][0]
    except Exception as e:
        logger.error(f"[CHAT] ChromaDB error: {e}")
        raise HTTPException(status_code=500, detail="Vector DB error")

    # Build context
    convo = "\n".join(docs) + "\n" + "\n".join(
        f"User: {h['user']}\nBot: {h['bot']}" for h in history
    )

    # Generate reply
    reply = generate_llm_response(convo, user_msg)

    # Update history
    history.append({"user": user_msg, "bot": reply})
    try:
        redis_client.set(session_id, json.dumps(history))
    except Exception as e:
        logger.error(f"[CHAT] Redis save error: {e}")

    return MessageResponse(response=reply, session_history=history)

# ——— Delete Session Endpoint ———
@app.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    try:
        redis_client.delete(session_id)
        logger.info(f"[DELETE] Cleared session {session_id}")
    except redis.ConnectionError as e:
        logger.error(f"[DELETE] Redis connection error: {e}")
        raise HTTPException(status_code=500, detail="Could not connect to Redis")
    except Exception as e:
        logger.error(f"[DELETE] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ——— Debug Raw Endpoint ———
@app.post("/debug_raw", response_model=Dict[str, Any])
async def debug_raw(request: MessageRequest):
    user_msg = request.message
    try:
        results = collection.query(query_texts=[user_msg], n_results=5)
        docs = results["documents"][0]
        prompt = f"Context:\n{docs}\n\nUser: {user_msg}\nBot:"        
        response = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
        return { "raw": str(response), "attrs": dir(response) }
    except Exception as e:
        logger.error(f"[DEBUG_RAW] error: {e}")
        raise HTTPException(status_code=500, detail="Debug error")
