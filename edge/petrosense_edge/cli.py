import argparse
import contextlib
import getpass
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from petrosense_edge.adapters import SimulatedSensorAdapter
from petrosense_edge.api_client import ApiClient, EdgeApiError
from petrosense_edge.contracts import (
    AdapterConfig,
    QualityStatus,
    SignalFrame,
    ValidationResult,
)
from petrosense_edge.decision import DecisionPolicy, DecisionResult
from petrosense_edge.features import FeatureExtractionError, FeatureExtractor
from petrosense_edge.inference import ModelArtifactError, load_model_artifact
from petrosense_edge.simulation import SCENARIOS, scenario_registry
from petrosense_edge.validation import SignalValidator


def _window_payload(
    frame: SignalFrame,
    result: ValidationResult,
    features: dict[str, float] | None = None,
) -> dict[str, Any]:
    valid = result.status == QualityStatus.VALID
    return {
        "window_index": frame.sequence_no,
        "window_start": frame.window_start.isoformat(),
        "window_end": frame.window_end.isoformat(),
        "samples": list(frame.samples) if valid else [],
        "quality_status": result.status.value,
        "features": features if valid else None,
        "validation_summary": {
            "issues": [asdict(issue) for issue in result.issues],
            "metrics": result.metrics,
            "scenario": frame.notes,
            "simulated": True,
        },
    }


def _prediction_payload(
    *,
    session_id: str,
    pump_id: str,
    sensor_id: str,
    window_id: str,
    active_model: dict[str, Any] | None,
    decision_result: DecisionResult,
    latency_ms: float,
) -> dict[str, Any]:
    return {
        "event_id": f"pred-{uuid4()}",
        "pump_id": pump_id,
        "sensor_id": sensor_id,
        "session_id": session_id,
        "signal_window_id": window_id,
        "model_version_id": active_model["id"] if active_model else None,
        "decision": decision_result.decision.value,
        "data_quality": "VALID",
        "decision_score": decision_result.decision_score,
        "uncertainty_score": decision_result.uncertainty_score,
        "explanation": decision_result.explanation,
        "latency_ms": latency_ms,
        "inferred_at": datetime.now(UTC).isoformat(),
    }


def _sensor_invalid_prediction(
    *,
    session_id: str,
    pump_id: str,
    sensor_id: str,
    window_id: str,
    result: ValidationResult,
) -> dict[str, Any]:
    codes = ", ".join(issue.code for issue in result.issues) or "unknown_validation_failure"
    return {
        "event_id": f"pred-{uuid4()}",
        "pump_id": pump_id,
        "sensor_id": sensor_id,
        "session_id": session_id,
        "signal_window_id": window_id,
        "model_version_id": None,
        "decision": "SENSOR_INVALID",
        "data_quality": "SENSOR_INVALID",
        "decision_score": None,
        "uncertainty_score": None,
        "explanation": (
            f"Signal validation failed ({codes}); condition inference was not attempted."
        ),
        "latency_ms": 0.0,
        "inferred_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="petrosense-edge",
        description="PUMPVERITY AI deterministic simulated acquisition client.",
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--email", default="engineer@petrosense.local")
    parser.add_argument("--password", default=None, help="Prefer PETROSENSE_EDGE_PASSWORD")
    parser.add_argument("--pump-code")
    parser.add_argument("--sensor-code")
    parser.add_argument("--scenario", default="normal", choices=sorted(SCENARIOS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--windows", type=int, default=5)
    parser.add_argument("--window-size", type=int, default=2048)
    parser.add_argument("--sampling-rate", type=float, default=2048.0)
    parser.add_argument("--overlap", type=float, default=0.5)
    parser.add_argument("--rated-speed-rpm", type=int, default=2900)
    parser.add_argument("--custom-amplitude", type=float, default=0.1)
    parser.add_argument("--custom-frequency", type=float, default=None)
    parser.add_argument("--device-id", default="edge-sim-cli")
    parser.add_argument(
        "--model-path",
        default=None,
        help="Local model artifact path; defaults to the active model's registered path",
    )
    parser.add_argument(
        "--no-inference",
        action="store_true",
        help="Store windows without loading the active model or creating predictions",
    )
    parser.add_argument("--list-scenarios", action="store_true")
    return parser


def _print_scenarios() -> None:
    for scenario in scenario_registry():
        print(
            f"{scenario.code:<20} {scenario.label:<38} "
            f"expected={scenario.expected_quality.value}"
        )
        print(f"  {scenario.description}")


def run(args: argparse.Namespace) -> int:
    if args.list_scenarios:
        _print_scenarios()
        return 0
    if not args.pump_code or not args.sensor_code:
        print("--pump-code and --sensor-code are required for simulation.", file=sys.stderr)
        return 2

    password = args.password or os.environ.get("PETROSENSE_EDGE_PASSWORD")
    if not password:
        password = getpass.getpass("PUMPVERITY password: ")

    client = ApiClient(args.api_base)
    try:
        client.login(args.email, password)
        pump = client.find_pump(args.pump_code)
        if pump is None:
            raise EdgeApiError(f"Pump '{args.pump_code}' was not found.")
        sensor = client.find_sensor(args.sensor_code, pump["id"])
        if sensor is None:
            raise EdgeApiError(
                f"Sensor '{args.sensor_code}' was not found for pump '{pump['pump_code']}'."
            )
        if not sensor["is_active"]:
            raise EdgeApiError(f"Sensor '{sensor['sensor_code']}' is inactive.")

        loaded_model = None
        active_model = None
        if not args.no_inference:
            active_model = client.get_active_model()
            if active_model is None:
                print(
                    "Warning: no active model. Windows will be stored without predictions."
                )
            else:
                runtime = active_model.get("runtime")
                if runtime not in {"LINEAR_JSON", "BASELINE"}:
                    raise EdgeApiError(
                        f"Active model runtime '{runtime}' is not supported by this edge build."
                    )
                configured_path = args.model_path or active_model.get("artifact_path")
                if not configured_path:
                    raise EdgeApiError("Active model has no artifact path.")
                artifact_path = Path(configured_path)
                if not artifact_path.is_absolute():
                    artifact_path = Path.cwd() / artifact_path
                expected_features = active_model.get("feature_contract", {}).get("features")
                try:
                    loaded_model = load_model_artifact(
                        artifact_path,
                        expected_sha256=active_model["artifact_sha256"],
                        expected_features=expected_features,
                    )
                except (ModelArtifactError, KeyError, TypeError) as exc:
                    raise EdgeApiError(f"Active model could not be loaded: {exc}") from exc
                if (
                    loaded_model.model_code
                    and loaded_model.model_code != active_model.get("model_code")
                ) or loaded_model.version != active_model.get("version"):
                    raise EdgeApiError(
                        "Local model artifact identity does not match the active model metadata."
                    )
                short_hash = active_model["artifact_sha256"][:12]
                print(
                    f"Active model: {loaded_model.label} "
                    f"({active_model.get('runtime')}, sha256 {short_hash}…)"
                )

        try:
            config = AdapterConfig(
                sensor_id=sensor["id"],
                pump_id=pump["id"],
                sampling_rate_hz=args.sampling_rate,
                window_size=args.window_size,
                overlap_fraction=args.overlap,
                rated_speed_rpm=args.rated_speed_rpm,
                scenario=args.scenario,
                seed=args.seed,
                window_count=args.windows,
                custom_amplitude_g=args.custom_amplitude,
                custom_frequency_hz=args.custom_frequency,
            )
        except ValueError as exc:
            raise EdgeApiError(f"Invalid simulation configuration: {exc}") from exc
        session = client.create_session(
            {
                "pump_id": pump["id"],
                "sensor_id": sensor["id"],
                "regime_id": pump.get("default_regime", {}).get("id")
                if pump.get("default_regime")
                else None,
                "sampling_rate_hz": config.sampling_rate_hz,
                "data_provenance": "SIMULATED",
                "random_seed": config.seed,
                "scenario": config.scenario,
                "source_device_id": args.device_id,
                "notes": (
                    f"Deterministic simulation: scenario={config.scenario}, "
                    f"seed={config.seed}, windows={config.window_count}."
                ),
            }
        )
        session_id = session["id"]
        print(
            f"Session {session_id} started for {pump['pump_code']} / "
            f"{sensor['sensor_code']} ({config.scenario}, seed={config.seed})."
        )

        adapter = SimulatedSensorAdapter(config)
        validator = SignalValidator()
        extractor = FeatureExtractor()
        policy = DecisionPolicy(loaded_model.thresholds) if loaded_model else None
        accepted = 0
        invalid = 0
        predicted = 0

        try:
            adapter.start(session_id, datetime.now(UTC))
            while True:
                frame = adapter.read()
                if frame is None:
                    break
                result = validator.validate(frame, config.sampling_rate_hz)
                features = None
                if result.status == QualityStatus.VALID:
                    try:
                        features = extractor.extract(
                            frame.samples,
                            config.sampling_rate_hz,
                            config.rated_speed_rpm,
                        )
                    except FeatureExtractionError as exc:
                        raise EdgeApiError(f"Feature extraction failed: {exc}") from exc

                if result.status == QualityStatus.VALID:
                    accepted += 1
                    rms = result.metrics.get("rms")
                    rms_text = f"{rms:.4f}" if isinstance(rms, float) else "n/a"
                    print(
                        f"  window {frame.sequence_no}: VALID "
                        f"rms={rms_text} {frame.units}"
                    )
                else:
                    invalid += 1
                    codes = ", ".join(issue.code for issue in result.issues)
                    print(f"  window {frame.sequence_no}: SENSOR_INVALID [{codes}]")

                window = client.ingest_window(
                    session_id, _window_payload(frame, result, features)
                )

                if args.no_inference:
                    continue

                if (
                    result.status == QualityStatus.VALID
                    and loaded_model is not None
                    and policy is not None
                ):
                    started = perf_counter()
                    score = loaded_model.score(features or {})
                    decision = policy.decide(
                        score,
                        model_label=loaded_model.label,
                        score_name="fault-class decision score",
                    )
                    latency_ms = round((perf_counter() - started) * 1000, 3)
                    client.create_prediction(
                        _prediction_payload(
                            session_id=session_id,
                            pump_id=pump["id"],
                            sensor_id=sensor["id"],
                            window_id=window["id"],
                            active_model=active_model,
                            decision_result=decision,
                            latency_ms=latency_ms,
                        )
                    )
                    predicted += 1
                    print(
                        f"    decision: {decision.decision.value} "
                        f"score={decision.decision_score:.4f} "
                        f"uncertainty={decision.uncertainty_score:.4f} "
                        f"latency={latency_ms:.2f}ms"
                    )
                elif result.status == QualityStatus.SENSOR_INVALID:
                    client.create_prediction(
                        _sensor_invalid_prediction(
                            session_id=session_id,
                            pump_id=pump["id"],
                            sensor_id=sensor["id"],
                            window_id=window["id"],
                            result=result,
                        )
                    )
                    predicted += 1

            client.stop_session(session_id, "COMPLETED")
        except Exception:
            with contextlib.suppress(EdgeApiError):
                client.stop_session(session_id, "ABORTED")
            raise

        print(
            f"Session complete: {accepted} valid windows, {invalid} sensor-invalid windows, "
            f"{predicted} prediction(s)."
        )
        return 0
    except EdgeApiError as exc:
        print(f"Simulation failed: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    return run(_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
