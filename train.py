"""
Train the agitation classifier on REAL captured data (data/*.csv).

Honesty guarantees (this is the whole point of the file):
  * Metrics use GroupKFold keyed on the recording session, so windows from the
    same CSV never land in both train and test. Windows within one recording are
    highly correlated; a random split would leak them and inflate the score. This
    doesn't.
  * NOTHING is hardcoded. Every number printed is computed from your data now.
  * If there isn't enough data to evaluate honestly (< 2 recordings per class),
    it says so and prints NO accuracy rather than inventing a meaningless one.

Run:  python train.py
Out:  data/model.joblib   (server.py / ble_bridge.py load it automatically)
"""

import datetime
import glob
import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold

from pipeline import HOP_N, MODEL_PATH, WINDOW_N, extract_features

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RF_PARAMS = dict(n_estimators=200, max_depth=8, random_state=7, n_jobs=-1)
LABELS = {"calm": 0, "agitated": 1}


def load_sessions():
    """-> list of (label_int, session_name, ndarray[N,3])"""
    sessions = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))):
        name = os.path.basename(path)
        label_str = name.split("_", 1)[0].lower()
        if label_str not in LABELS:
            print(f"  ! skip {name}: name must start with 'calm_' or 'agitated_'")
            continue
        try:
            rows = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
        except Exception as e:
            print(f"  ! skip {name}: could not parse ({e})")
            continue
        if rows.size == 0 or rows.shape[1] < 3:
            print(f"  ! skip {name}: no samples")
            continue
        sessions.append((LABELS[label_str], name, rows[:, :3].astype(float)))
    return sessions


def windows_from(arr):
    out, i = [], 0
    while i + WINDOW_N <= len(arr):
        out.append(extract_features(arr[i:i + WINDOW_N]))
        i += HOP_N
    return out


def build_dataset(sessions):
    X, y, groups = [], [], []
    for label, name, arr in sessions:
        w = windows_from(arr)
        if not w:
            print(f"  ! {name}: {len(arr)} samples < window ({WINDOW_N}); 0 windows")
            continue
        X.extend(w); y.extend([label] * len(w)); groups.extend([name] * len(w))
    return np.array(X), np.array(y), np.array(groups)


def main():
    sessions = load_sessions()
    if not sessions:
        print("No data in data/*.csv.")
        print("Capture first: run server.py, open the phone page, use the")
        print("'Rec calm' / 'Rec agitated' buttons. Each recording = one CSV.")
        return

    n_calm = sum(1 for s in sessions if s[0] == 0)
    n_agit = sum(1 for s in sessions if s[0] == 1)
    print(f"sessions: {len(sessions)}  (calm={n_calm}, agitated={n_agit})")

    X, y, groups = build_dataset(sessions)
    if len(X) == 0:
        print("No windows extracted -- recordings too short.")
        print(f"Record at least ~{WINDOW_N} samples (a few seconds) per session.")
        return
    print(f"windows:  {len(X)}  (calm={int((y == 0).sum())}, "
          f"agitated={int((y == 1).sum())})")
    print(f"features/window: {X.shape[1]}")

    meta = {
        "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "n_sessions": len(sessions), "n_windows": int(len(X)),
        "calm_sessions": n_calm, "agitated_sessions": n_agit,
    }

    # honest held-out eval needs >= 2 sessions PER class
    if n_calm >= 2 and n_agit >= 2:
        n_splits = min(5, len(set(groups)))
        gkf = GroupKFold(n_splits=n_splits)
        y_pred = np.empty_like(y)
        for tr, te in gkf.split(X, y, groups):
            m = RandomForestClassifier(**RF_PARAMS).fit(X[tr], y[tr])
            y_pred[te] = m.predict(X[te])
        acc = accuracy_score(y, y_pred)
        print(f"\n--- {n_splits}-fold GroupKFold, held out by session ---")
        print(f"cross-validated accuracy: {acc:.3f}")
        print(classification_report(y, y_pred, target_names=["calm", "agitated"],
                                    zero_division=0))
        print("confusion (rows=true, cols=pred) [calm, agitated]:")
        print(confusion_matrix(y, y_pred))
        meta["cv_folds"] = n_splits
        meta["cv_accuracy"] = round(float(acc), 4)
    else:
        print("\n!! Not enough data for an honest held-out score.")
        print("   Need >= 2 separate recordings of EACH class.")
        print("   Saving a model trained on everything, but reporting NO accuracy")
        print("   -- a number from this little data would be meaningless.")
        meta["cv_accuracy"] = None
        meta["note"] = "no held-out eval; < 2 sessions per class"

    final = RandomForestClassifier(**RF_PARAMS).fit(X, y)
    os.makedirs(DATA_DIR, exist_ok=True)
    joblib.dump({"model": final, "meta": meta}, MODEL_PATH)
    print(f"\nsaved -> {MODEL_PATH}")
    print("server.py / ble_bridge.py will load this real model automatically.")
    print(f"meta: {meta}")


if __name__ == "__main__":
    main()
