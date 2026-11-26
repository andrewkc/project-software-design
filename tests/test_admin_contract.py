"""Static contract checks for the isolated admin router and admin-web.

No running server or database is required. HTTP behaviour still needs the
integration suite against a disposable database.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROUTER = ROOT / "apps" / "backend" / "routers" / "admin.py"
ADMIN_API = ROOT / "apps" / "admin-web" / "src" / "lib" / "api.js"
ADMIN_STYLES = ROOT / "apps" / "admin-web" / "src" / "styles.css"
ADMIN_DOCKERFILE = ROOT / "apps" / "admin-web" / "Dockerfile"
ADMIN_LOCAL_DOCKERFILE = ROOT / "apps" / "admin-web" / "Dockerfile.local"
ADMIN_BRAND = ROOT / "apps" / "admin-web" / "src" / "components" / "Brand.jsx"
ADMIN_LOGIN = ROOT / "apps" / "admin-web" / "src" / "features" / "auth" / "LoginPage.jsx"
ADMIN_LAYOUT = ROOT / "apps" / "admin-web" / "src" / "components" / "layout" / "AdminLayout.jsx"
ADMIN_PACKAGE = ROOT / "apps" / "admin-web" / "package.json"
ADMIN_LOGO_SCRIPT = ROOT / "apps" / "admin-web" / "scripts" / "copy-official-logos.mjs"
DATABASE = ROOT / "apps" / "backend" / "database.py"
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"


def test_admin_router_exposes_required_routes():
    text = ADMIN_ROUTER.read_text(encoding="utf-8")
    required = (
        '@router.post("/admin/auth/login")',
        '@router.get("/admin/me")',
        '@router.get("/admin/users")',
        '@router.post("/admin/users")',
        '@router.get("/admin/stores")',
        '@router.patch("/admin/users/{uid}")',
        '@router.delete("/admin/users/{uid}")',
    )
    for route in required:
        assert route in text, f"Falta la ruta {route}"


def test_admin_cannot_touch_another_admin():
    text = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert 'if rol == "admin" and profile_id != who["id"]:' in text
    assert text.count("guard_admin_target(rol, profile_id, who)") >= 2
    assert "No puedes desactivar tu propia cuenta" in text


def test_deactivation_is_logical_and_passwords_are_hidden():
    text = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert "UPDATE {table} SET estado = 'inactivo' WHERE id = %s" in text
    assert "DELETE FROM" not in text
    response = text.split("def account_response", 1)[1].split("def admin_profile", 1)[0]
    assert "password" not in response


def test_all_four_roles_are_supported():
    text = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert 'ROLES = ("admin", "jefe", "empleado", "cliente")' in text


def test_admin_schema_is_idempotent():
    text = DATABASE.read_text(encoding="utf-8")
    for fragment in (
        "ALTER TABLE Jefe ADD COLUMN IF NOT EXISTS estado",
        "CREATE TABLE IF NOT EXISTS Admin",
        "ALTER TABLE Admin ADD COLUMN IF NOT EXISTS estado",
        "ALTER TABLE Admin ADD COLUMN IF NOT EXISTS fecha_creacion",
        "ALTER TABLE Admin ADD COLUMN IF NOT EXISTS ultimo_acceso",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_admin_correo_ci",
    ):
        assert fragment in text, f"Falta la migración {fragment}"


def test_admin_web_uses_isolated_token_and_routes():
    text = ADMIN_API.read_text(encoding="utf-8")
    assert 'TOKEN_KEY = "bodesmart-admin-token"' in text
    for route in ("/admin/auth/login", "/admin/me", "/admin/users", "/admin/stores"):
        assert route in text


def test_admin_web_build_does_not_require_a_missing_lockfile():
    for dockerfile in (ADMIN_DOCKERFILE, ADMIN_LOCAL_DOCKERFILE):
        text = dockerfile.read_text(encoding="utf-8")
        assert "RUN npm install" in text
        assert "RUN npm ci" not in text


def test_admin_web_local_dockerfile_uses_api_build_arg():
    text = ADMIN_LOCAL_DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG VITE_API_BASE_URL=http://localhost:8000" in text
    assert "ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}" in text


def test_admin_web_hides_mobile_nav_on_desktop():
    text = ADMIN_STYLES.read_text(encoding="utf-8")
    assert ".mobile-nav { display: none; }" in text


def test_admin_web_copies_and_uses_official_logos():
    script = ADMIN_LOGO_SCRIPT.read_text(encoding="utf-8")
    package = ADMIN_PACKAGE.read_text(encoding="utf-8")
    brand = ADMIN_BRAND.read_text(encoding="utf-8")
    login = ADMIN_LOGIN.read_text(encoding="utf-8")
    layout = ADMIN_LAYOUT.read_text(encoding="utf-8")
    styles = ADMIN_STYLES.read_text(encoding="utf-8")
    for token in ("BodeSmart-Logo.png", "BodeSmart-Mobile-Logo.png", "public/assets"):
        assert token in script, token
    for script_name in ("copy-logos", "predev", "prebuild"):
        assert f'"{script_name}"' in package, script_name
    assert '"/assets/BodeSmart-Logo.png"' in brand
    assert '"/assets/BodeSmart-Mobile-Logo.png"' in brand
    assert "<Brand light />" in login
    assert "<Brand mobile />" in login
    assert "<Brand mobile />" in layout
    assert ".sidebar-brand .brand-logo" in styles
    assert ".signup-art .brand-logo" in styles


def test_admin_web_login_fits_without_scrolling_on_desktop():
    styles = ADMIN_STYLES.read_text(encoding="utf-8")
    assert "@media (min-width: 721px)" in styles
    assert ".signup-shell { --font-scale: 1.08; height: 100vh; min-height: 0; }" in styles
    assert ".signup-panel { height: 100vh; min-height: 0;" in styles
    assert ".auth-form input { height: 50px;" in styles


def test_admin_web_login_has_no_demo_credentials():
    login = ADMIN_LOGIN.read_text(encoding="utf-8")
    styles = ADMIN_STYLES.read_text(encoding="utf-8")
    assert "Demo local:" not in login
    assert "admin@bodesmart.local" not in login
    assert "Admin123456" not in login
    assert "demo-credentials" not in login
    assert ".demo-credentials" not in styles
    assert "Prototipo académico" not in login
    assert "entrevistas exploratorias" not in login
    assert ".prototype-note" not in styles


def test_admin_profile_is_only_reachable_from_the_account_card():
    layout = ADMIN_LAYOUT.read_text(encoding="utf-8")
    assert 'label: "Perfil"' not in layout  # entrada redundante eliminada
    assert 'onClick={() => onNavigate("profile")}' in layout


def test_compose_and_env_expose_admin_web():
    compose = COMPOSE.read_text(encoding="utf-8")
    env = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "  admin-web:" in compose
    assert "ADMIN_DOCKERFILE" in compose
    assert "http://localhost:5175" in compose
    assert "ADMIN_DOCKERFILE=Dockerfile" in env
    assert "http://localhost:5175" in env
