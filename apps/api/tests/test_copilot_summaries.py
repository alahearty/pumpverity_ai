from app.copilot.contracts import CopilotPageContext
from app.copilot.summarizer import summarize
from tests.test_copilot import _setup_fault_context


def _executed(name, result):
    return {"name": name, "status": "EXECUTED", "result": result}


def test_alert_explanation_uses_the_alerts_retained_prediction_not_the_latest():
    alert = {
        "alert_id": "8e7331f8-0000-0000-0000-000000000000",
        "category": "UNCERTAIN",
        "severity": "MEDIUM",
        "status": "OPEN",
        "provenance": "SIMULATED",
        "prediction": {
            "decision": "UNCERTAIN",
            "data_quality": "VALID",
            "decision_score": 0.4785,
            "uncertainty_score": 0.4785,
        },
    }
    newer_latest = {"decision": "NORMAL", "data_quality": "VALID", "decision_score": 0.0058}
    text = summarize(
        intent="explain_alert",
        results=[
            _executed("pumpverity_get_alert_details", alert),
            _executed("pumpverity_get_latest_prediction", newer_latest),
        ],
        context=CopilotPageContext(),
    )
    assert "retained prediction decision is **UNCERTAIN**" in text
    assert "0.4785" in text
    assert "0.0058" not in text


def test_uncertainty_question_without_alert_explains_policy_and_latest_decision():
    text = summarize(
        intent="explain_uncertainty",
        results=[
            _executed(
                "pumpverity_get_latest_prediction",
                {"decision": "NORMAL", "decision_score": 0.006},
            ),
            _executed(
                "pumpverity_get_fault_history",
                {
                    "events": [
                        {"alert_id": "abcd1234-ffff", "category": "UNCERTAIN", "status": "OPEN"}
                    ]
                },
            ),
        ],
        context=CopilotPageContext(),
    )
    assert "abstains instead of guessing" in text
    assert "latest decision is **NORMAL**, not uncertain" in text
    assert "alert abcd1234" in text


def test_copilot_routes_uncertainty_question_with_pump_context(client):
    engineer, _pump, _sensor, _alert, context = _setup_fault_context(client)
    context = {key: value for key, value in context.items() if key != "selectedAlertId"}
    response = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Why was the latest decision uncertain?", "context": context},
        headers=engineer,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    tool_names = {run["toolName"] for run in body["toolRuns"]}
    assert tool_names == {"pumpverity_get_latest_prediction", "pumpverity_get_fault_history"}
    assert "abstains instead of guessing" in body["assistantMessage"]["content"]
