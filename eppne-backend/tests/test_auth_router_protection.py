"""
smoke test: auth_router بعد التقسيم.
- /api/auth/login و /api/auth/refresh لازم يفضلوا عامين (من غير get_current_active_user).
- /api/auth/logout, /api/auth/revoke-all, /api/auth/sessions لازم يعتمدوا على
  get_current_active_user القوية من app.core.security (اللي بتفحص session_version)
  مش النسخة الأضعف في app.api.deps.
"""
from app.main import fastapi_app
from app.core.security import get_current_active_user as strong_get_current_active_user
from app.api.deps import get_current_active_user as weak_get_current_active_user
from route_utils import find_route, direct_dependency_calls

PUBLIC_PATHS = ["/api/auth/login", "/api/auth/refresh"]
PROTECTED_PATHS = ["/api/auth/logout", "/api/auth/revoke-all", "/api/auth/sessions"]


def test_public_auth_endpoints_have_no_active_user_dependency():
    for path in PUBLIC_PATHS:
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert strong_get_current_active_user not in calls, f"{path} لازم يفضل عام (public)"
        assert weak_get_current_active_user not in calls, f"{path} لازم يفضل عام (public)"


def test_protected_auth_endpoints_require_strong_active_user():
    for path in PROTECTED_PATHS:
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert strong_get_current_active_user in calls, (
            f"{path} لازم يعتمد على get_current_active_user القوية من core.security"
        )
        assert weak_get_current_active_user not in calls, (
            f"{path} لازم متعتمدش على النسخة الأضعف من api.deps"
        )
