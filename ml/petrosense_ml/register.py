import os
from typing import Any

import httpx


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post(
        "/auth/login", json={"identifier": email, "password": password}
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.status_code} {response.text}")
    return response.json()["access_token"]


def register_manifest(
    manifest: dict[str, Any],
    *,
    api_base: str,
    email: str,
    password: str,
) -> list[dict[str, Any]]:
    results = []
    with httpx.Client(base_url=api_base, timeout=30.0) as client:
        token = _login(client, email, password)
        headers = _headers(token)
        for entry in manifest["models"]:
            metadata = entry["metadata"]
            response = client.get(
                "/models",
                params={"q": metadata["model_code"], "page_size": 100},
                headers=headers,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Model lookup failed: {response.text}")
            existing = next(
                (
                    model
                    for model in response.json()["items"]
                    if model["model_code"] == metadata["model_code"]
                    and model["version"] == metadata["version"]
                ),
                None,
            )
            if existing is None:
                created = client.post("/models", json=metadata, headers=headers)
                if created.status_code != 201:
                    raise RuntimeError(
                        f"Model registration failed: {created.status_code} {created.text}"
                    )
                model = created.json()
            else:
                model = existing

            detail = client.get(f"/models/{model['id']}", headers=headers)
            if detail.status_code != 200:
                raise RuntimeError(f"Model detail failed: {detail.text}")
            detail_body = detail.json()
            if not detail_body["evaluations"]:
                evaluated = client.post(
                    f"/models/{model['id']}/evaluations",
                    json=entry["evaluation"],
                    headers=headers,
                )
                if evaluated.status_code != 201:
                    raise RuntimeError(
                        f"Evaluation registration failed: "
                        f"{evaluated.status_code} {evaluated.text}"
                    )
                detail_body = client.get(
                    f"/models/{model['id']}", headers=headers
                ).json()

            if detail_body["status"] in {"REGISTERED", "VALIDATED"}:
                validated = client.post(
                    f"/models/{model['id']}/validate", headers=headers
                )
                if validated.status_code != 200:
                    raise RuntimeError(
                        f"Validation failed: {validated.status_code} {validated.text}"
                    )
                detail_body = validated.json()

            if entry.get("activate") and detail_body["status"] != "ACTIVE":
                activated = client.post(
                    f"/models/{model['id']}/activate", headers=headers
                )
                if activated.status_code != 200:
                    raise RuntimeError(
                        f"Activation failed: {activated.status_code} {activated.text}"
                    )
                detail_body = activated.json()

            results.append(
                {
                    "model_code": detail_body["model_code"],
                    "version": detail_body["version"],
                    "status": detail_body["status"],
                    "artifact_path": detail_body["artifact_path"],
                    "artifact_sha256": detail_body["artifact_sha256"],
                }
            )
    return results


def password_from_environment() -> str:
    password = os.environ.get("PETROSENSE_ML_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "Set PETROSENSE_ML_PASSWORD to the researcher/admin password before registering."
        )
    return password
