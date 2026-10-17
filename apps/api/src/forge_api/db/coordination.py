"""Transaction-scoped user coordination shared by auth rotation and CAD dispatch."""

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session


def user_lock(db: Session, user_id: str) -> None:
    # PostgreSQL lock order: user advisory -> session -> grant -> operational row.
    # SQLite is test-only; conditional claims/unique fences still enforce single use.
    if db.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(
            hashlib.sha256(("forge.user.v1:" + user_id).encode()).digest()[:8],
            "big",
            signed=True,
        )
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
