"""
classify.py  --  Version D helper: load the trained classifier and predict one order's type.

Used by the router (and by the Node backend, via a tiny CLI below).
Run train_classifier.py FIRST so models/classifier.joblib exists.

Two ways to use it:

  1) From Python:
        from classify import predict_type
        print(predict_type("one cheeseburger please"))
        # -> {"type": "simple", "confidence": 0.83}

  2) From the command line (this is how Node will call it):
        python classify.py "one cheeseburger please"
        # prints a JSON line: {"type": "simple", "confidence": 0.83}
"""

import os, sys, json
import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")

_clf = None
_le = None

def _load():
    global _clf, _le
    if _clf is None:
        _clf = joblib.load(os.path.join(MODELS, "classifier.joblib"))
        _le  = joblib.load(os.path.join(MODELS, "label_encoder.joblib"))
    return _clf, _le

def predict_type(text: str):
    """Return {'type': <category>, 'confidence': <0..1>} for one order string."""
    clf, le = _load()
    X = np.array([text], dtype=object)
    pred = clf.predict(X)[0]
    label = le.inverse_transform([pred])[0]

    # Confidence: LogisticRegression/RandomForest expose predict_proba.
    # LinearSVC does not, so we fall back to a calibrated-ish score or 1.0.
    conf = None
    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(X)[0]
        conf = float(np.max(proba))
    elif hasattr(clf, "decision_function"):
        scores = clf.decision_function(X)[0]
        scores = np.atleast_1d(scores)
        # squash margins to 0..1 just for a rough confidence signal
        e = np.exp(scores - np.max(scores))
        conf = float(np.max(e / e.sum()))
    else:
        conf = 1.0

    return {"type": label, "confidence": round(conf, 3)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: python classify.py \"order text\""}))
        sys.exit(1)
    text = sys.argv[1]
    try:
        print(json.dumps(predict_type(text)))
    except FileNotFoundError:
        print(json.dumps({"error": "model not found - run train_classifier.py first"}))
        sys.exit(1)
