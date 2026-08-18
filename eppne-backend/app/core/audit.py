# app/core/audit.py
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Logger مخصص للسجلات الأمنية
audit_logger = logging.getLogger("eppne.audit")
audit_logger.setLevel(logging.INFO)

# سيتم إرفاق معالج ملف خاص به في logging_conf.py لاحقاً
async def audit_log(
    action: str,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
    """تسجيل حركات النظام بصيغة JSON منظمة للامتثال."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "resource_id": resource_id,
        "ip": ip_address,  # سيتم تشفيره في طبقة الأمان قبل الوصول لهنا
        "details": details or {}
    }
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))