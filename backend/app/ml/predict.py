from __future__ import annotations

import os
import joblib
import numpy as np
from sqlalchemy.orm import Session

from .features import features_for_gw
from .train import resolve_model_dir, resolve_model_version

def load_models(model_dir: str | None = None):
    model_dir = resolve_model_dir(model_dir)
    clf_path = os.path.join(model_dir, "start_clf.joblib")
    reg_path = os.path.join(model_dir, "points_reg.joblib")
    if not (os.path.exists(clf_path) and os.path.exists(reg_path)):
        raise RuntimeError("Models not found. Run: python -m app.cli train")
    clf = joblib.load(clf_path)
    reg = joblib.load(reg_path)
    return clf, reg

def predict_for_gw(db: Session, gw: int, model_dir: str | None = None, model_version: str | None = None):
    model_dir = resolve_model_dir(model_dir)
    model_version = resolve_model_version(model_version)
    clf, reg = load_models(model_dir=model_dir)
    df = features_for_gw(db, gw)
    if df.empty:
        return [], model_version

    # Feature columns must match training
    # (We load from metrics.json if exists; otherwise infer from df.)
    metrics_path = os.path.join(model_dir, "metrics.json")
    feature_cols = None
    if os.path.exists(metrics_path):
        import json
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
            feature_cols = metrics.get("feature_cols")
            model_version = metrics.get("model_version") or model_version
    if not feature_cols:
        feature_cols = [c for c in df.columns if c.endswith("_avg_3") or c.endswith("_avg_5") or c.endswith("_trend")]
        feature_cols += ["is_home","difficulty","opp_strength_def","team_att","team_def","injury_flag","price"]

    X = df[feature_cols].astype(float)
    p_start = clf.predict_proba(X)[:, 1]
    exp_pts = reg.predict(X)

    out = []
    for pid, ps, ep in zip(df["player_id"].to_numpy(), p_start, exp_pts):
        out.append({
            "gw": int(gw),
            "player_id": int(pid),
            "p_start": float(ps),
            "expected_points": float(ep),
            "model_version": model_version
        })
    return out, model_version


# Backward-compatible wrapper used by app.main
def predict_gw(db: Session, gw: int, model_dir: str = None, model_version: str = None):
    rows, _ver = predict_for_gw(db, gw, model_dir=model_dir, model_version=model_version)
    return rows
