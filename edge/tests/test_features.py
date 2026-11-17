import math
from datetime import UTC, datetime

import pytest
from petrosense_edge.contracts import AdapterConfig
from petrosense_edge.features import (
    FEATURE_CONTRACT,
    FeatureExtractionError,
    FeatureExtractor,
    vector_for_contract,
)
from petrosense_edge.simulation import generate_frame

START = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def config(scenario="normal", seed=42):
    return AdapterConfig(
        sensor_id="sensor-1",
        pump_id="pump-1",
        scenario=scenario,
        seed=seed,
        window_count=1,
    )


def features_for(scenario="normal", seed=42):
    frame = generate_frame(config(scenario, seed), 0, START)
    return FeatureExtractor().extract(
        frame.samples, frame.sampling_rate_hz, config(scenario, seed).rated_speed_rpm
    )


def test_feature_contract_is_complete_and_finite():
    features = features_for()
    assert set(features) == set(FEATURE_CONTRACT["features"])
    assert all(isinstance(value, float) and math.isfinite(value) for value in features.values())
    assert features["rms"] > 0
    assert features["peak_abs"] > 0
    assert 0 <= features["zero_crossing_rate"] <= 1


def test_abnormal_scenarios_raise_features():
    normal = features_for("normal")
    imbalance = features_for("imbalance")
    cavitation = features_for("cavitation")
    incipient = features_for("incipient_fault")
    assert imbalance["rms"] > normal["rms"]
    assert cavitation["high_frequency_ratio"] > normal["high_frequency_ratio"]
    assert incipient["rms"] > normal["rms"]
    assert imbalance["spectral_1x_ratio"] > normal["spectral_1x_ratio"]


def test_features_are_deterministic():
    assert features_for(seed=7) == features_for(seed=7)
    assert features_for(seed=7) != features_for(seed=8)


def test_custom_abnormal_amplitude_changes_rms():
    low_frame = generate_frame(
        AdapterConfig(
            sensor_id="sensor-1",
            pump_id="pump-1",
            scenario="custom_abnormal",
            custom_amplitude_g=0.01,
            window_count=1,
        ),
        0,
        START,
    )
    high_frame = generate_frame(
        AdapterConfig(
            sensor_id="sensor-1",
            pump_id="pump-1",
            scenario="custom_abnormal",
            custom_amplitude_g=0.2,
            window_count=1,
        ),
        0,
        START,
    )
    extractor = FeatureExtractor()
    low = extractor.extract(low_frame.samples, low_frame.sampling_rate_hz, 2900)
    high = extractor.extract(high_frame.samples, high_frame.sampling_rate_hz, 2900)
    assert high["rms"] > low["rms"]


def test_feature_extraction_rejects_invalid_input():
    extractor = FeatureExtractor()
    with pytest.raises(FeatureExtractionError):
        extractor.extract((), 2048, 2900)
    with pytest.raises(FeatureExtractionError):
        extractor.extract((0.1,) * 15 + (float("nan"),), 2048, 2900)


def test_vector_for_contract_requires_all_features():
    features = features_for()
    vector = vector_for_contract(features, ["rms", "peak_abs"])
    assert len(vector) == 2
    with pytest.raises(FeatureExtractionError):
        vector_for_contract(features, ["rms", "not-a-feature"])
