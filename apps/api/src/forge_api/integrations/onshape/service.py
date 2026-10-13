"""Request-local snapshots; no CAD cache, persistence, polling or automatic retries."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import Lock
from time import monotonic

from forge_api.auth.provider import ProviderError
from forge_api.auth.runtime import AuthRuntime
from forge_api.db.models import OnshapeAuthorization

from .client import OnshapeReadClient, ReadError
from .contracts import WorkspaceReference
from .models import (
    FeatureSummaryList,
    MassSummary,
    ProofSection,
    ProviderDocument,
    SectionState,
    Snapshot,
    SnapshotProof,
)


def read_permission(auth: AuthRuntime, user_id: str) -> bool | None:
    with auth.sessions() as db:
        grant = db.get(OnshapeAuthorization, user_id)
        scope = grant.granted_scope if grant else None
    # Preserve Phase 2's uninterpreted bitmask. Never guess its bits or missing scope.
    if not scope:
        return None
    scopes = set(scope.split())
    if "OAuth2Read" in scopes:
        return True
    known = {
        "OAuth2ReadPII",
        "OAuth2Write",
        "OAuth2Delete",
        "OAuth2Share",
        "OAuth2Purchase",
    }
    return False if scopes and scopes <= known else None


class ReadGate:
    """Bounded per-process/per-user admission; stores no document identifiers/data."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._active: set[str] = set()
        self._until: dict[str, float] = {}

    @contextmanager
    def enter(self, user_id: str) -> Iterator[None]:
        with self._lock:
            self._until = {k: v for k, v in self._until.items() if v > monotonic()}
            if user_id in self._active:
                raise ReadError("unavailable", "request_in_progress", 5)
            remaining = self._until.get(user_id, 0) - monotonic()
            if (
                remaining > 0
                or len(self._active) >= 32
                or len(self._until) + len(self._active) >= 1024
            ):
                raise ReadError(
                    "rate_limited",
                    "rate_limited",
                    max(1, min(86400, int(remaining) + 1)),
                )
            self._active.add(user_id)
        try:
            yield
        finally:
            with self._lock:
                self._active.discard(user_id)
                self._until[user_id] = max(self._until.get(user_id, 0), monotonic() + 5)

    def defer(self, user_id: str, seconds: int) -> None:
        with self._lock:
            self._until[user_id] = max(
                self._until.get(user_id, 0), monotonic() + seconds
            )


def capture(
    auth: AuthRuntime,
    client: OnshapeReadClient,
    reference: WorkspaceReference,
    user_id: str,
    correlation: str,
    gate: ReadGate,
) -> Snapshot:
    sections: dict[str, SectionState] = {}
    documents: dict[str, ProviderDocument[object]] = {}
    stopped: SectionState | None = None
    for name, read in (
        ("features", client.features),
        ("parts", client.parts),
        ("bodies", client.bodies),
        ("mass", client.mass),
    ):
        if stopped:
            sections[name] = stopped
            continue
        try:
            # Checks ownership, stack, generation and refresh on each section.
            token = auth.tokens.get_valid_onshape_access_token(user_id)
            permission = read_permission(auth, user_id)
            if permission is False:
                raise ReadError("unauthorized", "read_permission_required")
            documents[name] = read(reference, token, correlation)
            sections[name] = SectionState(status="success", code="ok")
        except ProviderError as error:
            stopped = SectionState(
                status="unauthorized" if error.revoked else "provider_failure",
                code="connection_required" if error.revoked else "provider_unavailable",
            )
            sections[name] = stopped
        except ReadError as error:
            state = error.state
            if (
                state.status == "forbidden"
                and read_permission(auth, user_id) is not True
            ):
                state = SectionState(
                    status="forbidden", code="permission_or_access_required"
                )
            sections[name] = state
            if state.status in ("unauthorized", "rate_limited", "forbidden"):
                stopped = state
            if state.status == "unauthorized" and state.code == "connection_required":
                # No automatic 401 replay. The next explicit action may refresh once.
                auth.tokens.forget(user_id)
            if state.status == "rate_limited":
                gate.defer(user_id, state.retry_after_seconds or 60)
    versions = {v for document in documents.values() for v in document.microversions}
    feature_data = documents.get("features")
    skew = (
        feature_data is not None
        and isinstance(feature_data.normalized, FeatureSummaryList)
        and feature_data.normalized.microversion_skew is True
    )
    return Snapshot(
        context=reference,
        sections=sections,
        documents=documents,
        captured_at=datetime.now(UTC).isoformat(),
        consistency="mismatch" if len(versions) > 1 or skew else "unverified",
    )


def proof(snapshot: Snapshot, correlation: str) -> SnapshotProof:
    sections: dict[str, ProofSection] = {}
    has_mass: bool | None = None
    for name, state in snapshot.sections.items():
        data = (
            snapshot.documents[name].normalized if name in snapshot.documents else None
        )
        count: int | None = None
        if isinstance(data, FeatureSummaryList):
            # A filtered/incomplete provider list is not the Part Studio feature count.
            count = len(data.items) if data.complete is True else None
        elif isinstance(data, list):
            count = len(data)
            if (
                name == "mass"
                and data
                and all(isinstance(item, MassSummary) for item in data)
            ):
                flags = [
                    item.has_mass
                    if item.has_mass is False
                    or (item.mass is not None and item.mass_missing_count in (None, 0))
                    else None
                    for item in data
                ]
                has_mass = None if None in flags else all(flags)
        sections[name] = ProofSection(**state.model_dump(), count=count)
    return SnapshotProof(
        request_id=correlation,
        captured_at=snapshot.captured_at,
        consistency=snapshot.consistency,
        features=sections["features"],
        parts=sections["parts"],
        bodies=sections["bodies"],
        mass=sections["mass"],
        has_mass=has_mass,
    )


def failed_proof(state: SectionState, correlation: str) -> SnapshotProof:
    section = ProofSection(**state.model_dump())
    return SnapshotProof(
        request_id=correlation,
        captured_at=datetime.now(UTC).isoformat(),
        consistency="unverified",
        features=section,
        parts=section,
        bodies=section,
        mass=section,
        has_mass=None,
    )
