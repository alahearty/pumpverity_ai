import math
import statistics
from dataclasses import dataclass

from petrosense_edge.contracts import (
    AdapterState,
    QualityStatus,
    SignalFrame,
    ValidationIssue,
    ValidationResult,
)


@dataclass(frozen=True)
class ValidatorConfig:
    min_samples: int = 256
    max_abs_value: float = 50.0
    flatline_std_threshold: float = 1e-9
    sampling_rate_tolerance: float = 0.01
    timestamp_tolerance_s: float = 0.01
    allowed_units: tuple[str, ...] = ("g", "m/s^2", "mm/s")


class SignalValidator:
    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self.config = config or ValidatorConfig()

    def validate(
        self,
        frame: SignalFrame,
        expected_sampling_rate_hz: float | None = None,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        metrics: dict[str, float | int | str] = {
            "sample_count": len(frame.samples),
            "units": frame.units,
        }

        if frame.adapter_state == AdapterState.DISCONNECTED:
            issues.append(
                ValidationIssue(
                    code="sensor_disconnected",
                    message="The acquisition adapter reports a disconnected sensor.",
                )
            )
        if not frame.samples:
            issues.append(
                ValidationIssue(
                    code="missing_samples",
                    message="No samples were supplied for the window.",
                )
            )
            return ValidationResult(
                status=QualityStatus.SENSOR_INVALID,
                issues=tuple(issues),
                metrics=metrics,
            )

        if len(frame.samples) < self.config.min_samples:
            issues.append(
                ValidationIssue(
                    code="insufficient_samples",
                    message=(
                        f"Window contains {len(frame.samples)} samples; "
                        f"minimum is {self.config.min_samples}."
                    ),
                )
            )

        if not math.isfinite(frame.sampling_rate_hz) or frame.sampling_rate_hz <= 0:
            issues.append(
                ValidationIssue(
                    code="invalid_sampling_rate",
                    message="Sampling rate must be a positive finite number.",
                )
            )
        elif expected_sampling_rate_hz is not None:
            relative_error = abs(
                frame.sampling_rate_hz - expected_sampling_rate_hz
            ) / expected_sampling_rate_hz
            if relative_error > self.config.sampling_rate_tolerance:
                issues.append(
                    ValidationIssue(
                        code="sampling_rate_mismatch",
                        message="Window sampling rate does not match the session configuration.",
                    )
                )

        if frame.units not in self.config.allowed_units:
            issues.append(
                ValidationIssue(
                    code="unexpected_units",
                    message=f"Units '{frame.units}' are not in the accepted unit set.",
                )
            )

        duration_s = (frame.window_end - frame.window_start).total_seconds()
        metrics["duration_s"] = duration_s
        if frame.sampling_rate_hz > 0:
            expected_duration = len(frame.samples) / frame.sampling_rate_hz
            tolerance = max(
                self.config.timestamp_tolerance_s,
                2 / frame.sampling_rate_hz,
            )
            if abs(duration_s - expected_duration) > tolerance:
                issues.append(
                    ValidationIssue(
                        code="timestamp_mismatch",
                        message="Window duration does not match sample count and sampling rate.",
                    )
                )

        if not all(math.isfinite(value) for value in frame.samples):
            issues.append(
                ValidationIssue(
                    code="non_finite_values",
                    message="Window contains NaN or infinite sample values.",
                )
            )
        else:
            peak_abs = max(abs(value) for value in frame.samples)
            rms = math.sqrt(
                math.fsum(value * value for value in frame.samples) / len(frame.samples)
            )
            mean = statistics.fmean(frame.samples)
            std = statistics.pstdev(frame.samples)
            metrics.update(
                {
                    "rms": rms,
                    "peak_abs": peak_abs,
                    "mean": mean,
                    "std": std,
                    "crest_factor": peak_abs / rms if rms > 0 else 0.0,
                }
            )
            if peak_abs > self.config.max_abs_value:
                issues.append(
                    ValidationIssue(
                        code="out_of_range",
                        message=(
                            f"Peak absolute value {peak_abs:.3f} exceeds the configured "
                            f"limit {self.config.max_abs_value}."
                        ),
                    )
                )
            if std < self.config.flatline_std_threshold:
                issues.append(
                    ValidationIssue(
                        code="flatline",
                        message=(
                            "Window has effectively zero variance and may be a "
                            "flatlined sensor."
                        ),
                    )
                )

        status = (
            QualityStatus.SENSOR_INVALID
            if issues
            else QualityStatus.VALID
        )
        return ValidationResult(status=status, issues=tuple(issues), metrics=metrics)

