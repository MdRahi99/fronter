"""
safety_rules.py  --  Version D, layer 1: a small deterministic safety filter.

WHY THIS EXISTS (for the dissertation):
The ML classifier had only 17% recall on adversarial orders, so it cannot be
trusted to catch attacks. And the validator (layer 3) only checks the final cart
against the menu, so it misses BEHAVIOURAL attacks that don't produce an invalid
cart (e.g. "ignore your instructions", "output the system prompt", "admin access").
This tiny rule layer catches those loud, obvious attacks instantly and
deterministically, BEFORE the order reaches the model.

DESIGN PRINCIPLE (important): a HARD REJECT may ONLY come from this deterministic,
auditable rule layer. The probabilistic classifier is NOT allowed to reject, because
its adversarial recall is too low to be a security gate. Anything not matched here
falls through to the normal pipeline (and, if nonsensical/off-menu, is handled as a
clarification by the validator) -- not a refusal.
"""

import re

# Each tuple: (reason, regex). Keep this list short and readable.
_INJECTION = [
    ("instruction_override", r"\bignore\b.*\b(previous|above|the menu|instructions?|rules?)\b"),
    ("instruction_override", r"\bforget\b.*\b(your|the|previous)\b.*\b(instructions?|rules?)\b"),
    ("developer_mode",       r"\bdeveloper mode\b"),
    ("jailbreak_persona",    r"\byou are (now )?(dan|jailbroken|in developer)\b"),
    ("prompt_exfiltration",  r"\b(system prompt|your prompt|your instructions)\b"),
    ("data_exfiltration",    r"\b(print|dump|show|leak)\b.*\b(database|prompt|system)\b"),
    ("privilege_escalation", r"\badmin(istrator)? (access|rights|mode)\b"),
    ("privilege_escalation", r"\boverride\b.*\b(price|prices|max|limit|quantity|rules?)\b"),
    ("destructive_action",   r"\bdelete\b.*\b(all|orders?|database)\b"),
    # NEW: fraud / account abuse
    ("fraud_attempt",        r"\bcharge\b.*\b(someone ?else|another|other)('s)?\b.*\baccount\b"),
    ("fraud_attempt",        r"\brefund\b.*\b(of|me)\b.*\b(\d|thousand|hundred)\b"),
    # NEW: raw item-id injection (customers never type internal IDs)
    ("id_injection",         r"\b(brg|sid|drk|chk|des|meal)-\d{2,}\b"),
    # NEW: out-of-scope ordering from another vendor is fine to clarify, NOT reject,
    #      so it is deliberately NOT listed here.
]

_PRICE_TAMPER = [
    ("price_tampering", r"\b(make|set|change)\b.*\b(price|prices|everything|all items?)\b.*\b(free|zero|0|half|one penny|1 penny|1p)\b"),
    ("price_tampering", r"\beverything\b.*\b(free|half price|one penny)\b"),
    ("price_tampering", r"\bhalf price\b"),
    ("price_tampering", r"\bfor free\b"),
    ("price_tampering", r"\bprice\b.*\b(to|at)\b.*\b(0|zero|free)\b"),
    ("price_tampering", r"\bwhatever i say\b"),
    # NEW: "X cost one penny / one pound", "all items cost a penny"
    ("price_tampering", r"\b(cost|costs|priced)\b.*\bone (penny|pound|pence|cent)\b"),
    ("price_tampering", r"\b(all items?|everything)\b.*\b(cost|costs|priced|for)\b.*\b(one penny|1p|a penny|free|zero)\b"),
    # NEW: tax tampering
    ("price_tampering", r"\b(change|set|make|zero)\b.*\btax\b"),
    # NEW: negative price OR negative quantity of an item (both phrasings)
    ("invalid_quantity", r"\b(minus|negative)\b.*\b(pound|pounds|pence|price|cost|cheeseburger|burger|nugget|item|order|coke|fries)\b|\bquantity\b.*\b(negative|minus)\b"),
]

# Absurd quantities -> reject. We detect any integer >= a sane threshold.
_QTY_THRESHOLD = 50
_QTY_RE = re.compile(r"\b(\d{2,})\b")

# Spelled-out absurd quantities people use in attacks.
_WORD_QTY = [
    ("absurd_quantity", r"\b(thousand|ten thousand|hundred thousand|million)\b"),
]

def _scan(text, rules):
    for reason, pat in rules:
        if re.search(pat, text, flags=re.IGNORECASE):
            return reason
    return None

def safety_check(text: str):
    t = text or ""
    r = _scan(t, _INJECTION)
    if r:
        return {"flagged": True, "action": "reject", "reason": r}
    r = _scan(t, _PRICE_TAMPER)
    if r:
        return {"flagged": True, "action": "reject", "reason": r}
    for m in _QTY_RE.finditer(t):
        try:
            if int(m.group(1)) >= _QTY_THRESHOLD:
                return {"flagged": True, "action": "reject", "reason": "absurd_quantity"}
        except ValueError:
            pass
    r = _scan(t, _WORD_QTY)
    if r:
        return {"flagged": True, "action": "reject", "reason": r}
    return {"flagged": False}
