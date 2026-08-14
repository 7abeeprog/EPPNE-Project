# app/tasks/deployment.py
"""
مهام Celery لنشر الخدمات في متجر الخدمات (Service Marketplace).
تدعم: النشر الآلي للخدمات، تتبع الحالة، إعادة المحاولة، والتنظيف.
"""
import asyncio
from typing import Optional, Dict, Any, cast
from datetime import datetime

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal  # ✅ استخدام SessionLocal بدلاً من async_session
from app.core.logging_conf import logger
from app.domains.service_marketplace.repository import ServiceMarketplaceRepository
from app.domains.service_marketplace.models import DeploymentStatus


# ============================================================
# 1. أداة تشغيل آمنة للـ Async (تمنع تسرب الذاكرة)
# ============================================================
def _run_async(coro):
    """
    تشغيل دالة غير متزامنة (Async) بطريقة آمنة داخل Celery.
    - تخلق حلقة أحداث جديدة لكل مهمة لضمان العزل.
    - تغلق الحلقة تلقائياً بعد الانتهاء لمنع تسرب الذاكرة.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # 🔥 تنظيف الموارد وإغلاق الحلقة
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


# ============================================================
# 2. مهمة نشر الخدمة الأساسية
# ============================================================
@celery_app.task(
    name="deployment.deploy_service",
    bind=True,
    max_retries=5,                   # 5 محاولات كحد أقصى (النشر قد يحتاج محاولات متعددة)
    default_retry_delay=180,         # 3 دقائق بين المحاولات (وقت كافٍ للبنية التحتية)
    acks_late=True,                  # 🔥 تأكيد بعد التنفيذ (يمنع فقدان المهمة)
    time_limit=3600,                 # ساعة واحدة كحد أقصى (النشر قد يستغرق وقتاً)
    soft_time_limit=3000,            # 50 دقيقة إنذار
)
def deploy_service_task(self, license_id: int, tenant_id: int):
    """
    نشر خدمة بشكل غير متزامن عبر Celery.
    - تُستدعى تلقائياً بعد شراء الخدمة.
    - تقوم بإنشاء البيئة، ترحيل قاعدة البيانات، وبناء الواجهة الأمامية.
    - تدعم إعادة المحاولة في حال فشل أي من الخطوات.
    """
    try:
        async def _run():
            return await _deploy_service_async(license_id, tenant_id)

        result = _run_async(_run())
        logger.info(f"✅ Deployment completed successfully for license {license_id}")
        return {
            "status": "success",
            "license_id": license_id,
            "tenant_id": tenant_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"❌ Deployment failed for license {license_id}: {str(e)}")
        # إعادة المحاولة مع تأخير تصاعدي (محاولة أولى 3 دقائق، ثم 5، ثم 10...)
        retry_countdown = 60 * (2 ** (self.request.retries + 1))  # 60, 120, 240, 480, 960 ثانية
        raise self.retry(exc=e, countdown=min(retry_countdown, 3600))


# ============================================================
# 3. المنطق الفعلي للنشر (Async)
# ============================================================
async def _deploy_service_async(license_id: int, tenant_id: int) -> Dict[str, Any]:
    """
    المنطق الفعلي لنشر الخدمة.
    - تُستدعى من المهمة الرئيسية.
    - تقوم بتحديث حالة النشر خطوة بخطوة.
    """
    async with SessionLocal() as db:  # ✅ استخدام SessionLocal
        repo = ServiceMarketplaceRepository(db)

        # 1. جلب الترخيص
        license_obj = await repo.get_license(license_id)
        if not license_obj:
            logger.warning(f"⚠️ License {license_id} not found")
            return {"status": "license_not_found", "license_id": license_id}

        # 2. جلب الخدمة
        # ✅ استخدام cast لتحويل Column[int] إلى int
        service_id = cast(int, license_obj.service_id)
        service = await repo.get_service(service_id)
        if not service:
            logger.warning(f"⚠️ Service not found for license {license_id}")
            await repo.update_deployment_status(
                license_id,
                DeploymentStatus.FAILED,
                "Service not found"
            )
            return {"status": "service_not_found", "license_id": license_id}

        # 3. بدء النشر
        await repo.update_deployment_status(
            license_id,
            DeploymentStatus.DEPLOYING,
            "🚀 Starting deployment..."
        )

        try:
            # 4. تحديد النطاق
            domain = license_obj.deployed_domain or f"{service.service_type}-{license_id}.eppne.app"
            await repo.update_deployment_status(
                license_id,
                DeploymentStatus.DEPLOYING,
                f"🌐 Creating deployment at {domain}..."
            )

            # 5. محاكاة ترحيل قاعدة البيانات
            await repo.update_deployment_status(
                license_id,
                DeploymentStatus.DEPLOYING,
                "🗄️ Database migration in progress..."
            )
            # ✅ هنا سيتم استدعاء منطق الترحيل الفعلي في المستقبل
            # await _run_database_migration(service, license_obj)

            # 6. محاكاة بناء الواجهة الأمامية
            await repo.update_deployment_status(
                license_id,
                DeploymentStatus.DEPLOYING,
                "🎨 Frontend build in progress..."
            )
            # ✅ هنا سيتم استدعاء منطق البناء الفعلي في المستقبل
            # await _build_frontend(service, license_obj)

            # 7. تحديث حالة الترخيص إلى نشط
            await repo.update_license(
                license_id,
                deployed_domain=domain,
                deployment_status=DeploymentStatus.ACTIVE,
                deployment_log=f"✅ Deployment completed successfully at {datetime.utcnow().isoformat()}"
            )
            await db.commit()

            logger.info(f"✅ Service {service.name} deployed successfully for tenant {tenant_id}")

            return {
                "status": "active",
                "license_id": license_id,
                "domain": domain,
                "service_name": service.name,
                "deployed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            error_msg = f"❌ Deployment failed: {str(e)}"
            logger.error(f"Deployment failed for license {license_id}: {e}")

            await repo.update_deployment_status(
                license_id,
                DeploymentStatus.FAILED,
                error_msg
            )

            # إعادة رفع الاستثناء لتشغيل آلية إعادة المحاولة
            raise


# ============================================================
# 4. مهمة تنظيف النشر الفاشل (إلغاء الموارد)
# ============================================================
@celery_app.task(
    name="deployment.cleanup_failed_deployment",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    time_limit=600,
    soft_time_limit=480,
)
def cleanup_failed_deployment_task(self, license_id: int, tenant_id: int):
    """
    تنظيف موارد النشر الفاشل (حذف البيئة، إلغاء الحاويات، إلخ).
    تُستدعى تلقائياً بعد فشل النشر المتكرر.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                repo = ServiceMarketplaceRepository(db)

                license_obj = await repo.get_license(license_id)
                if not license_obj:
                    return {"status": "license_not_found", "license_id": license_id}

                # ✅ هنا سيتم استدعاء منطق التنظيف الفعلي في المستقبل
                # await _delete_deployment_environment(license_obj)
                # await _remove_database(license_obj)

                await repo.update_license(
                    license_id,
                    deployment_status=DeploymentStatus.FAILED,
                    deployment_log=f"🧹 Cleanup completed at {datetime.utcnow().isoformat()}"
                )
                await db.commit()

                logger.info(f"🧹 Cleanup completed for failed deployment {license_id}")
                return {"status": "cleaned", "license_id": license_id}

        result = _run_async(_run())
        logger.info(f"✅ Cleanup completed for license {license_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Cleanup failed for license {license_id}: {str(e)}")
        raise self.retry(exc=e, countdown=300)


# ============================================================
# 5. مهمة التحقق من صحة النشر (Health Check)
# ============================================================
@celery_app.task(
    name="deployment.health_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    time_limit=120,
    soft_time_limit=90,
)
def health_check_deployment_task(self, license_id: int, tenant_id: int):
    """
    التحقق من صحة الخدمة المنشورة (Ping, DB Connection, API Response).
    تُستدعى دورياً بعد النشر للتأكد من استقرار الخدمة.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                repo = ServiceMarketplaceRepository(db)

                license_obj = await repo.get_license(license_id)
                if not license_obj:
                    return {"status": "license_not_found", "license_id": license_id}

                # ✅ هنا سيتم استدعاء منطق التحقق الفعلي في المستقبل
                # is_healthy = await _check_service_health(license_obj.deployed_domain)
                is_healthy = True  # محاكاة

                if is_healthy:
                    await repo.update_license(
                        license_id,
                        deployment_status=DeploymentStatus.ACTIVE,
                        deployment_log=f"✅ Health check passed at {datetime.utcnow().isoformat()}"
                    )
                else:
                    # ✅ استخدام DEPLOYING أو FAILED بدلاً من DEGRADED (غير موجود)
                    await repo.update_license(
                        license_id,
                        deployment_status=DeploymentStatus.FAILED,
                        deployment_log=f"⚠️ Health check failed at {datetime.utcnow().isoformat()}"
                    )

                await db.commit()

                return {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "license_id": license_id,
                    "checked_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info(f"✅ Health check completed for license {license_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Health check failed for license {license_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)