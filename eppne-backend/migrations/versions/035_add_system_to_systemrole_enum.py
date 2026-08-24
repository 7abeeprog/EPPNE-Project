# migrations/versions/035_add_system_to_systemrole_enum.py
from alembic import op

revision = '035_add_system_to_systemrole_enum'
down_revision = '034_add_is_system_account_to_users'


def upgrade() -> None:
    # PostgreSQL restricts using a newly-added enum value inside the SAME
    # transaction that added it (INSERT/UPDATE/compare) — but running
    # ALTER TYPE ... ADD VALUE itself inside a transaction block has been
    # allowed since PG12. This migration only adds the value; it does not
    # use it. Verified against the live dev DB (postgres:16.14, eppne_db
    # container) and migrations/env.py (no transaction_per_migration set,
    # so this runs under alembic's default transactional-DDL wrapping) —
    # no explicit COMMIT / autocommit-block workaround is required here.
    # Any code that creates a User with system_role=SYSTEM must do so in a
    # transaction that starts AFTER this migration commits, which is
    # naturally the case (application code runs in a separate connection
    # from the one `alembic upgrade` uses).
    op.execute("ALTER TYPE systemrole ADD VALUE IF NOT EXISTS 'SYSTEM'")


def downgrade() -> None:
    # PostgreSQL has no DROP VALUE for enum types. Removing 'SYSTEM' would
    # require rebuilding the systemrole type from scratch (create a new
    # type, migrate the column over, drop the old type) and is
    # intentionally not implemented — fail loudly instead of pretending to
    # revert.
    raise NotImplementedError(
        "Cannot downgrade 035: PostgreSQL does not support dropping enum "
        "values. Rebuild the 'systemrole' type manually if this must be "
        "reverted."
    )
