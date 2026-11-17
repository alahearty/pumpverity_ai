from typing import Any

from app.copilot.contracts import CopilotPageContext


def _get(results: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in results:
        if item["name"] == name and item["status"] == "EXECUTED":
            return item["result"]
    return None


def _unavailable(results: list[dict[str, Any]]) -> str | None:
    failures = [item for item in results if item["status"] == "FAILED"]
    if not failures:
        return None
    return "Some authorised tools could not be executed: " + "; ".join(
        f"{item['name']} ({item.get('error') or 'tool error'})" for item in failures
    )


def _provenance(value: Any) -> str:
    return str(value or "unknown")


def _score(value: Any) -> str:
    return f"{float(value):.4f}" if isinstance(value, (int, float)) else "not available"


def summarize(
    *,
    intent: str,
    results: list[dict[str, Any]],
    context: CopilotPageContext,
    pending_tool: dict[str, Any] | None = None,
) -> str:
    alert = _get(results, "pumpverity_get_alert_details")
    prediction = _get(results, "pumpverity_get_latest_prediction")
    status = _get(results, "pumpverity_get_pump_status")
    sensors = _get(results, "pumpverity_get_sensor_health")
    vibration = _get(results, "pumpverity_get_vibration_summary")
    history = _get(results, "pumpverity_get_fault_history")
    model = _get(results, "pumpverity_get_model_evaluation")
    connectivity = _get(results, "pumpverity_get_edge_connectivity")
    overview = _get(results, "pumpverity_get_monitoring_overview")

    lines: list[str] = []
    if pending_tool is not None:
        lines.append(
            f"I prepared **{pending_tool['tool_name']}** with the exact arguments shown below. "
            "Nothing has been changed yet. Confirm the action to execute it through the MCP "
            "server, or reject it."
        )

    if intent == "app_help":
        lines.extend(_screen_help(context.screenName))
    elif intent in {"acknowledge_alert", "mark_reviewed", "add_note", "generate_report"}:
        if pending_tool:
            lines.append(
                "The write will be revalidated against your current role and the target record "
                "before execution. Original predictions are never overwritten."
            )
    elif intent in {"explain_alert", "alert_details"}:
        if alert:
            lines.extend(_alert_lines(alert, prediction, sensors, model))
        elif prediction:
            lines.append(_prediction_line(prediction))
        else:
            lines.append(
                "I could not retrieve that alert. No conclusion is inferred from missing data."
            )
    elif intent == "explain_uncertainty":
        lines.extend(_uncertainty_lines(prediction, history))
    elif intent in {"pump_status", "overview"}:
        if status:
            lines.extend(_status_lines(status))
        elif overview:
            lines.extend(_overview_lines(overview))
        elif prediction:
            lines.append(_prediction_line(prediction))
    elif intent in {"sensor_health", "sensor_health_overview"}:
        if sensors:
            lines.extend(_sensor_lines(sensors))
        elif overview:
            lines.append(
                f"The overview reports {overview.get('sensors_total', 0)} sensors, "
                f"{overview.get('active_alerts', 0)} active alerts and "
                f"{overview.get('invalid_windows', 0)} invalid windows."
            )
    elif intent == "vibration":
        if vibration:
            lines.extend(_vibration_lines(vibration))
    elif intent in {"fault_history", "fault_history_overview"}:
        if history:
            lines.extend(_history_lines(history))
        elif overview:
            lines.append(
                f"The authorised overview reports {overview.get('active_alerts', 0)} active "
                "alerts. No selected pump was available for a pump-specific history query."
            )
    elif intent == "model_evaluation":
        if model:
            lines.extend(_model_lines(model))
    elif intent in {"connectivity", "connectivity_overview"}:
        if connectivity:
            lines.extend(_connectivity_lines(connectivity))
        elif overview:
            lines.append(
                f"Data mode is {overview.get('data_mode')}; the overview does not represent a "
                "physical edge channel."
            )
    elif intent == "missing_pump_context":
        lines.append(
            "Select a pump in the application first. I will not guess which equipment you mean."
        )
    elif intent == "missing_alert_context":
        lines.append(
            "Open a specific alert first. I will not apply a review action to an ambiguous alert."
        )
    else:
        if prediction:
            lines.append(_prediction_line(prediction))
        elif status:
            lines.extend(_status_lines(status))
        elif overview:
            lines.extend(_overview_lines(overview))
        else:
            lines.append(
                "I could not retrieve authorised monitoring evidence for this question. "
                "Please check that a pump is registered and selected."
            )

    failure_text = _unavailable(results)
    if failure_text:
        lines.append(failure_text)

    if context.monitoring_mode == "SIMULATED":
        lines.append(
            "Data provenance: simulated. This is not experimental measurement or industrial "
            "diagnosis."
        )
    return "\n\n".join(line for line in lines if line)


def _alert_lines(alert, prediction, sensors, model) -> list[str]:
    lines = [
        f"Alert {str(alert.get('alert_id'))[:8]} is **{alert.get('category')}** with severity "
        f"**{alert.get('severity')}** and status **{alert.get('status')}**. "
        f"Provenance: {_provenance(alert.get('provenance'))}."
    ]
    # The alert's own retained prediction is the evidence being explained. The pump's latest
    # prediction may be newer (e.g. NORMAL again) and must not be presented as the alert's cause.
    evidence = alert.get("prediction") or prediction or {}
    if evidence:
        lines.append(
            f"The retained prediction decision is **{evidence.get('decision')}** with data "
            f"quality {evidence.get('data_quality')}. Decision score "
            f"{_score(evidence.get('decision_score'))}; uncertainty score "
            f"{_score(evidence.get('uncertainty_score'))}. These are model outputs, not "
            "probabilities of mechanical failure."
        )
        if evidence.get("model_name"):
            lines.append(
                f"Model: {evidence.get('model_name')} v{evidence.get('model_version')} "
                f"({evidence.get('model_runtime')})."
            )
        if evidence.get("explanation"):
            lines.append(f"Recorded explanation: {evidence.get('explanation')}")
    if sensors and sensors.get("sensors"):
        sensor = sensors["sensors"][0]
        lines.append(
            f"Sensor validity is **{sensor.get('sampling_status')}**; latest quality "
            f"{sensor.get('latest_quality')}; last valid reading "
            f"{sensor.get('last_valid_reading_at') or 'not recorded'}."
        )
    if model and model.get("evaluation"):
        evaluation = model["evaluation"]
        lines.append(
            f"Evaluation evidence: {evaluation.get('dataset_name')} "
            f"({evaluation.get('provenance')}), sample count {evaluation.get('sample_count')}, "
            f"verified={evaluation.get('is_verified')}. Synthetic metrics are not real-pump "
            "performance."
        )
    lines.append(
        "What remains unknown: the available record does not independently prove a mechanical "
        "fault. The evidence supports a review of the model decision and sensor context, not an "
        "automatic diagnosis."
    )
    if alert.get("reviews"):
        lines.append(
            f"There are {len(alert['reviews'])} review entries. They are engineer judgements and "
            "are not verified experimental ground truth."
        )
    return lines


def _uncertainty_lines(prediction, history) -> list[str]:
    lines = [
        "PUMPVERITY abstains instead of guessing. When the fault-class score falls inside the "
        "edge policy's uncertainty band (currently 0.35-0.65), the window is marked "
        "**UNCERTAIN** and routed to engineering review rather than forced into NORMAL or FAULT."
    ]
    decision = prediction.get("decision") if prediction else None
    if prediction:
        if decision == "UNCERTAIN":
            lines.append(
                f"The latest decision **is UNCERTAIN**: score "
                f"{_score(prediction.get('decision_score'))}, uncertainty "
                f"{_score(prediction.get('uncertainty_score'))}."
            )
            if prediction.get("explanation"):
                lines.append(f"Recorded explanation: {prediction.get('explanation')}")
        else:
            lines.append(
                f"The latest decision is **{decision}**, not uncertain (score "
                f"{_score(prediction.get('decision_score'))})."
            )
    if history:
        uncertain = [
            event for event in history.get("events", []) if event.get("category") == "UNCERTAIN"
        ]
        if uncertain and decision != "UNCERTAIN":
            latest = uncertain[0]
            lines.append(
                f"The most recent uncertain event is alert {str(latest.get('alert_id'))[:8]} "
                f"({latest.get('status')}). Open it in Alerts & Review to see its retained score "
                "and evidence."
            )
        elif not uncertain and decision != "UNCERTAIN":
            lines.append("No uncertain events are recorded for this pump.")
    if not prediction and not history:
        lines.append("Select a pump to see its latest decision and any uncertain events.")
    return lines


def _prediction_line(prediction) -> str:
    return (
        f"Latest decision: **{prediction.get('decision')}**; data quality "
        f"{prediction.get('data_quality')}; uncertainty "
        f"{_score(prediction.get('uncertainty_score'))}; "
        f"provenance {_provenance(prediction.get('provenance'))}. "
        "The score is a model output, not a failure probability."
    )


def _status_lines(status) -> list[str]:
    condition = status.get("equipment_condition") or "not available"
    return [
        f"**{status.get('pump_code')}** is {status.get('pump_status')} at "
        f"{status.get('location')}. Current condition: **{condition}** "
        f"(available={status.get('condition_available')}); latest data quality "
        f"{status.get('data_quality')}; mode {status.get('data_mode')}; provenance "
        f"{_provenance(status.get('data_provenance'))}."
    ]


def _overview_lines(overview) -> list[str]:
    return [
        f"The authorised overview shows {overview.get('pumps_total')} pumps, "
        f"{overview.get('sensors_total')} sensors, {overview.get('active_alerts')} active alerts "
        f"and condition **{overview.get('equipment_condition') or 'not inferred'}** "
        f"(available={overview.get('condition_available')}). Data mode: "
        f"{overview.get('data_mode')}; provenance: "
        f"{_provenance(overview.get('latest_evaluation_provenance'))}."
    ]


def _sensor_lines(sensors) -> list[str]:
    lines = []
    for sensor in sensors.get("sensors", []):
        lines.append(
            f"{sensor.get('sensor_code')}: status **{sensor.get('sampling_status')}**, latest "
            f"quality {sensor.get('latest_quality')}, latest RMS "
            f"{_score(sensor.get('latest_rms_g'))} g, invalid windows "
            f"{sensor.get('invalid_windows')}, gaps {sensor.get('missing_window_gaps')}. "
            f"Provenance: {_provenance(sensor.get('provenance'))}. Connection state: "
            f"{sensor.get('connection_state')}."
        )
    if not lines:
        lines.append("No sensor diagnostics are available for this pump.")
    return lines


def _vibration_lines(vibration) -> list[str]:
    return [
        f"Vibration summary for **{vibration.get('sensor_code')}** over "
        f"{vibration.get('window_count')} persisted windows: latest RMS "
        f"{_score(vibration.get('latest_rms_g'))} g, mean RMS "
        f"{_score(vibration.get('mean_rms_g'))} g, range "
        f"{_score(vibration.get('min_rms_g'))}-{_score(vibration.get('max_rms_g'))} g, latest "
        f"peak {_score(vibration.get('latest_peak_g'))} g. Valid/invalid windows: "
        f"{vibration.get('valid_window_count')}/{vibration.get('invalid_window_count')}. "
        f"Provenance: {_provenance(vibration.get('provenance'))}."
    ]


def _history_lines(history) -> list[str]:
    events = history.get("events", [])
    if not events:
        return ["No alert-backed fault, uncertain or sensor-invalid events were found."]
    summary = "; ".join(
        f"{event.get('category')} ({event.get('status')}, {str(event.get('alert_id'))[:8]})"
        for event in events[:5]
    )
    return [
        f"Found {history.get('total_events')} alert-backed events for "
        f"{history.get('pump_code')}. Most recent: {summary}. "
        "Open Alerts & Review for full evidence."
    ]


def _model_lines(model) -> list[str]:
    if not model.get("available"):
        return [str(model.get("message") or "No model evaluation is available.")]
    lines = [
        f"Active model **{model.get('name')}** v{model.get('version')} "
        f"({model.get('runtime')}), status {model.get('status')}."
    ]
    evaluation = model.get("evaluation")
    if evaluation:
        lines.append(
            f"Latest evaluation: provenance {evaluation.get('provenance')}, "
            f"balanced accuracy {_score(evaluation.get('balanced_accuracy'))}, macro-F1 "
            f"{_score(evaluation.get('macro_f1'))}, samples {evaluation.get('sample_count')}, "
            f"verified={evaluation.get('is_verified')}. These metrics are research evidence and "
            "are not real-pump performance claims."
        )
    return lines


def _connectivity_lines(connectivity) -> list[str]:
    return [
        f"Edge connectivity is **{connectivity.get('edge_connectivity')}**; data mode "
        f"{connectivity.get('data_mode')}; buffering "
        f"{connectivity.get('buffering_state') or 'not active'}. Last window "
        f"{connectivity.get('last_window_at') or 'not recorded'}. "
        f"{connectivity.get('api_note')}"
    ]


def _screen_help(screen_name: str) -> list[str]:
    guidance = {
        "Dashboard": (
            "Use the dashboard for aggregate monitoring state. Live Monitoring holds the "
            "pump/sensor signal view, AI Analysis holds retained predictions, and Alerts & Review "
            "holds the human review workflow."
        ),
        "Pump Registry": (
            "Register the pump in Pumps, including its initial vibration sensor. Duplicate pump "
            "or sensor codes are rejected. Registering equipment does not create measurements."
        ),
        "Live Monitoring": (
            "Select a pump and sensor to inspect persisted windows, signal quality and the "
            "current model decision. The stream is an API update channel, not proof of physical "
            "edge connectivity."
        ),
        "AI Analysis": (
            "AI Analysis shows the retained model decision, uncertainty and explanation. The "
            "decision score is not a probability of mechanical failure, and SENSOR_INVALID "
            "records have no condition decision."
        ),
        "Alerts & Review": (
            "Open an alert to inspect its original prediction. Acknowledge it, then record an "
            "engineering review. Reviews are appended and do not rewrite the prediction or become "
            "verified experimental ground truth."
        ),
        "Historical Trends": (
            "Historical Trends shows persisted window history and alert overlays linked by signal "
            "window. Use the pump/sensor selectors and window range to inspect evidence."
        ),
        "Reports & Exports": (
            "Reports are generated through an approved Copilot write action. Each report records "
            "its requester, generated file hash and simulated-data disclosure."
        ),
        "Model Registry": (
            "Model Registry reviews versioned artefacts, synthetic evaluation evidence and "
            "activation state. Only validated supported artefacts can be activated."
        ),
        "Sensor Health": (
            "Sensor Health explains validity, freshness, missing-window gaps and validation "
            "issues. Sensor invalidity is not an equipment fault."
        ),
        "System Settings": (
            "Runtime settings information is read-only in this build. Alert auto-creation settings "
            "exist in the database, but editable configuration is a later stage."
        ),
        "User Management": (
            "Roles are Administrator, Engineer, Researcher and Reviewer. Authorisation is enforced "
            "by the backend. I will not reveal credentials, password hashes or private tokens."
        ),
    }
    return [
        guidance.get(
            screen_name,
            "Ask about the selected pump, alert, sensor or model evidence.",
        )
    ]
