# app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import socketio
import time
import json
from typing import Dict, Optional

from app.core.database import engine
from app.core.logging_conf import setup_logging
from app.core.errors import SovereignError, IdempotencyError, RateLimitError
from app.core.redis_client import redis_client  # ملف redis_client الذي أنشأناه

# ==========================================
# استيراد جميع الموجهات (Routers) - 28 قطاعاً
# ==========================================
from app.domains.identity.router import router as identity_router
from app.domains.finance.router import router as finance_router
from app.domains.academy.router import router as academy_router
from app.domains.commerce.router import router as commerce_router
from app.domains.projects.router import router as projects_router
from app.domains.iot.router import router as iot_router
from app.domains.health.router import router as health_router
from app.domains.transport.router import router as transport_router
from app.domains.realestate.router import router as realestate_router
from app.domains.manufacturing.router import router as manufacturing_router
from app.domains.agritech.router import router as agritech_router
from app.domains.tourism_sports.router import router as tourism_sports_router
from app.domains.arbitration_syndicates.router import router as arbitration_syndicates_router
from app.domains.ai_agents.router import router as ai_agents_router
from app.domains.digital_twin.router import router as digital_twin_router
from app.domains.privacy.router import router as privacy_router
from app.domains.social.router import router as social_router
from app.domains.communications.router import router as communications_router
from app.domains.employment.router import router as employment_router
from app.domains.automation.router import router as automation_router
from app.domains.zamakana.router import router as zamakana_router
from app.domains.tenders_auctions.router import router as tenders_auctions_router
from app.domains.insurance.router import router as insurance_router
from app.domains.invitations.router import router as invitations_router
from app.domains.sovereign_entities.router import router as sovereign_router
from app.domains.translation.router import router as translation_router
from app.domains.service_marketplace.router import router as marketplace_router

# ==========================================
# 1. تضمين قطاع المساعد الصوتي 🆕 (جديد)
# ==========================================
from app.domains.voice_assistant.router import router as voice_assistant_router

# ==========================================
# 2. إعداد نظام التسجيل (Logging)
# ==========================================
setup_logging()

# ==========================================
# 3. إدارة دورة حياة التطبيق (Lifespan)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # عند بدء التشغيل
    print("🚀 إطلاق المنصة السيادية EPPNE...")
    await redis_client.initialize()  # تهيئة اتصال Redis
    yield
    # عند الإغلاق
    await engine.dispose()
    await redis_client.close()       # إغلاق اتصال Redis بأمان

# ==========================================
# 4. بناء المحرك الداخلي (FastAPI) 🟢
# ==========================================
fastapi_app = FastAPI(
    title="EPPNE Sovereign Platform",
    version="2.0.0",
    description="المنصة السيادية المتكاملة - 28 قطاعاً خدمياً",
    lifespan=lifespan
)

# ==========================================
# 5. معالجات الأخطاء المخصصة
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

# ==========================================
# 6. الـ Middlewares (الأمان والأداء)
# ==========================================

# 6.1. CORS (يدعم بيئات متعددة)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://eppne.sovereign.eg",      # بيئة الإنتاج
    "https://staging.eppne.sovereign.eg",
]

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6.2. Trusted Host (الحماية من هجمات Host Header)
fastapi_app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # يمكن تقييدها لاحقاً
)

# 6.3. 🔐 وسيط Idempotency الشامل (للعمليات الحساسة)
@fastapi_app.middleware("http")
async def idempotency_middleware(request: Request, call_next):
    """
    يقوم بالتحقق من مفتاح Idempotency للطلبات التي قد تتسبب في تغيير الحالة.
    يقوم بتخزين النتيجة في Redis لمدة 24 ساعة، ويعيدها إذا تكرر الطلب.
    """
    # العمليات الآمنة لا تحتاج إلى Idempotency
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return await call_next(request)

    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        # إذا لم يكن هناك مفتاح، نستمر مع تنبيه بسيط (يمكنك جعله إجبارياً للعمليات الحساسة)
        return await call_next(request)

    # توليد معرف فريد للطلب (بناءً على المسار + المفتاح)
    path = request.url.path
    cache_key = f"idem:{path}:{idem_key}"
    
    # التحقق من Redis أولاً
    cached_response = await redis_client.get_json(cache_key)
    if cached_response:
        # إعادة الرد المخزن سابقاً (لمنع التكرار)
        return JSONResponse(
            status_code=cached_response.get("status_code", 200),
            content=cached_response.get("body", {}),
            headers={"Idempotency-Result": "cached"}
        )

    # تنفيذ الطلب
    response = await call_next(request)

    # تخزين النتيجة في Redis (فقط إذا نجح الطلب)
    if 200 <= response.status_code < 300:
        # قراءة الجسم (لأنه Stream، نحتاج إلى نسخه)
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        response_body = body.decode("utf-8")
        
        # تخزين النتيجة مع صلاحية 24 ساعة
        await redis_client.set_json(
            cache_key,
            {
                "status_code": response.status_code,
                "body": json.loads(response_body) if response_body else {}
            },
            ex=86400  # 24 ساعة
        )
        
        # إعادة بناء الاستجابة (لأننا استهلكنا الـ body iterator)
        return JSONResponse(
            status_code=response.status_code,
            content=json.loads(response_body) if response_body else {},
            headers=dict(response.headers)
        )
    
    return response

# 6.4. ⏱️ وسيط تسجيل زمن الاستجابة (Performance Monitoring)
@fastapi_app.middleware("http")
async def performance_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # تسجيل الطلبات البطيئة للتحليل
    if process_time > 1.0:  # أكثر من ثانية
        print(f"⚠️ بطء في الطلب: {request.method} {request.url.path} - {process_time:.2f}s")
    
    return response

# ==========================================
# 7. تضمين جميع الموجهات (28 قطاعاً)
# ==========================================
routers = [
    identity_router,
    finance_router,
    academy_router,
    commerce_router,
    projects_router,
    iot_router,
    health_router,
    transport_router,
    realestate_router,
    manufacturing_router,
    agritech_router,
    tourism_sports_router,
    arbitration_syndicates_router,
    ai_agents_router,
    digital_twin_router,
    privacy_router,
    social_router,
    communications_router,
    employment_router,
    automation_router,
    zamakana_router,
    tenders_auctions_router,
    insurance_router,
    invitations_router,
    sovereign_router,
    translation_router,
    marketplace_router,
    # ⭐ القطاع الجديد (المساعد الصوتي)
    voice_assistant_router,
]

for router in routers:
    fastapi_app.include_router(router, prefix="/api")

# ==========================================
# 8. نقاط النهاية العامة (Public Endpoints)
# ==========================================
@fastapi_app.get("/health")
async def health():
    return {"status": "Sovereign System Operational", "version": "2.0.0"}

@fastapi_app.get("/ready")
async def readiness():
    # التحقق من جاهزية قاعدة البيانات و Redis
    try:
        await engine.connect()
        await redis_client.ping()
        return {"status": "ready", "components": {"database": "ok", "redis": "ok"}}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )

# ==========================================
# 9. إعداد خادم WebSockets (Socket.IO)
# ==========================================
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=ALLOWED_ORIGINS,
    logger=False,
    engineio_logger=False
)

@sio.event
async def connect(sid, environ, auth):
    print(f"🟢 عميل متصل: {sid}")
    # يمكنك استقبال data من العميل مثل user_id
    # await sio.emit('connected', {'message': 'مرحباً في المنصة السيادية'}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"🔴 عميل منقطع: {sid}")

@sio.event
async def echo(sid, data):
    # مثال: استقبال رسالة وإعادة إرسالها
    await sio.emit('echo_response', {'received': data}, room=sid)

# ==========================================
# 10. التغليف النهائي للمحرك (لتسليمه لـ Uvicorn)
# ==========================================
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path='/ws')