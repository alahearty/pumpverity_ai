import argparse
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import ConfigurationSetting, OperatingRegime, Role, User
from app.db.session import SessionLocal
from app.domain.enums import OperatingRegimeCode, RoleName

ROLE_SEEDS = [
    (RoleName.ADMINISTRATOR, "Full system administration and security configuration"),
    (RoleName.ENGINEER, "Pump registration, monitoring, alerts and engineering review"),
    (RoleName.RESEARCHER, "Experiments, model registration and evaluation"),
    (RoleName.REVIEWER, "Alert acknowledgement and engineering review"),
]

REGIME_SEEDS = [
    (OperatingRegimeCode.STEADY_STATE, "Steady state", "Nominal, thermally stable operation"),
    (OperatingRegimeCode.STARTUP, "Startup", "Controlled acceleration to operating speed"),
    (OperatingRegimeCode.SHUTDOWN, "Shutdown", "Controlled deceleration and stop"),
    (OperatingRegimeCode.VARIABLE_LOAD, "Variable load", "Operating point intentionally varied"),
    (OperatingRegimeCode.UNKNOWN, "Unknown", "Regime not recorded or not identifiable"),
]

USER_SEEDS = [
    ("admin@petrosense.local", "admin", "Amina Bello", RoleName.ADMINISTRATOR),
    ("engineer@petrosense.local", "engineer", "Chinedu Okafor", RoleName.ENGINEER),
    ("researcher@petrosense.local", "researcher", "Fatima Yusuf", RoleName.RESEARCHER),
    ("reviewer@petrosense.local", "reviewer", "Tunde Adeyemi", RoleName.REVIEWER),
]

SETTING_SEEDS: list[tuple[str, Any, str, str]] = [
    ("sampling.default_rate_hz", 2048, "sampling", "Default vibration sampling rate in hertz"),
    ("signal.window_size_samples", 2048, "signal", "Samples per inference window"),
    ("signal.overlap_fraction", 0.5, "signal", "Fractional overlap between windows"),
    ("decision.fault_threshold", 0.65, "decision", "Score threshold for a fault decision"),
    (
        "decision.uncertainty_threshold",
        0.35,
        "decision",
        "Minimum confidence margin required for a non-abstained decision",
    ),
    (
        "alerts.auto_create_for_fault",
        True,
        "alerts",
        "Create a reviewable alert when the decision is FAULT",
    ),
    (
        "alerts.auto_create_for_uncertain",
        True,
        "alerts",
        "Create a reviewable alert when the decision is UNCERTAIN",
    ),
    (
        "alerts.auto_create_for_sensor_invalid",
        True,
        "alerts",
        "Create a sensor-health alert when validation fails",
    ),
    ("storage.retention_days", 30, "storage", "Retention period for raw readings and waveforms"),
    ("sync.batch_size", 50, "sync", "Maximum events sent in one synchronisation batch"),
    ("sync.max_retry_attempts", 10, "sync", "Maximum retry attempts before dead-letter"),
    ("device.identity", "edge-lab-01", "device", "Local edge device identifier"),
    ("model.active_version_id", None, "model", "Currently active model version identifier"),
]


def seed_reference_data(db: Session) -> None:
    for name, description in ROLE_SEEDS:
        existing = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if existing is None:
            db.add(Role(name=name, description=description))
        elif not existing.description:
            existing.description = description

    for code, name, description in REGIME_SEEDS:
        existing = db.execute(
            select(OperatingRegime).where(OperatingRegime.code == code)
        ).scalar_one_or_none()
        if existing is None:
            db.add(OperatingRegime(code=code, name=name, description=description))

    for key, value, category, description in SETTING_SEEDS:
        existing = db.execute(
            select(ConfigurationSetting).where(ConfigurationSetting.key == key)
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                ConfigurationSetting(
                    key=key,
                    value=value,
                    category=category,
                    description=description,
                )
            )

    db.commit()


def seed_demo_users(db: Session, password: str, *, reset_passwords: bool = False) -> list[str]:
    seed_reference_data(db)
    roles = {role.name: role for role in db.execute(select(Role)).scalars().all()}
    created: list[str] = []

    for email, username, full_name, role_name in USER_SEEDS:
        existing = db.execute(
            select(User).where((User.email == email) | (User.username == username))
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                User(
                    email=email,
                    username=username,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role_id=roles[role_name].id,
                    is_active=True,
                )
            )
            created.append(email)
        else:
            existing.role_id = roles[role_name].id
            existing.full_name = full_name
            existing.is_active = True
            if reset_passwords:
                existing.password_hash = hash_password(password)
                existing.must_change_password = False
                existing.token_version += 1
    db.commit()
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed PUMPVERITY AI reference data and demo users")
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="Reset the four local demo accounts to PETROSENSE_DEMO_PASSWORD",
    )
    args = parser.parse_args()

    configured = get_settings().demo_password
    password = configured.get_secret_value() if configured is not None else ""
    if len(password) < 8:
        raise SystemExit(
            "PETROSENSE_DEMO_PASSWORD must be set to at least 8 characters before seeding."
        )

    with SessionLocal() as db:
        created = seed_demo_users(db, password, reset_passwords=args.reset_passwords)

    print("Reference data seeded.")
    if created:
        print("Created demo accounts: " + ", ".join(created))
    else:
        print("Demo accounts already present; passwords were left unchanged.")
    print("Local demo accounts are for development only.")


if __name__ == "__main__":
    main()
