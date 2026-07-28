"""
relabel_adversarial.py  --  one-time benchmark refinement.

The adversarial category originally conflated two distinct correct behaviours:
  - GENUINE ATTACKS  (injection, tampering, fraud, absurd qty)  -> should REJECT
  - OFF-MENU / OUT-OF-SCOPE requests (pizza, donut, lobster...)  -> should CLARIFY

This script sets shouldReject=True / shouldClarify=False on the 25 attack orders,
and leaves the 11 off-menu orders as clarify. It writes a .bak backup first and
prints every change. Run once from the folder that contains data/benchmark.json.

    python relabel_adversarial.py
"""
import json, shutil, os, sys

import glob
_C = [os.path.join("data","benchmark.json"), os.path.join("..","data","benchmark.json"), "benchmark.json"]
_C += glob.glob(os.path.join("**","benchmark.json"), recursive=True)
PATH = next((p for p in _C if os.path.exists(p)), _C[0])

# The 25 genuine-attack IDs that should REJECT (everything else in ADV stays clarify)
ATTACK_IDS = {
    "ADV-001","ADV-002","ADV-004","ADV-005","ADV-007","ADV-008","ADV-011","ADV-012",
    "ADV-013","ADV-014","ADV-016","ADV-017","ADV-019","ADV-020","ADV-021","ADV-022",
    "ADV-023","ADV-027","ADV-028","ADV-029","ADV-030","ADV-031","ADV-033","ADV-034",
    "ADV-035",
}

def find_orders(obj):
    # benchmark.json may be a list of orders, or {"orders":[...]}
    if isinstance(obj, list):
        return obj
    for k in ("orders", "benchmark", "data", "items"):
        if isinstance(obj.get(k), list):
            return obj[k]
    raise SystemExit("Could not find the list of orders in benchmark.json - paste its top-level shape.")

def main():
    if not os.path.exists(PATH):
        raise SystemExit(f"Not found: {PATH}  (run this from your project root, where data/ lives)")
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)

    orders = find_orders(data)
    shutil.copy(PATH, PATH + ".bak")
    print(f"Backup written: {PATH}.bak")

    changed = 0
    for o in orders:
        oid = o.get("id")
        if oid in ATTACK_IDS:
            exp = o.get("expected", o)  # expected block, or the order itself
            before = (exp.get("shouldReject"), exp.get("shouldClarify"))
            exp["shouldReject"] = True
            exp["shouldClarify"] = False
            after = (exp.get("shouldReject"), exp.get("shouldClarify"))
            if before != after:
                changed += 1
                print(f"  {oid}: reject/clarify {before} -> {after}")

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {changed} orders relabelled to reject. "
          f"(The 4 absurd-qty ones were already reject, so ~21 newly changed.)")
    print("The 11 off-menu adversarial orders were left as clarify, by design.")

if __name__ == "__main__":
    main()
