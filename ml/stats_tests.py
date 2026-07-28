"""
stats_tests.py - significance tests for the fronter 4x3 grid.

Reads every results/raw_<arch>_<model>_<stamp>.json, pairs the same orders
across architectures within each model, and runs McNemar's exact test for
D vs A, D vs B, D vs C. Also gives 95% Wilson confidence intervals for each
architecture's overall accuracy.

Usage (from the ml/ folder):
    py stats_tests.py

Needs: scipy   (py -m pip install scipy)
Outputs: results/stats_summary.txt and results/stats_summary.csv
"""

import json, os, glob, csv, math
from scipy.stats import binomtest

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

# treat llama3 and llama3.1 as one model column (C runs on llama3.1)
def model_family(model):
    m = model.lower()
    if m.startswith("llama3"):
        return "llama3"
    return m

def order_correct(score):
    return bool(score.get("outcome_correct")) and bool(score.get("items_correct"))

def load_runs():
    """Pick, for each (arch, model_family), the run with the most orders
    (so 12-order smoke tests are ignored automatically)."""
    runs = {}
    for path in glob.glob(os.path.join(RESULTS, "raw_*.json")):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        meta = data.get("meta", {})
        arch, model = meta.get("arch"), meta.get("model", "")
        if not arch or not model:
            continue
        fam = model_family(model)
        key = (arch, fam)
        n = meta.get("n", 0)
        if key not in runs or n > runs[key]["n"]:
            scores = {}
            for r in data.get("results", []):
                if "score" in r:
                    scores[r["order"]["id"]] = order_correct(r["score"])
            runs[key] = {"n": n, "scores": scores, "file": os.path.basename(path)}
    return runs

def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0, centre - half) * 100, min(1, centre + half) * 100)

def mcnemar_exact(b, c):
    """Exact McNemar p-value: b = D right & baseline wrong, c = D wrong & baseline right."""
    n = b + c
    if n == 0:
        return 1.0
    return binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue

def main():
    runs = load_runs()
    fams = sorted({fam for (_, fam) in runs})
    lines, csvrows = [], []

    lines.append("fronter statistical tests - McNemar's exact test, D vs baselines")
    lines.append("An order counts as correct only if outcome AND items are both right.")
    lines.append("p < 0.05 means the difference is statistically significant.")
    lines.append("=" * 72)

    for fam in fams:
        lines.append(f"\nMODEL: {fam}")
        # accuracy + CI per architecture
        for arch in ["A", "B", "C", "D"]:
            run = runs.get((arch, fam))
            if not run:
                continue
            k = sum(run["scores"].values()); n = len(run["scores"])
            lo, hi = wilson_ci(k, n)
            lines.append(f"  {arch}: {k}/{n} correct = {100*k/n:.1f}%   95% CI [{lo:.1f}%, {hi:.1f}%]   ({run['file']})")
            csvrows.append([fam, arch, n, k, f"{100*k/n:.1f}", f"{lo:.1f}", f"{hi:.1f}", "", "", "", ""])

        d = runs.get(("D", fam))
        if not d:
            continue
        lines.append(f"  D vs baselines (paired on the same orders):")
        for base in ["A", "B", "C"]:
            brun = runs.get((base, fam))
            if not brun:
                continue
            common = set(d["scores"]) & set(brun["scores"])
            b = sum(1 for oid in common if d["scores"][oid] and not brun["scores"][oid])
            c = sum(1 for oid in common if not d["scores"][oid] and brun["scores"][oid])
            p = mcnemar_exact(b, c)
            sig = "SIGNIFICANT" if p < 0.05 else "not significant"
            pstr = "< 0.001" if p < 0.001 else f"= {p:.3f}"
            lines.append(f"    D vs {base}: n={len(common)} paired | D-only-right={b} | {base}-only-right={c} | p {pstr}  -> {sig}")
            csvrows.append([fam, f"D_vs_{base}", len(common), "", "", "", "", b, c, f"{p:.6f}", sig])

    out = "\n".join(lines)
    print(out)
    open(os.path.join(RESULTS, "stats_summary.txt"), "w", encoding="utf-8").write(out)
    with open(os.path.join(RESULTS, "stats_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "arch_or_test", "n", "correct", "acc_pct", "ci_low", "ci_high",
                    "D_only_right", "base_only_right", "p_value", "verdict"])
        w.writerows(csvrows)
    print("\nSaved results/stats_summary.txt and results/stats_summary.csv")

if __name__ == "__main__":
    main()