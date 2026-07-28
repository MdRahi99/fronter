"""
run_eval.py — run one architecture across the benchmark and score every order.

Usage:
    python run_eval.py --arch A --model llama3 --limit 10     # quick test on 10 orders
    python run_eval.py --arch A --model llama3                # full 210-order run

Outputs (in results/):
    raw_<arch>_<model>_<timestamp>.json   every order, output, score, metrics
    summary_<arch>_<model>_<timestamp>.txt readable metrics report
    summary_<arch>_<model>_<timestamp>.csv per-category numbers for charting
"""

import argparse, json, time, os, csv
from datetime import datetime
from urllib import request as urlrequest

from scorer import score_order

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "results")
API = os.environ.get("FRONTER_API", "http://localhost:5000")


def call_backend(message, arch, model, timeout=300):
    body = json.dumps({"message": message, "architecture": arch, "model": model}).encode()
    req = urlrequest.Request(
        f"{API}/api/order", data=body, headers={"Content-Type": "application/json"}
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="A")
    ap.add_argument("--model", default="llama3")
    ap.add_argument("--limit", type=int, default=0, help="0 = all orders")
    args = ap.parse_args()

    menu = {i["itemId"]: i for i in json.load(open(os.path.join(DATA, "menu.json")))["items"]}
    bench = json.load(open(os.path.join(DATA, "benchmark.json")))
    orders = bench["orders"]
    if args.limit:
        # take a spread across categories, not just the first N
        by_cat = {}
        for o in orders:
            by_cat.setdefault(o["category"], []).append(o)
        per = max(1, args.limit // len(by_cat))
        picked = []
        for cat, lst in by_cat.items():
            picked.extend(lst[:per])
        orders = picked[: args.limit]

    os.makedirs(RESULTS, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = f"{args.arch}_{args.model}_{stamp}"

    results = []
    print(f"Running Version {args.arch} on {len(orders)} orders with {args.model}...\n")
    t0 = time.time()
    for n, o in enumerate(orders, 1):
        try:
            time.sleep(2)  # pace requests so Groq free-tier rate limit isn't hit
            resp = call_backend(o["text"], args.arch, args.model)
            order_out = resp.get("order", {})
            metrics = resp.get("metrics", {})
            sc = score_order(o, order_out, menu)
            ok = "OK " if sc.outcome_correct and sc.items_correct else "XX "
            hall = " [HALLUCINATION]" if sc.hallucinated else ""
            print(f"{ok}{o['id']:<8} {o['category']:<13} {metrics.get('totalDurationMs','?')}ms{hall}")
            results.append({
                "order": o, "output": order_out, "metrics": metrics,
                "score": sc.__dict__,
            })
        except Exception as e:
            print(f"ERR {o['id']:<8} {o['category']:<13} {e}")
            results.append({"order": o, "error": str(e)})

    elapsed = round(time.time() - t0, 1)
    raw_path = os.path.join(RESULTS, f"raw_{tag}.json")
    json.dump({"meta": {"arch": args.arch, "model": args.model, "elapsed_s": elapsed,
                        "n": len(orders)}, "results": results},
              open(raw_path, "w"), indent=2, default=str)

    write_summary(results, tag, args, elapsed)
    print(f"\nDone in {elapsed}s. Raw + summary saved in results/ ({tag})")


def write_summary(results, tag, args, elapsed):
    scored = [r for r in results if "score" in r]
    n = len(scored) or 1

    def rate(pred):
        return round(100 * sum(1 for r in scored if pred(r["score"])) / n, 1)

    overall_correct = rate(lambda s: s["outcome_correct"] and s["items_correct"])
    hallucination = rate(lambda s: s["hallucinated"])

    # per-category accuracy
    cats = {}
    for r in scored:
        s = r["score"]
        c = cats.setdefault(s["category"], {"n": 0, "correct": 0, "hall": 0})
        c["n"] += 1
        if s["outcome_correct"] and s["items_correct"]:
            c["correct"] += 1
        if s["hallucinated"]:
            c["hall"] += 1

    # clarify + reject success (outcome-type accuracy on those categories)
    def outcome_acc(target):
        rel = [r["score"] for r in scored if r["score"]["expected_outcome"] == target]
        if not rel:
            return None
        return round(100 * sum(1 for s in rel if s["outcome_correct"]) / len(rel), 1)

    clarify_acc = outcome_acc("clarify")
    reject_acc = outcome_acc("reject")

    lat = [r["metrics"].get("totalDurationMs") for r in scored
           if r.get("metrics", {}).get("totalDurationMs")]
    avg_lat = round(sum(lat) / len(lat)) if lat else None

    lines = [
        f"fronter evaluation summary",
        f"Architecture: {args.arch}   Model: {args.model}   Orders: {n}   Time: {elapsed}s",
        "-" * 52,
        f"Overall accuracy        : {overall_correct}%",
        f"Hallucination rate      : {hallucination}%",
        f"Clarification accuracy  : {clarify_acc}%" if clarify_acc is not None else "",
        f"Adversarial reject acc. : {reject_acc}%" if reject_acc is not None else "",
        f"Average latency         : {avg_lat} ms" if avg_lat else "",
        "-" * 52,
        "Per-category accuracy:",
    ]
    for c, v in cats.items():
        acc = round(100 * v["correct"] / v["n"], 1)
        lines.append(f"  {c:<14} {acc:>5}%   ({v['correct']}/{v['n']})   hall {v['hall']}")
    summary = "\n".join(l for l in lines if l != "")
    print("\n" + summary)

    open(os.path.join(RESULTS, f"summary_{tag}.txt"), "w").write(summary)

    with open(os.path.join(RESULTS, f"summary_{tag}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "n", "accuracy_pct", "hallucinations"])
        for c, v in cats.items():
            w.writerow([c, v["n"], round(100 * v["correct"] / v["n"], 1), v["hall"]])
        w.writerow(["OVERALL", n, overall_correct, sum(v["hall"] for v in cats.values())])


if __name__ == "__main__":
    main()
