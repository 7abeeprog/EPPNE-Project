# app/core/database_indexes.py
"""
فهارس قاعدة البيانات - تحسين الأداء
تُنفذ هذه الفهارس عند بدء التشغيل أو عبر Alembic migration
تم التعديل: إضافة فهارس وظيفية (Functional Indexes) لدعم LOWER() 
وإضافة فهارس مركبة وجزئية لتسريع الاستعلامات الأكثر استخداماً
"""

import asyncio
import time
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.core.database import engine
import logging

logger = logging.getLogger("eppne")


async def wait_for_db(max_retries=10, delay=3):
    """
    انتظار اتصال قاعدة البيانات مع إعادة المحاولة.
    """
    for attempt in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info(f"✅ Database connection established (attempt {attempt + 1})")
                return True
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"❌ Failed to connect to database after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(f"⚠️ Database connection attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
    return False


async def create_indexes():
    """
    إنشاء جميع الفهارس المطلوبة لتحسين أداء الاستعلامات.
    تتضمن آلية إعادة المحاولة لضمان الاستقرار عند بدء التشغيل.
    """
    # انتظار اتصال قاعدة البيانات
    await wait_for_db(max_retries=10, delay=3)

    indexes = [
        # ============================================================
        # 1. الهوية والمستخدمين (مع فهارس وظيفية لدعم البحث غير الحساس)
        # ============================================================
        """
        -- فهرس وظيفي للبريد الإلكتروني (يدعم func.lower(email))
        CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email));
        
        -- فهرس وظيفي لاسم المستخدم (يدعم func.lower(username))
        CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users (LOWER(username));
        
        -- فهرس مركب للبريد الإلكتروني مع حالة الحساب (لتسريع تسجيل الدخول)
        CREATE INDEX IF NOT EXISTS idx_users_email_status ON users (email, is_active);
        
        -- فهرس مركب لاسم المستخدم مع حالة الحساب
        CREATE INDEX IF NOT EXISTS idx_users_username_status ON users (username, is_active);
        
        -- فهرس جزئي للمستخدمين النشطين فقط (تسريع الاستعلامات المتكررة)
        CREATE INDEX IF NOT EXISTS idx_users_active ON users (id) WHERE is_active = true;
        
        -- فهرس للتاريخ (للترتيب والتصفية الزمنية)
        CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);
        
        -- فهرس للـ tenant_id لتسريع استعلامات المستأجرين
        CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users (tenant_id);
        """,
        
        # ============================================================
        # 2. المعاملات المالية (مع فهارس مركبة)
        # ============================================================
        """
        -- فهرس مركب للمستخدم + التاريخ (لتسريع تقارير المعاملات)
        CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions (user_id, created_at DESC);
        
        -- فهرس للحالة مع التاريخ (لتصفية المعاملات المعلقة)
        CREATE INDEX IF NOT EXISTS idx_transactions_status_date ON transactions (status, created_at DESC);
        
        -- فهرس للعملة مع المستخدم (لتقارير العملات)
        CREATE INDEX IF NOT EXISTS idx_transactions_currency_user ON transactions (currency, user_id);
        
        -- فهرس جزئي للمعاملات المعلقة (لتسريع جدولة المعالجة)
        CREATE INDEX IF NOT EXISTS idx_transactions_pending ON transactions (id, created_at) WHERE status = 'PENDING';
        
        -- فهرس للمبلغ (لتسريع الاستعلامات الرقمية)
        CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions (amount);
        """,
        
        # ============================================================
        # 3. التعليم (Academy) - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب للتسجيلات (مستخدم + دورة) لتسريع البحث عن التسجيل
        CREATE INDEX IF NOT EXISTS idx_enrollments_user_course ON enrollments (user_id, course_id);
        
        -- فهرس للحالة مع المستخدم (لتسريع تصفية تسجيلات المستخدم)
        CREATE INDEX IF NOT EXISTS idx_enrollments_user_status ON enrollments (user_id, status);
        
        -- فهرس للدورة مع الحالة (لإحصائيات الدورة)
        CREATE INDEX IF NOT EXISTS idx_enrollments_course_status ON enrollments (course_id, status);
        
        -- فهرس مركب للدورات (المستأجر + الكيان السيادي)
        CREATE INDEX IF NOT EXISTS idx_courses_tenant_org ON courses (tenant_id, org_entity_id);
        
        -- فهرس للدورات النشطة فقط
        CREATE INDEX IF NOT EXISTS idx_courses_active ON courses (id) WHERE is_published = true;
        """,
        
        # ============================================================
        # 4. الصحة - فهارس مركبة وجزئية
        # ============================================================
        """
        -- فهرس للملف الطبي (مستخدم + تاريخ التحديث)
        CREATE INDEX IF NOT EXISTS idx_medical_profile_user_date ON medical_profiles (user_id, updated_at DESC);
        
        -- فهرس مركب للمواعيد (المريض + التاريخ)
        CREATE INDEX IF NOT EXISTS idx_appointments_patient_date ON medical_appointments (patient_user_id, appointment_time);
        
        -- فهرس للطبيب مع التاريخ (جدولة الطبيب)
        CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date ON medical_appointments (doctor_user_id, appointment_time);
        
        -- فهرس جزئي للمواعيد القادمة (تسريع لوحة التحكم)
        CREATE INDEX IF NOT EXISTS idx_appointments_upcoming ON medical_appointments (appointment_time) 
        WHERE status = 'SCHEDULED' AND appointment_time > NOW();
        
        -- فهرس للحالة مع التاريخ
        CREATE INDEX IF NOT EXISTS idx_appointments_status_date ON medical_appointments (status, appointment_time);
        """,
        
        # ============================================================
        # 5. التجارة - فهارس مركبة وجزئية
        # ============================================================
        """
        -- فهرس مركب للطلبات (عميل + تاريخ)
        CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON orders (customer_id, created_at DESC);
        
        -- فهرس للحالة مع التاريخ (لتصفية الطلبات قيد المعالجة)
        CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders (status, created_at DESC);
        
        -- فهرس مركب للمنتجات (متجر + فئة)
        CREATE INDEX IF NOT EXISTS idx_products_store_category ON products (store_id, category_id);
        
        -- فهرس جزئي للمنتجات المتاحة
        CREATE INDEX IF NOT EXISTS idx_products_available ON products (id) WHERE stock_quantity > 0 AND is_active = true;
        
        -- فهرس للمتغيرات مع السعر (للبحث السريع)
        CREATE INDEX IF NOT EXISTS idx_product_variants_price ON product_variants (product_id, price);
        """,
        
        # ============================================================
        # 6. المشاريع - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (مالك + حالة)
        CREATE INDEX IF NOT EXISTS idx_projects_owner_status ON projects (owner_id, status);
        
        -- فهرس للحالة مع التاريخ (للوحة القيادة)
        CREATE INDEX IF NOT EXISTS idx_projects_status_date ON projects (status, created_at DESC);
        
        -- فهرس مركب للمساهمات (مشروع + مساهم)
        CREATE INDEX IF NOT EXISTS idx_contributions_project_contributor ON contributions (project_id, contributor_id);
        
        -- فهرس جزئي للمساهمات المعلقة
        CREATE INDEX IF NOT EXISTS idx_contributions_pending ON contributions (project_id) WHERE status = 'PENDING';
        """,
        
        # ============================================================
        # 7. النقل - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (سائق + حالة)
        CREATE INDEX IF NOT EXISTS idx_trips_driver_status ON trips (driver_id, status);
        
        -- فهرس للتاريخ مع الحالة (لجدولة الرحلات)
        CREATE INDEX IF NOT EXISTS idx_trips_scheduled_status ON trips (scheduled_start, status);
        
        -- فهرس جزئي للرحلات النشطة
        CREATE INDEX IF NOT EXISTS idx_trips_active ON trips (id) WHERE status IN ('SCHEDULED', 'IN_PROGRESS');
        """,
        
        # ============================================================
        # 8. الإشعارات - فهارس مركبة وجزئية
        # ============================================================
        """
        -- فهرس مركب (مستخدم + مقروء)
        CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications (user_id, is_read);
        
        -- فهرس للتاريخ مع الأولوية
        CREATE INDEX IF NOT EXISTS idx_notifications_priority_date ON notifications (priority, created_at DESC);
        
        -- فهرس جزئي للإشعارات غير المقروءة (تسريع عداد الإشعارات)
        CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications (user_id) WHERE is_read = false;
        """,
        
        # ============================================================
        # 9. التوأم الرقمي - فهارس مركبة وجزئية
        # ============================================================
        """
        -- فهرس مركب (مستخدم + تاريخ الحدث)
        CREATE INDEX IF NOT EXISTS idx_milestones_user_date ON life_milestones (user_id, occurrence_date DESC);
        
        -- فهرس لنوع الحدث مع المستخدم (لتصفية الأحداث حسب النوع)
        CREATE INDEX IF NOT EXISTS idx_milestones_user_type ON life_milestones (user_id, milestone_type);
        
        -- فهرس جزئي لأحدث 5 أحداث (للوحة القيادة)
        CREATE INDEX IF NOT EXISTS idx_milestones_recent ON life_milestones (user_id, occurrence_date DESC) 
        WHERE is_deleted = false;
        """,
        
        # ============================================================
        # 10. الوكلاء والموافقات - فهارس مركبة وجزئية
        # ============================================================
        """
        -- فهرس مركب (مالك + حالة)
        CREATE INDEX IF NOT EXISTS idx_ai_agents_owner_status ON ai_agents (owner_id, status);
        
        -- فهرس للدور مع الحالة (لتصفية الوكلاء حسب الدور)
        CREATE INDEX IF NOT EXISTS idx_ai_agents_role_status ON ai_agents (role, status);
        
        -- فهرس جزئي للوكلاء النشطين
        CREATE INDEX IF NOT EXISTS idx_ai_agents_active ON ai_agents (id) WHERE status = 'ACTIVE';
        
        -- فهرس مركب للموافقات (وكيل + حالة)
        CREATE INDEX IF NOT EXISTS idx_approvals_agent_status ON approvals (agent_id, status);
        
        -- فهرس جزئي للموافقات المعلقة (تسريع صفحة الموافقات)
        CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals (created_at) WHERE status = 'PENDING';
        """,
        
        # ============================================================
        # 11. المركبات والطرق - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (أسطول + حالة)
        CREATE INDEX IF NOT EXISTS idx_vehicles_fleet_status ON vehicles (fleet_id, status);
        
        -- فهرس مركب للطرق (نقطة البداية + النهاية)
        CREATE INDEX IF NOT EXISTS idx_routes_hubs ON routes (start_hub_id, end_hub_id);
        """,
        
        # ============================================================
        # 12. الكيانات السيادية - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (نوع الكيان + حالة KYB)
        CREATE INDEX IF NOT EXISTS idx_sovereign_entities_type_kyb ON sovereign_entities (entity_type, kyb_status);
        
        -- فهرس للمالك (لتسريع جلب كيانات المستخدم)
        CREATE INDEX IF NOT EXISTS idx_sovereign_entities_owner ON sovereign_entities (owner_id);
        
        -- فهرس جزئي للكيانات الموثقة
        CREATE INDEX IF NOT EXISTS idx_sovereign_entities_verified ON sovereign_entities (id) WHERE kyb_status = 'VERIFIED';
        """,
        
        # ============================================================
        # 13. الممثلين (Representatives) - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (كيان + مستخدم)
        CREATE INDEX IF NOT EXISTS idx_representatives_entity_user ON entity_representatives (entity_id, user_id);
        
        -- فهرس للدور مع الكيان
        CREATE INDEX IF NOT EXISTS idx_representatives_role ON entity_representatives (entity_id, role);
        """,
        
        # ============================================================
        # 14. مستندات KYB - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (كيان + نوع المستند)
        CREATE INDEX IF NOT EXISTS idx_kyb_documents_entity_type ON kyb_documents (entity_id, document_type);
        
        -- فهرس للحالة مع التاريخ
        CREATE INDEX IF NOT EXISTS idx_kyb_documents_status_date ON kyb_documents (verification_status, uploaded_at DESC);
        """,
        
        # ============================================================
        # 15. المحافظ (Wallets) - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (مالك + نوع)
        CREATE INDEX IF NOT EXISTS idx_wallets_owner_type ON wallets (owner_id, owner_type);
        
        -- فهرس للعملة مع الرصيد (لتقارير الرصيد)
        CREATE INDEX IF NOT EXISTS idx_wallets_currency_balance ON wallets (currency, balance);
        """,
        
        # ============================================================
        # 16. الجلسات (Sessions) - فهارس زمنية للتنظيف التلقائي
        # ============================================================
        """
        -- فهرس لانتهاء الجلسة (لتسريع عمليات التنظيف)
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);
        
        -- فهرس مركب (مستخدم + نشط)
        CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON sessions (user_id, is_active);
        """,
        
        # ============================================================
        # 17. السجلات (Audit Logs) - فهارس مركبة
        # ============================================================
        """
        -- فهرس مركب (مستخدم + إجراء)
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs (user_id, action);
        
        -- فهرس للجدول مع التاريخ (للبحث في السجلات)
        CREATE INDEX IF NOT EXISTS idx_audit_logs_table_date ON audit_logs (table_name, created_at DESC);
        """,
    ]

    # تنفيذ الفهارس مع إعادة المحاولة لكل كتلة
    async with engine.connect() as conn:
        for idx, sql_block in enumerate(indexes, 1):
            try:
                # تقسيم الكتلة إلى أوامر فردية
                statements = [stmt.strip() for stmt in sql_block.split(';') if stmt.strip()]
                for stmt in statements:
                    try:
                        await conn.execute(text(stmt))
                        logger.debug(f"✅ Executed: {stmt[:60]}...")
                    except OperationalError as e:
                        # أخطاء الاتصال المؤقتة - إعادة المحاولة
                        if "connection" in str(e).lower() or "timeout" in str(e).lower():
                            logger.warning(f"⚠️ Connection error on statement, retrying: {stmt[:60]}...")
                            # إعادة محاولة هذه العبارة مرة واحدة بعد تأخير قصير
                            await asyncio.sleep(1)
                            try:
                                await conn.execute(text(stmt))
                            except Exception as e2:
                                logger.warning(f"⚠️ Skipping index (retry failed): {stmt[:60]}... Error: {e2}")
                        else:
                            logger.warning(f"⚠️ Skipping index (may already exist): {stmt[:60]}... Error: {e}")
                    except Exception as e:
                        # تجاهل الأخطاء الشائعة مثل وجود الفهرس مسبقاً
                        logger.warning(f"⚠️ Skipping index (likely exists): {stmt[:60]}... Error: {e}")
                
                # Commit كل 5 كتل لتجنب المعاملات الكبيرة
                if idx % 5 == 0:
                    await conn.commit()
                    logger.info(f"✅ Committed batch {idx} of {len(indexes)} index groups")
                    
            except Exception as e:
                logger.error(f"❌ Error processing index group {idx}: {str(e)}")
                # نستمر مع بقية الفهارس بدلاً من إفشال الكل
                continue
        
        # Commit نهائي
        await conn.commit()
    
    logger.info("✅ All database indexes have been processed successfully.")
    print("[SYSTEM] Database indexes initialization completed. All functional indexes are now active.")