"""
AI Escape Room - Version 1
--------------------------
A simple escape-room game where Gemini acts as the Game Master.

In this version the LLM receives the full room design (including all
solutions) in its system prompt and decides everything by itself:
what the player sees, whether actions succeed, and when the player escapes.

Run from the project root:
    streamlit run "Version 2/app.py"
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------------
# .env lives in the project root (one level above this file)
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Marker the Game Master must output when the player escapes.
# Python looks for it to detect game completion.
ESCAPE_MARKER = "[ESCAPED]"

# ---------------------------------------------------------------------------
# 2. Game Master instructions (the whole game lives in this prompt in V1)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""
You are the Game Master of a text-based escape room game called "The Locked Library".
Describe the environment, respond to the player's actions, and guide the story.
Write in second person ("You see..."), atmospheric but short: 2-5 sentences per reply.

THE ROOM
The player wakes up in a dim, dusty library. The only exit is a heavy door with a
4-digit keypad. The room contains:

1. DESK - On it lies a handwritten note: "The books remember the order of the seasons."
2. BOOKSHELF - Among many old books, four stand out: titled "Winter", "Autumn",
   "Spring" and "Summer" (in that order on the shelf). Inside each cover is a
   handwritten number: Winter = 3, Autumn = 7, Spring = 4, Summer = 1.
3. DRAWER - A drawer in the desk, locked with a 4-digit combination lock.
   Code: 4173 (the book numbers in season order Spring, Summer, Autumn, Winter).
   Inside: a BRASS KEY and a TORN PAGE that reads "_ 8 _ 2".
4. PAINTING - A painting of an old scientist. It can be moved aside to reveal a small
   CABINET with a keyhole. The cabinet opens only with the brass key.
   Inside the cabinet: a PAPER that reads "Hydrogen, __, Beryllium, __".
5. PERIODIC TABLE - A large periodic table poster on the wall, showing every element
   with its atomic number (e.g. Hydrogen = 1, Beryllium = 4).
6. DOOR - The exit. 4-digit keypad. Code: 1842
   (paper gives 1 _ 4 _ via atomic numbers, torn page gives _ 8 _ 2).

PUZZLE ORDER
- Puzzle 1: Desk note + bookshelf numbers -> drawer code 4173 -> brass key + torn page.
- Puzzle 2: Move painting -> unlock cabinet with brass key -> element paper.
- Puzzle 3: Element paper + periodic table -> 1 _ 4 _ ; combine with torn page -> 1842.
- Final challenge: enter 1842 on the door.

RULES
- Only reveal what the player discovers through their actions. Do not give away
  codes or solutions directly.
- Keep track of which items the player has collected and which puzzles are solved.
- The player can only use items they have collected.
- If a code is wrong, say the lock does not open.
- If the player is stuck, you may give a small, subtle hint.
- Do not invent important new objects that are not part of the room.
- When the player correctly enters 1842 on the door, describe their escape and end
  your message with the exact text {ESCAPE_MARKER}
"""

INTRO_MESSAGE = (
    "You slowly open your eyes. The smell of old paper fills the air. "
    "You are lying on the floor of a **dim, dusty library**. "
    "The only door is shut tight, with a glowing **4-digit keypad** beside it.\n\n"
    "Around you, you can make out a **desk**, a tall **bookshelf**, a **painting** "
    "of an old scientist, and a large **periodic table** on the wall.\n\n"
    "*What do you do?*"
)

# ---------------------------------------------------------------------------
# 3. Gemini client
# ---------------------------------------------------------------------------
@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)


def ask_game_master(history):
    """Send the full conversation history to Gemini and return its reply."""
    client = get_client()
    contents = [
        types.Content(role=msg["role"], parts=[types.Part(text=msg["text"])])
        for msg in history
    ]
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )
    return response.text or "(The Game Master is silent...)"


# ---------------------------------------------------------------------------
# 4. Session state (conversation memory)
# ---------------------------------------------------------------------------
def reset_game():
    # "model" is Gemini's role name for the assistant
    st.session_state.history = [{"role": "model", "text": INTRO_MESSAGE}]
    st.session_state.escaped = False


if "history" not in st.session_state:
    reset_game()

# ---------------------------------------------------------------------------
# 5. User interface
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Escape Room - V1", page_icon="🔐")
st.title("🔐 AI Escape Room")
st.caption("Version 1 - The LLM is the Game Master")

with st.sidebar:
    st.header("How to play")
    st.markdown(
        "You are trapped in a locked library. Explore the room, find clues, "
        "solve the puzzles and escape through the door.\n\n"
        "**Type what you want to do**, for example:\n"
        "- *Examine the desk*\n"
        "- *Look at the books on the shelf*\n"
        "- *Take the key*\n"
        "- *Enter 1234 on the drawer*\n"
    )
    if st.button("🔄 Restart game", use_container_width=True):
        reset_game()
        st.rerun()
    st.divider()
    st.caption(f"Model: `{MODEL}`")

if not API_KEY:
    st.error("GEMINI_API_KEY not found. Create a .env file (see .env.example).")
    st.stop()

# Show the conversation so far
for msg in st.session_state.history:
    role = "assistant" if msg["role"] == "model" else "user"
    avatar = "🧙" if role == "assistant" else "🧑"
    with st.chat_message(role, avatar=avatar):
        st.markdown(msg["text"].replace(ESCAPE_MARKER, "").strip())

# Game finished
if st.session_state.escaped:
    st.success("🎉 Congratulations, you escaped the library!")
    st.balloons()
    st.stop()

# Player input
if player_input := st.chat_input("What do you do?"):
    st.session_state.history.append({"role": "user", "text": player_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(player_input)

    with st.chat_message("assistant", avatar="🧙"):
        with st.spinner("The Game Master is thinking..."):
            try:
                reply = ask_game_master(st.session_state.history)
            except Exception as e:
                st.error(f"Error contacting Gemini: {e}")
                st.session_state.history.pop()  # remove unanswered input
                st.stop()
        st.markdown(reply.replace(ESCAPE_MARKER, "").strip())

    st.session_state.history.append({"role": "model", "text": reply})

    if ESCAPE_MARKER in reply:
        st.session_state.escaped = True
        st.rerun()
