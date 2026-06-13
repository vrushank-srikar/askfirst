"""
app.py — Streamlit frontend for GeminiChat
Premium dark UI with multi-thread sidebar, chat bubbles, and universal memory indicator.
Run with: streamlit run app.py
"""

import streamlit as st
import requests
import os

# API_BASE is overridden via env var / Streamlit secrets in production
# Set API_BASE = https://your-app.vercel.app in Streamlit Cloud secrets
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")

# ─── Page Config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="GeminiChat — AI with Memory",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Premium CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stMarkdown, p, span, div, button {
    font-family: 'Inter', sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
[data-testid="stToolbar"]    { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── App background ── */
.stApp {
    background: radial-gradient(ellipse at 20% 0%, #0f1124 0%, #0a0c11 60%, #060810 100%);
}

/* ════════════════════════════════════════════
   SIDEBAR
════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0c14 0%, #080a12 100%) !important;
    border-right: 1px solid #1a1f35 !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.4) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
}

/* Sidebar buttons – base reset */
[data-testid="stSidebar"] .stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    border-radius: 10px !important;
    padding: 0.45rem 0.75rem !important;
    border: 1px solid transparent !important;
    transition: all 0.18s ease !important;
    text-align: left !important;
    width: 100% !important;
    background: transparent !important;
    color: #8b949e !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(102,126,234,0.1) !important;
    border-color: rgba(102,126,234,0.25) !important;
    color: #c9d1f5 !important;
    transform: translateX(2px) !important;
}

/* ── New Thread button (always first button in sidebar) ── */
div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-child(3) .stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border: none !important;
    box-shadow: 0 4px 18px rgba(102,126,234,0.35) !important;
    letter-spacing: 0.2px;
}
div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-child(3) .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(102,126,234,0.55) !important;
    color: #ffffff !important;
}

/* ════════════════════════════════════════════
   CHAT MESSAGES
════════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    padding: 0.5rem 0.75rem !important;
    margin: 0.2rem 0 !important;
    border: none !important;
    background: transparent !important;
}

/* User bubble */
[data-testid="stChatMessage"][data-testid="stChatMessage"] .stChatMessageContent {
    border-radius: 18px !important;
}

/* ════════════════════════════════════════════
   CHAT INPUT
════════════════════════════════════════════ */
[data-testid="stChatInput"] {
    background: rgba(10,12,20,0.95) !important;
    border-top: 1px solid #1a1f35 !important;
    backdrop-filter: blur(10px) !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stChatInput"] textarea {
    background: #111520 !important;
    border: 1px solid #252d4a !important;
    border-radius: 14px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1rem !important;
    resize: none !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.18) !important;
    outline: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #3a4060 !important;
}
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    border-radius: 10px !important;
    border: none !important;
    color: white !important;
    transition: all 0.2s !important;
}
[data-testid="stChatInput"] button:hover {
    transform: scale(1.05) !important;
    box-shadow: 0 4px 12px rgba(102,126,234,0.5) !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] {
    color: #667eea !important;
}

/* ── Divider ── */
hr {
    border-color: #1a1f35 !important;
    margin: 0.75rem 0 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #252d4a; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #667eea; }

/* ── Alert / info boxes ── */
.stAlert {
    border-radius: 12px !important;
    border: 1px solid #252d4a !important;
    background: #111520 !important;
}

/* ── Columns gap fix ── */
[data-testid="stHorizontalBlock"] {
    gap: 0.25rem !important;
    align-items: center !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Session State Init ───────────────────────────────────────────────────────
def init_state():
    defaults = {
        "active_thread_id":  None,
        "messages":          [],
        "last_loaded_tid":   None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── API Helpers ─────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs):
    """Thin wrapper around requests — returns (ok, data)."""
    try:
        r = getattr(requests, method)(f"{API_BASE}{path}", timeout=90, **kwargs)
        return r.ok, r.json() if r.ok else {}
    except requests.exceptions.ConnectionError:
        return False, {}
    except Exception:
        return False, {}


def fetch_threads() -> list:
    ok, data = api("get", "/threads")
    return data if ok else []


def fetch_messages(tid: int) -> list:
    ok, data = api("get", f"/threads/{tid}/messages")
    return data if ok else []


def create_thread(title: str | None = None) -> dict | None:
    ok, data = api("post", "/threads", json={"title": title or ""})
    return data if ok else None


def send_chat(tid: int, message: str) -> dict | None:
    ok, data = api("post", f"/threads/{tid}/chat", json={"message": message})
    return data if ok else None


def delete_thread(tid: int) -> bool:
    ok, _ = api("delete", f"/threads/{tid}")
    return ok


def backend_alive() -> bool:
    ok, _ = api("get", "/health")
    return ok


# ─── Load Data ───────────────────────────────────────────────────────────────
threads = fetch_threads()

# Auto-reload messages when the active thread changes
if st.session_state.active_thread_id != st.session_state.last_loaded_tid:
    if st.session_state.active_thread_id:
        st.session_state.messages = fetch_messages(st.session_state.active_thread_id)
    else:
        st.session_state.messages = []
    st.session_state.last_loaded_tid = st.session_state.active_thread_id


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Logo / Branding ──
    st.markdown("""
    <div style="
        padding: 1.6rem 1rem 1.2rem;
        border-bottom: 1px solid #1a1f35;
        margin-bottom: 0.75rem;
        text-align: center;
    ">
        <div style="
            display: inline-flex; align-items: center; justify-content: center;
            width: 52px; height: 52px; border-radius: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-size: 1.6rem;
            box-shadow: 0 6px 24px rgba(102,126,234,0.45);
            margin-bottom: 0.75rem;
        ">✦</div>
        <div style="
            font-size: 1.2rem; font-weight: 800; letter-spacing: -0.3px;
            background: linear-gradient(135deg, #a5b4fc, #c084fc);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        ">GeminiChat</div>
        <div style="font-size: 0.7rem; color: #3a4060; margin-top: 0.2rem; letter-spacing: 0.3px;">
            GEMINI 1.5 FLASH · UNIVERSAL MEMORY
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Backend Status ──
    if not backend_alive():
        st.markdown("""
        <div style="
            margin: 0 0.75rem 0.75rem;
            padding: 0.65rem 0.9rem;
            background: rgba(239,68,68,0.12);
            border: 1px solid rgba(239,68,68,0.3);
            border-radius: 10px;
            font-size: 0.78rem; color: #f87171;
            line-height: 1.5;
        ">
            ⚠️ <strong>Backend offline</strong><br>
            <span style="color:#6b7280;">Run: <code style="color:#fbbf24;">uvicorn main:app --reload</code></span>
        </div>
        """, unsafe_allow_html=True)

    # ── New Thread ──
    st.markdown("<div style='padding: 0 0.6rem;'>", unsafe_allow_html=True)
    if st.button("＋  New Thread", use_container_width=True, key="btn_new_thread"):
        new_t = create_thread()
        if new_t and new_t.get("id"):
            st.session_state.active_thread_id = new_t["id"]
            st.session_state.last_loaded_tid  = None
            st.rerun()
        else:
            st.error("Could not create thread — is the backend running?")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Section label ──
    thread_count = len(threads)
    st.markdown(f"""
    <div style="
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 1rem; margin-bottom: 0.35rem;
    ">
        <span style="font-size:0.68rem; font-weight:700; color:#3a4060;
                     text-transform:uppercase; letter-spacing:1.2px;">
            Conversations
        </span>
        <span style="
            font-size:0.68rem; font-weight:600; color:#667eea;
            background:rgba(102,126,234,0.12);
            padding:1px 8px; border-radius:20px;
        ">{thread_count}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Thread List ──
    if not threads:
        st.markdown("""
        <div style="
            text-align:center; padding:2rem 1rem;
            color:#2a3050; font-size:0.82rem; line-height:1.8;
        ">
            <div style="font-size:1.8rem; margin-bottom:0.5rem; opacity:0.4;">💬</div>
            No threads yet.<br>Hit <strong style="color:#667eea;">New Thread</strong> to begin.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding: 0 0.5rem;'>", unsafe_allow_html=True)
        for t in threads:
            is_active = st.session_state.active_thread_id == t["id"]

            # Highlight active thread with a wrapper
            if is_active:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg,rgba(102,126,234,0.15),rgba(118,75,162,0.12));
                    border: 1px solid rgba(102,126,234,0.3);
                    border-radius: 10px; padding: 0 0 0 6px; margin: 2px 0;
                    display:flex; align-items:center; gap:6px;
                ">
                    <span style="color:#818cf8; font-size:0.6rem;">●</span>
                </div>
                """, unsafe_allow_html=True)

            col_btn, col_del = st.columns([5, 1])
            with col_btn:
                label = t["title"]
                if st.button(
                    label,
                    key=f"t_{t['id']}",
                    use_container_width=True,
                ):
                    st.session_state.active_thread_id = t["id"]
                    st.session_state.last_loaded_tid  = None
                    st.rerun()
            with col_del:
                if st.button("✕", key=f"d_{t['id']}", help=f"Delete {t['title']}"):
                    if delete_thread(t["id"]):
                        if st.session_state.active_thread_id == t["id"]:
                            st.session_state.active_thread_id = None
                            st.session_state.messages         = []
                            st.session_state.last_loaded_tid  = None
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Universal Memory Badge ──
    if thread_count > 1:
        st.markdown(f"""
        <div style="
            margin: 1.5rem 0.75rem 0.5rem;
            padding: 0.8rem 1rem;
            background: linear-gradient(135deg,
                rgba(102,126,234,0.1) 0%,
                rgba(56,239,125,0.07) 100%);
            border: 1px solid rgba(102,126,234,0.22);
            border-radius: 12px;
        ">
            <div style="
                font-size:0.78rem; font-weight:600; color:#818cf8;
                display:flex; align-items:center; gap:0.4rem; margin-bottom:0.3rem;
            ">
                🧠 Universal Memory Active
            </div>
            <div style="font-size:0.72rem; color:#3a4060; line-height:1.5;">
                Gemini sees context from all <strong style="color:#667eea;">{thread_count}</strong> threads
                — start a new thread and it still remembers everything.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─── MAIN AREA ───────────────────────────────────────────────────────────────

if st.session_state.active_thread_id is None:
    # ── Welcome / Empty State ──
    st.markdown("""
    <div style="
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        min-height: 78vh; text-align: center; padding: 2rem;
        animation: fadeIn 0.6s ease;
    ">
        <!-- Glowing orb -->
        <div style="
            width: 90px; height: 90px; border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 60%, #38ef7d 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 2.4rem; margin-bottom: 1.75rem;
            box-shadow:
                0 0 0 12px rgba(102,126,234,0.08),
                0 0 0 24px rgba(102,126,234,0.04),
                0 12px 40px rgba(102,126,234,0.5);
            animation: glow 3s ease-in-out infinite;
        ">✦</div>

        <h1 style="
            font-size: 2.1rem; font-weight: 800; margin: 0 0 0.6rem;
            background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 60%, #818cf8 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        ">Welcome to GeminiChat</h1>

        <p style="
            color: #4a5568; max-width: 420px; line-height: 1.75;
            font-size: 0.95rem; margin-bottom: 2.5rem;
        ">
            Your AI assistant with <strong style="color:#818cf8;">universal memory</strong>.
            Every conversation — across every thread — is remembered forever.
        </p>

        <!-- Feature cards -->
        <div style="display:flex; gap:1rem; flex-wrap:wrap; justify-content:center; margin-bottom:2.5rem;">
            <div style="
                background:#0f1220; border:1px solid #1e2540;
                border-radius:16px; padding:1.25rem 1.5rem; min-width:148px;
                transition:all 0.3s;
            ">
                <div style="font-size:1.6rem; margin-bottom:0.5rem;">💬</div>
                <div style="color:#a5b4fc; font-weight:600; font-size:0.85rem;">Multi-Thread</div>
                <div style="color:#374151; font-size:0.75rem; margin-top:0.25rem; line-height:1.4;">
                    Separate topics,<br>one AI
                </div>
            </div>
            <div style="
                background:#0f1220; border:1px solid #1e2540;
                border-radius:16px; padding:1.25rem 1.5rem; min-width:148px;
            ">
                <div style="font-size:1.6rem; margin-bottom:0.5rem;">🧠</div>
                <div style="color:#a5b4fc; font-weight:600; font-size:0.85rem;">Universal Memory</div>
                <div style="color:#374151; font-size:0.75rem; margin-top:0.25rem; line-height:1.4;">
                    Remembers all<br>past chats
                </div>
            </div>
            <div style="
                background:#0f1220; border:1px solid #1e2540;
                border-radius:16px; padding:1.25rem 1.5rem; min-width:148px;
            ">
                <div style="font-size:1.6rem; margin-bottom:0.5rem;">⚡</div>
                <div style="color:#a5b4fc; font-weight:600; font-size:0.85rem;">Gemini Flash</div>
                <div style="color:#374151; font-size:0.75rem; margin-top:0.25rem; line-height:1.4;">
                    Fast, powerful<br>responses
                </div>
            </div>
            <div style="
                background:#0f1220; border:1px solid #1e2540;
                border-radius:16px; padding:1.25rem 1.5rem; min-width:148px;
            ">
                <div style="font-size:1.6rem; margin-bottom:0.5rem;">🗄️</div>
                <div style="color:#a5b4fc; font-weight:600; font-size:0.85rem;">MySQL Backed</div>
                <div style="color:#374151; font-size:0.75rem; margin-top:0.25rem; line-height:1.4;">
                    Persistent<br>storage
                </div>
            </div>
        </div>

        <div style="
            color:#2a3050; font-size:0.82rem;
            display:flex; align-items:center; gap:0.4rem;
        ">
            <span style="font-size:1rem;">←</span>
            Create a thread from the sidebar to begin
        </div>
    </div>

    <style>
    @keyframes glow {
        0%,100% { box-shadow: 0 0 0 12px rgba(102,126,234,0.08),
                               0 0 0 24px rgba(102,126,234,0.04),
                               0 12px 40px rgba(102,126,234,0.5); }
        50%      { box-shadow: 0 0 0 16px rgba(102,126,234,0.12),
                               0 0 0 32px rgba(102,126,234,0.06),
                               0 12px 60px rgba(102,126,234,0.7); }
    }
    @keyframes fadeIn {
        from { opacity:0; transform: translateY(16px); }
        to   { opacity:1; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)

else:
    # ── Active Thread View ──
    active_thread = next(
        (t for t in threads if t["id"] == st.session_state.active_thread_id), None
    )

    # ── Thread Header ──
    if active_thread:
        mem_note = (
            f'<span style="font-size:0.72rem; color:#38ef7d; '
            f'background:rgba(56,239,125,0.1); border:1px solid rgba(56,239,125,0.2); '
            f'padding:2px 9px; border-radius:20px; margin-left:0.5rem;">🧠 Memory</span>'
            if thread_count > 1 else ""
        )
        st.markdown(f"""
        <div style="
            display: flex; align-items: center;
            padding: 0.85rem 0 1rem;
            border-bottom: 1px solid #1a1f35;
            margin-bottom: 0.5rem;
        ">
            <div style="
                width: 9px; height: 9px; background: #38ef7d; border-radius: 50%;
                box-shadow: 0 0 10px rgba(56,239,125,0.7); flex-shrink:0; margin-right:0.7rem;
            "></div>
            <span style="font-size:1.05rem; font-weight:700; color:#e2e8f0;">
                {active_thread['title']}
            </span>
            <span style="
                font-size:0.7rem; color:#3a4060;
                background:#0f1220; border:1px solid #1e2540;
                padding:2px 9px; border-radius:20px; margin-left:0.6rem;
            ">Gemini 1.5 Flash</span>
            {mem_note}
        </div>
        """, unsafe_allow_html=True)

    # ── Messages ──
    messages = st.session_state.messages

    if not messages:
        st.markdown("""
        <div style="
            text-align:center; padding:4rem 1rem;
            animation: fadeIn 0.4s ease;
        ">
            <div style="font-size:2rem; opacity:0.25; margin-bottom:0.75rem;">✦</div>
            <div style="color:#2a3050; font-size:0.875rem; line-height:1.6;">
                Send your first message below.<br>
                <span style="color:#1e2540;">Gemini is ready to chat.</span>
            </div>
        </div>
        <style>
        @keyframes fadeIn {
            from { opacity:0; transform:translateY(10px); }
            to   { opacity:1; transform:translateY(0); }
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        for msg in messages:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(
                        f'<div style="color:#f0f4ff; font-size:0.9rem; line-height:1.7;">'
                        f'{msg["content"]}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                with st.chat_message("assistant", avatar="✦"):
                    st.markdown(msg["content"])

    # ── Chat Input ──
    user_input = st.chat_input("Message GeminiChat…  (Enter to send)")

    if user_input and user_input.strip():
        text = user_input.strip()

        # Append + display user message immediately
        st.session_state.messages.append({"role": "user", "content": text})
        with st.chat_message("user", avatar="👤"):
            st.markdown(
                f'<div style="color:#f0f4ff; font-size:0.9rem; line-height:1.7;">{text}</div>',
                unsafe_allow_html=True,
            )

        # Stream-style placeholder while waiting
        with st.chat_message("assistant", avatar="✦"):
            with st.spinner(""):
                result = send_chat(st.session_state.active_thread_id, text)

            if result and result.get("reply"):
                reply = result["reply"]
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                st.error(
                    "⚠️ No response received. "
                    "Make sure the FastAPI backend is running on port 8000."
                )
