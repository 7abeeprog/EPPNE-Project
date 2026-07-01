# app/core/ai_engine.py
import json
import logging
import httpx
import os

logger = logging.getLogger(__name__)

# تأكد من وضع المفتاح في ملف .env الخاص بك
AI_API_KEY = os.getenv("GEMINI_API_KEY", "your_api_key_here")
# رابط API كمثال (يمكن تغييره حسب النموذج المستخدم)
AI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={AI_API_KEY}"

async def analyze_and_recommend_courses(cognitive_map: dict, learning_style: str, available_courses: list) -> list:
    """
    يقوم هذا الوكيل بتحليل التوأم الرقمي ومطابقته مع الكورسات المتاحة.
    """
    if not available_courses:
        return []

    # تجهيز كتالوج الكورسات للذكاء الاصطناعي
    catalog = "\n".join([f"- ID: {c.id} | Title: {c.title} | Level: {c.level} | Desc: {c.description}" for c in available_courses])
    
    prompt = f"""
    أنت مستشار أكاديمي خبير في منصة EPPNE السيادية.
    أمامك التوأم الرقمي لطالب، ومطلوب منك ترشيح الكورسات الأنسب لمعالجة نقاط ضعفه وتطوير مهاراته.
    
    بيانات الطالب:
    - نمط التعلم المهيمن: {learning_style}
    - الخريطة الإدراكية (نقاط القوة والضعف): {json.dumps(cognitive_map, ensure_ascii=False)}
    
    كتالوج الكورسات المتاحة في الأكاديمية:
    {catalog}
    
    قم بتحليل حالة الطالب، ثم أرجع ردك بصيغة JSON فقط يحتوي على مصفوفة أرقام (IDs) للكورسات المرشحة، بدون أي نصوص إضافية.
    مثال للرد المطلوب: [1, 4, 7]
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2} # درجة حرارة منخفضة لضمان دقة الردود وصيغة الـ JSON
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(AI_API_URL, json=payload, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
            # استخراج النص من رد الذكاء الاصطناعي
            ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # تنظيف النص لاستخراج مصفوفة الـ JSON
            clean_text = ai_text.strip().strip("`").removeprefix("json").strip()
            recommended_ids = json.loads(clean_text)
            
            if isinstance(recommended_ids, list):
                return [int(cid) for cid in recommended_ids if str(cid).isdigit()]
            return []
            
    except Exception as e:
        logger.error(f"فشل محرك الذكاء الاصطناعي في توليد التوصيات: {e}")
        return []