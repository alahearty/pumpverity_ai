# ruff: noqa: E402
import os
import tempfile
from pathlib import Path

_test_database_path = (
    Path(tempfile.gettempdir()) / f"pumpverity-api-tests-{os.getpid()}.db"
)
_test_database_path.unlink(missing_ok=True)

os.environ["PETROSENSE_ENVIRONMENT"] = "test"
os.environ["PETROSENSE_SECRET_KEY"] = "test-secret-key-with-more-than-32-characters-0001"
os.environ["PETROSENSE_DATABASE_URL"] = (
    f"sqlite:///{_test_database_path.as_posix()}"
)
os.environ["PETROSENSE_DEMO_PASSWORD"] = "TestPass!234"
os.environ["PETROSENSE_MCP_TRANSPORT"] = "memory"

import pytest
from app.copilot.runtime import configure_session_factory
from app.core import security
from app.db.base import Base
from app.db.seed import seed_demo_users
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

security._password_hash = PasswordHash(
    (Argon2Hasher(time_cost=1, memory_cost=8192, parallelism=1),)
)

TEST_PASSWORD = "TestPass!234"

test_engine = create_engine(
    f"sqlite:///{_test_database_path.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
)

configure_session_factory(TestingSessionLocal)


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def engine():
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()
    _test_database_path.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        Path(f"{_test_database_path}{suffix}").unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def seeded_database(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    configure_session_factory(TestingSessionLocal)
    with TestingSessionLocal() as session:
        seed_demo_users(session, TEST_PASSWORD)
    yield


@pytest.fixture()
def db(seeded_database) -> Session:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(seeded_database):
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(
    client: TestClient,
    identifier: str = "admin@petrosense.local",
    password: str = TEST_PASSWORD,
):
    return client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )


def auth_headers(client: TestClient, identifier: str, password: str = TEST_PASSWORD):
    response = login(client, identifier, password)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}



