def find_route(fastapi_app, path: str):
    for route in fastapi_app.routes:
        if getattr(route, "path", None) == path:
            return route
    raise AssertionError(f"Route not found: {path}")


def direct_dependency_calls(route):
    """الـ dependency callables المطبقة مباشرة على الـ route (endpoint params + router-level dependencies)،
    من غير النزول جوه الـ sub-dependencies بتاعة كل واحدة منها."""
    return {d.call for d in route.dependant.dependencies}
