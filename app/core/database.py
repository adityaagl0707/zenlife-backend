"""
DEPRECATED — kept as a thin shim for backward compatibility.

The database is now MongoDB. All persistence flows through app/core/mongo.py.
This file remains so legacy imports (`from ..core.database import get_db`)
still resolve. The yielded value is the pymongo Database for any callers that
still want it; most route code now imports `mongo` directly and ignores `db`.
"""
from . import mongo


def get_db():
    """Compat shim. Yields the pymongo Database — but most routes just take
    the dependency to satisfy the type and never use it."""
    yield mongo.db


# Keep these as no-op placeholders so any legacy imports don't crash at import time.
class _NoopBase:
    metadata = type("Metadata", (), {"create_all": staticmethod(lambda **kw: None)})()


Base = _NoopBase()
engine = None
SessionLocal = None
