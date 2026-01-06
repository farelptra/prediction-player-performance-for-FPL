from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import f1_score, roc_auc_score, mean_absolute_error, mean_squared_error

from .features import build_rolling_features, dataset_for_training, load_flat_table


def resolve_model_dir(model_dir: str | None = None) -> str:
    if model_dir:
        return os.path.abspath(model_dir)
    env_dir = os.getenv("MODEL_DIR")
    if env_dir:
        return os.path.abspath(env_dir)
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    return os.path.join(backend_root, "models_store")


def resolve_model_version(model_version: str | None = None) -> str:
    if model_version:
        return str(model_version)
    env_ver = os.getenv("MODEL_VERSION")
    if env_ver:
        return str(env_ver)
    return "rf_v1"

def _rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))

def train_models(db, model_dir: str | None = None, model_version: str | None = None) -> Tuple[RandomForestClassifier, RandomForestRegressor, Dict[str, Any]]:
    model_dir = resolve_model_dir(model_dir)
    model_version = resolve_model_version(model_version)

    df = load_flat_table(db)
    if df.empty:
        raise RuntimeError("No data in player_gameweek_stats. Run import first.")

    df_feat = build_rolling_features(df)
    X, y_start, y_points, meta, feature_cols = dataset_for_training(df_feat)

    gws = meta["gw"].to_numpy()
    unique_gws = sorted(set(gws))
    if len(unique_gws) < 4:
        raise RuntimeError("Not enough gameweeks for training/evaluation. Need at least 4 GWs.")

    # rolling-origin evaluation (test one GW at a time after initial warmup)
    test_gws = unique_gws[3:]
    f1s, aucs, maes, rmses = [], [], [], []
    per_gw = []

    for test_gw in test_gws:
        train_mask = gws < test_gw
        test_mask = gws == test_gw

        Xtr, Xte = X[train_mask], X[test_mask]
        ytr_s, yte_s = y_start[train_mask], y_start[test_mask]
        ytr_p, yte_p = y_points[train_mask], y_points[test_mask]

        clf = RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
        reg = RandomForestRegressor(
            n_estimators=600,
            max_depth=None,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )

        clf.fit(Xtr, ytr_s)
        reg.fit(Xtr, ytr_p)

        p_start = clf.predict_proba(Xte)[:, 1]
        yhat_start = (p_start >= 0.5).astype(int)
        yhat_pts = reg.predict(Xte)

        f1 = float(f1_score(yte_s, yhat_start, zero_division=0))
        try:
            auc = float(roc_auc_score(yte_s, p_start))
        except Exception:
            auc = float("nan")
        mae = float(mean_absolute_error(yte_p, yhat_pts))
        rmse = _rmse(yte_p, yhat_pts)

        f1s.append(f1); aucs.append(auc); maes.append(mae); rmses.append(rmse)
        per_gw.append({"test_gw": int(test_gw), "f1": f1, "roc_auc": auc, "mae": mae, "rmse": rmse})

    _toggle = lambda arr: float(np.nanmean(arr)) if len(arr) else float('nan')

    metrics = {
        "model_version": model_version,
        "n_rows": int(len(df_feat)),
        "max_gw": int(max(unique_gws)),
        "classification": {"f1_mean": _toggle(f1s), "roc_auc_mean": _toggle(aucs)},
        "regression": {"mae_mean": _toggle(maes), "rmse_mean": _toggle(rmses)},
        "per_gw": per_gw,
        "feature_cols": feature_cols,
    }

    # fit final models on all data
    clf_final = RandomForestClassifier(
        n_estimators=800, min_samples_leaf=3, random_state=42, n_jobs=-1
    )
    reg_final = RandomForestRegressor(
        n_estimators=900, min_samples_leaf=3, random_state=42, n_jobs=-1
    )
    clf_final.fit(X, y_start)
    reg_final.fit(X, y_points)

    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(clf_final, os.path.join(model_dir, "start_clf.joblib"))
    joblib.dump(reg_final, os.path.join(model_dir, "points_reg.joblib"))
    with open(os.path.join(model_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return clf_final, reg_final, metrics


# Backward-compatible wrapper used by app.cli/app.main
def train_and_save(db, model_dir: str = None, model_version: str = None):
    _, _, metrics = train_models(db, model_dir=model_dir, model_version=model_version)
    return metrics
