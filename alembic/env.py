from logging.config import fileConfig

from alembic import context
from app import models  # noqa: F401 - registers models with Base.metadata
from app.database import Base, engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Alembic compares this metadata against PostgreSQL.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    raise RuntimeError(
        "Offline migrations are not supported because the migration history "
        "contains data-dependent backfills"
    )


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
