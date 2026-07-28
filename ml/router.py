"""
router.py  --  Version D, layer 2: the router (the "decision maker").

It decides what to DO with each order, using two inputs:
  1) safety_rules.safety_check()  -> catches obvious attacks first (deterministic)
  2) classify.predict_type()      -> the ML sorter, for everything else

It outputs a ROUTE (a decision), not the final order. The chosen architecture
then executes that route, and the validator (layer 3) checks the result.

Routes:
  "reject"   -> refuse (attack / tampering / absurd quantity)
  "clarify"  -> ask a question (ambiguous / incomplete / contradictory / off-menu)
  "execute"  -> build the order decisively (simple / complex)

DESIGN PRINCIPLE (important, for the dissertation):
  A HARD REJECT may come ONLY from Layer 1 (the deterministic, auditable rule
  layer). The ML classifier's adversarial recall was only 17%, so it is NOT
  trusted to make a security decision. When the classifier *guesses* adversarial,
  we treat that as "I am not sure what this is" and ASK (clarify) rather than
  refuse a possibly-legitimate customer (e.g. someone asking for an off-menu item).
  Layer 3 (the validator) is the final backstop. Defence in depth.
"""

from safety_rules import safety_check

try:
    from classify import predict_type
except Exception:
    predict_type = None  # allows router to be imported before model is trained

# How each predicted order-type should be handled.
CLARIFY_TYPES = {"ambiguous", "incomplete", "contradictory"}
EXECUTE_TYPES = {"simple", "complex"}

# If the classifier is very unsure, prefer to ASK rather than guess.
LOW_CONFIDENCE = 0.40

def route_order(text: str):
    """
    Returns a decision dict:
      {
        "route": "reject"|"clarify"|"execute",
        "reason": "...",            # why
        "type": "<classifier type or 'rule'>",
        "confidence": <0..1 or None>
      }
    """
    # --- Layer 1: deterministic safety check FIRST (the ONLY thing that can reject) ---
    safe = safety_check(text)
    if safe["flagged"]:
        return {"route": safe["action"], "reason": f"safety:{safe['reason']}",
                "type": "rule", "confidence": 1.0}

    # --- Layer 2: ML classifier for quality routing (never rejects) ---
    if predict_type is None:
        # Model not trained yet - fail safe by asking.
        return {"route": "clarify", "reason": "classifier_unavailable",
                "type": None, "confidence": None}

    pred = predict_type(text)
    ptype, conf = str(pred["type"]), pred["confidence"]

    # If the model is very unsure, be cautious and ask.
    if conf is not None and conf < LOW_CONFIDENCE:
        return {"route": "clarify", "reason": "low_confidence",
                "type": ptype, "confidence": conf}

    if ptype in CLARIFY_TYPES:
        return {"route": "clarify", "reason": f"type:{ptype}",
                "type": ptype, "confidence": conf}

    if ptype in EXECUTE_TYPES:
        return {"route": "execute", "reason": f"type:{ptype}",
                "type": ptype, "confidence": conf}

    # If the classifier GUESSES adversarial, we do NOT reject on its word alone
    # (17% recall - untrustworthy as a security gate). Treat as "unsure" -> clarify.
    # Genuine attacks were already hard-rejected by Layer 1 above.
    if ptype == "adversarial":
        return {"route": "clarify", "reason": "classifier_adversarial_unconfirmed",
                "type": ptype, "confidence": conf}

    # Fallback: ask rather than guess.
    return {"route": "clarify", "reason": "fallback", "type": ptype, "confidence": conf}
