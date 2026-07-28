"""
router_demo.py  --  DEMO-ONLY variant of the Version D router.

This is NOT the evaluated system. The frozen router.py (the one measured in the
210-order benchmark and all statistics) is unchanged. This variant exists only so
the live web demo takes normal customer orders smoothly.

WHAT IS DIFFERENT FROM router.py (one added step, nothing removed):
  A menu-match override sits between Layer 1 (safety) and the classifier. If an
  order plainly names real, available menu items and Layer 1 did not flag it, the
  order is built directly - a low-confidence or mislabelled classifier guess is no
  longer allowed to block an obviously valid order.

WHY THIS IS CONSISTENT WITH THE DISSERTATION:
  It applies the SAME principle the project already argues for adversarial handling
  - trust the deterministic layer (here, menu matching) over the weak ML classifier
  (~51% overall, low confidence on unseen phrasings) - now for routing as well.
  The classifier still runs and still routes anything the menu layer can't resolve.

  Safety is untouched: hard rejects still come ONLY from Layer 1 (safety_rules).
"""

import os
import re
import json

from safety_rules import safety_check

try:
    from classify import predict_type
except Exception:
    predict_type = None

CLARIFY_TYPES = {"ambiguous", "incomplete", "contradictory"}
EXECUTE_TYPES = {"simple", "complex"}
LOW_CONFIDENCE = 0.40

# --------------------------------------------------------------------------- menu
# Load the menu once so the override is cheap. Path can be overridden with the
# FRONTER_MENU_PATH env var; otherwise we look in the usual project locations.
def _find_menu():
    candidates = [
        os.environ.get("FRONTER_MENU_PATH"),
        os.path.join("data", "menu.json"),
        os.path.join("..", "data", "menu.json"),
        os.path.join(os.path.dirname(__file__), "..", "data", "menu.json"),
        "menu.json",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

def _load_menu():
    path = _find_menu()
    if not path:
        return [], {}
    data = json.load(open(path, encoding="utf-8"))
    items = data.get("items", [])
    available = [it for it in items if it.get("available", True)]
    # Category -> count of available items, to detect "which one?" ambiguity.
    cat_counts = {}
    for it in available:
        c = it.get("category", "")
        cat_counts[c] = cat_counts.get(c, 0) + 1
    return available, cat_counts

_MENU, _CAT_COUNTS = _load_menu()

# Phrases that name a whole category rather than one item. If a customer says one
# of these and the category has 2+ items, we still ask which one they meant.
_CATEGORY_WORDS = {
    "burger": "burgers",
    "chicken burger": "burgers",   # crispy vs spicy -> ambiguous on purpose
    "chicken": "chicken",
    "fries": "sides",              # note: "fries" is also a specific item; handled below
    "side": "sides",
    "drink": "drinks",
    "soda": "drinks",
    "milkshake": "drinks",         # 3 milkshakes -> ambiguous
    "shake": "drinks",
    "dessert": "desserts",
    "meal": "meals",
    "juice": "drinks",
}

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())

def _item_names_and_aliases():
    """Yield (searchable_text, item) for every available item name + alias."""
    for it in _MENU:
        yield _norm(it.get("name", "")), it
        for al in it.get("aliases", []):
            yield _norm(al), it

def _specific_matches(text: str):
    """Return the set of item names that appear by exact name/alias in the text."""
    t = " " + _norm(text) + " "
    hits = set()
    for phrase, it in _item_names_and_aliases():
        if phrase and (" " + phrase + " ") in t:
            hits.add(it.get("name"))
    return hits

def _ambiguous_category_mention(text: str) -> bool:
    """True if the text leans on a category word (e.g. 'chicken burger') that maps
    to 2+ items without naming which specific item is meant.

    This fires even when the order also contains other clearly-named items, because
    the ambiguous part alone is enough reason to ask (e.g. "one chicken burger and
    a fries" - the fries is clear, but which chicken burger?)."""
    t = " " + _norm(text) + " "
    specific_texts = {p for p, _ in _item_names_and_aliases()
                      if p and (" " + p + " ") in t}
    for word, cat in _CATEGORY_WORDS.items():
        if (" " + word + " ") not in t:
            continue
        if _CAT_COUNTS.get(cat, 0) < 2:
            continue
        if word == "fries":
            # "fries" is itself a specific item name, so a bare "fries" is fine.
            continue
        # Is this category word already covered by a specific item name the customer
        # gave? e.g. "crispy chicken burger" contains the word "burger" but the
        # specific alias "crispy chicken burger" resolves it.
        covered = any(word in st and st != word for st in specific_texts)
        if not covered:
            return True
    return False

def _looks_orderable(text: str) -> bool:
    """True if the order plainly names at least one real, available menu item and
    is not just an ambiguous category mention."""
    if _ambiguous_category_mention(text):
        return False
    return len(_specific_matches(text)) >= 1

# --------------------------------------------------------------------------- route
def route_order(text: str):
    """Same contract as router.py, with one extra menu-match step (see module docstring)."""
    # --- Layer 1: deterministic safety FIRST (the ONLY thing that can reject) ---
    safe = safety_check(text)
    if safe["flagged"]:
        return {"route": safe["action"], "reason": f"safety:{safe['reason']}",
                "type": "rule", "confidence": 1.0}

    # --- Layer 1.5 (DEMO ONLY): trust the menu over a weak classifier label ---
    if _looks_orderable(text):
        return {"route": "execute", "reason": "menu_match_override",
                "type": "menu-match", "confidence": 1.0}

    # --- Layer 2: ML classifier (never rejects), unchanged from router.py ---
    if predict_type is None:
        return {"route": "clarify", "reason": "classifier_unavailable",
                "type": None, "confidence": None}

    pred = predict_type(text)
    ptype, conf = str(pred["type"]), pred["confidence"]

    if conf is not None and conf < LOW_CONFIDENCE:
        return {"route": "clarify", "reason": "low_confidence",
                "type": ptype, "confidence": conf}
    if ptype in CLARIFY_TYPES:
        return {"route": "clarify", "reason": f"type:{ptype}",
                "type": ptype, "confidence": conf}
    if ptype in EXECUTE_TYPES:
        return {"route": "execute", "reason": f"type:{ptype}",
                "type": ptype, "confidence": conf}
    if ptype == "adversarial":
        return {"route": "clarify", "reason": "classifier_adversarial_unconfirmed",
                "type": ptype, "confidence": conf}
    return {"route": "clarify", "reason": "fallback", "type": ptype, "confidence": conf}
