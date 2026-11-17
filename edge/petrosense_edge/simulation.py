import math
import random
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from petrosense_edge.contracts import (
    AdapterConfig,
    AdapterState,
    QualityStatus,
    ScenarioDefinition,
    SignalClass,
    SignalFrame,
)

SCENARIOS: dict[str, ScenarioDefinition] = {
    "normal": ScenarioDefinition(
        code="normal",
        label="Normal operation",
        description="Low-amplitude shaft harmonics with low broadband noise.",
        signal_class=SignalClass.NORMAL,
        expected_quality=QualityStatus.VALID,
        expected_notes="Integration baseline only; not evidence of model performance.",
    ),
    "imbalance": ScenarioDefinition(
        code="imbalance",
        label="Imbalance-like abnormal signal",
        description="Elevated 1x and 2x shaft harmonics consistent with a synthetic imbalance.",
        signal_class=SignalClass.ABNORMAL,
        expected_quality=QualityStatus.VALID,
        expected_notes="Synthetic abnormal scenario for workflow and pipeline testing.",
    ),
    "cavitation": ScenarioDefinition(
        code="cavitation",
        label="Cavitation-like abnormal signal",
        description="Broadband/high-frequency energy with low-frequency modulation.",
        signal_class=SignalClass.ABNORMAL,
        expected_quality=QualityStatus.VALID,
        expected_notes="Synthetic abnormal scenario; not validated against a real pump.",
    ),
    "incipient_fault": ScenarioDefinition(
        code="incipient_fault",
        label="Incipient abnormal signal",
        description="Mid-level abnormal energy intended for future uncertainty/abstention tests.",
        signal_class=SignalClass.INCONCLUSIVE,
        expected_quality=QualityStatus.VALID,
        expected_notes="Signal quality is valid; condition confidence is intentionally ambiguous.",
    ),
    "custom_abnormal": ScenarioDefinition(
        code="custom_abnormal",
        label="Engineer-defined abnormal component",
        description="Normal baseline plus an engineer-configurable sinusoid.",
        signal_class=SignalClass.ABNORMAL,
        expected_quality=QualityStatus.VALID,
        expected_notes="Amplitude/frequency are supplied by the experimenter and recorded.",
    ),
    "sensor_disconnect": ScenarioDefinition(
        code="sensor_disconnect",
        label="Sensor disconnection",
        description="Adapter reports disconnection and emits no samples.",
        signal_class=SignalClass.INVALID,
        expected_quality=QualityStatus.SENSOR_INVALID,
        expected_notes="Must suppress condition inference; never a fresh normal outcome.",
    ),
    "corrupted_samples": ScenarioDefinition(
        code="corrupted_samples",
        label="Corrupted measurements",
        description="Normal waveform deliberately injected with NaN, infinity and extreme values.",
        signal_class=SignalClass.INVALID,
        expected_quality=QualityStatus.SENSOR_INVALID,
        expected_notes="Validation must reject the window before inference.",
    ),
}


def scenario_registry() -> list[ScenarioDefinition]:
    return list(SCENARIOS.values())


def _rng_for(config: AdapterConfig, sequence_no: int) -> random.Random:
    mixed = (config.seed * 1_000_003) ^ ((sequence_no + 1) * 2_654_435_761)
    return random.Random(mixed)


def _normal_waveform(config: AdapterConfig, sequence_no: int) -> list[float]:
    rng = _rng_for(config, sequence_no)
    rotor_hz = config.rated_speed_rpm / 60
    samples = []
    for index in range(config.window_size):
        t = index / config.sampling_rate_hz
        value = (
            0.030 * math.sin(2 * math.pi * rotor_hz * t)
            + 0.012 * math.sin(2 * math.pi * 2 * rotor_hz * t + 0.7)
            + 0.004 * math.sin(2 * math.pi * 137 * t)
            + rng.gauss(0, 0.002)
        )
        samples.append(value)
    return samples


def _generate_samples(config: AdapterConfig, sequence_no: int) -> list[float]:
    scenario = config.scenario
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown simulation scenario: {scenario}")

    if scenario in {"sensor_disconnect"}:
        return []

    if scenario == "normal":
        samples = _normal_waveform(config, sequence_no)
    elif scenario == "imbalance":
        rng = _rng_for(config, sequence_no)
        rotor_hz = config.rated_speed_rpm / 60
        samples = []
        for index in range(config.window_size):
            t = index / config.sampling_rate_hz
            value = (
                0.130 * math.sin(2 * math.pi * rotor_hz * t)
                + 0.028 * math.sin(2 * math.pi * 2 * rotor_hz * t + 0.4)
                + 0.008 * math.sin(2 * math.pi * 3 * rotor_hz * t + 1.1)
                + rng.gauss(0, 0.004)
            )
            samples.append(value)
    elif scenario == "cavitation":
        rng = _rng_for(config, sequence_no)
        rotor_hz = config.rated_speed_rpm / 60
        samples = []
        for index in range(config.window_size):
            t = index / config.sampling_rate_hz
            modulation = 0.55 + 0.45 * math.sin(2 * math.pi * 7 * t)
            value = (
                0.035 * math.sin(2 * math.pi * rotor_hz * t)
                + 0.055 * modulation * math.sin(2 * math.pi * 640 * t)
                + 0.018 * math.sin(2 * math.pi * 1250 * t)
                + rng.gauss(0, 0.022)
            )
            samples.append(value)
    elif scenario == "incipient_fault":
        rng = _rng_for(config, sequence_no)
        rotor_hz = config.rated_speed_rpm / 60
        samples = []
        for index in range(config.window_size):
            t = index / config.sampling_rate_hz
            value = (
                0.070 * math.sin(2 * math.pi * rotor_hz * t + 0.2)
                + 0.020 * math.sin(2 * math.pi * 2 * rotor_hz * t + 0.5)
                + 0.010 * math.sin(2 * math.pi * 410 * t)
                + rng.gauss(0, 0.009)
            )
            samples.append(value)
    elif scenario == "custom_abnormal":
        rng = _rng_for(config, sequence_no)
        frequency = config.custom_frequency_hz or (2 * config.rated_speed_rpm / 60)
        samples = _normal_waveform(config, sequence_no)
        for index in range(config.window_size):
            t = index / config.sampling_rate_hz
            samples[index] += config.custom_amplitude_g * math.sin(
                2 * math.pi * frequency * t
            )
            samples[index] += rng.gauss(0, 0.002)
    else:
        samples = _normal_waveform(config, sequence_no)

    if scenario == "corrupted_samples":
        count = len(samples)
        for index, value in {
            17: float("nan"),
            101: float("inf"),
            333: 9999.0,
            512: float("-inf"),
        }.items():
            samples[index % count] = value

    return samples


def generate_frame(
    config: AdapterConfig,
    sequence_no: int,
    start_time: datetime,
) -> SignalFrame:
    if start_time.tzinfo is None:
        raise ValueError("start_time must be timezone-aware")
    if config.scenario not in SCENARIOS:
        raise ValueError(f"Unknown simulation scenario: {config.scenario}")

    start = start_time.astimezone(UTC)
    end = start + timedelta(seconds=config.window_duration_s)
    samples = tuple(_generate_samples(config, sequence_no))
    adapter_state = (
        AdapterState.DISCONNECTED
        if config.scenario == "sensor_disconnect"
        else AdapterState.CONNECTED
    )
    return SignalFrame(
        sensor_id=config.sensor_id,
        session_id="",
        sequence_no=sequence_no,
        window_start=start,
        window_end=end,
        sampling_rate_hz=config.sampling_rate_hz,
        samples=samples,
        units=config.units,
        adapter_state=adapter_state,
        notes=SCENARIOS[config.scenario].description,
    )


def generate_frames(
    config: AdapterConfig, start_time: datetime
) -> Iterator[SignalFrame]:
    hop_seconds = config.hop_samples / config.sampling_rate_hz
    for sequence_no in range(config.window_count):
        frame_start = start_time + timedelta(seconds=sequence_no * hop_seconds)
        yield generate_frame(config, sequence_no, frame_start)
