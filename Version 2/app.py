"""
AI Escape Room - Version 2
-------------------------------------
Python is the referee, Gemini is the storyteller.

Each turn:
  1. Gemini PARSES the player's text into a structured action (JSON)
  2. Python VALIDATES the action against the game state (actions.py)
  3. Python UPDATES the game state (game_state.py)
  4. Gemini NARRATES the outcome - without ever seeing the secret codes

Run from the project root:
    streamlit run "Version 2/app.py"
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

from game_state import new_state, visible_summary, DISPLAY_NAMES  
from actions import execute 
from llm import get_client, parse_action, narrate, MODEL 

INTRO_MESSAGE = (
    "You slowly open your eyes. The smell of old paper fills the air. "
    "You are lying on the floor of a **dim, dusty library**. "
    "The only door is shut tight, with a glowing **4-digit keypad** beside it.\n\n"
    "Around you, you can make out a **desk**, a tall **bookshelf**, a **painting** "
    "of an old scientist, and a large **periodic table** on the wall.\n\n"
    "*What do you do?*"
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def reset_game():
    st.session_state.game = new_state()
    st.session_state.chat = [{"role": "assistant", "text": INTRO_MESSAGE}]
    st.session_state.last_parsed = None


if "game" not in st.session_state:
    reset_game()


@st.cache_resource
def client():
    return get_client()


# ---------------------------------------------------------------------------
# User interface
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Escape Room - V2", page_icon="🔐")
st.title("🔐 AI Escape Room")
st.caption("Version 2 - Python validates every action, the LLM only narrates")

game = st.session_state.game

with st.sidebar:
    st.header("How to play")
    st.markdown(
        "You are trapped in a locked library. Explore, collect items, solve the "
        "puzzles and escape through the door.\n\n"
        "**Examples:** *examine the desk*, *take the key*, *move the painting*, "
        "*use the key on the cabinet*, *enter 1234 on the drawer*, *inventory*, *hint*"
    )
    if st.button("🔄 Restart game", use_container_width=True):
        reset_game()
        st.rerun()

    st.divider()
    st.subheader("🎒 Inventory")
    if game["inventory"]:
        for item in game["inventory"]:
            st.write(f"- {DISPLAY_NAMES[item]}")
    else:
        st.caption("Empty")

    st.subheader("✅ Solved puzzles")
    st.write(", ".join(game["solved_puzzles"]) or "None yet")

    # Developer view
    with st.expander("🛠 Game state (debug)"):
        st.json(game)
        if st.session_state.last_parsed is not None:
            st.caption("Last parsed action:")
            st.json(st.session_state.last_parsed)

    st.caption(f"Model: `{MODEL}`")

if not os.getenv("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY not found. Create a .env file (see .env.example).")
    st.stop()

for msg in st.session_state.chat:
    avatar = "🧙" if msg["role"] == "assistant" else "🧑"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["text"])

if game["escaped"]:
    st.success("🎉 Congratulations, you escaped the library!")
    st.balloons()
    st.stop()

if player_input := st.chat_input("What do you do?"):
    st.session_state.chat.append({"role": "user", "text": player_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(player_input)

    with st.chat_message("assistant", avatar="🧙"):
        with st.spinner("The Game Master is thinking..."):
            try:
                parsed = parse_action(client(), player_input)          
                outcome = execute(game, parsed)                         
                story = narrate(client(), player_input, outcome,       
                                visible_summary(game))
            except Exception as e:
                st.error(f"Error contacting Gemini: {e}")
                st.session_state.chat.pop()
                st.stop()
        st.markdown(story)

    st.session_state.last_parsed = parsed
    st.session_state.chat.append({"role": "assistant", "text": story})
    st.rerun()
