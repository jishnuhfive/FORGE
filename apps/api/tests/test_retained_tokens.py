"""Cache-only access must never enter refresh, DB, or mutation capabilities."""

from typing import Any

import pytest
from retained_support import RetainedCase
from test_retained_recovery import case as case

from forge_api.auth.provider import ProviderError
from forge_api.cad_edits.retained_contracts import RetainedRecoveryDenied
from forge_api.db.models import now


@pytest.mark.parametrize(
    "change",
    [
        "hit",
        "miss",
        "expired",
        "short",
        "exact_budget",
        "generation",
        "user",
        "permission",
        "unknown_scope",
        "budget",
        "bool_budget",
    ],
)
def test_cache_accessor_is_purely_cache_only(
    case: RetainedCase, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    tokens, ref = case.harness.runtime.tokens, case.reference
    user, generation, scope, budget = (
        ref.independent.user,
        ref.review.current_generation,
        "OAuth2Read",
        30,
    )
    cached = tokens._cache[user]
    if change == "miss":
        tokens.forget(user)
    elif change == "expired":
        cached.expires_at = now() - 1
    elif change == "short":
        cached.expires_at = now() + 29
    elif change == "exact_budget":
        cached.expires_at = now() + 30
    elif change == "generation":
        generation = "synthetic-other"
    elif change == "user":
        user = "synthetic-other"
    elif change == "permission":
        scope = "OAuth2Write"
    elif change == "unknown_scope":
        scope = "onshape_bitmask:7"
    elif change == "budget":
        budget = -1
    elif change == "bool_budget":
        budget = True
    before = case.snapshot()

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("cache accessor reached a forbidden capability")

    monkeypatch.setattr(tokens, "sessions", forbidden)
    monkeypatch.setattr(tokens.provider, "refresh", forbidden)
    monkeypatch.setattr(tokens, "get_valid_onshape_access_token", forbidden)
    if change == "hit":
        credential = tokens.cached_read_credential(
            user, generation, scope, capture_seconds=budget
        )
        assert credential.get_secret_value() == "synthetic-cached-read"
    else:
        with pytest.raises(ProviderError):
            tokens.cached_read_credential(
                user, generation, scope, capture_seconds=budget
            )
    assert case.snapshot() == before and case.provider.calls == []


@pytest.mark.parametrize("change", ["miss", "expired", "generation"])
def test_coordinator_cache_failure_is_fenced_and_makes_no_request(
    case: RetainedCase, change: str
) -> None:
    tokens, user = case.harness.runtime.tokens, case.reference.independent.user
    if change == "miss":
        tokens.forget(user)
    elif change == "expired":
        tokens._cache[user].expires_at = now() - 1
    else:
        tokens._cache[user].generation = "synthetic-stale-generation"
    before = case.snapshot()
    with pytest.raises(RetainedRecoveryDenied, match="cached_read_credential_required"):
        case.recover()
    assert case.snapshot() == before and case.provider.calls == []
