import streamlit as st
import json
import os
import hashlib

st.set_page_config("BookBuddy", layout="wide")

BOOK_FILE = "consolidated_books.json"
ANNOT_FILE = "annotations.json"
USERS_FILE = "users.json"

# ---------- CSS ----------
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

/* Auth container */
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

/* Inputs */
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

/* Buttons */
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

/* Cards */
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

/* Tab-style toggle */
.tab-toggle {
    display: flex;
    background: #2a2a2a;
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 28px;
    gap: 4px;
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


# ---------- Load Book Data ----------
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
st.session_state.setdefault("auth_mode", "login")   # "login" or "register"


# ---------- Auth Page ----------
if not st.session_state.user:

    # Centered logo/title area
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

    # Toggle between Login / Register
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

    # Form
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

        else:  # Register
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

# Header
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

# Search
selected = st.selectbox("🔍 Search Books", titles, index=st.session_state.idx)
st.session_state.idx = titles.index(selected)
book = books[st.session_state.idx]

# Book Title Card
st.markdown(
    f"<div class='title-card'><h2 style='margin:0'>{book['book_title']}</h2></div>",
    unsafe_allow_html=True
)

# Book Detail Cards
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

# Annotations
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

# Navigation
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