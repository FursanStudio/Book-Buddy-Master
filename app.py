import streamlit as st
import json
import os
import hashlib
import requests
from dotenv import load_dotenv
import os
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config("BookBuddy", layout="wide")

BOOK_FILE = "consolidated_books.json"
ANNOT_FILE = "annotations.json"
USERS_FILE = "users.json"

# ---------- CSS (original, unchanged) ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #111 !important;
    color: #fff !important;
}

[data-testid="stAppViewContainer"] > .main {
    background-color: #111 !important;
}

[data-testid="stSidebar"] { display: none; }

h1, h2, h3, h4 {
    font-family: 'Playfair Display', serif !important;
    color: #fff !important;
}

p, label, div, span {
    font-family: 'DM Sans', sans-serif !important;
}

.auth-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 60px;
}

.auth-box {
    background: #1e1e1e;
    border-radius: 16px;
    padding: 48px 56px;
    width: 100%;
    max-width: 460px;
    box-shadow: 0 20px 60px rgba(0,212,255,0.08);
    border: 1px solid #2a2a2a;
}

.auth-title {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    color: #fff;
    margin-bottom: 8px;
    text-align: center;
}

.auth-subtitle {
    color: #888;
    text-align: center;
    margin-bottom: 32px;
    font-size: 0.9rem;
}

.gradient-text {
    background: linear-gradient(90deg, #00d4ff, #0f8faa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.stTextInput > div > div > input {
    background: #2a2a2a !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    color: #fff !important;
    padding: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
}

.stTextInput > div > div > input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 2px rgba(0,212,255,0.15) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #00d4ff, #0f8faa) !important;
    color: #000 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px 32px !important;
    width: 100% !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    transition: opacity 0.2s !important;
}

.stButton > button:hover {
    opacity: 0.85 !important;
}

.card {
    background-color: #1e1e1e;
    color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #2a2a2a;
    font-family: 'DM Sans', sans-serif;
}

.title-card {
    background: linear-gradient(135deg, #111827, #1a2540);
    color: white;
    padding: 28px 32px;
    border-radius: 14px;
    margin-bottom: 20px;
    border: 1px solid #1e3a5f;
}

.user-pill {
    background: #1e1e1e;
    border: 1px solid #00d4ff44;
    padding: 6px 16px;
    border-radius: 100px;
    display: inline-block;
    color: #00d4ff;
    font-size: 0.85rem;
}

.tab-toggle {
    display: flex;
    background: #2a2a2a;
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 28px;
    gap: 4px;
}

/* Chat bubbles */
.chat-user {
    background: #1e1e1e;
    border: 1px solid #00d4ff33;
    border-radius: 12px 12px 4px 12px;
    padding: 12px 16px;
    margin: 8px 0;
    color: #00d4ff;
    font-size: 0.9rem;
    text-align: right;
}
.chat-ai {
    background: #1a2540;
    border: 1px solid #1e3a5f;
    border-radius: 12px 12px 12px 4px;
    padding: 12px 16px;
    margin: 8px 0;
    color: #e0e0e0;
    font-size: 0.9rem;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)


# ---------- User Store ----------
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ---------- Load Book Data (original JSON, still works) ----------
if not os.path.exists(BOOK_FILE):
    st.error(f"Book file not found: {BOOK_FILE}")
    st.stop()

with open(BOOK_FILE, "r", encoding="utf-8") as f:
    books = json.load(f)["books"]

titles = [b["book_title"] for b in books]

if not os.path.exists(ANNOT_FILE):
    with open(ANNOT_FILE, "w") as f:
        json.dump({}, f)

with open(ANNOT_FILE, "r") as f:
    annotations = json.load(f)


# ---------- Session Defaults ----------
st.session_state.setdefault("user", None)
st.session_state.setdefault("idx", 0)
st.session_state.setdefault("auth_mode", "login")
st.session_state.setdefault("ai_book_data", None)   # holds Gemini result
st.session_state.setdefault("chat_history", [])      # deep Q&A history
st.session_state.setdefault("mode", "library")       # "library" or "ai"


# ---------- Gemini helpers ----------
RATING_PROMPT = """You are a professional book content rating analyst.
Given a book title, provide a detailed content rating using BOTH Kids-in-Mind AND Common Sense Media frameworks.

Return ONLY valid JSON, no markdown, no extra text:
{
  "book_title": "exact title",
  "author": "author name",
  "summary": "2-3 sentence plot summary",
  "age_recommendation": "e.g. Ages 14+",
  "overall_score": 5,
  "sexandnudity":   {"score": 3, "max": 10, "evidence": "..."},
  "violenceandgore": {"score": 5, "max": 10, "evidence": "..."},
  "profanity":       {"score": 2, "max": 10, "evidence": "..."},
  "substanceuse":    {"score": 1, "max": 5,  "evidence": "..."},
  "positivemessages":{"score": 4, "max": 5,  "evidence": "..."},
  "rolemodels":      {"score": 3, "max": 5,  "evidence": "..."},
  "diversity":       {"score": 2, "max": 5,  "evidence": "..."},
  "educationalvalue":{"score": 3, "max": 5,  "evidence": "..."}
}"""

def _gemini(messages, api_key):
    # Convert Gemini-style messages to OpenAI-style for Groq
    openai_messages = []
    for m in messages:
        role = "assistant" if m["role"] == "model" else m["role"]
        content = m["parts"][0]["text"] if isinstance(m["parts"], list) else m["parts"]
        openai_messages.append({"role": role, "content": content})

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "llama-3.1-8b-instant", "messages": openai_messages, "max_tokens": 512, "temperature": 0.7},
        timeout=30
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def get_ai_rating(book_name, api_key):
    prompt = RATING_PROMPT + f'\n\nRate this book: "{book_name}"'
    raw = _gemini([{"role": "user", "parts": [{"text": prompt}]}], api_key).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())

def chat_with_buddy(history, api_key):
    system = """You are BookBuddy, a concise book assistant. Keep all replies under 200 words.
- Recommend books by age/genre with brief descriptions
- Rate books using Kids-in-Mind (Sex & Nudity, Violence, Profanity /10) and Common Sense Media (Substance Use, Positive Messages, Role Models, Diversity, Educational Value /5)
- Answer book questions about themes, age-suitability, comparisons
Be friendly and to the point."""

    messages = [
        {"role": "user",  "parts": [{"text": system}]},
        {"role": "model", "parts": [{"text": "Hi! I'm BookBuddy. Ask me anything about books!"}]}
    ]
    for h in history:
        role = "model" if h["role"] == "model" else "user"
        messages.append({"role": role, "parts": [{"text": h["content"]}]})
    return _gemini(messages, api_key)


# ---------- Auth Page (original, unchanged) ----------
if not st.session_state.user:

    st.markdown("""
        <div style='text-align:center; margin-top:48px; margin-bottom:8px;'>
            <span style='font-size:2.8rem;'>📚</span>
            <h1 style='font-family:Playfair Display,serif; font-size:2.4rem; margin:0;'>
                Book<span style='background:linear-gradient(90deg,#00d4ff,#0f8faa);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>Buddy</span>
            </h1>
            <p style='color:#666; margin-top:6px;'>Your personal book annotation system</p>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([2, 2, 2])
    with col_c:
        mode = st.radio(
            "",
            options=["Login", "Register"],
            horizontal=True,
            label_visibility="collapsed",
            index=0 if st.session_state.auth_mode == "login" else 1
        )
        st.session_state.auth_mode = mode.lower()

    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        users = load_users()

        if st.session_state.auth_mode == "login":
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            email = st.text_input("Email", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Your password", key="login_pw")

            if st.button("Login →"):
                if not email.strip() or not password.strip():
                    st.error("Please fill in all fields.")
                elif email.strip() not in users:
                    st.error("No account found with this email. Please register first.")
                elif users[email.strip()]["password"] != hash_password(password):
                    st.error("Incorrect password.")
                else:
                    st.session_state.user = email.strip()
                    st.rerun()

        else:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Your display name", key="reg_name")
            email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
            password = st.text_input("Password", type="password", placeholder="Create a password", key="reg_pw")
            confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_confirm")

            if st.button("Create Account →"):
                if not all([username.strip(), email.strip(), password.strip(), confirm.strip()]):
                    st.error("Please fill in all fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif email.strip() in users:
                    st.warning("An account with this email already exists. Please log in.")
                else:
                    users[email.strip()] = {
                        "username": username.strip(),
                        "password": hash_password(password)
                    }
                    save_users(users)
                    st.success("Account created! You can now log in.")
                    st.session_state.auth_mode = "login"
                    st.rerun()

    st.stop()


# ---------- Main App ----------
users = load_users()
display_name = users.get(st.session_state.user, {}).get("username", st.session_state.user)

# Header (original)
hcol1, hcol2 = st.columns([6, 1])
with hcol1:
    st.markdown(
        f"<span class='user-pill'>👤 {display_name}</span>",
        unsafe_allow_html=True
    )
with hcol2:
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

st.divider()

# ── Mode Toggle (NEW: switch between Library and AI Search) ──
m1, m2, _ = st.columns([1, 1, 4])
with m1:
    if st.button("📚 Library" if st.session_state.mode != "library" else "📚 Library ✓"):
        st.session_state.mode = "library"
        st.rerun()
with m2:
    if st.button("🤖 AI Search" if st.session_state.mode != "ai" else "🤖 AI Search ✓"):
        st.session_state.mode = "ai"
        st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


# ============================================================
# MODE 1: ORIGINAL LIBRARY (unchanged)
# ============================================================
if st.session_state.mode == "library":

    selected = st.selectbox("🔍 Search Books", titles, index=st.session_state.idx)
    st.session_state.idx = titles.index(selected)
    book = books[st.session_state.idx]

    st.markdown(
        f"<div class='title-card'><h2 style='margin:0'>{book['book_title']}</h2></div>",
        unsafe_allow_html=True
    )

    cols = st.columns(3)
    keys = ["sexandnudity", "violenceandgore", "profanity"]
    icons = ["🔞", "⚔️", "🤬"]

    for i, (k, icon) in enumerate(zip(keys, icons)):
        with cols[i]:
            st.markdown(
                f"""
                <div class="card">
                    <h4>{icon} {k.replace("and", " & ").title()}</h4>
                    <b>Score:</b> {book[k]['score']}<br><br>
                    <small style="color:#aaa">{book[k]['evidence']}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    st.markdown("## 🏷️ Annotations")

    with st.expander("➕ Add Label"):
        label = st.text_input("Label name")
        score = st.slider("Score", 0, 5, 1)
        comment = st.text_area("Short comment")

        if st.button("Save Label") and label.strip():
            title = book["book_title"]
            annotations.setdefault(title, {})
            annotations[title].setdefault(st.session_state.user, [])
            annotations[title][st.session_state.user].append({
                "label": label,
                "score": score,
                "comment": comment
            })
            with open(ANNOT_FILE, "w") as f:
                json.dump(annotations, f, indent=4)
            st.success("Label saved!")
            st.rerun()

    if book["book_title"] in annotations:
        for user_email, labs in annotations[book["book_title"]].items():
            uname = users.get(user_email, {}).get("username", user_email)
            st.markdown(f"#### 👤 {uname}")
            for l in labs:
                st.info(f"**{l['label']}** | Score: {l['score']}\n\n{l['comment']}")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅ Previous"):
            st.session_state.idx = max(0, st.session_state.idx - 1)
            st.rerun()
    with c2:
        if st.button("Next ➡"):
            st.session_state.idx = min(len(titles) - 1, st.session_state.idx + 1)
            st.rerun()


# ============================================================
# MODE 2: AI CHATBOT
# ============================================================
else:

    st.markdown("<small style='color:#888'>Ask me anything — recommend books, rate a book, compare titles, find books by age or genre...</small>", unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Starter suggestions (only when chat is empty)
    if not st.session_state.chat_history:
        st.markdown("<div style='color:#555; font-size:0.8rem; margin-bottom:8px;'>Try asking:</div>", unsafe_allow_html=True)
        sg1, sg2, sg3 = st.columns(3)
        starters = [
            "📚 Books for kids age 5",
            "⭐ Rate The Hunger Games",
            "🔍 Best fantasy books for teens"
        ]
        for col, s in zip([sg1, sg2, sg3], starters):
            with col:
                if st.button(s, key=f"start_{s[:8]}"):
                    st.session_state.chat_history.append({"role": "user", "content": s})
                    with st.spinner("BookBuddy is thinking..."):
                        try:
                            reply = chat_with_buddy(st.session_state.chat_history, GROQ_API_KEY)
                            st.session_state.chat_history.append({"role": "model", "content": reply})
                        except Exception as e:
                            st.session_state.chat_history.pop()
                            st.error(f"Error: {e}")
                    st.rerun()

    # Render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-user'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-ai'>{msg['content']}</div>", unsafe_allow_html=True)

    # Input row
    ci1, ci2 = st.columns([5, 1])
    with ci1:
        user_msg = st.text_input("Message BookBuddy...", key="chat_input", label_visibility="collapsed",
                                  placeholder="e.g. Rate Harry Potter, suggest books for a 10-year-old...")
    with ci2:
        send = st.button("Send →", key="chat_send")

    if send and user_msg.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_msg.strip()})
        with st.spinner("BookBuddy is thinking..."):
            try:
                reply = chat_with_buddy(st.session_state.chat_history, GROQ_API_KEY)
                st.session_state.chat_history.append({"role": "model", "content": reply})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.chat_history.pop()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()