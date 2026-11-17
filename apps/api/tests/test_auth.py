from app.db.models import AuditLog, User
from sqlalchemy import select
from tests.conftest import TEST_PASSWORD, auth_headers, login


def test_login_success_sets_secure_session_cookie(client):
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["role"] == "ADMINISTRATOR"
    assert body["user"]["email"] == "admin@petrosense.local"
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "path=/api/v1/auth" in set_cookie
    assert "samesite=lax" in set_cookie
    assert TEST_PASSWORD not in response.text


def test_login_by_username(client):
    response = login(client, identifier="engineer")
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "engineer"
    assert response.json()["user"]["role"] == "ENGINEER"


def test_invalid_credentials_are_generic_and_audited(client, db):
    response = login(client, password="WrongPass!234")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "Invalid email/username or password" in response.json()["error"]["message"]

    db.expire_all()
    entries = (
        db.execute(select(AuditLog).where(AuditLog.action == "AUTH_LOGIN_FAILED"))
        .scalars()
        .all()
    )
    assert len(entries) == 1
    assert entries[0].actor_user_id is None
    assert entries[0].actor_label == "admin@petrosense.local"
    assert entries[0].request_id


def test_successful_login_and_logout_are_audited(client, db):
    response = login(client)
    token = response.json()["access_token"]
    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})

    db.expire_all()
    actions = db.execute(select(AuditLog.action).order_by(AuditLog.id)).scalars().all()
    assert "AUTH_LOGIN_SUCCEEDED" in actions
    assert "AUTH_LOGOUT" in actions


def test_unknown_account_returns_same_error(client):
    known = login(client, password="WrongPass!234")
    unknown = login(client, identifier="nobody@example.com", password="WrongPass!234")
    assert unknown.status_code == known.status_code == 401
    assert unknown.json()["error"]["code"] == known.json()["error"]["code"]
    assert unknown.json()["error"]["message"] == known.json()["error"]["message"]


def test_login_does_not_echo_password_on_validation_error(client):
    secret = "p@ss"
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": secret},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert secret not in response.text


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_returns_authenticated_account(client):
    response = client.get("/api/v1/auth/me", headers=auth_headers(client, "researcher"))
    assert response.status_code == 200
    assert response.json()["role"] == "RESEARCHER"


def test_refresh_restores_session_and_rotates_cookie(client):
    login_response = login(client)
    first_cookie = login_response.headers["set-cookie"]

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.headers["set-cookie"] != first_cookie

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_response.json()['access_token']}"},
    )
    assert me_response.status_code == 200


def test_refresh_without_cookie_fails(client):
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_refresh_token_cannot_be_used_as_access_token(client):
    login_response = login(client)
    refresh_token = (
        login_response.headers["set-cookie"].split("petrosense_refresh=")[1].split(";")[0]
    )
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 401


def test_logout_clears_cookie_and_prevents_refresh(client):
    login(client)
    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert "petrosense_refresh=" in logout_response.headers["set-cookie"]
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_inactive_user_cannot_login(client, db):
    user = db.execute(select(User).where(User.username == "reviewer")).scalar_one()
    user.is_active = False
    db.commit()

    response = login(client, identifier="reviewer")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_token_version_revocation_invalidates_existing_access_token(client, db):
    headers = auth_headers(client, "engineer")
    user = db.execute(select(User).where(User.username == "engineer")).scalar_one()
    user.token_version += 1
    db.commit()

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
