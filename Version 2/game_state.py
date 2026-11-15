"""
Game state and game configuration for Version 2.

Everything the game "knows" lives here in plain Python data structures.
The LLM never sees SECRETS - only Python uses them to check codes.
"""

import copy

# ---------------------------------------------------------------------------
# Secrets: puzzle solutions. NEVER sent to the LLM.
# ---------------------------------------------------------------------------
SECRETS = {
    "drawer_code": "4173",
    "door_code": "1842",
}

# ---------------------------------------------------------------------------
# Objects in the room (canonical names) and the words players may use for them
# ---------------------------------------------------------------------------
DISPLAY_NAMES = {
    "desk": "desk",
    "note": "note",
    "bookshelf": "bookshelf",
    "drawer": "drawer",
    "painting": "painting",
    "cabinet": "cabinet",
    "periodic_table": "periodic table",
    "door": "door",
    "brass_key": "brass key",
    "torn_page": "torn page",
    "element_paper": "element paper",
}

ALIASES = {
    "desk": ["desk", "wooden desk", "writing desk"],
    "note": ["note", "handwritten note"],
    "bookshelf": ["bookshelf", "bookcase", "shelf", "books", "book",
                  "winter", "spring", "summer", "autumn"],
    "drawer": ["drawer", "desk drawer", "combination lock"],
    "painting": ["painting", "picture", "portrait", "scientist"],
    "cabinet": ["cabinet", "small cabinet", "keyhole", "safe"],
    "periodic_table": ["periodic table", "poster", "elements", "table"],
    "door": ["door", "keypad", "exit"],
    "brass_key": ["brass key", "key"],
    "torn_page": ["torn page", "page"],
    "element_paper": ["element paper", "paper", "hydrogen paper"],
}

# Items that can be collected into the inventory
COLLECTIBLE_ITEMS = ["brass_key", "torn_page", "element_paper"]

# ---------------------------------------------------------------------------
# Initial state of a new game
# ---------------------------------------------------------------------------
INITIAL_STATE = {
    "inventory": [],           
    "drawer_unlocked": False,
    "painting_moved": False,
    "cabinet_unlocked": False,
    "door_unlocked": False,
    "escaped": False,
    "solved_puzzles": [],      
    "failed_attempts": 0,
    "action_log": [],       
}


def new_state():
    """Return a fresh copy of the initial game state."""
    return copy.deepcopy(INITIAL_STATE)


def normalize_object(text):
    """
    Map whatever the player (or parser) wrote to a canonical object name.
    Returns None if the object does not exist in this room.
    """
    if not text:
        return None
    text = text.lower().strip()
    if text in ALIASES:
        return text
    # Check longest aliases first for periodic table
    pairs = [(alias, name) for name, aliases in ALIASES.items() for alias in aliases]
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    for alias, name in pairs:
        if alias == text or alias in text:
            return name
    return None


def visible_summary(state):
    """Short, secret-free summary of progress, given to the narrator."""
    inv = [DISPLAY_NAMES[i] for i in state["inventory"]] or ["nothing"]
    return (
        f"Inventory: {', '.join(inv)}. "
        f"Puzzles solved: {', '.join(state['solved_puzzles']) or 'none'}. "
        f"Painting moved: {state['painting_moved']}."
    )
