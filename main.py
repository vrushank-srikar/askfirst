"""
main.py — FastAPI backend for GeminiChat
Endpoints:
    GET    /health
    GET    /threads
    POST   /threads
    GET    /threads/{id}/messages
    POST   /threads/{id}/chat        ← Gemini + universal memory
    DELETE /threads/{id}

Uses: google-genai SDK (google.genai)
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from dotenv import load_dotenv

from database import (
    create_tables, get_db,
    create_thread       as db_create_thread,
    get_threads         as db_get_threads,
    get_thread          as db_get_thread,
    get_messages        as db_get_messages,
    add_message         as db_add_message,
    delete_thread_by_id,
    get_all_messages_for_memory,
)

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# ─── Gemini Setup ────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"
MEMORY_LIMIT   = 50   # max messages from other threads used as memory context

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are GeminiChat, a warm and highly capable AI assistant with persistent "
    "universal memory. You remember everything from all past conversations with "
    "the user — across every thread — and use that knowledge to give personalised, "
    "context-aware responses. When the user references something from a past "
    "conversation, acknowledge it naturally and build on it. Be concise, helpful, "
    "and conversational."
)


# ─── App Lifespan ────────────────────────────────────────────────────────────

# ── Ensure DB tables exist on every cold start (Vercel-safe) ────────────────
try:
    create_tables()
    print("[OK] Database tables ready")
except Exception as _db_err:
    print(f"[WARNING] DB init warning: {_db_err}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are already created at import time above.
    # This lifespan is kept for local dev logging.
    print("[OK] GeminiChat API is live")
    yield


# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="GeminiChat API",
    version="1.0.0",
    description="Multi-thread AI chat with universal memory powered by Gemini 1.5 Flash",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class ThreadCreateRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _thread_dict(t) -> dict:
    return {"id": t.id, "title": t.title, "created_at": t.created_at.isoformat()}


def _message_dict(m) -> dict:
    return {
        "id":         m.id,
        "role":       m.role,
        "content":    m.content,
        "created_at": m.created_at.isoformat(),
    }


def _build_gemini_contents(memory_msgs: list, current_msgs: list) -> list:
    """
    Construct the `contents` list for Gemini:
      1. Optional synthetic memory turn (past-threads context)
      2. Current thread history
    The last item is always the just-saved user message.
    """
    contents = []

    # ── Universal memory block ──
    if memory_msgs:
        lines = [f"[{m.role.upper()}]: {m.content}" for m in memory_msgs]
        memory_text = "\n".join(lines)
        contents.append({
            "role": "user",
            "parts": [
                "[MEMORY CONTEXT — your past conversations with the user]\n"
                f"{memory_text}\n"
                "[END MEMORY CONTEXT]\n"
                "Please acknowledge that you have this context available."
            ],
        })
        contents.append({
            "role": "model",
            "parts": [
                "Acknowledged — I have reviewed our previous conversation history and "
                "will use that context to give you personalised, memory-aware responses."
            ],
        })

    # ── Current thread messages ──
    for m in current_msgs:
        contents.append({
            "role":  "user" if m.role == "user" else "model",
            "parts": [m.content],
        })

    return contents


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Utility"])
def health_check():
    """Quick liveness probe."""
    return {"status": "ok", "model": GEMINI_MODEL}


# ── Threads ──────────────────────────────────────────────────────────────────

@app.get("/threads", tags=["Threads"])
def list_threads(db: Session = Depends(get_db)):
    """Return all threads ordered newest-first."""
    return [_thread_dict(t) for t in db_get_threads(db)]


@app.post("/threads", status_code=201, tags=["Threads"])
def create_thread(req: Optional[ThreadCreateRequest] = None, db: Session = Depends(get_db)):
    """Create a new thread. Auto-generates title if not supplied."""
    count = len(db_get_threads(db)) + 1
    title = (req.title if req and req.title else None) or f"Thread #{count}"
    thread = db_create_thread(db, title)
    return _thread_dict(thread)


@app.get("/threads/{thread_id}/messages", tags=["Threads"])
def get_thread_messages(thread_id: int, db: Session = Depends(get_db)):
    """Return all messages in a thread, oldest-first."""
    thread = db_get_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return [_message_dict(m) for m in db_get_messages(db, thread_id)]


@app.delete("/threads/{thread_id}", tags=["Threads"])
def delete_thread(thread_id: int, db: Session = Depends(get_db)):
    """Delete a thread and all its messages."""
    thread = delete_thread_by_id(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": f"Thread '{thread.title}' deleted successfully"}


# ── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/threads/{thread_id}/chat", tags=["Chat"])
def chat(thread_id: int, req: ChatRequest, db: Session = Depends(get_db)):
    """
    Core endpoint:
    1. Persist user message
    2. Fetch universal memory from all other threads (last MEMORY_LIMIT msgs)
    3. Build Gemini contents list
    4. Call gemini-1.5-flash
    5. Persist + return AI reply
    """
    # Validate thread
    thread = db_get_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # 1. Save user message first so it is included in current history
    db_add_message(db, thread_id, "user", req.message)

    # 2. Universal memory (other threads)
    memory_msgs = get_all_messages_for_memory(
        db, exclude_thread_id=thread_id, limit=MEMORY_LIMIT
    )

    # 3. Current thread (includes the just-saved user message)
    current_msgs = db_get_messages(db, thread_id)

    # 4. Build Gemini payload
    raw_contents = _build_gemini_contents(memory_msgs, current_msgs)

    if not raw_contents:
        raise HTTPException(status_code=400, detail="No content to send to Gemini")

    # Convert to google.genai Content objects
    genai_contents = [
        types.Content(
            role=c["role"],
            parts=[types.Part(text=p) for p in c["parts"]]
        )
        for c in raw_contents
    ]

    # 5. Call Gemini
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=genai_contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )
        ai_reply = response.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {exc}")

    # 6. Persist AI reply
    db_add_message(db, thread_id, "assistant", ai_reply)

    return {"reply": ai_reply, "thread_id": thread_id}
