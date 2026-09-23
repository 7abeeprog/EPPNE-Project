# migrations/versions/068_invoice_number_counters.py
from alembic import op
import sqlalchemy as sa

revision = '068_invoice_number_counters'
down_revision = '067_site_legal_clearance'

# جدول عداد per-tenant لـinvoice_number بدل COUNT(*)+1 (اللي بيقفل التينانت للأبد
# لو اتحذفت أي فاتورة مش الأخيرة — tenant 1 و16 مقفولين حاليًا). الـseed بياخد أعلى
# seq موجود فعلًا لكل تينانت من invoice_number نفسه (مش COUNT) — الصيغة
# INV-{tenant_id}-{seq}، والـregex بيتجاهل أي صف بصيغة مختلفة (صفر صفوف حاليًا).
# صفر لمس على صفوف invoices الموجودة.
#
# تحذير downgrade: InvoicingRepository.next_invoice_seq بيعتمد على الجدول ده — downgrade
# من غير revert لكود invoicing (service._generate_invoice_number + repository.next_invoice_seq
# + models.InvoiceNumberCounter) بيكسر create_invoice بالكامل (relation does not exist).
# الاتنين لازم يترجعوا مع بعض دايمًا.


def upgrade() -> None:
    op.create_table(
        'invoice_number_counters',
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('academy_tenants.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('last_seq', sa.Integer(), nullable=False),
        sa.CheckConstraint('last_seq >= 0', name='check_invoice_number_counters_last_seq_non_negative'),
    )
    op.execute(
        """
        INSERT INTO invoice_number_counters (tenant_id, last_seq)
        SELECT tenant_id, MAX(split_part(invoice_number, '-', 3)::int)
        FROM invoices
        WHERE invoice_number ~ ('^INV-' || tenant_id || '-[0-9]+$')
        GROUP BY tenant_id
        """
    )


def downgrade() -> None:
    op.drop_table('invoice_number_counters')
