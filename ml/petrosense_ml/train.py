from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from petrosense_edge.features import FEATURE_CONTRACT
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = list(FEATURE_CONTRACT["features"])


@dataclass(frozen=True)
class ThresholdBaselineModel:
    center: float
    scale: float
    normal_z: float = 2.2
    fault_z: float = 3.0

    def score(self, frame: pd.DataFrame) -> np.ndarray:
        values = frame["rms"].to_numpy(dtype=float)
        z = (values - self.center) / self.scale
        return np.clip((z - self.normal_z) / (self.fault_z - self.normal_z), 0.0, 1.0)


@dataclass
class SplitData:
    train: pd.DataFrame
    test: pd.DataFrame
    train_groups: int
    test_groups: int
    split_description: str


@dataclass
class TrainedModels:
    threshold: ThresholdBaselineModel
    random_forest: Pipeline
    logistic: Pipeline
    split: SplitData


def split_by_run(frame: pd.DataFrame) -> SplitData:
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
    train_index, test_index = next(
        splitter.split(frame, groups=frame["run_id"])
    )
    train = frame.iloc[train_index].reset_index(drop=True)
    test = frame.iloc[test_index].reset_index(drop=True)
    if train["label"].nunique() < 2 or test["label"].nunique() < 2:
        raise ValueError("Grouped split must contain both classes in train and test")
    return SplitData(
        train=train,
        test=test,
        train_groups=int(train["run_id"].nunique()),
        test_groups=int(test["run_id"].nunique()),
        split_description=(
            "GroupShuffleSplit by run_id (scenario + seed); windows from one simulated "
            "run never appear in both train and test."
        ),
    )


def train_models(train: pd.DataFrame) -> tuple[ThresholdBaselineModel, Pipeline, Pipeline]:
    features = train[FEATURE_NAMES]
    labels = train["label"].astype(int).to_numpy()
    normal_rms = train.loc[train["label"] == 0, "rms"].to_numpy(dtype=float)
    center = float(np.mean(normal_rms))
    scale = float(np.std(normal_rms, ddof=1))
    if not np.isfinite(scale) or scale <= 1e-9:
        scale = 1e-6
    threshold = ThresholdBaselineModel(center=center, scale=scale)

    random_forest = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=10,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )
    logistic = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    random_forest.fit(features, labels)
    logistic.fit(features, labels)
    return threshold, random_forest, logistic


def build_trained_models(frame: pd.DataFrame) -> TrainedModels:
    split = split_by_run(frame)
    threshold, random_forest, logistic = train_models(split.train)
    return TrainedModels(
        threshold=threshold,
        random_forest=random_forest,
        logistic=logistic,
        split=split,
    )


def score_models(trained: TrainedModels) -> dict[str, np.ndarray]:
    test = trained.split.test
    features = test[FEATURE_NAMES]
    return {
        "threshold_baseline": trained.threshold.score(test),
        "random_forest": trained.random_forest.predict_proba(features)[:, 1],
        "linear_json": trained.logistic.predict_proba(features)[:, 1],
    }


def score_summary(trained: TrainedModels) -> dict[str, Any]:
    logistic = trained.logistic.named_steps["classifier"]
    scaler = trained.logistic.named_steps["scaler"]
    return {
        "linear_mean": [float(value) for value in scaler.mean_],
        "linear_scale": [float(value) for value in scaler.scale_],
        "linear_coefficients": [float(value) for value in logistic.coef_[0]],
        "linear_intercept": float(logistic.intercept_[0]),
    }
