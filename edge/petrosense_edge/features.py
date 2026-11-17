import itertools
import math

FEATURE_CONTRACT: dict[str, object] = {
    "version": "petrosense-time-v1",
    "features": [
        "rms",
        "peak_abs",
        "std",
        "skewness",
        "kurtosis_excess",
        "crest_factor",
        "zero_crossing_rate",
        "spectral_1x_ratio",
        "spectral_2x_ratio",
        "high_frequency_ratio",
    ],
}


class FeatureExtractionError(ValueError):
    pass


def _goertzel_amplitude(
    samples: tuple[float, ...],
    sampling_rate_hz: float,
    frequency_hz: float,
) -> float:
    if frequency_hz <= 0 or frequency_hz >= sampling_rate_hz / 2:
        return 0.0
    n = len(samples)
    omega = 2 * math.pi * frequency_hz / sampling_rate_hz
    coefficient = 2 * math.cos(omega)
    s_prev = 0.0
    s_prev2 = 0.0
    for sample in samples:
        current = sample + coefficient * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = current
    power = s_prev2 * s_prev2 + s_prev * s_prev - coefficient * s_prev * s_prev2
    return 2 * math.sqrt(max(power, 0.0)) / n


class FeatureExtractor:
    def __init__(self, contract: dict[str, object] | None = None) -> None:
        self.contract = contract or FEATURE_CONTRACT
        self.feature_names = list(self.contract["features"])  # type: ignore[index]

    def extract(
        self,
        samples: tuple[float, ...],
        sampling_rate_hz: float,
        rated_speed_rpm: int,
    ) -> dict[str, float]:
        if len(samples) < 16:
            raise FeatureExtractionError("At least 16 samples are required")
        if sampling_rate_hz <= 0 or rated_speed_rpm <= 0:
            raise FeatureExtractionError("Sampling rate and rated speed must be positive")
        if not all(math.isfinite(value) for value in samples):
            raise FeatureExtractionError("Features require finite samples")

        n = len(samples)
        mean = math.fsum(samples) / n
        centred = [value - mean for value in samples]
        variance = math.fsum(value * value for value in centred) / n
        std = math.sqrt(variance)
        rms = math.sqrt(math.fsum(value * value for value in samples) / n)
        peak_abs = max(abs(value) for value in samples)
        if std > 1e-12:
            skewness = math.fsum(value**3 for value in centred) / (n * std**3)
            kurtosis = math.fsum(value**4 for value in centred) / (n * std**4) - 3
        else:
            skewness = 0.0
            kurtosis = 0.0

        crest_factor = peak_abs / rms if rms > 1e-12 else 0.0
        zero_crossings = 0
        for previous, current in itertools.pairwise(samples):
            if (previous < 0 <= current) or (previous >= 0 > current):
                zero_crossings += 1
        zero_crossing_rate = zero_crossings / (n - 1)
        shaft_hz = rated_speed_rpm / 60
        amplitude_1x = _goertzel_amplitude(samples, sampling_rate_hz, shaft_hz)
        amplitude_2x = _goertzel_amplitude(samples, sampling_rate_hz, shaft_hz * 2)
        differences = tuple(
            current - previous for previous, current in itertools.pairwise(samples)
        )
        difference_rms = math.sqrt(
            math.fsum(value * value for value in differences) / len(differences)
        )
        denominator = rms if rms > 1e-12 else 1.0
        features = {
            "rms": rms,
            "peak_abs": peak_abs,
            "std": std,
            "skewness": skewness,
            "kurtosis_excess": kurtosis,
            "crest_factor": crest_factor,
            "zero_crossing_rate": zero_crossing_rate,
            "spectral_1x_ratio": amplitude_1x / denominator,
            "spectral_2x_ratio": amplitude_2x / denominator,
            "high_frequency_ratio": difference_rms / denominator,
        }
        return {name: round(float(features[name]), 8) for name in self.feature_names}


def vector_for_contract(features: dict[str, float], names: list[str]) -> list[float]:
    missing = [name for name in names if name not in features]
    if missing:
        raise FeatureExtractionError(f"Missing model features: {', '.join(missing)}")
    vector = []
    for name in names:
        value = features[name]
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise FeatureExtractionError(f"Feature '{name}' is not a finite number")
        vector.append(float(value))
    return vector
