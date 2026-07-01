# سياسات Row-Level Security (RLS) المقترحة

## جدول `saas_tenant_subscriptions`
```sql
-- منع المستخدمين من رؤية اشتراكات المستأجرين الآخرين
CREATE POLICY tenant_isolation ON saas_tenant_subscriptions
    USING (tenant_id = current_setting('app.current_tenant_id')::int);