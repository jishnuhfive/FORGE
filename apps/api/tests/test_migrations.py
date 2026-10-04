from pathlib import Path

import pytest
from conftest import migrate
from sqlalchemy import create_engine, inspect

from forge_api.db.database import verify_schema


def test_fresh_database_upgrade_is_repeatable(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///" + str(tmp_path / "fresh.sqlite"))
    migrate(engine)
    verify_schema(engine)
    tables = inspect(engine).get_table_names()
    migrate(engine)
    assert inspect(engine).get_table_names() == tables
    engine.dispose()


def test_unmigrated_database_fails_closed(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient
    from pydantic import SecretStr

    from forge_api.core.config import Settings
    from forge_api.main import create_app

    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=SecretStr("sqlite:///" + str(tmp_path / "empty.sqlite")),
    )
    with (
        pytest.raises(RuntimeError, match="migration required"),
        TestClient(create_app(settings)),
    ):
        pass
