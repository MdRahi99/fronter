"""
train_classifier.py  --  Version D, Part 1: the order-type classifier ("the sorter")

What this does, in plain words:
  It reads your 210 labelled orders, learns to read an order's TEXT and predict
  its TYPE (simple / complex / ambiguous / incomplete / contradictory / adversarial),
  tries 3 simple ML models + 1 rule-of-thumb baseline, picks the best by
  cross-validation, and saves it to disk so the live system can use it.

No deep learning. Classic scikit-learn only.

Run:
    python train_classifier.py
Outputs:
    models/classifier.joblib      <- the trained sorter (used later by the router)
    models/label_encoder.joblib   <- maps category names <-> numbers
    models/classifier_report.txt  <- accuracy + confusion matrix for your dissertation
"""

import json, os, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

HERE = os.path.dirname(os.path.abspath(__file__))
# benchmark.json lives in ../data/ in your project; fall back to same folder
CANDIDATES = [
    os.path.join(HERE, "..", "data", "benchmark.json"),
    os.path.join(HERE, "benchmark.json"),
]

def load_orders():
    for path in CANDIDATES:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # benchmark.json is a list of orders; each has text + category
            orders = data if isinstance(data, list) else data.get("orders", data)
            texts, labels = [], []
            for o in orders:
                t = o.get("text", "").strip()
                c = o.get("category", "").strip()
                if t and c:
                    texts.append(t)
                    labels.append(c)
            print(f"Loaded {len(texts)} orders from {os.path.relpath(path)}")
            return texts, labels
    print("ERROR: could not find benchmark.json in ../data/ or this folder.")
    print("Put this script in your project's ml/ folder and try again.")
    sys.exit(1)

def build_models():
    # Each model is a pipeline: turn text into TF-IDF features, then classify.
    # TF-IDF = simple, well-understood way to turn words into numbers.
    tfidf = lambda: TfidfVectorizer(ngram_range=(1,2), min_df=1, sublinear_tf=True)
    return {
        "Logistic Regression": Pipeline([("tfidf", tfidf()),
                            ("clf", LogisticRegression(max_iter=1000, C=10))]),
        "Random Forest":       Pipeline([("tfidf", tfidf()),
                            ("clf", RandomForestClassifier(n_estimators=300, random_state=42))]),
        "Linear SVM":          Pipeline([("tfidf", tfidf()),
                            ("clf", LinearSVC(C=1.0))]),
        "Baseline (most-frequent)": Pipeline([("tfidf", tfidf()),
                            ("clf", DummyClassifier(strategy="most_frequent"))]),
    }

def main():
    texts, labels = load_orders()
    le = LabelEncoder()
    y = le.fit_transform(labels)
    X = np.array(texts, dtype=object)

    # 5-fold cross-validation: every order gets predicted once while held out,
    # so the accuracy is honest (not memorised).
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print("\n--- Cross-validated accuracy (higher = better) ---")
    results = {}
    for name, model in build_models().items():
        preds = cross_val_predict(model, X, y, cv=cv)
        acc = accuracy_score(y, preds)
        results[name] = (acc, preds)
        print(f"  {name:28s} {acc*100:5.1f}%")

    # Pick the best real model (ignore the dummy baseline when choosing).
    best_name = max((n for n in results if "Baseline" not in n),
                    key=lambda n: results[n][0])
    best_acc, best_preds = results[best_name]
    print(f"\nBest model: {best_name}  ({best_acc*100:.1f}%)")

    # Detailed report for your dissertation (per-category precision/recall).
    target_names = list(le.classes_)
    report = classification_report(y, best_preds, target_names=target_names, digits=3)
    cm = confusion_matrix(y, best_preds)

    print("\n--- Per-category report (best model, cross-validated) ---")
    print(report)
    print("Confusion matrix (rows = true, cols = predicted):")
    print("labels:", target_names)
    print(cm)

    # Retrain the best model on ALL data and save it for the live system.
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    final_model = build_models()[best_name]
    final_model.fit(X, y)

    import joblib
    joblib.dump(final_model, os.path.join(HERE, "models", "classifier.joblib"))
    joblib.dump(le,          os.path.join(HERE, "models", "label_encoder.joblib"))

    with open(os.path.join(HERE, "models", "classifier_report.txt"), "w") as f:
        f.write(f"fronter Version D - order-type classifier\n")
        f.write(f"Best model: {best_name} ({best_acc*100:.1f}% cross-validated)\n\n")
        f.write("Cross-validated accuracy of all candidates:\n")
        for name,(acc,_) in results.items():
            f.write(f"  {name:28s} {acc*100:5.1f}%\n")
        f.write("\nPer-category report (best model):\n")
        f.write(report + "\n")
        f.write("Confusion matrix (rows=true, cols=pred):\n")
        f.write("labels: " + ", ".join(target_names) + "\n")
        f.write(str(cm) + "\n")

    print("\nSaved:")
    print("  models/classifier.joblib")
    print("  models/label_encoder.joblib")
    print("  models/classifier_report.txt")
    print("\nNext: a quick predict() helper the router will call.")

if __name__ == "__main__":
    main()
