"""
MongoDB connection and data-access helpers.

Replaces SQLAlchemy/SQLite. Each entity is a collection. We maintain integer
auto-increment IDs via a counters collection so the existing API contract
(routes like /reports/1) keeps working unchanged.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database

# Load .env (idempotent — main.py also calls this; we call here in case
# anything imports mongo before main.py has loaded the env).
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=False)

# ── Connection ────────────────────────────────────────────────────────────────

_MONGO_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
if not _MONGO_URI:
    raise RuntimeError("MONGODB_URI env var not set")

_client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=10_000)
_default_db = _client.get_default_database()
db: Database = _default_db if _default_db is not None else _client["zenlife"]


# ── Auto-increment integer IDs (preserve SQLite IDs via counters collection) ─

_counters: Collection = db["_counters"]


def next_id(name: str) -> int:
    """Atomically increment and return the next integer ID for a collection."""
    res = _counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,  # ReturnDocument.AFTER
    )
    return int(res["seq"])


# ── Collections ──────────────────────────────────────────────────────────────

users:               Collection = db["users"]
otp_sessions:        Collection = db["otp_sessions"]
orders:              Collection = db["orders"]
reports:             Collection = db["reports"]
organ_scores:        Collection = db["organ_scores"]
findings:            Collection = db["findings"]
health_priorities:   Collection = db["health_priorities"]
consultation_notes:  Collection = db["consultation_notes"]
chat_messages:       Collection = db["chat_messages"]
report_sections:     Collection = db["report_sections"]
body_ages:           Collection = db["body_ages"]


# ── Indexes (idempotent — safe to call on every startup) ─────────────────────

def ensure_indexes() -> None:
    users.create_index("phone", unique=True)
    users.create_index("id", unique=True)
    otp_sessions.create_index("phone")
    orders.create_index("id", unique=True)
    orders.create_index("booking_id", unique=True)
    orders.create_index("user_id")
    reports.create_index("id", unique=True)
    reports.create_index("order_id", unique=True)
    organ_scores.create_index("report_id")
    findings.create_index("report_id")
    health_priorities.create_index("report_id")
    consultation_notes.create_index("report_id")
    chat_messages.create_index("report_id")
    report_sections.create_index([("report_id", ASCENDING), ("section_type", ASCENDING)], unique=True)
    body_ages.create_index("report_id", unique=True)


# ── Doc — dict with attribute access (so code can do user.phone) ────────────

class Doc(dict):
    """A dict you can also access via attributes. user.phone <==> user["phone"]."""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            return None  # mirror SQLAlchemy nullable columns behavior
    def __setattr__(self, k, v):
        self[k] = v


def doc(d: Optional[dict]) -> Optional["Doc"]:
    """Wrap a dict as a Doc, or return None."""
    if d is None:
        return None
    if isinstance(d, Doc):
        return d
    return Doc(d)


# ── Helpers ──────────────────────────────────────────────────────────────────

def now() -> datetime:
    return datetime.utcnow()


def insert(coll: Collection, doc: dict, *, id_seq: str) -> dict:
    """Insert with auto-incremented integer 'id' field. Returns inserted doc."""
    if "id" not in doc:
        doc["id"] = next_id(id_seq)
    coll.insert_one(doc)
    return doc


def to_response(doc: Optional[dict]) -> Optional[dict]:
    """Strip MongoDB internal _id from a single doc for safe API output."""
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


def list_response(docs) -> list:
    return [to_response(d) for d in docs]


# ── Object-style accessors (so route code can do mdb.User.find_one(...)) ─────

class _Coll:
    """Wrapper so existing code can write mdb.User.objects(...)."""
    def __init__(self, c: Collection, id_seq: str):
        self._c = c
        self._seq = id_seq

    def find_one(self, query=None):
        return doc(self._c.find_one(query or {}))

    def find(self, query=None, **kw):
        return [doc(d) for d in self._c.find(query or {}, **kw)]

    def insert(self, doc: dict) -> dict:
        return insert(self._c, doc, id_seq=self._seq)

    def update_one(self, query: dict, update: dict) -> int:
        r = self._c.update_one(query, update)
        return r.modified_count

    def delete_one(self, query: dict) -> int:
        r = self._c.delete_one(query)
        return r.deleted_count

    def delete_many(self, query: dict) -> int:
        r = self._c.delete_many(query)
        return r.deleted_count

    def count(self, query=None) -> int:
        return self._c.count_documents(query or {})

    @property
    def coll(self) -> Collection:
        return self._c


User              = _Coll(users,              "users")
OTPSession        = _Coll(otp_sessions,       "otp_sessions")
Order             = _Coll(orders,             "orders")
Report            = _Coll(reports,            "reports")
OrganScore        = _Coll(organ_scores,       "organ_scores")
Finding           = _Coll(findings,           "findings")
HealthPriority    = _Coll(health_priorities,  "health_priorities")
ConsultationNote  = _Coll(consultation_notes, "consultation_notes")
ChatMessage       = _Coll(chat_messages,      "chat_messages")
ReportSection     = _Coll(report_sections,    "report_sections")
BodyAgeDoc        = _Coll(body_ages,          "body_ages")
