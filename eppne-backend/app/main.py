# app/main.py
from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import socketio
import time
import json
import uuid
from typing import Dict, Optional, Any

from app.core.database import engine
from app.core.logging_conf import setup_logging, logger, set_trace_id
from app.core.errors import SovereignError, IdempotencyError, RateLimitError
from app.core.redis_client import redis_client
from app.core.config import settings

# ==========================================
# استيرادات الإضافات الأساسية
# ==========================================
from app.core.database_indexes import create_indexes
# from app.core.metrics import metrics

# 🔥 استيراد dependencies الخاصة بالمصادقة والصلاحيات
from app.api.deps import get_current_user, get_current_user_optional, require_sector
from app.domains.identity.models import User

# ==========================================
# استيراد جميع الموجهات (Routers) المتوافقة مع الشجرة
# ==========================================
from app.domains.academy.router import router as academy_router
from app.domains.affiliate.router import router as affiliate_router
from app.domains.agritech.router import router as agritech_router
from app.domains.ai_agents.router import router as ai_agents_router
from app.domains.ai_governance.router import router as ai_governance_router
from app.domains.arbitration_syndicates.router import router as arbitration_syndicates_router
from app.domains.auth.router import router as auth_router
from app.domains.automation.router import router as automation_router
from app.domains.command.router import router as command_router
from app.domains.commerce.router import router as commerce_router
from app.domains.communications.router import router as communications_router
from app.domains.employment.router import router as employment_router
from app.domains.finance.router import router as finance_router
from app.domains.health.router import router as health_router
from app.domains.identity.router import router as identity_router
from app.domains.insurance.router import router as insurance_router
from app.domains.invitations.router import router as invitations_router
from app.domains.iot.router import router as iot_router
from app.domains.logistics.router import router as logistics_router
from app.domains.manufacturing.router import router as manufacturing_router
from app.domains.privacy.router import router as privacy_router
from app.domains.projects.router import router as projects_router
from app.domains.realestate.router import router as realestate_router
from app.domains.saas.router import router as saas_router
from app.domains.service_marketplace.router import router as marketplace_router
from app.domains.social.router import router as social_router
from app.domains.sovereign_entities.router import router as sovereign_router
from app.domains.tenders_auctions.router import router as tenders_auctions_router
from app.domains.tourism_sports.router import router as tourism_sports_router
from app.domains.translation.router import router as translation_router
from app.domains.transport.router import router as transport_router
from app.domains.digital_twin.router import router as digital_twin_router
from app.domains.zamakana.router import router as zamakana_router

import sqlalchemy.orm.clsregistry as clsregistry

print("--- فحص سجل كلاسات SQLAlchemy ---")

# ==========================================
# إعداد نظام التسجيل و دورة الحياة
# ==========================================
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق (بدء التشغيل والإيقاف)."""
    logger.info("🚀 إطلاق المنصة السيادية EPPNE...")
    
    # تهيئة Redis
    await redis_client.initialize()
    
    # إنشاء الفهارس في قاعدة البيانات
    await create_indexes()
    
    logger.info("✅ تم تهيئة جميع المكونات الأساسية.")
    yield
    
    # تنظيف الموارد عند الإيقاف
    await engine.dispose()
    await redis_client.close()
    logger.info("🛑 تم إيقاف المنصة السيادية EPPNE.")


# ==========================================
# بناء المحرك الداخلي
# ==========================================
fastapi_app = FastAPI(
    title="EPPNE Sovereign Platform",
    version="2.0.0",
    description="المنصة السيادية المتكاملة - جميع القطاعات",
    lifespan=lifespan
)


# ==========================================
# معالجات الأخطاء المخصصة
# ==========================================
@fastapi_app.exception_handler(SovereignError)
async def sovereign_error_handler(request: Request, exc: SovereignError):
    return JSONResponse(
        status_code=exc.status_code or 400,
        content={"detail": exc.message, "code": exc.code}
    )


@fastapi_app.exception_handler(IdempotencyError)
async def idempotency_error_handler(request: Request, exc: IdempotencyError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "code": "IDEMPOTENCY_CONFLICT"}
    )


@fastapi_app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": exc.message, "code": "RATE_LIMIT_EXCEEDED"}
    )


# ============================================================
#  🔥 MIDDLEWARE 1: Trace-ID & Request-ID (يُضاف أولاً)
# ============================================================
@fastapi_app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """
    إضافة Trace-ID لكل طلب للربط مع السجلات في بيئة موزعة.
    - يقرأ X-Trace-ID من الهيدر إن وُجد، أو يُنشئ واحداً جديداً.
    - يُخزّنه في request.state.trace_id لاستخدامه في السجلات.
    - يُخزّنه في ContextVar للـ Logging باستخدام set_trace_id().
    - يُعيده في Response Headers لتتبعه من العميل.
    """
    trace_id = request.headers.get("X-Trace-ID")
    if not trace_id:
        trace_id = str(uuid.uuid4())
    
    request.state.trace_id = trace_id
    set_trace_id(trace_id)
    
    request_id = request.headers.get("X-Request-ID", trace_id[:8])
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    
    return response


# ============================================================
#  MIDDLEWARE 2: Idempotency (مع دعم المسار وحفظ الهيدرز)
# ============================================================
@fastapi_app.middleware("http")
async def idempotency_middleware(request: Request, call_next):
    """
    تنفيذ Idempotency للطلبات غير الآمنة (POST, PUT, PATCH, DELETE).
    - يخزن استجابة الطلب الناجح (2xx) مع الهيدرز في Redis لمدة 24 ساعة.
    - يعيد الاستجابة المخزّنة (مع الهيدرز الأصلية) إذا تكرر نفس المفتاح لنفس المسار.
    """
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return await call_next(request)

    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        return await call_next(request)

    path = request.url.path
    cache_key = f"idem:{path}:{idem_key}"
    
    cached_response = await redis_client.get_json(cache_key)
    if cached_response:
        logger.info(f"🔄 Idempotency cache hit: {cache_key}")
        return JSONResponse(
            status_code=cached_response.get("status_code", 200),
            content=cached_response.get("body", {}),
            headers=cached_response.get("headers", {})
        )

    response = await call_next(request)

    if 200 <= response.status_code < 300:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        response_body = body.decode("utf-8")
        
        await redis_client.set_json(
            cache_key,
            {
                "status_code": response.status_code,
                "body": json.loads(response_body) if response_body else {},
                "headers": dict(response.headers)
            },
            ex=86400
        )
        
        logger.info(f"✅ Idempotency stored for: {cache_key}")
        
        return JSONResponse(
            status_code=response.status_code,
            content=json.loads(response_body) if response_body else {},
            headers=dict(response.headers)
        )
    
    return response


# ============================================================
#  MIDDLEWARE 3: CORS (السماح بالنطاقات)
# ============================================================
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"] + getattr(settings, "ALLOWED_ORIGINS", []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Skip", "X-Limit", "X-Process-Time", "X-Trace-ID"],
    max_age=3600,
)


# ============================================================
#  MIDDLEWARE 4: Trusted Hosts
# ============================================================
fastapi_app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)


# ============================================================
#  MIDDLEWARE 5: أداء (Performance)
# ============================================================
@fastapi_app.middleware("http")
async def performance_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    if process_time > 1.0:
        trace_id = getattr(request.state, "trace_id", "unknown")
        logger.warning(
            f"⚠️ بطء في الطلب: {request.method} {request.url.path} - {process_time:.2f}s [Trace: {trace_id}]"
        )
    return response


# ==========================================
# 🔥 تضمين جميع الموجهات مع صلاحيات القطاعات (Sector Permissions)
# ==========================================
# تعريف كل Router مع القطاع المطلوب (يُستثنى auth_router لأنه عام)
routers_config = [
    # (router_obj, prefix_path, tags_list, sector)
    (academy_router, "/academy", ["Academy"], "academy"),
    (affiliate_router, "/affiliate", ["Affiliate"], "affiliate"),
    (agritech_router, "/agritech", ["Agritech"], "agritech"),
    (ai_agents_router, "/ai-agents", ["AI Agents"], "ai"),
    (ai_governance_router, "/ai-governance", ["AI Governance"], "ai"),
    (arbitration_syndicates_router, "/arbitration", ["Arbitration Syndicates"], "arbitration"),
    (automation_router, "/automation", ["Automation"], "automation"),
    (command_router, "/command", ["Command Center"], "command"),
    (commerce_router, "/commerce", ["Commerce"], "commerce"),
    (communications_router, "/communications", ["Communications"], "communications"),
    (digital_twin_router, "/digital-twin", ["Digital Twin"], "digital_twin"),
    (employment_router, "/employment", ["Employment"], "employment"),
    (finance_router, "/finance", ["Finance"], "finance"),
    (health_router, "/health", ["Health"], "health"),
    (identity_router, "/identity", ["Identity"], "identity"),
    (insurance_router, "/insurance", ["Insurance"], "insurance"),
    (invitations_router, "/invitations", ["Invitations"], "invitations"),
    (iot_router, "/iot", ["IoT"], "iot"),
    (logistics_router, "/logistics", ["Logistics"], "logistics"),
    (manufacturing_router, "/manufacturing", ["Manufacturing"], "manufacturing"),
    (privacy_router, "/privacy", ["Privacy"], "privacy"),
    (projects_router, "/projects", ["Projects"], "projects"),
    (realestate_router, "/realestate", ["Real Estate"], "realestate"),
    (saas_router, "/saas", ["SaaS"], "saas"),
    (marketplace_router, "/marketplace", ["Service Marketplace"], "marketplace"),
    (social_router, "/social", ["Social"], "social"),
    (sovereign_router, "/sovereign", ["Sovereign Entities"], "sovereign"),
    (tenders_auctions_router, "/tenders", ["Tenders & Auctions"], "tenders"),
    (tourism_sports_router, "/tourism-sports", ["Tourism & Sports"], "tourism"),
    (translation_router, "/translation", ["Translation"], "translation"),
    (transport_router, "/transport", ["Transport"], "transport"),
    (zamakana_router, "/zamakana", ["Zamakana"], "zamakana"),
]

# تضمين Routers القطاعات مع تطبيق require_sector
for router_obj, prefix_path, tags_list, sector in routers_config:
    fastapi_app.include_router(
        router_obj,
        prefix="/api",
        tags=tags_list,
        dependencies=[Depends(require_sector(sector))]  # 🔥 تطبيق صلاحية القطاع
    )

# 🔥 استثناء Router المصادقة (يُسمح للجميع)
fastapi_app.include_router(auth_router, prefix="/api", tags=["Authentication"])


# ==========================================
# نقاط النهاية العامة (الصحة والجاهزية) – بدون حماية
# ==========================================
@fastapi_app.get("/health")
async def health():
    """
    نقطة فحص الصحة (Liveness Probe) – تُستخدم في K8s للتحقق من أن الحاوية تعمل.
    """
    return {"status": "Sovereign System Operational", "version": "2.0.0"}


@fastapi_app.get("/ready")
async def readiness():
    """
    نقطة فحص الجاهزية (Readiness Probe) – تُستخدم في K8s للتحقق من جاهزية الخدمة.
    تتحقق من: اتصال قاعدة البيانات، اتصال Redis.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        await redis_client.ping()
        return {"status": "ready", "components": {"database": "ok", "redis": "ok"}}
    except Exception as e:
        logger.error(f"❌ Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )


# ==========================================
# نقاط النهاية للذكاء الاصطناعي (تستخدم optional user)
# ==========================================
@fastapi_app.post("/api/ai/chat")
async def ai_chat(
    request: Request,
    body: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    from app.services.ai import ai_engine, TaskType
    result = await ai_engine.generate(
        prompt=body.get("prompt", ""),
        system_prompt=body.get("system_prompt"),
        language=body.get("language", "ar"),
        task_type=TaskType(body.get("task_type", "arabic_chat")),
        use_cache=body.get("use_cache", True),
        use_batch=body.get("use_batch", False),
        max_tokens=body.get("max_tokens", 2048),
        temperature=body.get("temperature", 0.7),
    )
    return result


@fastapi_app.get("/api/ai/cost")
async def get_ai_cost(
    model_id: Optional[str] = None,
    period: str = "total",
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    from app.services.ai import CostTracker
    if period == "daily":
        data = await CostTracker.get_daily_cost(model_id) if model_id else {"error": "الرجاء تحديد النموذج"}
    elif period == "monthly":
        data = await CostTracker.get_monthly_cost(model_id) if model_id else {"error": "الرجاء تحديد النموذج"}
    else:
        data = await CostTracker.get_total_cost(model_id)
    return data


@fastapi_app.put("/api/ai/routing")
async def update_ai_routing(
    percentages: Dict[str, int],
    current_user: User = Depends(get_current_user),  # يتطلب توكن صالح
):
    from app.services.ai import AIRouter, AIModelId
    new_percentages = {}
    for key, value in percentages.items():
        try:
            model_id = AIModelId(key)
            new_percentages[model_id] = value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"نموذج غير معروف: {key}")

    AIRouter.update_routing_percentages(new_percentages)
    return {"status": "updated", "percentages": new_percentages}


# ==========================================
# إعداد خادم WebSockets
# ==========================================
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.ALLOWED_ORIGINS,
    logger=False,
    engineio_logger=False
)

@sio.event
async def connect(sid, environ, auth):
    print(f"🟢 عميل متصل: {sid}")

@sio.event
async def disconnect(sid):
    print(f"🔴 عميل منقطع: {sid}")

@sio.event
async def echo(sid, data):
    await sio.emit('echo_response', {'received': data}, room=sid)

# إنشاء التطبيق النهائي (ASGI)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path='/ws')