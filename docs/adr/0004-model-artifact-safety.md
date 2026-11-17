# ADR-0004: Model artefacts require metadata and compatibility validation

**Status:** Accepted; Stage 4 implements metadata registration, hash/feature-contract checks,
validation, activation, retirement and rollback. Only JSON linear/threshold artefacts are supported.

## Context

Allowing arbitrary uploaded model files to execute would be unsafe and scientifically weak.
Activation must be evidence-based, compatible with the feature pipeline and auditable.

## Decision

- Prefer ONNX Runtime for edge inference and portable model artefacts.
- Treat scikit-learn/joblib artefacts as trusted-local only; never load pickle-based uploads as
  arbitrary code.
- Registration records model code, version, algorithm, runtime, feature contract, training and
  evaluation dataset versions, artefact path and SHA-256, compatibility metadata and downstream
  metrics.
- Activation requires: artefact hash match, feature-contract compatibility, runtime compatibility,
  valid evaluation evidence, authorised role, explicit action and audit record.
- The previously active version is retired but retained for rollback.

## Consequences

Positive: safer model lifecycle, reproducible predictions, clear rollback, no arbitrary code
execution from uploads.

Negative: model packaging overhead; ONNX conversion work; strict compatibility can reject convenient
experiments until metadata is complete.

## Verification required in Stage 4

- Hash/metadata mismatch rejection.
- Incompatible feature-contract rejection.
- Unauthorised activation/rollback rejection.
- Rollback and change-history tests.
- Edge latency/memory measurements on the selected device.
