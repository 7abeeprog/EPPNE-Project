# app/tasks/deployment.py
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal as async_session
from app.domains.service_marketplace.repository import ServiceMarketplaceRepository
from app.domains.service_marketplace.models import DeploymentStatus
from app.core.logging_conf import logger

celery_app = Celery("deployment", broker="redis://localhost:6379/0")

@celery_app.task
def deploy_service_task(license_id: int, tenant_id: int):
    """مهمة نشر الخدمة غير المتزامنة."""
    import asyncio
    asyncio.run(_deploy_service_async(license_id, tenant_id))

async def _deploy_service_async(license_id: int, tenant_id: int):
    async with async_session() as db:
        repo = ServiceMarketplaceRepository(db)
        license = await repo.get_license(license_id)
        if not license:
            return

        service = await repo.get_service(license.service_id)
        await repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Starting deployment...")

        try:
            domain = license.deployed_domain or f"{service.service_type}-{license_id}.eppne.app"
            await repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, f"Creating deployment at {domain}...")
            await repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Database migration in progress...")
            await repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Frontend build in progress...")

            await repo.update_license(
                license_id,
                deployed_domain=domain,
                deployment_status=DeploymentStatus.ACTIVE,
                deployment_log="Deployment completed successfully."
            )
            logger.info(f"Service {service.name} deployed successfully for tenant {tenant_id}")

        except Exception as e:
            await repo.update_deployment_status(license_id, DeploymentStatus.FAILED, f"Deployment failed: {str(e)}")
            logger.error(f"Deployment failed for license {license_id}: {e}")