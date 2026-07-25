# ============================================================
# المرحلة 1: بناء الاعتماديات (Builder)
# ============================================================
FROM python:3.11-slim AS builder

# تعيين متغيرات البيئة لتقليل حجم الملفات وتحسين الأداء
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# تثبيت أدوات النظام اللازمة لتثبيت بعض حزم Python (مثل psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ ملف الاعتماديات أولاً (للاستفادة من Cache Layer)
COPY requirements.txt .

# إنشاء بيئة افتراضية وتثبيت الاعتماديات داخلها
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================
# المرحلة 2: الصورة النهائية (Runtime)
# ============================================================
FROM python:3.11-slim

# تثبيت مكتبة libpq و curl (للـ Healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# نسخ البيئة الافتراضية من مرحلة البناء
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# إضافة PYTHONPATH لضمان اكتشاف مسارات التطبيق
ENV PYTHONPATH="/app"

# إنشاء مستخدم غير جذري (Root) لتعزيز الأمان
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# تعيين مجلد العمل
WORKDIR /app

# نسخ كود التطبيق بالكامل (باستثناء الملفات المستثناة في .dockerignore)
COPY --chown=appuser:appgroup . .

# التبديل إلى المستخدم غير الجذري
USER appuser

# تعريض المنفذ الذي يعمل عليه FastAPI
EXPOSE 8000

# ============================================================
# 🔥 Healthcheck (فحص الصحة) - ضروري لـ K8s و Docker Compose
# ============================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ============================================================
# أمر تشغيل التطبيق (مع دعم متغير UVICORN_WORKERS)
# ============================================================
# يستخدم Uvicorn مع عدد عمال (workers) بناءً على متغير البيئة
# أو افتراضياً عدد الـ CPU cores (باستخدام --workers auto)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-4}"]