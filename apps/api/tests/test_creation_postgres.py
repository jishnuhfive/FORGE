"""Creation approval uses the same PostgreSQL one-use fence serialization."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any, cast

from conftest import Harness
from sqlalchemy import Engine, select
from test_cad_read import REF
from test_creation_api import BRIEF, Provider, post
from test_modify_plan_postgres import use_postgres
from test_postgres import postgres as postgres
from test_safe_edit import running

from forge_api.db.models import WriteFence


def test_creation_double_approval_has_one_execution(
    postgres: Engine, harness: Harness
) -> None:
    use_postgres(harness, postgres)
    provider = Provider()
    with running(harness, cast(Any, provider)):
        preview = post(
            harness, "/api/create/plan", {"context": REF.model_dump(), "brief": BRIEF}
        ).json()
        barrier = Barrier(2)

        def attempt() -> int:
            barrier.wait(timeout=5)
            return int(
                post(
                    harness,
                    f"/api/create/plans/{preview['proposal_id']}/approve",
                    {"digest": preview["digest"], "brief_confirmed": True},
                ).status_code
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(attempt), pool.submit(attempt)
            assert sorted((a.result(timeout=15), b.result(timeout=15))) == [200, 409]
        assert provider.writes == 2
        with harness.runtime.sessions() as db:
            assert db.scalar(select(WriteFence)) is None
