"""
scorer.py — decides whether one architecture's answer to one order is correct.

The benchmark labels each order with exactly one correct OUTCOME:
  - produce items   (expected.items is non-empty)
  - clarify         (expected.shouldClarify is true)
  - reject          (expected.shouldReject is true)

Scoring philosophy (kept deliberately transparent for the dissertation):
  1. We first check the system produced the RIGHT OUTCOME TYPE.
     e.g. if it should have clarified but instead invented an order, that is wrong.
  2. For item orders we check the SET of (itemId, quantity) matches.
     Modifications are scored separately and more leniently, because phrasing
     ("no onions" vs "hold the onions") varies — we report a modification score
     but do not fail an order purely on modification wording.
  3. Hallucination is tracked independently: any itemId the system returned that
     is NOT in the menu, or any unavailable item sold, counts as a hallucination,
     regardless of whether the order was otherwise right.
"""

from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    order_id: str
    category: str
    outcome_correct: bool          # did it do the right TYPE of thing
    items_correct: bool            # did the item set match (only meaningful for item orders)
    modification_score: float      # 0..1, how many expected mods were reflected
    hallucinated: bool             # did it invent items or sell unavailable ones
    expected_outcome: str          # "items" | "clarify" | "reject"
    actual_outcome: str
    notes: str = ""


def _expected_outcome(expected):
    if expected.get("shouldReject"):
        return "reject"
    if expected.get("shouldClarify"):
        return "clarify"
    return "items"


def _actual_outcome(order_output):
    """Infer what the system actually did from its returned order object.

    Order of checks matters. An explicit 'rejected' flag is the strongest signal
    and is checked FIRST — a reject path may also set needsClarification, but a
    deliberate refusal must be scored as a reject, not a clarify.
    """
    if order_output.get("rejected"):
        return "reject"
    if order_output.get("needsClarification"):
        return "clarify"
    items = order_output.get("items") or []
    if len(items) == 0:
        # No items and no explicit clarify/reject flag — treat as a (weak) clarify
        return "clarify"
    return "items"


def score_order(benchmark_order, order_output, menu_index):
    """
    benchmark_order: one entry from benchmark.json
    order_output:    the 'order' object an architecture returned
    menu_index:      dict itemId -> menu item (for hallucination + availability checks)
    """
    expected = benchmark_order["expected"]
    exp_outcome = _expected_outcome(expected)
    act_outcome = _actual_outcome(order_output)

    returned_items = order_output.get("items") or []

    # ---- hallucination check (independent of correctness) ----
    hallucinated = False
    for it in returned_items:
        iid = it.get("itemId")
        if iid not in menu_index:
            hallucinated = True
            break
        if not menu_index[iid].get("available", True):
            hallucinated = True  # sold an unavailable item
            break

    outcome_correct = exp_outcome == act_outcome

    # ---- item-set correctness (only when items were expected) ----
    items_correct = False
    modification_score = 1.0
    if exp_outcome == "items":
        exp_pairs = sorted((i["itemId"], i["quantity"]) for i in expected["items"])
        act_pairs = sorted(
            (i.get("itemId"), i.get("quantity", 1)) for i in returned_items
        )
        items_correct = exp_pairs == act_pairs and not hallucinated

        # modification score: fraction of expected mod keywords that appear somewhere
        exp_mods = []
        for i in expected["items"]:
            exp_mods.extend(m.lower() for m in i.get("modifications", []))
        if exp_mods:
            blob = " ".join(
                " ".join(i.get("modifications", [])).lower() for i in returned_items
            )
            hit = sum(1 for m in exp_mods if any(w in blob for w in m.split() if len(w) > 2))
            modification_score = round(hit / len(exp_mods), 2)
    else:
        # for clarify/reject, "items_correct" mirrors outcome correctness
        items_correct = outcome_correct

    return ScoreResult(
        order_id=benchmark_order["id"],
        category=benchmark_order["category"],
        outcome_correct=outcome_correct,
        items_correct=items_correct,
        modification_score=modification_score,
        hallucinated=hallucinated,
        expected_outcome=exp_outcome,
        actual_outcome=act_outcome,
    )
