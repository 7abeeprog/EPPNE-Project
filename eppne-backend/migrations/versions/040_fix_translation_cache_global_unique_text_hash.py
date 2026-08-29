# migrations/versions/040_fix_translation_cache_global_unique_text_hash.py
from alembic import op
import sqlalchemy as sa

revision = '040_fix_translation_cache_global_unique_text_hash'
down_revision = '039_expand_projects_contributions_updates_schema'


def upgrade() -> None:
    # Backlog #45: text_hash كان unique=True عالميًا (عبر كل التينانتات)، بينما
    # get_cache_by_hash() بتفلتر بـ(tenant_id, text_hash) معًا — نفس نص مشترك بين
    # تينانتين يسبب IntegrityError حقيقي مؤكَّد حيًا (تينانت A يترجم النص، تينانت B
    # يحاول يترجم نفس النص فيصطدم بالقيد العالمي رغم إن get_cache_by_hash رجعت له None).
    op.drop_index('ix_translation_cache_text_hash', table_name='translation_cache')
    op.create_index('ix_translation_cache_text_hash', 'translation_cache', ['text_hash'], unique=False)
    op.create_unique_constraint(
        'uq_translation_cache_tenant_text_hash',
        'translation_cache',
        ['tenant_id', 'text_hash'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_translation_cache_tenant_text_hash', 'translation_cache', type_='unique')
    op.drop_index('ix_translation_cache_text_hash', table_name='translation_cache')
    op.create_index('ix_translation_cache_text_hash', 'translation_cache', ['text_hash'], unique=True)
