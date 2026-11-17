import http.client
import json
from typing import Any
from urllib import error, parse, request


class EdgeApiError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class ApiClient:
    def __init__(self, base_url: str, timeout_s: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.access_token: str | None = None

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout_s) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            code = None
            message = f"API request failed with status {exc.code}."
            try:
                parsed = json.loads(body)
                error_body = parsed.get("error", {})
                code = error_body.get("code")
                message = error_body.get("message", message)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise EdgeApiError(message, status=exc.code, code=code) from exc
        except error.URLError as exc:
            raise EdgeApiError(
                f"Monitoring API is unreachable at {self.base_url}: {exc.reason}"
            ) from exc
        except (OSError, http.client.HTTPException) as exc:
            # Connection reset/aborted mid-response, timeouts and malformed status lines.
            raise EdgeApiError(
                f"Connection to the monitoring API at {self.base_url} failed: {exc}"
            ) from exc

    def login(self, identifier: str, password: str) -> dict[str, Any]:
        session = self._request(
            "POST",
            "/auth/login",
            {"identifier": identifier, "password": password},
            authenticated=False,
        )
        self.access_token = session["access_token"]
        return session

    def find_pump(self, pump_code: str) -> dict[str, Any] | None:
        query = parse.urlencode({"q": pump_code, "page_size": 100})
        page = self._request("GET", f"/pumps?{query}")
        for pump in page["items"]:
            if pump["pump_code"].upper() == pump_code.strip().upper():
                return pump
        return None

    def find_sensor(self, sensor_code: str, pump_id: str) -> dict[str, Any] | None:
        query = parse.urlencode({"q": sensor_code, "pump_id": pump_id, "page_size": 100})
        page = self._request("GET", f"/sensors?{query}")
        for sensor in page["items"]:
            if sensor["sensor_code"].upper() == sensor_code.strip().upper():
                return sensor
        return None

    def get_active_model(self) -> dict[str, Any] | None:
        return self._request("GET", "/models/active")

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/acquisition-sessions", payload)

    def create_prediction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/predictions", payload)

    def ingest_window(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST", f"/acquisition-sessions/{session_id}/windows", payload
        )

    def stop_session(self, session_id: str, terminal_status: str = "COMPLETED") -> dict[str, Any]:
        return self._request(
            "POST",
            f"/acquisition-sessions/{session_id}/stop",
            {"status": terminal_status},
        )

    def list_sessions(self, *, pump_id: str | None = None) -> dict[str, Any]:
        query = parse.urlencode({"page_size": 25, **({"pump_id": pump_id} if pump_id else {})})
        return self._request("GET", f"/acquisition-sessions?{query}")
