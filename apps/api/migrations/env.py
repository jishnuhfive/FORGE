from alembic import context

from forge_api.core.config import Settings
from forge_api.db.database import make_engine
from forge_api.db.models import Base

# No logging.fileConfig: never echo SQL, connection URLs or parameters.
connection = context.config.attributes.get("connection")
if connection is not None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(Settings())
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
