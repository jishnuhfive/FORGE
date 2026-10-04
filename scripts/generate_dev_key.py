"""Fill the blank local encryption-key placeholder without printing the key."""

import os
from pathlib import Path

from cryptography.fernet import Fernet


def write_dev_key(path: Path) -> None:
    if not path.is_file():
        raise SystemExit("Copy .env.example to .env first. No file was created.")
    content = path.read_text()
    lines = content.splitlines()
    matches = [
        i for i, line in enumerate(lines) if line.startswith("TOKEN_ENCRYPTION_KEY=")
    ]
    if len(matches) != 1 or lines[matches[0]].strip() != "TOKEN_ENCRYPTION_KEY=":
        raise SystemExit(
            "Expected one empty TOKEN_ENCRYPTION_KEY placeholder; nothing changed."
        )
    lines[matches[0]] = "TOKEN_ENCRYPTION_KEY=" + Fernet.generate_key().decode()
    os.chmod(path, 0o600)
    path.write_text("\n".join(lines) + "\n")
    print("Development encryption key saved to the ignored .env. Keep it private.")


if __name__ == "__main__":
    write_dev_key(Path(__file__).resolve().parents[1] / ".env")
