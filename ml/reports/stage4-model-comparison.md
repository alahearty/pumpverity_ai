# Stage 4 model comparison (synthetic)

Generated: 2026-11-16T17:20:51.391105+00:00
Dataset: synthetic-grouped-v2
Provenance: **SIMULATED**
Feature contract: petrosense-time-v1

> These metrics are generated from synthetic signals. They do not establish real-world pump-fault detection performance and must not be reported as such.

| Model | Balanced accuracy | Macro-F1 | Coverage | Risk | False-alert rate |
|---|---:|---:|---:|---:|---:|
| threshold_baseline | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| random_forest | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| linear_json | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |

Metrics are computed on accepted decisions after uncertainty abstention. Coverage is the fraction accepted; risk is the error rate among accepted samples.

Split: GroupShuffleSplit by run_id (scenario + seed); windows from one simulated run never appear in both train and test.
Train runs: 84; test runs: 36; test samples: 108.

The lightweight linear model is selected for Stage 4 edge deployment. The threshold baseline and random forest are comparison candidates. No real-pump performance claim is supported by this report.
