from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xgboost as xgb

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
    matthews_corrcoef,
    classification_report,
    confusion_matrix,
)

from xgboost import XGBClassifier

# ============================================================
# 1. USER SETTINGS
# ============================================================

DATA_ROOT = Path(
    r"C:\omnetpp-6.0.3\omnetpp-6.0.3\OMNeT_DDoS_Reproducibility_Package\CICDDoS2019"
)
RESULTS_DIR = Path(r"C:\CICDDoS_FullFeature_SHAP\results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 104729
DDoS_RESERVOIR_TARGET = 300_000
CHUNK_SIZE = 200_000
SHAP_SAMPLE_SIZE = 10_000

# ============================================================
# 2. FEATURE DEFINITIONS
# ============================================================

CROSS_ENV_FEATURES = [
    "Total Fwd Packets",
    "Total Backward Packets",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Flow Duration",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Mean",
]

NON_PREDICTIVE_COLUMNS = {
    "Unnamed: 0",
    "Flow ID",
    "Source IP",
    "Source Port",
    "Destination IP",
    "Destination Port",
    "Timestamp",
    "SimillarHTTP",
    "Label",
}

LABEL_COL = "Label"

# ============================================================
# 3. UTILITIES
# ============================================================

def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def binary_label(value):
    s = str(value).strip().upper()
    return 0 if s == "BENIGN" else 1


def get_csv_files(root):
    files = sorted(root.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found below: {root}")
    return files


def inspect_schema(files):
    schemas = {}
    for f in files:
        header = pd.read_csv(f, nrows=0)
        header = normalize_columns(header)
        schemas[str(f)] = header.columns.tolist()

    all_columns = sorted(set().union(*[set(v) for v in schemas.values()]))
    if LABEL_COL not in all_columns:
        raise RuntimeError("Could not find Label column.")

    candidates = [c for c in all_columns if c not in NON_PREDICTIVE_COLUMNS]
    return schemas, candidates

# ============================================================
# 4. FIRST PASS: BUILD BENIGN SET + DDoS RESERVOIR
# ============================================================

def collect_balanced_candidates(files, feature_cols):
    rng = np.random.default_rng(RANDOM_SEED)
    benign_parts = []
    ddos_reservoir = []
    total_ddos_seen = 0
    usecols = feature_cols + [LABEL_COL]

    print("\nScanning CICDDoS2019 CSV files...\n")

    for file_idx, f in enumerate(files, start=1):
        print(f"[{file_idx}/{len(files)}] {f.name}")
        for chunk in pd.read_csv(f, chunksize=CHUNK_SIZE, low_memory=False):
            chunk = normalize_columns(chunk)
            missing = [c for c in usecols if c not in chunk.columns]
            if missing:
                print(f"  Skipping incompatible file/chunk; missing: {missing}")
                continue

            chunk = chunk[usecols].copy()
            for c in feature_cols:
                chunk[c] = pd.to_numeric(chunk[c], errors="coerce")

            chunk.replace([np.inf, -np.inf], np.nan, inplace=True)
            chunk.dropna(subset=feature_cols + [LABEL_COL], inplace=True)
            if chunk.empty:
                continue

            chunk["_y"] = chunk[LABEL_COL].map(binary_label)
            benign = chunk[chunk["_y"] == 0].copy()
            if not benign.empty:
                benign_parts.append(benign)

            attacks = chunk[chunk["_y"] == 1].copy()
            for row in attacks.itertuples(index=False, name=None):
                total_ddos_seen += 1
                if len(ddos_reservoir) < DDoS_RESERVOIR_TARGET:
                    ddos_reservoir.append(row)
                else:
                    j = rng.integers(0, total_ddos_seen)
                    if j < DDoS_RESERVOIR_TARGET:
                        ddos_reservoir[j] = row

    if not benign_parts:
        raise RuntimeError("No BENIGN records were found.")

    benign_df = pd.concat(benign_parts, ignore_index=True)
    columns = usecols + ["_y"]
    ddos_df = pd.DataFrame(ddos_reservoir, columns=columns)
    return benign_df, ddos_df

# ============================================================
# 5. CLEAN + DEDUPLICATE + BALANCE
# ============================================================

def prepare_dataset(benign_df, ddos_df, feature_cols):
    print("\nBefore exact deduplication:")
    print("BENIGN:", len(benign_df))
    print("DDoS reservoir:", len(ddos_df))

    dedup_cols = feature_cols + [LABEL_COL]
    benign_df = benign_df.drop_duplicates(subset=dedup_cols).copy()
    ddos_df = ddos_df.drop_duplicates(subset=dedup_cols).copy()

    print("\nAfter exact deduplication:")
    print("BENIGN:", len(benign_df))
    print("DDoS reservoir:", len(ddos_df))

    n = min(len(benign_df), len(ddos_df))
    if n == 0:
        raise RuntimeError("No records available after cleaning.")

    if len(benign_df) <= len(ddos_df):
        benign_selected = benign_df.copy()
        ddos_selected = ddos_df.sample(
            n=len(benign_selected), random_state=RANDOM_SEED, replace=False
        )
    else:
        benign_selected = benign_df.sample(
            n=n, random_state=RANDOM_SEED, replace=False
        )
        ddos_selected = ddos_df.copy()

    combined = pd.concat([benign_selected, ddos_selected], ignore_index=True)
    combined = combined.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    print("\nBalanced analysis dataset:")
    print(combined["_y"].value_counts().sort_index())
    return combined

# ============================================================
# 6. TRAIN FULL-SPACE XGBOOST MODEL
# ============================================================

def train_model(df, feature_cols):
    X = df[feature_cols].astype(np.float32)
    y = df["_y"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_SEED, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        learning_rate=0.07,
        max_depth=5,
        subsample=1.0,
        colsample_bytree=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=RANDOM_SEED,
        n_jobs=-1,
        tree_method="hist",
    )

    print("\nTraining full-feature XGBoost...")
    model.fit(X_train, y_train)

    prob = model.predict_proba(X_test)[:, 1]
    pred = (prob >= 0.5).astype(int)

    metrics = {
        "accuracy": accuracy_score(y_test, pred),
        "f1": f1_score(y_test, pred),
        "roc_auc": roc_auc_score(y_test, prob),
        "pr_auc_ddos": average_precision_score(y_test, prob),
        "pr_auc_benign": average_precision_score(1 - y_test, 1 - prob),
        "balanced_accuracy": balanced_accuracy_score(y_test, pred),
        "mcc": matthews_corrcoef(y_test, pred),
    }

    print("\nFULL-SPACE BENCHMARK RESULTS")
    for k, v in metrics.items():
        print(f"{k}: {v:.6f}")

    print("\nConfusion matrix:")
    print(confusion_matrix(y_test, pred))

    print("\nClassification report:")
    print(classification_report(y_test, pred, digits=5))

    return model, X_train, X_test, y_train, y_test, metrics

# ============================================================
# 7. NATIVE XGBOOST TREESHAP
# ============================================================

def run_shap(model, X_test, feature_cols):
    """Calculate exact TreeSHAP contributions with XGBoost pred_contribs."""
    n = min(SHAP_SAMPLE_SIZE, len(X_test))
    X_shap = X_test.sample(n=n, random_state=RANDOM_SEED, replace=False)

    print(f"\nCalculating native XGBoost TreeSHAP on {n:,} held-out observations...")

    booster = model.get_booster()
    dshap = xgb.DMatrix(X_shap, feature_names=feature_cols)
    contributions = booster.predict(dshap, pred_contribs=True)

    shap_values = contributions[:, :-1]
    base_values = contributions[:, -1]

    if shap_values.shape[1] != len(feature_cols):
        raise RuntimeError(
            f"Expected {len(feature_cols)} SHAP columns but got {shap_values.shape[1]}"
        )

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = pd.DataFrame({
        "Feature": feature_cols,
        "MeanAbsSHAP": mean_abs_shap,
    })
    importance = importance.sort_values("MeanAbsSHAP", ascending=False).reset_index(drop=True)
    importance["Rank"] = np.arange(1, len(importance) + 1)

    importance.to_csv(RESULTS_DIR / "full_feature_shap_ranking.csv", index=False)
    pd.DataFrame(
        shap_values, columns=feature_cols, index=X_shap.index
    ).to_parquet(RESULTS_DIR / "full_feature_shap_values.parquet")
    pd.DataFrame({"base_value": base_values}).to_csv(
        RESULTS_DIR / "full_feature_shap_base_values.csv", index=False
    )

    return importance, X_shap, shap_values

# ============================================================
# 8. CROSS-ENVIRONMENT FEATURE RANK TABLE
# ============================================================

def cross_environment_ranks(importance):
    rows = []
    for feature in CROSS_ENV_FEATURES:
        match = importance[importance["Feature"] == feature]
        if match.empty:
            rows.append({"Feature": feature, "Rank": "not available", "MeanAbsSHAP": np.nan})
        else:
            row = match.iloc[0]
            rows.append({
                "Feature": feature,
                "Rank": int(row["Rank"]),
                "MeanAbsSHAP": float(row["MeanAbsSHAP"]),
            })

    result = pd.DataFrame(rows)
    result.to_csv(RESULTS_DIR / "cross_environment_feature_ranks.csv", index=False)
    return result

# ============================================================
# 9. FIGURES
# ============================================================

def create_figures(importance, X_shap, shap_values):
    top20 = importance.head(20).sort_values("MeanAbsSHAP", ascending=True)

    plt.figure(figsize=(9, 8))
    plt.barh(top20["Feature"], top20["MeanAbsSHAP"])
    plt.xlabel("Mean absolute TreeSHAP contribution")
    plt.ylabel("Feature")
    plt.title(
        "CICDDoS2019 Full-Feature XGBoost Importance\n"
        "Top 20 Predictors by Mean |TreeSHAP|"
    )
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "full_feature_shap_top20.png", dpi=300, bbox_inches="tight")
    plt.close()

    cross_imp = importance[
        importance["Feature"].isin(CROSS_ENV_FEATURES)
    ].copy().sort_values("MeanAbsSHAP", ascending=True)

    plt.figure(figsize=(9, 6))
    plt.barh(cross_imp["Feature"], cross_imp["MeanAbsSHAP"])
    plt.xlabel("Mean absolute TreeSHAP contribution")
    plt.ylabel("Cross-environment feature")
    plt.title(
        "Importance of Cross-Environment Features\n"
        "Within the Full CICDDoS2019 Predictor Space"
    )
    plt.tight_layout()
    plt.savefig(
        RESULTS_DIR / "cross_environment_features_fullspace.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

# ============================================================
# 10. MAIN
# ============================================================

def main():
    files = get_csv_files(DATA_ROOT)

    print(f"Found {len(files)} CSV files:")
    for f in files:
        print(" -", f)

    schemas, candidate_features = inspect_schema(files)

    print("\nOriginal source columns:")
    first_schema = next(iter(schemas.values()))
    print(len(first_schema))

    print("\nEligible predictor candidates:")
    print(len(candidate_features))

    print("\nPredictors:")
    for i, feature in enumerate(candidate_features, start=1):
        print(f"{i:02d}. {feature}")

    with open(RESULTS_DIR / "schema_inventory.json", "w", encoding="utf-8") as fh:
        json.dump(schemas, fh, indent=2)

    benign_df, ddos_df = collect_balanced_candidates(files, candidate_features)
    dataset = prepare_dataset(benign_df, ddos_df, candidate_features)

    model, X_train, X_test, y_train, y_test, metrics = train_model(
        dataset, candidate_features
    )

    with open(RESULTS_DIR / "full_feature_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    importance, X_shap, shap_values = run_shap(model, X_test, candidate_features)
    cross_ranks = cross_environment_ranks(importance)
    create_figures(importance, X_shap, shap_values)

    print("\nTOP 20 FULL-SPACE FEATURES")
    print(importance.head(20)[["Rank", "Feature", "MeanAbsSHAP"]].to_string(index=False))

    print("\nYOUR EIGHT CROSS-ENVIRONMENT FEATURES")
    print(cross_ranks.to_string(index=False))

    print("\nDone.")
    print("Results saved to:")
    print(RESULTS_DIR)


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()
