"""
smoke test: كل method في IoTRepository و PrivacyRepository بتعمل
SELECT/UPDATE/DELETE/INSERT على الجداول العشرة، لازم تاخد tenant_id كباراميتر
مطلوب (من غير قيمة افتراضية) عشان نضمن إن الاستدعاء متمرش من غير tenant_id.
"""
import inspect

from app.domains.iot.repository import IoTRepository
from app.domains.privacy.repository import PrivacyRepository

IOT_METHODS = [
    "create_asset", "get_asset", "list_assets", "update_asset",
    "create_grid", "get_grid", "list_grids", "update_grid_load",
    "create_reading", "list_readings", "get_unsettled_carbon_credits",
    "mark_carbon_settled", "create_maintenance", "resolve_maintenance",
    "get_idempotency", "save_idempotency", "log_request",
]

PRIVACY_METHODS = [
    "get_privacy_settings", "update_privacy_settings", "create_consent_log",
    "create_erasure_request", "get_erasure_request", "get_pending_erasure_request",
    "list_erasure_requests", "get_pending_erasure_requests_for_admin",
    "update_erasure_request", "create_tombstone", "get_tombstones_by_user",
    "update_tombstone_by_tx", "_estimate_row_count", "_estimate_pending_count",
    "get_erasure_requests_with_tombstones",
]


def _assert_requires_tenant_id(cls, method_name: str):
    method = getattr(cls, method_name)
    params = inspect.signature(method).parameters
    assert "tenant_id" in params, f"{cls.__name__}.{method_name} لازم ياخد tenant_id"
    assert params["tenant_id"].default is inspect.Parameter.empty, (
        f"{cls.__name__}.{method_name}: tenant_id لازم يبقى مطلوب (من غير قيمة افتراضية)"
    )


def test_iot_repository_methods_require_tenant_id():
    for name in IOT_METHODS:
        _assert_requires_tenant_id(IoTRepository, name)


def test_privacy_repository_methods_require_tenant_id():
    for name in PRIVACY_METHODS:
        _assert_requires_tenant_id(PrivacyRepository, name)
