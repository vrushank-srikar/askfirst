"""
database.py — SQLAlchemy ORM models + CRUD helpers for GeminiChat
Tables:
    threads  (id, title, created_at)
    messages (id, thread_id, role, content, created_at)
"""

import os
import pymysql
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey
)
from pathlib import Path
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# ─── Config ──────────────────────────────────────────────────────────────────
MYSQL_HOST     = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT     = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER     = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "chatapp")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

engine       = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


# ─── Models ──────────────────────────────────────────────────────────────────

class Thread(Base):
    __tablename__ = "threads"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship(
        "Message", back_populates="thread", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    thread_id  = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String(20), nullable=False)   # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("Thread", back_populates="messages")


# ─── Initialisation ──────────────────────────────────────────────────────────

def _ensure_database_exists() -> None:
    """Create the MySQL database schema if it does not yet exist."""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=int(MYSQL_PORT),
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`")
        conn.commit()
    finally:
        conn.close()


def create_tables() -> None:
    """Ensure the database and all ORM tables exist."""
    _ensure_database_exists()
    Base.metadata.create_all(bind=engine)


# ─── Dependency ──────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── CRUD — Threads ──────────────────────────────────────────────────────────

def create_thread(db, title: str) -> Thread:
    thread = Thread(title=title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def get_threads(db) -> list[Thread]:
    return db.query(Thread).order_by(Thread.created_at.desc()).all()


def get_thread(db, thread_id: int) -> Optional[Thread]:
    return db.query(Thread).filter(Thread.id == thread_id).first()


def delete_thread_by_id(db, thread_id: int) -> Optional[Thread]:
    thread = get_thread(db, thread_id)
    if thread:
        db.delete(thread)
        db.commit()
    return thread


# ─── CRUD — Messages ─────────────────────────────────────────────────────────

def add_message(db, thread_id: int, role: str, content: str) -> Message:
    msg = Message(thread_id=thread_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db, thread_id: int) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def get_all_messages_for_memory(
    db,
    exclude_thread_id: Optional[int] = None,
    limit: int = 50,
) -> list:
    """
    Fetch the most-recent `limit` messages from every thread except
    `exclude_thread_id`.  Used to build the universal-memory context
    block that is prepended to every Gemini request.
    """
    query = db.query(Message).order_by(Message.created_at.asc())
    if exclude_thread_id is not None:
        query = query.filter(Message.thread_id != exclude_thread_id)
    all_msgs = query.all()
    return all_msgs[-limit:] if len(all_msgs) > limit else all_msgs
