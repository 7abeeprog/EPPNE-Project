"""
smoke test: identity_router بعد نقله من تغطية test_auth_router_protection.py
(المحذوف مع دومين auth في Phase 4).
- /api/identity/register, /api/identity/login, /api/identity/logout,
  /api/identity/refresh لازم يفضلوا عامين (من غير get_current_active_user).
- /api/identity/me, /api/identity/sessions, /api/identity/revoke-all,
  /api/identity/me/password لازم يعتمدوا على get_current_active_user
  القوية من app.core.security (اللي بتفحص session_version) مش النسخة
  الأضعف في app.api.deps.
"""
from app.main import fastapi_app
from app.core.security import get_current_active_user as strong_get_current_active_user
from app.api.deps import get_current_active_user as weak_get_current_active_user
from route_utils import find_route, direct_dependency_calls

PUBLIC_PATHS = ["/api/identity/register", "/api/identity/login", "/api/identity/logout", "/api/identity/refresh"]
PROTECTED_PATHS = ["/api/identity/me", "/api/identity/sessions", "/api/identity/revoke-all", "/api/identity/me/password"]


def test_public_identity_endpoints_have_no_active_user_dependency():
    for path in PUBLIC_PATHS:
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert strong_get_current_active_user not in calls, f"{path} لازم يفضل عام (public)"
        assert weak_get_current_active_user not in calls, f"{path} لازم يفضل عام (public)"


def test_protected_identity_endpoints_require_strong_active_user():
    for path in PROTECTED_PATHS:
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert strong_get_current_active_user in calls, (
            f"{path} لازم يعتمد على get_current_active_user القوية من core.security"
        )
        assert weak_get_current_active_user not in calls, (
            f"{path} لازم متعتمدش على النسخة الأضعف من api.deps"
        )
