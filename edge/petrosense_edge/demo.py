"""Presentation-mode demo driver.

Streams deterministic SIMULATED vibration windows through the normal edge pipeline
(validation -> features -> on-device inference -> decision policy -> API) at a steady,
human-watchable pace. The scenario is chosen by the presenter in the web UI
(``/demo/control``); this process polls that state through its heartbeat.

Every window is stamped with the wall-clock time it was generated and carries ``SIMULATED``
provenance. Nothing here bypasses the API or writes to the database directly.

Usage (from the repository root, API running with PETROSENSE_DEMO_MODE=true)::

    apps/api/.venv/Scripts/python -m petrosense_edge.demo --warmup
"""

import argparse
import contextlib
import dataclasses
import os
import random
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, TypeVar

from petrosense_edge.api_client import ApiClient, EdgeApiError
from petrosense_edge.cli import (
    _prediction_payload,
    _sensor_invalid_prediction,
    _window_payload,
)
from petrosense_edge.contracts import AdapterConfig, QualityStatus
from petrosense_edge.decision import DecisionPolicy
from petrosense_edge.features import FeatureExtractionError, FeatureExtractor
from petrosense_edge.inference import ModelArtifactError, load_model_artifact
from petrosense_edge.simulation import generate_frame
from petrosense_edge.validation import SignalValidator

REPO_ROOT = Path(__file__).resolve().parents[2]

DEMO_PUMP: dict[str, Any] = {
    "pump_code": "LAB-PUMP-01",
    "name": "Centrifugal pump test rig",
    "pump_type": "CENTRIFUGAL",
    "location": "Research laboratory - guarded water loop (simulated stream)",
    "rated_speed_rpm": 2900,
    "status": "ACTIVE",
    "notes": (
        "Research test rig used for the PumpVerity AI demonstration. All signals shown are "
        "SIMULATED until the calibrated sensor and edge device are commissioned."
    ),
    "sensor": {
        "sensor_code": "VIB-01",
        "sensor_type": "VIBRATION",
        "manufacturer": "Analog Devices (candidate)",
        "model_name": "ADXL355-class MEMS accelerometer",
        "mounting_axis": "RADIAL_X",
        "mounting_position": "Drive-end bearing housing",
        "sampling_rate_hz": 2048.0,
        "is_active": True,
    },
}

# (preset code, number of windows) - a short scripted history so the dashboard, alerts and
# historical trends have content before the presenter takes control.
WARMUP_SCRIPT: list[tuple[str, int]] = [
    ("normal", 40),
    ("weak_anomaly", 10),
    ("normal", 20),
    ("imbalance", 12),
    ("normal", 20),
    ("cavitation", 10),
    ("normal", 20),
    ("sensor_disconnect", 6),
    ("normal", 25),
]

T = TypeVar("T")


def _log(message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def _read_env_password(env_file: Path) -> str | None:
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "PETROSENSE_DEMO_PASSWORD" and value.strip():
            return value.strip()
    return None


class DemoDriver:
    def __init__(self, args: argparse.Namespace, password: str) -> None:
        self.args = args
        self.password = password
        self.client = ApiClient(args.api_base, timeout_s=15.0)
        self.validator = SignalValidator()
        self.extractor = FeatureExtractor()
        self.presets: dict[str, dict[str, Any]] = {}
        self.pump: dict[str, Any] | None = None
        self.sensor: dict[str, Any] | None = None
        self.active_model: dict[str, Any] | None = None
        self.loaded_model = None
        self.policy: DecisionPolicy | None = None
        self.session_id: str | None = None
        self.session_preset: str | None = None
        self.config: AdapterConfig | None = None
        self.window_index = 0
        self.windows_streamed = 0
        self.last_decision: str | None = None
        self.orphaned_sessions: list[str] = []

    # ------------------------------------------------------------------ API plumbing
    def _call(self, fn: Callable[..., T], *args: Any) -> T:
        try:
            return fn(*args)
        except EdgeApiError as exc:
            if exc.status == 401:
                self.client.login(self.args.email, self.password)
                return fn(*args)
            raise

    def login(self) -> None:
        self.client.login(self.args.email, self.password)
        _log(f"Signed in to {self.args.api_base} as {self.args.email}.")
        while self.orphaned_sessions:
            session_id = self.orphaned_sessions.pop()
            with contextlib.suppress(EdgeApiError):
                self.client.stop_session(session_id, "ABORTED")
                _log(f"Closed interrupted session {session_id[:8]} as ABORTED.")

    def control(self, message: str | None = None) -> dict[str, Any]:
        state = self._call(
            self.client._request,
            "POST",
            "/demo/heartbeat",
            {
                "preset": self.session_preset,
                "pump_code": self.pump["pump_code"] if self.pump else None,
                "session_id": self.session_id,
                "windows_streamed": self.windows_streamed,
                "last_decision": self.last_decision,
                "message": message,
            },
        )
        self.presets = {preset["code"]: preset for preset in state.get("presets", [])}
        return state

    # ------------------------------------------------------------------ setup
    def ensure_pump(self) -> None:
        pump = self._call(self.client.find_pump, DEMO_PUMP["pump_code"])
        if pump is None:
            payload = dict(DEMO_PUMP)
            regimes = self._call(self.client._request, "GET", "/operating-regimes") or []
            steady = next((r for r in regimes if r.get("code") == "STEADY_STATE"), None)
            if steady is not None:
                payload["default_regime_id"] = steady["id"]
            pump = self._call(self.client._request, "POST", "/pumps", payload)
            _log(f"Registered demo pump {pump['pump_code']} with sensor VIB-01.")
        sensor = self._call(
            self.client.find_sensor, DEMO_PUMP["sensor"]["sensor_code"], pump["id"]
        )
        if sensor is None or not sensor["is_active"]:
            raise EdgeApiError("Demo sensor VIB-01 is missing or inactive on LAB-PUMP-01.")
        self.pump, self.sensor = pump, sensor
        self.close_stale_sessions()

    def close_stale_sessions(self) -> None:
        """Abort ACTIVE sessions this driver left behind (e.g. after a forced stop)."""
        assert self.pump is not None
        query = f"/acquisition-sessions?pump_id={self.pump['id']}&status=ACTIVE&page_size=100"
        page = self._call(self.client._request, "GET", query) or {}
        for session in page.get("items", []):
            if session.get("source_device_id") == self.args.device_id:
                with contextlib.suppress(EdgeApiError):
                    self._call(self.client.stop_session, session["id"], "ABORTED")
                    _log(f"Closed stale session {session['id'][:8]} as ABORTED.")

    def load_model(self) -> None:
        active = self._call(self.client.get_active_model)
        if active is None:
            _log("WARNING: no active model - windows will stream without AI decisions.")
            self.active_model = self.loaded_model = self.policy = None
            return
        if active.get("runtime") not in {"LINEAR_JSON", "BASELINE"}:
            raise EdgeApiError(f"Active model runtime {active.get('runtime')} unsupported.")
        artifact = Path(active.get("artifact_path") or "")
        candidates = [artifact] if artifact.is_absolute() else [
            Path.cwd() / artifact,
            REPO_ROOT / artifact,
        ]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None:
            raise EdgeApiError(f"Model artefact not found: {artifact}")
        try:
            self.loaded_model = load_model_artifact(
                path,
                expected_sha256=active["artifact_sha256"],
                expected_features=active.get("feature_contract", {}).get("features"),
            )
        except (ModelArtifactError, KeyError, TypeError) as exc:
            raise EdgeApiError(f"Active model could not be loaded: {exc}") from exc
        self.active_model = active
        self.policy = DecisionPolicy(self.loaded_model.thresholds)
        _log(
            f"Edge model loaded: {self.loaded_model.label} "
            f"(sha256 {active['artifact_sha256'][:12]}..., hash verified)."
        )

    # ------------------------------------------------------------------ sessions
    def start_session(self, preset_code: str) -> None:
        self.stop_session()
        preset = self.presets.get(preset_code)
        if preset is None:
            raise EdgeApiError(f"Unknown preset {preset_code!r} from demo control.")
        assert self.pump is not None and self.sensor is not None
        seed = random.randint(1, 1_000_000)
        self.config = AdapterConfig(
            sensor_id=self.sensor["id"],
            pump_id=self.pump["id"],
            sampling_rate_hz=float(self.sensor.get("sampling_rate_hz") or 2048.0),
            window_size=2048,
            overlap_fraction=0.0,
            rated_speed_rpm=int(self.pump.get("rated_speed_rpm") or 2900),
            scenario=preset["scenario"],
            seed=seed,
            window_count=1_000_000,
            custom_amplitude_g=preset.get("custom_amplitude_g") or 0.1,
        )
        regime = self.pump.get("default_regime") or {}
        session = self._call(
            self.client.create_session,
            {
                "pump_id": self.pump["id"],
                "sensor_id": self.sensor["id"],
                "regime_id": regime.get("id"),
                "sampling_rate_hz": self.config.sampling_rate_hz,
                "data_provenance": "SIMULATED",
                "random_seed": seed,
                "scenario": self.config.scenario,
                "source_device_id": self.args.device_id,
                "notes": (
                    f"Presentation demo stream: preset={preset_code} ({preset['label']}), "
                    f"scenario={self.config.scenario}, seed={seed}."
                ),
            },
        )
        self.session_id = session["id"]
        self.session_preset = preset_code
        self.window_index = 0
        _log(f"Session started: {preset['label']} -> expect {preset['expected_outcome']}.")

    def stop_session(self, status: str = "COMPLETED") -> None:
        if self.session_id is None:
            return
        with contextlib.suppress(EdgeApiError):
            self._call(self.client.stop_session, self.session_id, status)
        self.session_id = None
        self.session_preset = None

    # ------------------------------------------------------------------ one window
    def step(self) -> None:
        assert self.config is not None and self.session_id is not None
        assert self.pump is not None and self.sensor is not None
        end = datetime.now(UTC)
        start = end - timedelta(seconds=self.config.window_duration_s)
        frame = generate_frame(self.config, self.window_index, start)
        frame = dataclasses.replace(frame, session_id=self.session_id)
        result = self.validator.validate(frame, self.config.sampling_rate_hz)
        features = None
        if result.status == QualityStatus.VALID:
            try:
                features = self.extractor.extract(
                    frame.samples, self.config.sampling_rate_hz, self.config.rated_speed_rpm
                )
            except FeatureExtractionError as exc:
                raise EdgeApiError(f"Feature extraction failed: {exc}") from exc
        window = self._call(
            self.client.ingest_window,
            self.session_id,
            _window_payload(frame, result, features),
        )
        self.window_index += 1
        self.windows_streamed += 1

        rms = result.metrics.get("rms")
        rms_text = f"rms={rms:.4f}g" if isinstance(rms, float) else "rms=n/a"
        if result.status != QualityStatus.VALID:
            self._call(
                self.client.create_prediction,
                _sensor_invalid_prediction(
                    session_id=self.session_id,
                    pump_id=self.pump["id"],
                    sensor_id=self.sensor["id"],
                    window_id=window["id"],
                    result=result,
                ),
            )
            self.last_decision = "SENSOR_INVALID"
            codes = ", ".join(issue.code for issue in result.issues)
            _log(f"  #{self.window_index:<4} SENSOR_INVALID  inference suppressed [{codes}]")
            return
        if self.loaded_model is None or self.policy is None:
            self.last_decision = None
            _log(f"  #{self.window_index:<4} VALID {rms_text} (no active model)")
            return
        started = perf_counter()
        score = self.loaded_model.score(features or {})
        decision = self.policy.decide(
            score,
            model_label=self.loaded_model.label,
            score_name="fault-class decision score",
        )
        latency_ms = round((perf_counter() - started) * 1000, 3)
        self._call(
            self.client.create_prediction,
            _prediction_payload(
                session_id=self.session_id,
                pump_id=self.pump["id"],
                sensor_id=self.sensor["id"],
                window_id=window["id"],
                active_model=self.active_model,
                decision_result=decision,
                latency_ms=latency_ms,
            ),
        )
        self.last_decision = decision.decision.value
        _log(
            f"  #{self.window_index:<4} {decision.decision.value:<9} {rms_text} "
            f"score={decision.decision_score:.3f} "
            f"uncertainty={decision.uncertainty_score:.3f} latency={latency_ms:.2f}ms"
        )

    # ------------------------------------------------------------------ modes
    def warmup(self) -> None:
        _log("Warm-up: streaming a scripted history (normal, uncertain, faults, invalid).")
        self.control("warm-up in progress")
        for preset_code, windows in WARMUP_SCRIPT:
            self.start_session(preset_code)
            for _ in range(windows):
                self.step()
                time.sleep(self.args.warmup_interval)
        self.stop_session()
        _log("Warm-up complete.")

    def live(self) -> None:
        _log("Live mode: follow the scenario selected in the web UI. Ctrl+C to stop.")
        last_model_check = time.monotonic()
        while True:
            state = self.control()
            if state.get("paused"):
                if self.session_id is not None:
                    self.stop_session()
                    _log("Stream paused from the web UI.")
                time.sleep(1.0)
                continue
            wanted = state.get("preset") or "normal"
            if wanted != self.session_preset:
                self.start_session(wanted)
            if time.monotonic() - last_model_check > 30:
                current = self._call(self.client.get_active_model)
                current_id = current["id"] if current else None
                active_id = self.active_model["id"] if self.active_model else None
                if current_id != active_id:
                    _log("Active model changed - reloading edge artefact.")
                    self.load_model()
                    self.stop_session()
                last_model_check = time.monotonic()
                if self.session_id is None:
                    continue
            self.step()
            time.sleep(self.args.interval)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="petrosense-edge-demo",
        description="PumpVerity AI presentation-mode simulated edge stream.",
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--email", default="engineer@petrosense.local")
    parser.add_argument("--env-file", default=str(REPO_ROOT / "apps" / "api" / ".env"))
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between windows")
    parser.add_argument("--warmup", action="store_true", help="Stream a scripted history first")
    parser.add_argument("--warmup-interval", type=float, default=0.2)
    parser.add_argument("--warmup-only", action="store_true", help="Exit after warm-up")
    parser.add_argument("--device-id", default="edge-demo-sim")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    password = (
        os.environ.get("PETROSENSE_EDGE_PASSWORD")
        or os.environ.get("PETROSENSE_DEMO_PASSWORD")
        or _read_env_password(Path(args.env_file))
    )
    if not password:
        print("Set PETROSENSE_EDGE_PASSWORD or provide --env-file.", file=sys.stderr)
        return 2

    driver = DemoDriver(args, password)
    backoff = 2.0
    while True:
        try:
            driver.login()
            driver.ensure_pump()
            driver.load_model()
            driver.control("driver connected")
            backoff = 2.0
            if args.warmup or args.warmup_only:
                driver.warmup()
                args.warmup = False
                if args.warmup_only:
                    return 0
            driver.live()
        except KeyboardInterrupt:
            driver.stop_session()
            _log("Demo driver stopped.")
            return 0
        except Exception as exc:  # the presentation stream must recover from anything
            if isinstance(exc, EdgeApiError) and exc.code == "DEMO_MODE_DISABLED":
                print("Start the API with PETROSENSE_DEMO_MODE=true.", file=sys.stderr)
                return 2
            _log(f"Stream interrupted ({type(exc).__name__}: {exc}) - retrying in {backoff:.0f}s.")
            if driver.session_id is not None:
                driver.orphaned_sessions.append(driver.session_id)
            driver.session_id = None
            driver.session_preset = None
            try:
                time.sleep(backoff)
            except KeyboardInterrupt:
                return 0
            backoff = min(backoff * 2, 15.0)


if __name__ == "__main__":
    raise SystemExit(main())
