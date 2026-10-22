"""A1 resolver and sequential executor. No AI authority.

Team B may consume discover/prepare and semantic contracts. Only a separately
authenticated, same-origin/CSRF-protected explicit approval handler may invoke
approve; a planner must never be given that capability.
"""

from collections.abc import Callable
from contextlib import suppress
from time import monotonic
from typing import cast

from fastapi import Request
from sqlalchemy.orm import Session

from forge_api.auth.runtime import AuthRuntime
from forge_api.auth.security import audit, random_token
from forge_api.db.coordination import user_lock
from forge_api.db.models import now
from forge_api.integrations.onshape.client import ReadError
from forge_api.integrations.onshape.contracts import WorkspaceReference
from forge_api.integrations.onshape.edit_registry import (
    SUPPORTED_EDITS,
    applicable,
    change,
    label,
)
from forge_api.integrations.onshape.modify_evidence import (
    ModifyEvidence,
    verify_operation,
)
from forge_api.integrations.onshape.service import ReadGate
from forge_api.integrations.onshape.write_client import SafeEditClient

from . import plan_diagnostics, plan_storage, service, storage
from .domain import Baseline, Binding, EditError
from .plan_events import (
    OperationOutcome,
    OperationResultEvent,
    Progress,
    ProgressEvent,
    ProgressStage,
)
from .plans import (
    FeatureType,
    ModifyPlan,
    OperationState,
    OperationType,
    PlanPreview,
    PlanResult,
    ResolvedOperation,
    SemanticPlan,
    Target,
    TargetCatalog,
    TargetOption,
    TargetPreview,
    plan_preview,
)


def _enabled(auth: AuthRuntime) -> None:
    if not auth.settings.forge_cad_writes_enabled:
        raise EditError("write_disabled", 403)


def _capture(
    request: Request, binding: Binding, provider: SafeEditClient
) -> ModifyEvidence:
    try:
        with cast(ReadGate, request.app.state.cad_gate).enter(binding.user):
            return provider.modify_evidence(binding.context)
    except ReadError:
        raise EditError("rate_limited", 429) from None


def discover(
    request: Request, auth: AuthRuntime, context: WorkspaceReference
) -> TargetPreview:
    _enabled(auth)
    provider = service.client(request, auth)
    with auth.sessions.begin() as db:
        binding = service.authority(request, auth, db, context, lock=True)
        service.admit(db, binding)
    evidence = _capture(request, binding, provider)
    features = evidence.features()
    targets: list[Target] = []
    options: list[TargetOption] = []
    for position, feature in enumerate(features, 1):
        if feature.get("featureType") not in ("extrude", "fillet"):
            continue
        target = Target(
            handle=random_token(),
            feature_id=cast(str, feature["featureId"]),
            feature_type=cast(FeatureType, feature["featureType"]),
            position=position,
        )
        supported: list[OperationType] = []
        for kind in SUPPORTED_EDITS:
            try:
                applicable(features, target, cast(OperationType, kind))
                supported.append(cast(OperationType, kind))
            except EditError:
                pass
        if supported:
            targets.append(target)
            options.append(
                TargetOption(
                    handle=target.handle,
                    label=label(feature, target),
                    feature_type=target.feature_type,
                    position=position,
                    supported_operations=tuple(supported),
                )
            )
    if not targets:
        raise EditError("unsupported_target", 422)
    at = now()
    catalog = TargetCatalog(
        proposal_id=random_token(),
        binding=binding,
        baseline=evidence.baseline,
        targets=tuple(targets),
        created_at=at,
        expires_at=at + 120,
    )
    with auth.sessions.begin() as db:
        if service.authority(request, auth, db, context, lock=True) != binding:
            raise EditError("context_changed")
        storage.unfenced(db, binding)
        storage.store(db, catalog, "candidate")
    return TargetPreview(
        target_catalog=catalog.proposal_id,
        expires_at=catalog.expires_at,
        targets=tuple(options),
    )


def prepare(request: Request, auth: AuthRuntime, semantic: SemanticPlan) -> PlanPreview:
    _enabled(auth)
    semantic = SemanticPlan.model_validate_json(semantic.model_dump_json())
    provider = service.client(request, auth)
    with auth.sessions.begin() as db:
        user, session = service.identity(request, auth, db)
        user_lock(db, user)
        catalog = plan_storage.catalog(
            storage.owned(db, semantic.target_catalog, user, session)
        )
        binding = service.authority(
            request, auth, db, catalog.binding.context, lock=True
        )
        if binding != catalog.binding:
            raise EditError("context_changed")
        service.admit(db, binding)
    evidence = _capture(request, binding, provider)
    if evidence.baseline != catalog.baseline or now() >= catalog.expires_at:
        raise EditError("model_changed")
    features = evidence.features()
    resolved: list[ResolvedOperation] = []
    for operation in semantic.operations:
        matches = [t for t in catalog.targets if t.handle == operation.target]
        if len(matches) != 1:
            raise EditError("unsupported_target", 422)
        target = matches[0]
        updated, preview = change(features, target, operation)
        resolved.append(
            ResolvedOperation(operation=operation, target=target, preview=preview)
        )
        # This predicts only allowed definition fields for an exact sequential
        # preview, not provider success or geometry. Each step re-proves evidence.
        features[target.position - 1] = updated
    at = now()
    plan = ModifyPlan(
        proposal_id=random_token(),
        binding=binding,
        baseline=evidence.baseline,
        created_at=at,
        expires_at=at + 120,
        operations=tuple(resolved),
    )
    with auth.sessions.begin() as db:
        if service.authority(request, auth, db, binding.context, lock=True) != binding:
            raise EditError("context_changed")
        # Catalog invalidation/expiry during the reads must not mint authority.
        current = plan_storage.catalog(
            storage.owned(db, catalog.proposal_id, user, session)
        )
        if current != catalog:
            raise EditError("model_changed")
        storage.unfenced(db, binding)
        plan_storage.store(db, plan)
    return plan_preview(plan)


def _current(
    request: Request, auth: AuthRuntime, db: Session, plan: ModifyPlan, started: float
) -> None:
    _enabled(auth)
    if (
        service.authority(request, auth, db, plan.binding.context, lock=True)
        != plan.binding
    ):
        raise EditError("context_changed")
    if now() >= plan.expires_at:
        raise EditError("proposal_expired")
    # Preserve Phase 9's total 30-second verification budget and 25-second
    # pre-dispatch bound for the *whole* plan, not five independently renewed TTLs.
    if monotonic() - started > 25:
        raise EditError("model_changed")


def approve(
    request: Request,
    auth: AuthRuntime,
    handle: str,
    digest: str,
    progress: Callable[[Progress], None] | None = None,
) -> PlanResult:
    _enabled(auth)
    with auth.sessions.begin() as db:
        user, session = service.identity(request, auth, db)
        user_lock(db, user)
        plan = plan_storage.claim(db, handle, user, session, digest)
    # Claim/fence is durable before any provider work. No resume/retry entry point.
    started = monotonic()
    expected: Baseline = plan.baseline
    states: list[OperationState] = ["pending"] * len(plan.operations)
    index = 0
    dispatched = False
    verify_stage: plan_diagnostics.Stage | None = None
    development = auth.settings.environment == "development"

    def diagnostic(stage: plan_diagnostics.Stage) -> None:
        plan_diagnostics.emit(development, stage, True)

    def observe(event: Progress) -> None:
        if progress is not None:
            # Presentation cannot change dispatch, verification or replay.
            with suppress(Exception):
                progress(event)

    def stage(value: ProgressStage) -> None:
        observe(ProgressEvent(operation=index + 1, total=len(states), stage=value))

    def outcome(number: int, value: OperationOutcome) -> None:
        observe(OperationResultEvent(operation=number, total=len(states), state=value))

    try:
        provider = service.client(request, auth)
        for index, operation in enumerate(plan.operations):
            dispatched = False
            verify_stage = None
            states[index] = "checking"
            with auth.sessions.begin() as db:
                _current(request, auth, db, plan, started)
                plan_storage.journal(
                    db, plan, PlanResult(state="claimed", operations=tuple(states))
                )
            stage("checking")
            evidence = provider.modify_evidence(plan.binding.context)
            if evidence.baseline != expected:
                raise EditError("model_changed")
            _, preview = change(
                evidence.features(), operation.target, operation.operation
            )
            if preview != operation.preview:
                raise EditError("model_changed")
            provider.check_operation(evidence, operation)
            with auth.sessions.begin() as db:
                _current(request, auth, db, plan, started)
                if provider.head(plan.binding.context) != expected.microversion:
                    raise EditError("model_changed")
                states[index] = "executing"
                plan_storage.journal(
                    db, plan, PlanResult(state="claimed", operations=tuple(states))
                )
                audit(db, "write_dispatch_started", user_id=user)
            stage("executing")
            # The per-operation dispatch boundary is committed before the POST.
            # Reacquire auth locks and close the inter-transaction head race.
            with auth.sessions.begin() as db:
                _current(request, auth, db, plan, started)
                plan_storage.journal(
                    db, plan, PlanResult(state="claimed", operations=tuple(states))
                )
                if provider.head(plan.binding.context) != expected.microversion:
                    raise EditError("model_changed")
                dispatched = True
                marker = provider.execute_operation(evidence, operation)
                audit(db, "write_provider_acknowledged", user_id=user)
                states[index] = "verifying"
                plan_storage.journal(
                    db, plan, PlanResult(state="verifying", operations=tuple(states))
                )
            stage("verifying")
            verify_stage = "post_read"
            after = provider.modify_evidence(plan.binding.context)
            diagnostic(verify_stage)
            verify_stage = "operation_compare"
            verify_operation(evidence, after, operation, marker)
            diagnostic(verify_stage)
            verify_stage = "deadline"
            if not 0 <= monotonic() - started <= 30:
                raise EditError("verification_failed")
            diagnostic(verify_stage)
            verify_stage = "authority"
            with auth.sessions.begin() as db:
                if (
                    service.authority(
                        request, auth, db, plan.binding.context, lock=True
                    )
                    != plan.binding
                ):
                    raise EditError("context_changed")
                diagnostic(verify_stage)
                verify_stage = None
                states[index] = "verified_success"
                plan_storage.journal(
                    db, plan, PlanResult(state="verifying", operations=tuple(states))
                )
                audit(db, "write_verified", user_id=user)
            outcome(index + 1, "verified_success")
            expected = after.baseline  # M0 -> verified M1 -> verified M2 only.
        result = PlanResult(state="verified_success", operations=tuple(states))
    except Exception as error:
        if verify_stage is not None:
            plan_diagnostics.emit(development, verify_stage, False)
        # No raw exception/provider data escapes and no later operation executes.
        stale = isinstance(error, EditError) and error.code in (
            "model_changed",
            "context_changed",
        )
        states[index] = (
            "execution_uncertain"
            if dispatched
            else "rejected_stale"
            if stale
            else "write_failed"
        )
        states[index + 1 :] = ["skipped"] * (len(states) - index - 1)
        result = PlanResult(
            state="execution_uncertain"
            if dispatched
            else "partial_failure"
            if "verified_success" in states
            else "rejected_stale"
            if stale
            else "write_failed",
            operations=tuple(states),
        )
    with auth.sessions.begin() as db:
        user_lock(db, user)
        plan_storage.finish(db, plan, result)
    if result.state != "verified_success":
        for number in range(index + 1, len(states) + 1):
            outcome(number, cast(OperationOutcome, states[number - 1]))
    return result


def cancel(request: Request, auth: AuthRuntime, handle: str) -> PlanResult:
    with auth.sessions.begin() as db:
        user, session = service.identity(request, auth, db)
        user_lock(db, user)
        return plan_storage.cancel(db, handle, user, session)


def status(request: Request, auth: AuthRuntime, handle: str) -> PlanResult:
    with auth.sessions.begin() as db:
        user, session = service.identity(request, auth, db)
        storage.cleanup(db)
        return plan_storage.result(storage.owned(db, handle, user, session))
