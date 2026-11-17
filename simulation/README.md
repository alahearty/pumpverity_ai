# Simulation orchestration (Stage 6)

Signal simulation is implemented in the edge package at
[`edge/petrosense_edge/simulation.py`](../edge/petrosense_edge/simulation.py) during Stage 2. It
supports deterministic normal, abnormal, incipient, custom-abnormal, sensor-disconnect and
corrupted-sample scenarios.

This top-level directory is reserved for orchestration of network/offline scenarios:

1. Network outage.
2. Offline buffering.
3. Edge restart with unsynchronised events.
4. Network restoration and retry.
5. Duplicate delivery and idempotent receiver processing.

Those behaviours depend on the Stage 6 transactional outbox and synchronisation service and are not
yet implemented. Synthetic signals support software integration testing and demonstration only; they
cannot establish real-world fault-detection accuracy.

See [`docs/simulation/engine.md`](../docs/simulation/engine.md) for the implemented engine and its
scientific limitations.
