# migrations/versions/042_add_held_balances_to_wallets.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '042_add_held_balances_to_wallets'
down_revision = '041_widen_asset_tokenizations_token_symbol'


def upgrade() -> None:
    # جلسة #29 (finance-service-hold-funds-missing، 2026-08-29): FinanceService
    # كانت بتفتقد أي بنية لتمثيل "أموال محجوزة" منفصلة عن الرصيد المتاح —
    # لازمة لـ hold_funds/release_held_funds/settle_held_funds
    # (tenders_auctions.place_bid/close_auction). نفس شكل عمود balances
    # بالضبط (نفس العملات الخمس، صفر ابتدائي لكل المحافظ الموجودة).
    op.add_column(
        'wallets',
        sa.Column(
            'held_balances',
            JSONB,
            nullable=False,
            server_default=sa.text(
                "'{\"MR_POUND\": 0, \"MR_USDT\": 0, \"MR7\": 0, \"NBT\": 0, \"MRX\": 0}'::jsonb"
            ),
        ),
    )
    op.create_check_constraint(
        "check_wallet_held_balances_non_negative",
        "wallets",
        "(held_balances->>'MR_POUND')::numeric >= 0 AND "
        "(held_balances->>'MR_USDT')::numeric >= 0 AND "
        "(held_balances->>'MR7')::numeric >= 0 AND "
        "(held_balances->>'NBT')::numeric >= 0 AND "
        "(held_balances->>'MRX')::numeric >= 0",
    )


def downgrade() -> None:
    op.drop_constraint('check_wallet_held_balances_non_negative', 'wallets', type_='check')
    op.drop_column('wallets', 'held_balances')
