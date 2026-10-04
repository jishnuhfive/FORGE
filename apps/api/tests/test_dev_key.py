import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from cryptography.fernet import Fernet

from forge_api.core.config import REPOSITORY_ROOT


def writer() -> Callable[[Path], None]:
    spec = importlib.util.spec_from_file_location(
        "dev_key", REPOSITORY_ROOT / "scripts/generate_dev_key.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Callable[[Path], None], module.write_dev_key)


def test_key_generator_writes_private_key_without_printing_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / ".env"
    path.write_text("TOKEN_ENCRYPTION_KEY=\nONSHAPE_CLIENT_ID=\n")
    writer()(path)
    key = path.read_text().splitlines()[0].split("=", 1)[1]
    Fernet(key.encode())
    assert key not in capsys.readouterr().out
    assert path.stat().st_mode & 0o777 == 0o600


def test_key_generator_refuses_to_overwrite_or_create_an_environment(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".env"
    with pytest.raises(SystemExit, match="Copy .env.example"):
        writer()(path)
    assert not path.exists()
    path.write_text("TOKEN_ENCRYPTION_KEY=already-configured\n")
    with pytest.raises(SystemExit, match="nothing changed"):
        writer()(path)
    assert path.read_text() == "TOKEN_ENCRYPTION_KEY=already-configured\n"
