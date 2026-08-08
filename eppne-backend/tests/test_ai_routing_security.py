"""
smoke test: PUT /api/ai/routing لازم يعتمد على get_current_superuser
مش get_current_user (الثغرة الأصلية كانت إن أي مستخدم مسجل دخول يقدر يغيّر
توزيع نسب الـ AI routing على مستوى النظام كله).
"""
from app.main import fastapi_app
from app.core.security import get_current_superuser, get_current_user
from route_utils import find_route, direct_dependency_calls


def test_ai_routing_requires_superuser():
    route = find_route(fastapi_app, "/api/ai/routing")
    direct_calls = direct_dependency_calls(route)

    assert get_current_superuser in direct_calls, (
        "PUT /api/ai/routing لازم يعتمد على get_current_superuser مباشرة"
    )
    assert get_current_user not in direct_calls, (
        "PUT /api/ai/routing لازم متبقاش متاحة لأي مستخدم مسجل دخول (get_current_user) مباشرة"
    )
