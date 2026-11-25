"""Static check between the backend routes and the frontend API calls.

Run from the repository root:
    python -m pytest tests/test_endpoint_usage.py -v -s

The last test prints the full matrix; -s is needed to see it.
No running server or database is required for this file.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_FILE = ROOT / "apps" / "backend" / "main.py"
BACKEND_ROUTERS_DIR = ROOT / "apps" / "backend" / "routers"
FRONTEND_FILE = ROOT / "apps" / "operations-web" / "src" / "lib" / "api.js"

# Utility endpoints that are not part of the UI contract.
ALLOWED_UNUSED = {("GET", "/"), ("GET", "/health")}

ROUTE_RE = re.compile(r'@(?:app|router)\.(get|post|patch|put|delete)\(\s*["\']([^"\']+)["\']')
CALL_RE = re.compile(r'request\(\s*["\'`](/[^"\'`]+)["\'`]')
METHOD_RE = re.compile(r'method:\s*["\'](GET|POST|PATCH|PUT|DELETE)["\']')
PLACEHOLDER_RE = re.compile(r"\$\{[^{}]*\}|\{[^{}]*\}")


def normalize(path):
    """Make {empleado_id} and ${encodeURIComponent(id)} comparable."""
    return PLACEHOLDER_RE.sub("{}", path)


def backend_routes():
    routes = set()
    files = [BACKEND_FILE, *sorted(BACKEND_ROUTERS_DIR.glob("*.py"))]
    for path in files:
        text = path.read_text(encoding="utf-8")
        routes.update(
            (match.group(1).upper(), normalize(match.group(2)))
            for match in ROUTE_RE.finditer(text)
        )
    return routes


def frontend_calls():
    text = FRONTEND_FILE.read_text(encoding="utf-8")
    calls = set()
    for line in text.splitlines():
        call = CALL_RE.search(line)
        if not call:
            continue
        method = METHOD_RE.search(line)
        calls.add((method.group(1).upper() if method else "GET", normalize(call.group(1))))
    return calls


def test_frontend_calls_have_backend_routes():
    missing = sorted(frontend_calls() - backend_routes())
    detail = ", ".join(f"{method} {path}" for method, path in missing)
    assert not missing, f"El frontend llama a rutas que el backend no expone: {detail}"


def test_backend_routes_are_used():
    unused = sorted(backend_routes() - frontend_calls() - ALLOWED_UNUSED)
    detail = ", ".join(f"{method} {path}" for method, path in unused)
    assert not unused, f"Endpoints del backend sin uso en el frontend: {detail}"


def test_coverage_report():
    routes = sorted(backend_routes())
    calls = frontend_calls()
    print("\nMETODO  RUTA                                        FRONTEND")
    for method, path in routes:
        status = "USADO" if (method, path) in calls else "SIN USO"
        print(f"{method:<7} {path:<44} {status}")
    for method, path in sorted(calls - set(routes)):
        print(f"{method:<7} {path:<44} SIN RUTA EN BACKEND")
