from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from petrosense_edge.contracts import AdapterConfig
from petrosense_edge.features import FEATURE_CONTRACT, FeatureExtractor
from petrosense_edge.simulation import generate_frame

RUN_DEFINITIONS = (
    ("normal", "normal"),
    ("imbalance", "imbalance"),
    ("cavitation", "cavitation"),
    ("incipient_fault", "incipient_fault"),
    ("custom_abnormal", "custom_abnormal"),
    ("incipient_boundary", "custom_abnormal"),
)
SCENARIOS = tuple(label for label, _ in RUN_DEFINITIONS)
DATASET_VERSION = "synthetic-grouped-v2"
RATED_SPEEDS = (2800, 2900, 3000)


@dataclass(frozen=True)
class DatasetMetadata:
    dataset_version: str
    feature_contract: dict[str, object]
    seeds: list[int]
    scenarios: list[str]
    windows_per_run: int
    rated_speeds: list[int]
    sample_count: int
    run_count: int
    generated_at: str
    provenance: str = "SIMULATED"
    limitations: str = (
        "Synthetic signals only. This dataset cannot establish real-world pump "
        "fault-detection performance."
    )


def generate_dataset(
    seeds: range | list[int] = range(1, 41),
    windows_per_run: int = 3,
) -> tuple[pd.DataFrame, DatasetMetadata]:
    extractor = FeatureExtractor()
    seed_list = list(seeds)
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)

    for seed in seed_list:
        rated_speed = RATED_SPEEDS[seed % len(RATED_SPEEDS)]
        for run_scenario, generator_scenario in RUN_DEFINITIONS:
            run_id = f"{run_scenario}-{seed}"
            if run_scenario == "incipient_boundary":
                custom_amplitude = 0.015 + (seed % 8) * 0.005
            else:
                custom_amplitude = 0.06 + (seed % 5) * 0.01
            config = AdapterConfig(
                sensor_id="sim-sensor",
                pump_id="sim-pump",
                sampling_rate_hz=2048,
                window_size=2048,
                overlap_fraction=0.5,
                rated_speed_rpm=rated_speed,
                scenario=generator_scenario,
                seed=seed,
                window_count=windows_per_run,
                custom_amplitude_g=custom_amplitude,
            )
            for window_index in range(windows_per_run):
                frame = generate_frame(config, window_index, start)
                features = extractor.extract(
                    frame.samples,
                    frame.sampling_rate_hz,
                    rated_speed,
                )
                rows.append(
                    {
                        "run_id": run_id,
                        "seed": seed,
                        "scenario": run_scenario,
                        "rated_speed_rpm": rated_speed,
                        "window_index": window_index,
                        "label": 0 if run_scenario == "normal" else 1,
                        "uncertainty_stress": run_scenario
                        in {"incipient_fault", "incipient_boundary"},
                        **features,
                    }
                )

    frame = pd.DataFrame(rows)
    metadata = DatasetMetadata(
        dataset_version=DATASET_VERSION,
        feature_contract=FEATURE_CONTRACT,
        seeds=seed_list,
        scenarios=list(SCENARIOS),
        windows_per_run=windows_per_run,
        rated_speeds=list(RATED_SPEEDS),
        sample_count=len(frame),
        run_count=len(seed_list) * len(SCENARIOS),
        generated_at=datetime.now(UTC).isoformat(),
    )
    return frame, metadata
