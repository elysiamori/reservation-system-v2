"""
Alembic Environment Configuration
──────────────────────────────────
- Reads DATABASE_URL from app/config.py (which reads from .env)
- Imports ALL models via app/models/__init__.py so Alembic can detect schema changes
- Runs in "offline" mode (generates SQL) or "online" mode (applies to DB)
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ─── Make sure app/ is importable ─────────────────────────────────────────────
# This allows: from app.database import Base
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ─── Import settings & Base ────────────────────────────────────────────────────
from app.config import settings
from app.database import Base

# ─── Import ALL models so Alembic detects them ────────────────────────────────
import app.models  # noqa: F401 — side-effect import registers models on Base.metadata

# ─── Alembic config object ────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with value from our settings (reads from .env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# ─── Offline Mode ─────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL script without connecting to the database.
    Useful for reviewing migrations before applying them.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,        # Detect column type changes
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ─── Online Mode ──────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Connects to the database and applies migrations directly.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # Use NullPool during migrations (no connection pooling)
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
