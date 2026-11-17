# Stage 4 acceptance evidence

**Date:** 2026-11-16
**Environment:** Windows 11, Python 3.13, Node.js 24, Chrome (Playwright), SQLite
**Isolation:** Model registration, inference and E2E verification used
`apps/api/data/stage4-verify.db`; the developer database was not used for write tests.
**Versions:** API `0.4.0`, edge `0.4.0`, ML pipeline `0.4.0`, migration `cc4e2d9b7f12`

## 1. Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Versioned feature extraction is shared by research and edge inference | **Met** | `edge/petrosense_edge/features.py`; edge tests |
| 2 | Edge loads only a hash-verified model artefact with a matching feature contract | **Met** | inference tests; CLI hash check |
| 3 | Valid windows produce persisted model predictions | **Met** | 18 predictions in isolated DB; API tests |
| 4 | Model supports NORMAL, FAULT and explicit UNCERTAIN abstention | **Met** | CLI runs; decision unit tests; AI Analysis UI |
| 5 | Sensor-invalid windows cannot receive condition inference | **Met** | SENSOR_INVALID prediction, live suppression, API test |
| 6 | Predictions preserve model version, score, uncertainty, explanation and window features | **Met** | prediction API tests; AI Analysis screen |
| 7 | Model registry records metadata, hash, feature contract and evaluation evidence | **Met** | two registered models; synthetic evaluations |
| 8 | Validation and activation are guarded; unsupported runtimes cannot activate | **Met** | model API tests; runtime/evidence checks |
| 9 | Activation retires the previous model; rollback is available | **Met** | lifecycle tests |
| 10 | AI Analysis screen displays model output and uncertainty without failure-probability claims | **Met** | Playwright + UI tests |
| 11 | Model Management screen exposes review/activation/rollback and provenance | **Met** | UI tests; screenshot review |
| 12 | Reproducible synthetic model comparison and report exist | **Met** | `ml/reports/stage4-model-comparison.*` |
| 13 | Automated tests cover backend, edge, ML, frontend and E2E | **Met** | test results below |

## 2. Executed verification

```text
API ruff check ......................... All checks passed
API pytest ............................. 54 passed
Edge ruff check ........................ All checks passed
Edge pytest ............................ 38 passed
ML ruff check .......................... All checks passed
ML pytest .............................. 3 passed
Web oxlint ............................. 0 errors, 3 fast-refresh warnings
Web vitest ............................. 35 passed
Web tsc + vite build ................... passed (bundle-size warning)
Playwright ............................. 7 passed (incl. live inference + AI Analysis)
Alembic ................................ 4 migrations applied
```

## 3. Model evaluation evidence (synthetic)

Pipeline run: 20 seeds, six run types per seed, three windows per run.

- Total runs: 120; total samples: 360.
- Group split: 84 train runs / 36 test runs; 108 test samples.
- Synthetic hold-out results for all three candidates:
  balanced accuracy `1.000`, macro-F1 `1.000`, coverage `1.000`, risk `0.000`.
- The synthetic scenarios separate easily. **These values are not real-pump accuracy and must not
  be presented as industrial performance.**
- Selected edge model: `petrosense-linear` v`0.1.0` (`LINEAR_JSON`), artefact hash
  `cdf98e3d5a161fc5969a35d9e7ac97718e3f382fea1348a5c4e287c33431c2dd`.
- Baseline `petrosense-threshold` v`0.1.0` is validated but not active.
- Report: `ml/reports/stage4-model-comparison.md`.

The report includes risk–coverage points, a confusion matrix, calibration (Brier/ECE), false-alert
rate and accepted/abstained counts. Dataset provenance is `SIMULATED`.

## 4. Edge inference evidence

Using an activated linear model on `LAB-PUMP-04` / `VIB-04`:

| Scenario | Decision | Score | Uncertainty | Prediction persisted |
|---|---|---:|---:|---|
| normal | NORMAL | ~0.011 | ~0.011 | Yes |
| imbalance | FAULT | ~0.997 | ~0.003 | Yes |
| custom abnormal (0.01 g) | UNCERTAIN | ~0.393 | ~0.393 | Yes |
| sensor disconnect | SENSOR_INVALID | — | — | Yes (no model) |

The CLI verified the model SHA-256 and feature contract before inference. Feature values stored with
each valid window include RMS, peak, std, skewness, excess kurtosis, crest factor, zero-crossing
rate, 1x/2x spectral ratios and high-frequency ratio.

The sensor-disconnect prediction is recorded with no model, no scores and no waveform. The Live
Monitoring page showed **Not inferred** and suppressed the current waveform; the AI Analysis screen
can still inspect the SENSOR_INVALID outcome.

## 5. Isolated database summary

From the Stage 4 verification database:

```text
models .................. 2 (1 ACTIVE linear, 1 VALIDATED baseline)
evaluations ............. 2 (provenance SIMULATED)
pumps ................... 7 (repeated E2E runs)
acquisition sessions .... 10
signal windows .......... 18
predictions ............. 18
decisions ............... NORMAL 8, FAULT 8, UNCERTAIN 1, SENSOR_INVALID 1
latest prediction ....... FAULT / FAULT / score 0.997 / provenance SIMULATED
```

Counts include repeated E2E runs and are not experimental evidence. After acceptance testing, the
developer database was migrated to Stage 4 and the same two synthetic model versions were registered
there (linear active, threshold baseline validated); it contains no pump, session or prediction rows.
A fresh environment must run the research pipeline registration command before inference is available.

## 6. UI evidence

- AI Analysis screen shows model name/version, decision score, uncertainty, data quality,
  latency, window, operating context, feature values and the immutable explanation.
- The screen states that decision scores are not failure probabilities.
- Model Management shows artifact paths/hashes, synthetic dataset provenance and metrics, activation
  and rollback controls, and synthetic-metric warnings.
- The E2E suite navigates from Live Monitoring to AI Analysis after an imbalance scenario and
  verifies a FAULT decision and the linear model identity.
- No screen claims real-pump accuracy or automatic shutdown.

## 7. Deviations and limitations

1. **Synthetic-only evidence.** No physical pump data, verified labels or real-world accuracy exist.
2. **Model registration is pipeline-driven.** The research pipeline registers metadata/evaluation
   through the API; the Model Management UI reviews, validates, activates and rolls back but does
   not upload arbitrary model files. This is intentional to avoid execution of uploaded code.
3. **ONNX/TFLite are not implemented.** The schema/runtime enum includes them, but only
   `LINEAR_JSON` and `BASELINE` artefacts are supported by the Stage 4 edge loader.
4. **Perfect synthetic comparison metrics.** The synthetic scenarios are easily separable; the
   uncertainty path is demonstrated with a weak custom input, not by the comparison set.
5. **No alerts/review.** Predictions requiring review are recorded, but alert routing and review
   are Stage 5.
6. **No hardware.** Physical integration and real-data validation remain outstanding.
7. **The ML pipeline is not in the API Docker image**, and the research dependencies are installed
   separately.
8. **Bundle size** is approximately 995 kB minified / 289 kB gzip because charting is included.
9. **E2E requirements:** writes and an active Stage 4 model are required; those tests skip by default.
10. **Preprocessing is minimal.** Stage 4 performs validation, bounded windowing and
    centering/shape-statistics inside feature extraction. Configurable filtering/band-pass
    preprocessing remains future work; no filter is claimed in the current model.

## 8. Entry criteria for Stage 5

- Alert creation from FAULT, UNCERTAIN and SENSOR_INVALID decisions.
- Acknowledge/review workflow with immutable original predictions.
- Reviewer identity, label confirmation/correction and notes.
- Filtering, assigned reviewers and alert status transitions.
- Historical fault-event overlay and label-provenance distinction.
- Automated alert-to-review and role tests.
