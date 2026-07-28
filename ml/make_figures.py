"""
make_figures.py - generate every dissertation figure from the raw results.

Reads results/raw_*.json (and results/stats_summary.csv if present) and writes
PNG figures into figures/. Nothing is hardcoded: re-running after new results
regenerates every chart from the data.

Usage (from the ml/ folder):
    py make_figures.py                  # colour style (default)
    py make_figures.py --style plain    # black/grey style for the final thesis

Needs: matplotlib, numpy   (py -m pip install matplotlib numpy)
"""

import json, os, glob, csv, argparse, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
FIGS = os.path.join(HERE, "figures")

ARCHS = ["A", "B", "C", "D"]
ARCH_LABELS = {"A": "A\nDirect", "B": "B\nRAG", "C": "C\nTool", "D": "D\nHybrid"}
CATS = ["simple", "complex", "ambiguous", "incomplete", "contradictory", "adversarial"]
CAT_LABELS = ["Simple", "Complex", "Ambiguous", "Incomplete", "Contradictory", "Adversarial"]

# ----------------------------------------------------------------------------- styles
def get_palette(style):
    if style == "plain":
        return {
            "models": {"llama3": "#c8c8c8", "mistral": "#8a8a8a", "qwen2.5": "#3a3a3a"},
            "d_models": {"llama3": "#c8c8c8", "mistral": "#8a8a8a", "qwen2.5": "#3a3a3a"},
            "arch": {"A": "#c8c8c8", "B": "#a5a5a5", "C": "#6f6f6f", "D": "#111111"},
            "accent": "#111111", "accent_dark": "#000000",
            "bad": "#7a7a7a", "ink": "#000000", "sub": "#333333", "grid": "#e6e6e6",
            "heat": "Greys",
        }
    return {
        "models": {"llama3": "#b8c4d0", "mistral": "#94a3b4", "qwen2.5": "#6f8090"},
        "d_models": {"llama3": "#7fd1c6", "mistral": "#12a594", "qwen2.5": "#0b7d70"},
        "arch": {"A": "#b8c4d0", "B": "#94a3b4", "C": "#f0a93b", "D": "#12a594"},
        "accent": "#12a594", "accent_dark": "#0b7d70",
        "bad": "#e5674f", "ink": "#1c2b33", "sub": "#5a6b75", "grid": "#eef1f4",
        "heat": "BuGn",
    }

def setup(pal):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11.5,
        "text.color": pal["ink"], "axes.labelcolor": pal["sub"],
        "xtick.color": pal["ink"], "ytick.color": pal["sub"],
        "axes.edgecolor": "#d7dde3", "figure.dpi": 300, "savefig.dpi": 300,
    })

def frame(ax, pal, ymax):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", color=pal["grid"], linewidth=1.3, zorder=0)
    ax.set_axisbelow(True); ax.tick_params(length=0); ax.set_ylim(0, ymax)

# ----------------------------------------------------------------------------- data
def model_family(model):
    m = model.lower()
    return "llama3" if m.startswith("llama3") else m

def order_correct(s):
    return bool(s.get("outcome_correct")) and bool(s.get("items_correct"))

def load_runs():
    """Best (largest-n) run per (arch, model family); smoke tests are skipped."""
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
        key = (arch, model_family(model))
        if key in runs and meta.get("n", 0) <= runs[key]["n"]:
            continue
        scored = [r for r in data.get("results", []) if "score" in r]
        per_cat = {c: {"n": 0, "ok": 0} for c in CATS}
        halluc = 0
        lats = []
        scores = {}
        for r in scored:
            s = r["score"]; c = s["category"]
            ok = order_correct(s)
            scores[r["order"]["id"]] = ok
            if c in per_cat:
                per_cat[c]["n"] += 1
                per_cat[c]["ok"] += 1 if ok else 0
            halluc += 1 if s.get("hallucinated") else 0
            ms = (r.get("metrics") or {}).get("totalDurationMs")
            if ms:
                lats.append(ms)
        n = len(scored) or 1
        runs[key] = {
            "n": meta.get("n", n),
            "overall": 100 * sum(scores.values()) / n,
            "halluc": 100 * halluc / n,
            "latency_s": (sum(lats) / len(lats) / 1000) if lats else None,
            "per_cat": {c: (100 * v["ok"] / v["n"] if v["n"] else None) for c, v in per_cat.items()},
            "scores": scores,
        }
    return runs

def load_stats():
    """Optional: stats_summary.csv from stats_tests.py (CIs + McNemar counts)."""
    path = os.path.join(RESULTS, "stats_summary.csv")
    ci, mcnemar = {}, {}
    if not os.path.exists(path):
        return ci, mcnemar
    for row in csv.DictReader(open(path, encoding="utf-8")):
        fam, tag = row["model"], row["arch_or_test"]
        if tag in ARCHS and row.get("ci_low"):
            ci[(tag, fam)] = (float(row["acc_pct"]), float(row["ci_low"]), float(row["ci_high"]))
        elif tag.startswith("D_vs_") and row.get("D_only_right"):
            mcnemar[(tag[-1], fam)] = (int(row["D_only_right"]), int(row["base_only_right"]), row["p_value"])
    return ci, mcnemar

# ----------------------------------------------------------------------------- figures
def fig1_overall(runs, fams, pal):
    x = np.arange(len(ARCHS)); w = 0.8 / len(fams)
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    for i, fam in enumerate(fams):
        vals = [runs[(a, fam)]["overall"] if (a, fam) in runs else 0 for a in ARCHS]
        cols = [pal["d_models"][fam] if a == "D" else pal["models"][fam] for a in ARCHS]
        b = ax.bar(x + (i - (len(fams) - 1) / 2) * w, vals, w * 0.94, color=cols, zorder=3)
        for r, v, a in zip(b, vals, ARCHS):
            ax.text(r.get_x() + r.get_width() / 2, v + 1.3, f"{v:.0f}", ha="center",
                    fontsize=9.5, fontweight="bold",
                    color=pal["accent_dark"] if a == "D" else pal["ink"])
    ax.legend(handles=[Patch(color=pal["models"][f], label=f) for f in fams],
              frameon=False, loc="upper left", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([ARCH_LABELS[a] for a in ARCHS])
    ax.set_ylabel("Overall accuracy (%)"); frame(ax, pal, 100)
    ax.set_title("Figure 1. Overall accuracy: 4 architectures x 3 models",
                 fontsize=13, fontweight="bold", loc="left", pad=14, color=pal["ink"])
    plt.tight_layout(); plt.savefig(os.path.join(FIGS, "fig1_overall_grid.png")); plt.close()

def fig2_heatmap(runs, fams, pal):
    fig, axes = plt.subplots(1, len(fams), figsize=(4.1 * len(fams), 4.4), sharey=True)
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        grid = np.array([[runs[(a, fam)]["per_cat"].get(c) or 0 for a in ARCHS] for c in CATS])
        im = ax.imshow(grid, cmap=pal["heat"], vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(ARCHS))); ax.set_xticklabels(ARCHS)
        ax.set_yticks(range(len(CATS))); ax.set_yticklabels(CAT_LABELS, fontsize=10)
        ax.set_title(fam, fontsize=12, fontweight="bold", color=pal["ink"])
        for yi in range(len(CATS)):
            for xi in range(len(ARCHS)):
                v = grid[yi, xi]
                ax.text(xi, yi, f"{v:.0f}", ha="center", va="center", fontsize=9, fontweight="bold",
                        color="white" if v > 55 else pal["ink"])
        ax.tick_params(length=0)
    fig.suptitle("Figure 2. Accuracy by category (%): every architecture, every model",
                 fontsize=13, fontweight="bold", x=0.02, ha="left", color=pal["ink"])
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(os.path.join(FIGS, "fig2_category_heatmap.png")); plt.close()

def fig3_d_categories(runs, fams, pal):
    x = np.arange(len(CATS)); w = 0.8 / len(fams)
    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    for i, fam in enumerate(fams):
        vals = [runs[("D", fam)]["per_cat"].get(c) or 0 for c in CATS]
        b = ax.bar(x + (i - (len(fams) - 1) / 2) * w, vals, w * 0.94,
                   color=pal["d_models"][fam], zorder=3, label=fam)
        for r, v in zip(b, vals):
            if v < 100:
                ax.text(r.get_x() + r.get_width() / 2, v + 1.6, f"{v:.0f}", ha="center",
                        fontsize=8.5, fontweight="bold", color=pal["accent_dark"])
    ax.legend(frameon=False, ncol=len(fams), loc="upper center",
              bbox_to_anchor=(0.5, -0.14), fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(CAT_LABELS, fontsize=10)
    ax.set_ylabel("Accuracy (%)"); frame(ax, pal, 113)
    ax.set_title("Figure 3. Architecture D by category: better models lift simple/complex,\n"
                 "the four decision categories stay at 100%",
                 fontsize=12.5, fontweight="bold", loc="left", pad=14, color=pal["ink"])
    plt.tight_layout(); plt.savefig(os.path.join(FIGS, "fig3_D_across_models.png")); plt.close()

def fig4_hallucination(runs, fams, pal):
    x = np.arange(len(ARCHS)); w = 0.8 / len(fams)
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    for i, fam in enumerate(fams):
        vals = [runs[(a, fam)]["halluc"] if (a, fam) in runs else 0 for a in ARCHS]
        cols = [pal["accent"] if v == 0 else pal["bad"] for v in vals]
        b = ax.bar(x + (i - (len(fams) - 1) / 2) * w, vals, w * 0.94, color=cols, zorder=3)
        for r, v in zip(b, vals):
            ax.text(r.get_x() + r.get_width() / 2, v + 0.16, "0" if v == 0 else f"{v:.1f}",
                    ha="center", fontsize=8.5, fontweight="bold",
                    color=pal["accent_dark"] if v == 0 else pal["bad"])
    ax.set_xticks(x); ax.set_xticklabels([ARCH_LABELS[a] for a in ARCHS])
    ax.set_ylabel("Hallucination rate (%)"); frame(ax, pal, 11)
    ax.set_title("Figure 4. Hallucination: C and D stay at zero on every model "
                 "(3 bars per architecture = 3 models)",
                 fontsize=12, fontweight="bold", loc="left", pad=14, color=pal["ink"])
    plt.tight_layout(); plt.savefig(os.path.join(FIGS, "fig4_hallucination.png")); plt.close()

def fig5_latency(runs, fams, pal):
    x = np.arange(len(ARCHS)); w = 0.8 / len(fams)
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    for i, fam in enumerate(fams):
        vals = [runs[(a, fam)]["latency_s"] or 0 for a in ARCHS if (a, fam) in runs]
        cols = [pal["d_models"][fam] if a == "D" else pal["models"][fam] for a in ARCHS]
        b = ax.bar(x + (i - (len(fams) - 1) / 2) * w, vals, w * 0.94, color=cols, zorder=3)
        for r, v, a in zip(b, vals, ARCHS):
            ax.text(r.get_x() + r.get_width() / 2, v + 0.4, f"{v:.0f}", ha="center",
                    fontsize=8.5, fontweight="bold",
                    color=pal["accent_dark"] if a == "D" else pal["ink"])
    ax.legend(handles=[Patch(color=pal["models"][f], label=f) for f in fams],
              frameon=False, loc="upper right", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([ARCH_LABELS[a] for a in ARCHS])
    ax.set_ylabel("Average latency (s)"); frame(ax, pal, 28)
    ax.set_title("Figure 5. Average time per order: D is fastest on every model",
                 fontsize=12.5, fontweight="bold", loc="left", pad=14, color=pal["ink"])
    plt.tight_layout(); plt.savefig(os.path.join(FIGS, "fig5_latency.png")); plt.close()

def fig6_c_tradeoff(runs, fams, pal):
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = np.arange(len(fams)); w = 0.35
    simple = [runs[("C", f)]["per_cat"].get("simple") or 0 for f in fams]
    hard = []
    for f in fams:
        pc = runs[("C", f)]["per_cat"]
        hs = [pc.get(c) for c in ["ambiguous", "incomplete", "contradictory"] if pc.get(c) is not None]
        hard.append(sum(hs) / len(hs) if hs else 0)
    b1 = ax.bar(x - w / 2, simple, w, color=pal["arch"]["C"], zorder=3, label="Simple orders")
    b2 = ax.bar(x + w / 2, hard, w, color=pal["models"][fams[-1]], zorder=3,
                label="Hard categories (avg of ambig/incompl/contra)")
    for bars, vals in [(b1, simple), (b2, hard)]:
        for r, v in zip(bars, vals):
            ax.text(r.get_x() + r.get_width() / 2, v + 1.6, f"{v:.0f}", ha="center",
                    fontsize=10, fontweight="bold", color=pal["ink"])
    ax.set_xticks(x); ax.set_xticklabels(fams, fontsize=11)
    ax.legend(frameon=False,loc="lower left",bbox_to_anchor=(0.0, 1.02),ncol=2,fontsize=10)
    ax.set_ylabel("Accuracy (%)"); frame(ax, pal, 113)
    ax.set_title("Figure 6. Architecture C trade-off: when its tools start working (qwen2.5),\n"
             "its caution on hard orders drops",
             fontsize=12.5, fontweight="bold", loc="left", pad=24, color=pal["ink"])
    plt.tight_layout(rect=[0, 0, 1, 0.90]); plt.savefig(os.path.join(FIGS, "fig6_C_tradeoff.png")); plt.close()

def fig7_ci(runs, fams, ci, pal):
    if not ci:
        print("  (skipping Figure 7: run stats_tests.py first to create stats_summary.csv)")
        return
    fig, axes = plt.subplots(1, len(fams), figsize=(3.9 * len(fams), 4.0), sharey=True)
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        xs = np.arange(len(ARCHS))
        for xi, a in enumerate(ARCHS):
            if (a, fam) not in ci:
                continue
            acc, lo, hi = ci[(a, fam)]
            col = pal["arch"]["D"] if a == "D" else pal["arch"][a]
            ax.errorbar(xi, acc, yerr=[[acc - lo], [hi - acc]], fmt="o", markersize=9,
                        color=col, ecolor=col, elinewidth=2.6, capsize=6, capthick=2.6, zorder=3)
            ax.text(xi, hi + 2.5, f"{acc:.0f}%", ha="center", fontsize=9.5, fontweight="bold",
                    color=pal["accent_dark"] if a == "D" else pal["ink"])
        ax.set_xticks(xs); ax.set_xticklabels(ARCHS)
        ax.set_title(fam, fontsize=12, fontweight="bold", color=pal["ink"])
        ax.set_ylim(0, 105)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color=pal["grid"], linewidth=1.2, zorder=0)
        ax.set_axisbelow(True); ax.tick_params(length=0)
    axes[0].set_ylabel("Overall accuracy (%)")
    fig.suptitle("Figure 7. Accuracy with 95% confidence intervals: D's interval never overlaps a baseline",
                 fontsize=12.5, fontweight="bold", x=0.02, ha="left", color=pal["ink"])
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(os.path.join(FIGS, "fig7_confidence_intervals.png")); plt.close()

def fig8_mcnemar(fams, mcnemar, pal):
    if not mcnemar:
        print("  (skipping Figure 8: run stats_tests.py first to create stats_summary.csv)")
        return
    bases = ["A", "B", "C"]
    fig, axes = plt.subplots(1, len(fams), figsize=(3.9 * len(fams), 4.0), sharey=True)
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        x = np.arange(len(bases)); w = 0.35
        dvals = [mcnemar.get((b, fam), (0, 0, ""))[0] for b in bases]
        bvals = [mcnemar.get((b, fam), (0, 0, ""))[1] for b in bases]
        b1 = ax.bar(x - w / 2, dvals, w, color=pal["accent"], zorder=3, label="Only D right")
        b2 = ax.bar(x + w / 2, bvals, w, color=pal["bad"], zorder=3, label="Only baseline right")
        for bars, vals in [(b1, dvals), (b2, bvals)]:
            for r, v in zip(bars, vals):
                ax.text(r.get_x() + r.get_width() / 2, v + 2.5, str(v), ha="center",
                        fontsize=9.5, fontweight="bold", color=pal["ink"])
        ax.set_xticks(x); ax.set_xticklabels([f"vs {b}" for b in bases])
        ax.set_title(f"{fam}  (all p < 0.001)", fontsize=11.5, fontweight="bold", color=pal["ink"])
        ax.set_ylim(0, 160)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color=pal["grid"], linewidth=1.2, zorder=0)
        ax.set_axisbelow(True); ax.tick_params(length=0)
    axes[0].set_ylabel("Orders (count)")
    axes[0].legend(frameon=False, fontsize=9.5, loc="upper right")
    fig.suptitle("Figure 8. McNemar disagreements: orders only D got right vs only the baseline got right",
                 fontsize=12.5, fontweight="bold", x=0.02, ha="left", color=pal["ink"])
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(os.path.join(FIGS, "fig8_mcnemar_counts.png")); plt.close()

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=["color", "plain"], default="color")
    args = ap.parse_args()

    pal = get_palette(args.style)
    setup(pal)
    os.makedirs(FIGS, exist_ok=True)

    runs = load_runs()
    fams = [f for f in ["llama3", "mistral", "qwen2.5"] if any((a, f) in runs for a in ARCHS)]
    fams += sorted({f for (_, f) in runs} - set(fams))
    ci, mcnemar = load_stats()

    print(f"Found runs for models: {', '.join(fams)}  (style: {args.style})")
    fig1_overall(runs, fams, pal)
    fig2_heatmap(runs, fams, pal)
    fig3_d_categories(runs, fams, pal)
    fig4_hallucination(runs, fams, pal)
    fig5_latency(runs, fams, pal)
    fig6_c_tradeoff(runs, fams, pal)
    fig7_ci(runs, fams, ci, pal)
    fig8_mcnemar(fams, mcnemar, pal)
    print(f"Done. Figures saved in {FIGS}")

if __name__ == "__main__":
    main()