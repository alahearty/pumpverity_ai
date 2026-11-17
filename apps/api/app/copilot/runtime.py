from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.session import SessionLocal

SessionFactory = Callable[[], Session]
_session_factory: SessionFactory = SessionLocal


def configure_session_factory(factory: SessionFactory) -> None:
    global _session_factory
    _session_factory = factory


def reset_session_factory() -> None:
    global _session_factory
    _session_factory = SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
