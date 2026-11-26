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
CUSTOMER_FRONTEND_FILE = ROOT / "apps" / "customer-web" / "src" / "lib" / "api.js"
ADMIN_FRONTEND_FILE = ROOT / "apps" / "admin-web" / "src" / "lib" / "api.js"

# Utility endpoints that are not part of a browser UI contract.
ALLOWED_UNUSED = {
    ("GET", "/"), ("GET", "/health"),
    # Mercado Pago calls this server-to-server with a signed notification.
    ("POST", "/customer/payments/webhook"),
}

ROUTE_RE = re.compile(r'@(?:app|router)\.(get|post|patch|put|delete)\(\s*["\']([^"\']+)["\']')
CALL_RE = re.compile(r'request\(\s*["\'`](/[^"\'`]+)["\'`]')
ARROW_METHOD_RE = re.compile(r'\b(get|post|patch|put|delete)\(\s*["\'`](/[^"\'`]+)["\'`]', re.I)
METHOD_RE = re.compile(r'method:\s*["\'](GET|POST|PATCH|PUT|DELETE)["\']')
PLACEHOLDER_RE = re.compile(r"\$\{[^{}]*\}|\{[^{}]*\}")
PREFIX_RE = re.compile(r'APIRouter\(\s*prefix\s*=\s*["\']([^"\']+)["\']')


def normalize(path):
    """Make {empleado_id} and ${encodeURIComponent(id)} comparable."""
    return PLACEHOLDER_RE.sub("{}", path)


def backend_routes():
    routes = set()
    files = [BACKEND_FILE, *sorted(BACKEND_ROUTERS_DIR.glob("*.py"))]
    for path in files:
        text = path.read_text(encoding="utf-8")
        prefix_match = PREFIX_RE.search(text)
        prefix = prefix_match.group(1) if prefix_match else ""
        routes.update(
            (match.group(1).upper(), normalize(prefix + match.group(2)))
            for match in ROUTE_RE.finditer(text)
        )
    return routes


def frontend_calls():
    calls = set()
    for source in (FRONTEND_FILE, ADMIN_FRONTEND_FILE):
        text = source.read_text(encoding="utf-8")
        for line in text.splitlines():
            call = CALL_RE.search(line)
            if call:
                method = METHOD_RE.search(line)
                calls.add((method.group(1).upper() if method else "GET", normalize(call.group(1))))
                continue
            arrow = ARROW_METHOD_RE.search(line)
            if arrow:
                calls.add((arrow.group(1).upper(), normalize(arrow.group(2))))
    return calls


CUSTOMER_CALL_RE = re.compile(
    r'\b(request|post|get|put|patch|delete)\(\s*["\'`](/[^"\'`]*)["\'`]'
)


def customer_frontend_calls():
    """Calls from customer-web, whose request() already prefixes /customer."""
    text = CUSTOMER_FRONTEND_FILE.read_text(encoding="utf-8")
    calls = set()
    for verb, raw in CUSTOMER_CALL_RE.findall(text):
        method = "GET" if verb == "request" else verb.upper()
        path = re.sub(r"\$\{[^}]*\}", "{}", raw.split("?", 1)[0])
        calls.add((method, normalize("/customer" + path)))
    return calls


def all_frontend_calls():
    return frontend_calls() | customer_frontend_calls()


def test_frontend_calls_have_backend_routes():
    missing = sorted(all_frontend_calls() - backend_routes())
    detail = ", ".join(f"{method} {path}" for method, path in missing)
    assert not missing, f"El frontend llama a rutas que el backend no expone: {detail}"


def test_backend_routes_are_used():
    unused = sorted(backend_routes() - all_frontend_calls() - ALLOWED_UNUSED)
    detail = ", ".join(f"{method} {path}" for method, path in unused)
    assert not unused, f"Endpoints del backend sin uso en el frontend: {detail}"


def test_coverage_report():
    routes = sorted(backend_routes())
    calls = all_frontend_calls()
    print("\nMETODO  RUTA                                        FRONTEND")
    for method, path in routes:
        status = "USADO" if (method, path) in calls else "SIN USO"
        print(f"{method:<7} {path:<44} {status}")
    for method, path in sorted(calls - set(routes)):
        print(f"{method:<7} {path:<44} SIN RUTA EN BACKEND")
