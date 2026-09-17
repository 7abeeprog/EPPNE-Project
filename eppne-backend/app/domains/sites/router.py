# app/domains/sites/router.py
"""صفر endpoint فعلي بعد — الهدف الوحيد من وجود الملف ده هو تسجيل
`app.domains.sites.models` في Base.metadata عبر main.py، بنفس الآلية
المتبعة فعليًا لكل دومين تاني في المشروع (main.py يستورد router فقط،
والاستيراد بيسحب service→repository→models بالتبعية). صفر router في
دومين = صفر تسجيل models في العملية الفعلية — اكتُشف ده حيًا في جلسة
ربط iot.SmartAsset بـsite_id (NoReferencedTableError). راجع:
.claude/reports/unified-site-model-and-academy-camera-design-proposal.md
"""
from fastapi import APIRouter
from app.domains.sites import models as _models  # noqa: F401 — يسجّل Site في Base.metadata (صفر service/repository بعد)

router = APIRouter(prefix="/sites", tags=["Sites"])
