# migrations/versions/041_widen_asset_tokenizations_token_symbol.py
from alembic import op
import sqlalchemy as sa

revision = '041_widen_asset_tokenizations_token_symbol'
down_revision = '040_fix_translation_cache_global_unique_text_hash'


def upgrade() -> None:
    # اكتُشف أثناء جلسة realestate-buyfraction-amount-trust-check
    # (2026-08-29): token_symbol كان VARCHAR(10)، بينما
    # RealEstateService.tokenize_asset() بيولّد
    # f"EPPNE-RE-{unit_id}-{uuid.uuid4().hex[:4].upper()}" — دايمًا 15+
    # حرف. أي استدعاء حقيقي لـtokenize_asset كان بيفشل بـ
    # StringDataRightTruncationError عند الـINSERT، بغض النظر عن الـcaller.
    op.alter_column(
        'asset_tokenizations', 'token_symbol',
        existing_type=sa.String(length=10),
        type_=sa.String(length=30),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'asset_tokenizations', 'token_symbol',
        existing_type=sa.String(length=30),
        type_=sa.String(length=10),
        existing_nullable=True,
    )
