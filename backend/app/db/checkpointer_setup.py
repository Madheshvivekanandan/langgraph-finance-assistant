"""Creates the LangGraph checkpointer's own tables (`checkpoints`, `checkpoint_migrations`, ...).

Run once per database by the compose `migrate` one-shot, alongside Alembic - not
by Alembic itself, and not at FastAPI startup. See plan D2: the checkpointer
owns its own schema and its own version table, so wrapping it in Alembic would
give one set of tables two migration ledgers. Running it at app startup would
reintroduce the replica race the `migrate` service exists to eliminate.
"""

import logging

from langgraph.checkpoint.postgres import PostgresSaver

from app.db.psycopg_dsn import psycopg_dsn

logger = logging.getLogger(__name__)


def setup_checkpointer(database_url: str) -> None:
    """Create (or bring up to date) the checkpointer's tables.

    Safe to run more than once: `PostgresSaver.setup()` tracks its own applied
    migrations and is a no-op once the schema is current.
    """
    with PostgresSaver.from_conn_string(psycopg_dsn(database_url)) as saver:
        saver.setup()
    logger.info("checkpointer_schema_ready")


if __name__ == "__main__":
    from app.core.config import get_settings

    logging.basicConfig(level=logging.INFO)
    setup_checkpointer(get_settings().database_url)
