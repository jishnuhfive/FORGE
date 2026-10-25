"""Synthetic server-attested incidents; never reads a real database/provider."""

from dataclasses import dataclass

import httpx2 as httpx
from conftest import Harness
from depth_support import seed_depth
from sqlalchemy import select
from test_modify_plan import PlanProvider

from forge_api.cad_edits.depth_contracts import (
    DevelopmentIncidentReview,
    ServerAttestedDepthReference,
)
from forge_api.cad_edits.depth_recovery import (
    _development_reference,
    recover_depth_record,
    recover_development_depth_incident,
)
from forge_api.db.models import AuditEvent, WriteFence, WriteRecord


def review(h: Harness) -> DevelopmentIncidentReview:
    return DevelopmentIncidentReview(
        operator_authorized=True,
        server_attested_policy_accepted=True,
        disposable_fixture=True,
        writers_drained=True,
        upstream_settled=True,
        settlement_review=(
            "Synthetic independent upstream settlement review; "
            "no activity remains in flight."
        ),
        stack=str(h.runtime.settings.onshape_api_base_url),
        company_id=h.runtime.settings.onshape_company_id,
    )


@dataclass
class ServerCase:
    harness: Harness
    provider: PlanProvider
    reference: ServerAttestedDepthReference
    use_operator_entry: bool = False

    def recover(self) -> object:
        if self.use_operator_entry:
            return recover_development_depth_incident(
                self.harness.runtime,
                review(self.harness),
                transport=httpx.MockTransport(self.provider.handle),
            )
        return recover_depth_record(
            self.harness.runtime.sessions,
            self.harness.runtime.settings,
            self.harness.runtime.tokens,
            self.reference,
            transport=httpx.MockTransport(self.provider.handle),
        )

    def snapshot(self) -> tuple[object, ...]:
        with self.harness.runtime.sessions() as db:
            row = db.get(WriteRecord, self.reference.historical.record_id)
            fences = tuple(
                (f.workspace_key, f.user_id, f.record_id)
                for f in db.scalars(select(WriteFence))
            )
            audits = tuple(
                (a.kind, a.outcome)
                for a in db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.kind == "write_depth_development_recovery"
                    )
                )
            )
            return (
                None
                if row is None
                else (
                    row.state,
                    row.payload,
                    row.digest,
                    row.session_hash,
                    row.purge_at,
                ),
                fences,
                audits,
            )


def seed_server(h: Harness, p: PlanProvider) -> ServerCase:
    seed_depth(h, p)
    with h.runtime.sessions.begin() as db:
        reference = _development_reference(db, h.runtime.settings, review(h))
    p.calls.clear()
    return ServerCase(h, p, reference)
