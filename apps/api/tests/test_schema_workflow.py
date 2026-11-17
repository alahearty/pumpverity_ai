from datetime import UTC, datetime

import pytest
from app.db.models import (
    AcquisitionSession,
    Alert,
    AlertReview,
    ModelEvaluation,
    ModelVersion,
    Prediction,
    Pump,
    Sensor,
    SensorReading,
    SignalWindow,
    User,
)
from app.domain.enums import (
    AlertCategory,
    AlertSeverity,
    DataQuality,
    LabelSource,
    ModelRuntime,
    ModelStatus,
    MountingAxis,
    PredictionDecision,
    Provenance,
    PumpType,
    ReviewAction,
    SensorType,
    SessionStatus,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


def _build_chain(db):
    admin = db.execute(select(User).where(User.username == "admin")).scalar_one()
    reviewer = db.execute(select(User).where(User.username == "reviewer")).scalar_one()

    pump = Pump(
        pump_code="LAB-PUMP-01",
        name="Laboratory Centrifugal Pump",
        pump_type=PumpType.CENTRIFUGAL,
        location="Thermofluids Laboratory",
        rated_speed_rpm=2900,
        created_by_id=admin.id,
    )
    db.add(pump)

    sensor = Sensor(
        sensor_code="VIB-01",
        pump=pump,
        sensor_type=SensorType.VIBRATION,
        mounting_axis=MountingAxis.RADIAL_X,
        mounting_position="Drive-end bearing housing",
        sampling_rate_hz=2048.0,
    )
    db.add(sensor)

    session = AcquisitionSession(
        pump=pump,
        sensor=sensor,
        sampling_rate_hz=2048.0,
        data_provenance=Provenance.SIMULATED,
        random_seed=42,
        status=SessionStatus.ACTIVE,
        started_by_id=admin.id,
    )
    db.add(session)
    db.flush()

    reading = SensorReading(
        session_id=session.id,
        sensor_id=sensor.id,
        sequence_no=1,
        recorded_at=datetime.now(UTC),
        value=0.42,
        unit="g",
        quality_status=DataQuality.VALID,
    )
    db.add(reading)

    window = SignalWindow(
        session_id=session.id,
        sensor_id=sensor.id,
        window_index=0,
        window_start=datetime.now(UTC),
        window_end=datetime.now(UTC),
        sampling_rate_hz=2048.0,
        sample_count=2048,
        signal_payload=b"\x00" * 64,
        features={"rms": 0.42, "kurtosis": 3.1},
        quality_status=DataQuality.VALID,
        data_provenance=Provenance.SIMULATED,
    )
    db.add(window)

    model = ModelVersion(
        model_code="rms-threshold-baseline",
        name="RMS threshold baseline",
        version="0.1.0",
        algorithm="engineering-threshold",
        runtime=ModelRuntime.BASELINE,
        feature_contract={"features": ["rms", "kurtosis"], "window_samples": 2048},
        training_dataset_version="simulated-v1",
        evaluation_dataset="simulated-eval-v1",
        artifact_path="ml/artifacts/rms-threshold-baseline-0.1.0.json",
        artifact_sha256="a" * 64,
        status=ModelStatus.VALIDATED,
        registered_by_id=admin.id,
    )
    db.add(model)

    evaluation = ModelEvaluation(
        model_version=model,
        dataset_name="Synthetic integration set",
        dataset_version="simulated-eval-v1",
        data_provenance=Provenance.SIMULATED,
        evaluation_protocol="held-out seeded runs",
        split_description="Grouped by simulated run; not experimental evidence",
        sample_count=120,
        balanced_accuracy=0.81,
        macro_f1=0.79,
        metrics={"false_alert_rate": 0.08},
        confusion_matrix={"NORMAL": {"NORMAL": 55, "FAULT": 5}},
        risk_coverage={"0.8": 0.86},
        evaluated_by="research-pipeline",
    )
    db.add(evaluation)
    db.flush()

    prediction = Prediction(
        event_id="evt-test-001",
        pump_id=pump.id,
        sensor_id=sensor.id,
        session_id=session.id,
        signal_window_id=window.id,
        model_version_id=model.id,
        decision=PredictionDecision.FAULT,
        data_quality=DataQuality.VALID,
        equipment_condition=None,
        decision_score=0.82,
        uncertainty_score=0.18,
        explanation="Synthetic fault demonstration",
        latency_ms=12.5,
        inferred_at=datetime.now(UTC),
        data_provenance=Provenance.SIMULATED,
    )
    db.add(prediction)
    db.flush()

    alert = Alert(
        event_id="alert-test-001",
        pump_id=pump.id,
        sensor_id=sensor.id,
        prediction_id=prediction.id,
        category=AlertCategory.FAULT,
        severity=AlertSeverity.HIGH,
        title="Simulated fault decision requiring review",
        description="Synthetic waveform generated for integration testing.",
        data_provenance=Provenance.SIMULATED,
    )
    db.add(alert)
    db.flush()

    review = AlertReview(
        alert_id=alert.id,
        reviewer_id=reviewer.id,
        action=ReviewAction.CONFIRM_LABEL,
        reviewed_label=PredictionDecision.FAULT,
        notes="Synthetic scenario confirmed for workflow demonstration.",
        label_source=LabelSource.ENGINEER_REVIEW,
        is_verified_ground_truth=False,
    )
    db.add(review)
    db.commit()

    return {
        "admin": admin,
        "reviewer": reviewer,
        "pump": pump,
        "sensor": sensor,
        "session": session,
        "reading": reading,
        "window": window,
        "model": model,
        "evaluation": evaluation,
        "prediction": prediction,
        "alert": alert,
        "review": review,
    }


def test_pump_to_review_traceability_chain(db):
    chain = _build_chain(db)

    prediction = db.get(Prediction, chain["prediction"].id)
    assert prediction is not None
    assert prediction.window is not None
    assert prediction.window.session.pump.id == chain["pump"].id
    assert prediction.sensor.id == chain["sensor"].id
    assert prediction.model_version.id == chain["model"].id

    alert = db.get(Alert, chain["alert"].id)
    assert alert.prediction.id == prediction.id
    assert alert.reviews[0].reviewer.id == chain["reviewer"].id
    assert alert.reviews[0].is_verified_ground_truth is False
    assert alert.reviews[0].label_source is LabelSource.ENGINEER_REVIEW
    assert alert.data_provenance is Provenance.SIMULATED


def test_review_never_overwrites_original_prediction(db):
    chain = _build_chain(db)
    original_decision = chain["prediction"].decision
    original_score = chain["prediction"].decision_score

    correction = AlertReview(
        alert_id=chain["alert"].id,
        reviewer_id=chain["reviewer"].id,
        action=ReviewAction.CORRECT_LABEL,
        reviewed_label=PredictionDecision.NORMAL,
        notes="Engineering assessment differs from the original model output.",
        label_source=LabelSource.ENGINEER_REVIEW,
    )
    db.add(correction)
    db.commit()
    db.refresh(chain["prediction"])

    assert chain["prediction"].decision == original_decision
    assert chain["prediction"].decision_score == original_score
    reviews = (
        db.execute(
            select(AlertReview).where(AlertReview.alert_id == chain["alert"].id)
        )
        .scalars()
        .all()
    )
    assert len(reviews) == 2
    assert {review.action for review in reviews} == {
        ReviewAction.CONFIRM_LABEL,
        ReviewAction.CORRECT_LABEL,
    }


def test_duplicate_prediction_event_id_is_rejected(db):
    chain = _build_chain(db)
    duplicate = Prediction(
        event_id=chain["prediction"].event_id,
        pump_id=chain["pump"].id,
        sensor_id=chain["sensor"].id,
        session_id=chain["session"].id,
        decision=PredictionDecision.NORMAL,
        data_quality=DataQuality.VALID,
        inferred_at=datetime.now(UTC),
        data_provenance=Provenance.SIMULATED,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.execute(select(func.count(Prediction.id))).scalar_one() == 1


def test_duplicate_sensor_code_is_rejected(db):
    chain = _build_chain(db)
    duplicate = Sensor(
        sensor_code=chain["sensor"].sensor_code,
        sensor_type=SensorType.VIBRATION,
        sampling_rate_hz=2048.0,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.execute(select(func.count(Sensor.id))).scalar_one() == 1


def test_simulated_and_experimental_provenance_remain_distinct(db):
    chain = _build_chain(db)
    experimental = ModelEvaluation(
        model_version_id=chain["model"].id,
        dataset_name="Experimental pump rig (placeholder for later stage)",
        dataset_version="rig-v0-not-acquired",
        data_provenance=Provenance.EXPERIMENTAL,
        evaluation_protocol="grouped hold-out by run",
        split_description="Reserved for measured rig data only",
        sample_count=0,
        evaluated_by="pending",
    )
    db.add(experimental)
    db.commit()

    simulated_rows = (
        db.execute(
            select(ModelEvaluation).where(
                ModelEvaluation.data_provenance == Provenance.SIMULATED
            )
        )
        .scalars()
        .all()
    )
    experimental_rows = (
        db.execute(
            select(ModelEvaluation).where(
                ModelEvaluation.data_provenance == Provenance.EXPERIMENTAL
            )
        )
        .scalars()
        .all()
    )
    assert len(simulated_rows) == 1
    assert len(experimental_rows) == 1
    assert simulated_rows[0].id != experimental_rows[0].id
