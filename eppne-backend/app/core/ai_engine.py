# app/core/ai_engine.py
import json
import logging
import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.errors import AIProviderError
from app.core.features import ensure_ai_available

logger = logging.getLogger(__name__)

# 🔥 جعل المفتاح اختيارياً في بيئة التطوير (يعطل الذكاء الاصطناعي تلقائياً)
AI_API_KEY = os.environ.get("GEMINI_API_KEY")

# إذا لم يكن المفتاح موجوداً، نعطل الميزة ونصدر تحذيراً بدلاً من رفع خطأ
if not AI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY not set. AI features will be disabled.")
    AI_API_KEY = None

# URL يُبنى فقط إذا كان المفتاح موجوداً
AI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={AI_API_KEY}" if AI_API_KEY else None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.TimeoutException),
    reraise=True
)
async def analyze_and_recommend_courses(cognitive_map: dict, learning_style: str, available_courses: list) -> list:
    # Kill Switch — قبل فحص المفتاح وقبل الـ try الداخلي (الذي يبتلع الأخطاء ويرجع [])
    await ensure_ai_available("gemini.recommend_courses")

    # إذا كان المفتاح غير موجود أو الـ URL غير معرف، نرجع قائمة فارغة فوراً
    if not AI_API_KEY or not AI_API_URL:
        logger.info("AI features disabled: returning empty recommendation list.")
        return []

    if not available_courses:
        return []

    catalog = "\n".join([f"- ID: {c.id} | Title: {c.title} | Level: {c.level} | Desc: {c.description}" for c in available_courses])
    
    prompt = f"""... (نفس الكود القديم) ..."""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(AI_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = ai_text.strip().strip("`").removeprefix("json").strip()
            recommended_ids = json.loads(clean_text)
            
            if isinstance(recommended_ids, list):
                return [int(cid) for cid in recommended_ids if str(cid).isdigit()]
            return []
            
    except httpx.TimeoutException as e:
        logger.error(f"AI service timeout: {e}")
        raise AIProviderError("AI service is currently overloaded, please try again later.")
    except Exception as e:
        logger.error(f"AI engine failed: {e}")
        return []