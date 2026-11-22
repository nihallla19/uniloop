from alembic import context
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


class _MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url_direct: str


# Migrations always use the direct (non-pooled) connection as baton_migrator.
# Tests pass an explicit URL through the Alembic config.
url = context.config.get_main_option("sqlalchemy.url") or _MigrationSettings().database_url_direct  # type: ignore[call-arg]


def run() -> None:
    engine = create_engine(url, poolclass=NullPool)
    with engine.connect() as conn:
        # The version table lives in system, so that schema must exist first.
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS system"))
        conn.commit()
        context.configure(
            connection=conn,
            include_schemas=True,
            version_table="alembic_version",
            version_table_schema="system",
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run()
