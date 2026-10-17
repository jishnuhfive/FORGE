from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from forge_api.core.config import Settings

SCHEMA_REVISION = "0002_safe_edit"


def make_engine(config: Settings) -> Engine:
    if not config.database_url:
        raise ValueError("Database is not configured")
    return create_engine(
        config.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
        echo=False,
    )


def verify_schema(engine: Engine) -> None:
    """Never create tables at startup. Migrations are an explicit operator action."""
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        if revision != SCHEMA_REVISION:
            raise RuntimeError("Database migration required; run make migrate")


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
