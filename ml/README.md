# Machine-learning research pipeline

Stage 4 implements a reproducible synthetic-data pipeline that compares three approaches:

1. engineering RMS threshold baseline;
2. random-forest classifier;
3. lightweight logistic-regression scorer exported as a JSON edge artefact.

Research code and application code remain separate. The edge consumes the selected JSON artefact;
the API records its metadata, hashes and evaluation evidence.

> Every metric in this directory is synthetic. It cannot establish real-world pump-fault
> detection performance and must not be reported as industrial accuracy.

## Install and test

From the repository root:

```powershell
apps/api/.venv/Scripts/python -m pip install -e edge
apps/api/.venv/Scripts/python -m pip install -e ml
apps/api/.venv/Scripts/ruff check ml/petrosense_ml ml/tests
apps/api/.venv/Scripts/python -m pytest ml/tests
```

`scripts/verify.ps1` includes these checks.

## Run the pipeline

Training, evaluation, report and artefact generation:

```powershell
apps/api/.venv/Scripts/python -m petrosense_ml.pipeline --seeds 40
```

Outputs:

- `ml/datasets/stage4_synthetic_features.csv` — generated feature dataset (gitignored);
- `ml/reports/stage4-model-comparison.json` and `.md` — synthetic comparison report;
- `ml/reports/stage4-registration-manifest.json` — metadata/evaluation payloads;
- `ml/artifacts/petrosense-linear-0.1.0.json` — selected lightweight edge model;
- `ml/artifacts/petrosense-threshold-0.1.0.json` — engineering baseline.

Register, validate and activate through the API (the API must be running):

```powershell
$env:PETROSENSE_ML_PASSWORD = "<researcher or admin password>"
apps/api/.venv/Scripts/python -m petrosense_ml.pipeline --register
```

The script is idempotent for an existing model code/version: it attaches evaluation evidence if
missing, validates, and activates the linear model. The threshold baseline is validated but not
activated.

## Dataset

- Synthetic grouped dataset version: `synthetic-grouped-v2`.
- Scenarios per seed: normal, imbalance, cavitation, incipient fault, custom abnormal, and an
  incipient-boundary run with a weak custom component.
- Six runs per seed, three windows per run.
- Rated-speed variation across 2800, 2900 and 3000 RPM.
- `GroupShuffleSplit` by `run_id` (scenario + seed); windows from one run never cross train/test.
- Labels are synthetic engineering hypotheses, not verified experimental ground truth.
- Sensor-disconnect/corrupted signals are excluded from classifier training; validation handles them.

## Evaluation

The report includes accepted-decision balanced accuracy, macro-F1, precision/recall, confusion
matrix, coverage, risk, false-alert rate, risk–coverage curves and Brier/ECE calibration diagnostics.
Abstention uses the fixed decision band `0.35 < score < 0.65`.

The current synthetic dataset separates easily and all three models reach 1.000 on the synthetic
hold-out. This is **not** evidence of real-world performance. A weak custom-abnormal input
(amplitude 0.01) produces an UNCERTAIN edge decision at score ≈0.39, which is used to demonstrate
the abstention path. The comparison metrics must not be quoted as industrial accuracy.

## Selected edge artefact

`petrosense-linear-0.1.0.json`:

- type: linear;
- runtime: `LINEAR_JSON`;
- feature contract: `petrosense-time-v1` (10 time/spectral features);
- preprocessing mean/scale, logistic coefficients and intercept;
- decision thresholds 0.35 / 0.65;
- provenance: SIMULATED;
- SHA-256 recorded during registration.

The edge verifies the hash and feature contract before loading it. The API never executes an
uploaded model.

## Registration safety

- Artifact metadata and SHA-256 are recorded.
- Activation requires a verified evaluation, a supported runtime and a matching feature contract.
- Only one model is active; previous versions are retired and retained.
- Rollback restores the most recently active retired version.
- API activation does not execute the artefact; the edge loads only the verified JSON scorer.
- ONNX/TFLite runtimes are registered in the schema but are not supported by the Stage 4 edge
  loader; activation rejects them.

## Limitations

- Synthetic data only; no real pump, no measured faults, no verified labels.
- No physical sensor or hardware-in-the-loop results.
- Perfect synthetic separation means the current comparison does not characterise real difficulty.
- Risk–coverage and calibration diagnostics are synthetic.
- ONNX runtime, TFLite and full dataset governance are later work.
- The research pipeline is not part of the API Docker image.
