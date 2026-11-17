from tests.conftest import auth_headers


def test_engineer_cannot_list_users(client):
    response = client.get(
        "/api/v1/users", headers=auth_headers(client, "engineer@petrosense.local")
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_anonymous_cannot_list_users(client):
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_administrator_can_list_users(client):
    response = client.get(
        "/api/v1/users", headers=auth_headers(client, "admin@petrosense.local")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert {item["role"] for item in body["items"]} == {
        "ADMINISTRATOR",
        "ENGINEER",
        "RESEARCHER",
        "REVIEWER",
    }
    assert "password_hash" not in response.text


def test_user_list_filters_and_pagination(client):
    headers = auth_headers(client, "admin")
    response = client.get(
        "/api/v1/users",
        params={"role": "ENGINEER", "q": "chinedu", "page": 1, "page_size": 10},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "engineer"


def test_roles_endpoint_requires_authentication(client):
    assert client.get("/api/v1/auth/roles").status_code == 401
    response = client.get("/api/v1/auth/roles", headers=auth_headers(client, "admin"))
    assert response.status_code == 200
    assert len(response.json()) == 4
