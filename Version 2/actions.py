"""
Action validation for Version 2.

Python decides whether each action succeeds not the LLM.
Every function checks the game state, updates it if the action is allowed,
and returns a result dictionary:

    {"success": bool, "facts": "what actually happened, in plain words"}

The narrator LLM only turns these facts into a story.
"""

from game_state import SECRETS, COLLECTIBLE_ITEMS, DISPLAY_NAMES, normalize_object

NOT_HERE = "There is no such thing in this room."


def result(success, facts):
    return {"success": success, "facts": facts}


# ---------------------------------------------------------------------------
# EXAMINE
# ---------------------------------------------------------------------------
def examine(state, target):
    obj = normalize_object(target)
    if obj is None:
        if not target:
            return result(True, "A dim, dusty library: a desk, a tall bookshelf, a painting "
                                "of an old scientist, a periodic table poster on the wall, "
                                "and a locked door with a 4-digit keypad.")
        return result(False, NOT_HERE)

    if obj == "desk":
        drawer = ("The drawer is open." if state["drawer_unlocked"]
                  else "It has a drawer locked with a 4-digit combination lock.")
        return result(True, "An old wooden desk. On it lies a handwritten note: "
                            "'The books remember the order of the seasons.' " + drawer)

    if obj == "note":
        return result(True, "The note says: 'The books remember the order of the seasons.'")

    if obj == "bookshelf":
        return result(True, "Among many dusty books, four stand out, in this order: "
                            "'Winter', 'Autumn', 'Spring', 'Summer'. Inside each cover is a "
                            "handwritten number: Winter 3, Autumn 7, Spring 4, Summer 1.")

    if obj == "drawer":
        if not state["drawer_unlocked"]:
            return result(True, "The drawer is locked with a 4-digit combination lock.")
        remaining = [DISPLAY_NAMES[i] for i in ["brass_key", "torn_page"]
                     if i not in state["inventory"]]
        return result(True, "The drawer is open. Inside: "
                            + (", ".join(remaining) if remaining else "nothing anymore") + ".")

    if obj == "painting":
        if state["painting_moved"]:
            return result(True, "The painting has been moved aside, revealing a small cabinet.")
        return result(True, "A painting of an old scientist. It hangs slightly crooked, "
                            "as if it could be moved.")

    if obj == "cabinet":
        if not state["painting_moved"]:
            return result(False, NOT_HERE)  # not discovered yet
        if not state["cabinet_unlocked"]:
            return result(True, "A small wall cabinet with a brass keyhole. It is locked.")
        inside = ("a paper" if "element_paper" not in state["inventory"] else "nothing anymore")
        return result(True, f"The cabinet is open. Inside: {inside}.")

    if obj == "periodic_table":
        return result(True, "A large periodic table of the elements. Each element shows its "
                            "atomic number, e.g. Hydrogen 1, Helium 2, Lithium 3, Beryllium 4, "
                            "Boron 5, Carbon 6, ...")

    if obj == "door":
        if state["door_unlocked"]:
            return result(True, "The door stands open.")
        return result(True, "A heavy locked door with a glowing 4-digit keypad.")

    # Items: only readable if the player actually holds them
    if obj in COLLECTIBLE_ITEMS:
        if obj not in state["inventory"]:
            return result(False, f"You don't have the {DISPLAY_NAMES[obj]}.")
        texts = {
            "brass_key": "A small, old brass key.",
            "torn_page": "A torn page. It reads: '_ 8 _ 2'.",
            "element_paper": "A paper that reads: 'Hydrogen, __, Beryllium, __'.",
        }
        return result(True, texts[obj])

    return result(False, NOT_HERE)


# ---------------------------------------------------------------------------
# TAKE
# ---------------------------------------------------------------------------
def take(state, target):
    obj = normalize_object(target)
    if obj is None:
        return result(False, NOT_HERE)
    if obj not in COLLECTIBLE_ITEMS:
        return result(False, f"You can't take the {DISPLAY_NAMES[obj]}.")
    if obj in state["inventory"]:
        return result(False, f"You already have the {DISPLAY_NAMES[obj]}.")

    if obj in ("brass_key", "torn_page") and not state["drawer_unlocked"]:
        return result(False, f"You don't see any {DISPLAY_NAMES[obj]} anywhere.")
    if obj == "element_paper" and not state["cabinet_unlocked"]:
        return result(False, "You don't see any such paper anywhere.")

    state["inventory"].append(obj)
    return result(True, f"The {DISPLAY_NAMES[obj]} is now in your inventory.")


# ---------------------------------------------------------------------------
# MOVE
# ---------------------------------------------------------------------------
def move(state, target):
    obj = normalize_object(target)
    if obj is None:
        return result(False, NOT_HERE)
    if obj != "painting":
        return result(False, f"The {DISPLAY_NAMES[obj]} doesn't move.")
    if state["painting_moved"]:
        return result(False, "The painting has already been moved aside.")
    state["painting_moved"] = True
    return result(True, "You move the painting aside. Behind it is a small cabinet "
                        "with a brass keyhole.")


# ---------------------------------------------------------------------------
# OPEN
# ---------------------------------------------------------------------------
def open_object(state, target):
    obj = normalize_object(target)
    if obj is None:
        return result(False, NOT_HERE)
    if obj == "drawer":
        if state["drawer_unlocked"]:
            return examine(state, "drawer")
        return result(False, "The drawer is locked. It needs a 4-digit combination.")
    if obj == "cabinet":
        if not state["painting_moved"]:
            return result(False, NOT_HERE)
        if state["cabinet_unlocked"]:
            return examine(state, "cabinet")
        return result(False, "The cabinet is locked. It has a keyhole.")
    if obj == "door":
        if state["door_unlocked"]:
            return result(True, "The door is already open.")
        return result(False, "The door is locked. It needs a 4-digit code on the keypad.")
    return result(False, f"You can't open the {DISPLAY_NAMES[obj]}.")


# ---------------------------------------------------------------------------
# USE ITEM
# ---------------------------------------------------------------------------
def use_item(state, item, target):
    item_obj = normalize_object(item)
    target_obj = normalize_object(target)

    if item_obj is None:
        return result(False, NOT_HERE)
    # Inventory check: you can only use what you have collected
    if item_obj not in state["inventory"]:
        return result(False, f"You don't have the {DISPLAY_NAMES[item_obj]}.")
    if target_obj is None:
        return result(False, "Use it on what? That target is not in this room.")

    if item_obj == "brass_key" and target_obj == "cabinet":
        if not state["painting_moved"]:
            return result(False, NOT_HERE)
        if state["cabinet_unlocked"]:
            return result(False, "The cabinet is already unlocked.")
        state["cabinet_unlocked"] = True
        state["solved_puzzles"].append("cabinet")
        return result(True, "The brass key turns. The cabinet opens. Inside lies a paper.")

    if item_obj == "brass_key":
        return result(False, f"The brass key doesn't fit the {DISPLAY_NAMES[target_obj]}.")

    return result(False, f"Nothing happens when you use the {DISPLAY_NAMES[item_obj]} "
                         f"on the {DISPLAY_NAMES[target_obj]}.")


# ---------------------------------------------------------------------------
# ENTER CODE
# ---------------------------------------------------------------------------
def enter_code(state, target, code):
    obj = normalize_object(target)
    code = "".join(ch for ch in str(code or "") if ch.isdigit())

    if obj not in ("drawer", "door"):
        return result(False, "There is no keypad or combination lock there. "
                             "Codes can be entered on the drawer or the door.")
    if len(code) != 4:
        return result(False, "The lock needs exactly 4 digits.")

    if obj == "drawer":
        if state["drawer_unlocked"]:
            return result(False, "The drawer is already open.")
        if code == SECRETS["drawer_code"]:
            state["drawer_unlocked"] = True
            state["solved_puzzles"].append("drawer")
            return result(True, f"Code {code} is correct. The drawer clicks open. "
                                "Inside: a brass key and a torn page.")
        state["failed_attempts"] += 1
        return result(False, f"Code {code} is wrong. The drawer stays locked.")

    if obj == "door":
        if code == SECRETS["door_code"]:
            state["door_unlocked"] = True
            state["escaped"] = True
            state["solved_puzzles"].append("door")
            return result(True, f"Code {code} is correct. The keypad turns green and the "
                                "door swings open. The player has ESCAPED the library.")
        state["failed_attempts"] += 1
        return result(False, f"Code {code} is wrong. The keypad flashes red.")


# ---------------------------------------------------------------------------
# INVENTORY / HINT / UNKNOWN
# ---------------------------------------------------------------------------
def show_inventory(state):
    if not state["inventory"]:
        return result(True, "Your inventory is empty.")
    items = ", ".join(DISPLAY_NAMES[i] for i in state["inventory"])
    return result(True, f"You are carrying: {items}.")


def hint(state):
    """Progress-based hints. Never reveals a code directly."""
    if not state["drawer_unlocked"]:
        h = "The note on the desk and the four books seem connected. Think about seasons."
    elif "brass_key" not in state["inventory"]:
        h = "Something useful is still in the open drawer."
    elif not state["painting_moved"]:
        h = "The painting hangs crooked. Maybe something is behind it."
    elif not state["cabinet_unlocked"]:
        h = "The cabinet has a keyhole. Do you have something that fits?"
    elif "element_paper" not in state["inventory"]:
        h = "Take what is inside the cabinet."
    else:
        h = ("Chemical elements have numbers. Combine the paper with the torn page "
             "to form the door code.")
    return result(True, f"Hint: {h}")


def unknown(state, player_text=""):
    return result(False, "That action is not possible in this game. The rules of the "
                         "room cannot be changed by words alone.")


# ---------------------------------------------------------------------------
# Dispatcher: parsed action -> validation function
# ---------------------------------------------------------------------------
def execute(state, parsed):
    """Run the validated action and log it."""
    action = (parsed.get("action") or "unknown").lower()
    target = parsed.get("target")
    item = parsed.get("item")
    code = parsed.get("code")

    if action == "look":
        res = examine(state, None)
    elif action == "examine":
        res = examine(state, target)
    elif action == "take":
        res = take(state, target or item)
    elif action == "move":
        res = move(state, target)
    elif action == "open":
        res = open_object(state, target)
    elif action == "use":
        res = use_item(state, item, target)
    elif action == "enter_code":
        res = enter_code(state, target, code)
    elif action == "inventory":
        res = show_inventory(state)
    elif action == "hint":
        res = hint(state)
    else:
        res = unknown(state)

    state["action_log"].append({
        "action": action, "target": target, "item": item,
        "code": code, "success": res["success"],
    })
    return res
