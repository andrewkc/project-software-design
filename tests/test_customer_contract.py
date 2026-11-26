"""Static traceability checks for the customer-web scope expansion.

No server, database or browser is needed: these checks keep the approved
customer flow aligned with the operations-web visual contract and with the
single stock-decrement rule.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_customer_router_is_registered():
    main = read("apps/backend/main.py")
    assert "from routers import auth, categories, customer," in main
    assert "app.include_router(customer.router)" in main


def test_stock_is_decremented_by_one_shared_rule():
    service = read("apps/backend/sales_service.py")
    router = read("apps/backend/routers/customer.py")
    assert "def decrement_stock_once(conn, items):" in service
    assert "def approve_reserved_order(conn, order):" in service
    assert "decrement_stock_once(conn, [" in service
    assert "approve_reserved_order(conn, order)" in router
    assert "from sales_service import approve_reserved_order" in router
    # A paid order has no live reservation left to display or extend.
    assert "reserva_hasta = NULL" in service
    # The router must not own a second stock-decrement path.
    assert "UPDATE ProductosBodega SET stock" not in router


def test_payment_flags_come_from_config():
    config = read("apps/backend/config.py")
    router = read("apps/backend/routers/customer.py")
    for token in (
        "from dotenv import load_dotenv", "load_dotenv()",
        "ALLOW_SIMULATED_PAYMENT =", "MERCADOPAGO_ACCESS_TOKEN =",
        "MERCADOPAGO_WEBHOOK_SECRET =", "http://127.0.0.1:5174",
    ):
        assert token in config, token
    assert "os.getenv(" not in router
    assert "from config import (" in router


def test_order_history_does_not_hide_non_paid_orders():
    router = read("apps/backend/routers/customer.py")
    view = read("apps/customer-web/src/features/orders/OrdersPage.jsx")
    assert "WHERE c.id_cliente = %s" in router
    assert 'c.estado = \'pagado\'' not in router
    assert "orders.map((order)" in view
    assert 'orders.filter((order) => order.state === "pagado")' not in view


def test_customer_ui_reuses_operations_visual_tokens():
    css = read("apps/customer-web/src/styles.css")
    for token in (
        "--ink: #252c26", "--muted: #858c84", "--green: #397a55",
        "--green-dark: #2c6646", "--green-soft: #eef5ed", "--line: #e9ece5",
        "--cream: #f7f8f3", "--font-scale: 1.4", '"DM Sans"', '"Manrope"',
        "calc(", "@media (max-width: 720px)", ".mobile-nav",
    ):
        assert token in css, token
    assert css.count(":root") == 1, "No dupliques la paleta en otro :root"


def test_login_logo_has_no_cream_box_and_auth_heading_is_larger():
    css = read("apps/customer-web/src/styles.css")
    compact = css.split("/* Acceso compacto")[1].split("/* Shell lateral")[0]
    assert "--font-scale: 1.08" in compact  # se conserva la escala anterior
    assert "--font-scale: 1;" not in compact
    assert "--font-scale: .94" not in compact
    assert ".art-brand { display: inline-flex; }" in compact
    assert "background: #f7f8f3" not in compact
    assert "font-size: clamp(34px, 4.2vw, 52px)" in compact  # titular del panel
    assert ".signup-form-wrap h2 { font-size: calc(34px * var(--font-scale)); }" in compact
    assert css.count(".signup-form-wrap h2 { font-size: calc(31px * var(--font-scale)); }") == 2


def test_customer_menu_and_profile_role_match_approved_copy():
    nav = read("apps/customer-web/src/data/navigation.js")
    layout = read("apps/customer-web/src/components/layout/CustomerLayout.jsx")
    for label in ("Inicio", "Bodegas", "Mi cesta", "Mis pedidos", "Perfil"):
        assert f'label: "{label}"' in nav, label
    assert "<small>Cliente</small>" in layout
    stores = read("apps/customer-web/src/features/catalog/StoresPage.jsx")
    orders = read("apps/customer-web/src/features/orders/OrdersPage.jsx")
    auth = read("apps/customer-web/src/features/auth/AuthScreen.jsx")
    assert "Bodegas y ofertas" in stores
    assert "Tu cesta" in read("apps/customer-web/src/features/cart/CartPage.jsx")
    assert "Mis pedidos" in orders
    assert "Pagar con Mercado Pago de prueba" in orders
    assert "Simular pago" in orders
    assert "Comprobar estado" in orders
    assert "Demo académica · Pagos de prueba" in auth


def test_auth_forms_have_balanced_jsx_roots():
    auth = read("apps/customer-web/src/features/auth/AuthScreen.jsx")
    signup = auth.split("function SignupForm", 1)[1]
    # SignupForm opens <div className="register-auth">, so it cannot close a fragment.
    assert "return <div className=\"register-auth\"" in signup
    assert "</>;" not in signup
    assert "</div>;" in signup


def test_official_logos_are_copied_into_customer_web_and_used():
    script = read("apps/customer-web/scripts/copy-official-logos.mjs")
    package = read("apps/customer-web/package.json")
    brand = read("apps/customer-web/src/components/Brand.jsx")
    layout = read("apps/customer-web/src/components/layout/CustomerLayout.jsx")
    css = read("apps/customer-web/src/styles.css")
    for token in ("BodeSmart-Logo.png", "BodeSmart-Mobile-Logo.png", "public/assets"):
        assert token in script, token
    for script_name in ("copy-logos", "predev", "prebuild"):
        assert f'"{script_name}"' in package, script_name
    assert '"/assets/BodeSmart-Logo.png"' in brand
    assert '"/assets/BodeSmart-Mobile-Logo.png"' in brand
    assert "<Brand mobile />" in layout
    assert 'className="art-brand"' in read("apps/customer-web/src/features/auth/AuthScreen.jsx")
    assert ".brand-logo" in css
    assert ".sidebar-brand .brand-logo" in css
    assert ".art-brand .brand-logo" in css


def test_auth_screen_has_a_compact_desktop_layout():
    css = read("apps/customer-web/src/styles.css")
    assert "@media (min-width: 721px)" in css
    assert ".signup-shell { --font-scale: 1.08; height: 100vh; min-height: 0; }" in css
    assert ".signup-panel { height: 100vh; min-height: 0;" in css
    assert ".auth-form input { height: 50px;" in css


def test_profile_page_reuses_the_sidebar_profile_card():
    page = read("apps/customer-web/src/features/profile/ProfilePage.jsx")
    css = read("apps/customer-web/src/styles.css")
    for token in (
        'className="profile-card profile-card-page"',
        '<span className="profile-avatar">',
        "<small>Cliente</small>",
        'className="profile-dots"',
        "&middot;&middot;&middot;",
    ):
        assert token in page, token
    assert ".profile-card-page" in css
    assert ".profile-card-page .profile-avatar" in css


def test_demo_seed_is_additive_and_credentials_are_ignored():
    seed = read("apps/backend/seed_customer_demo.py")
    gitignore = read(".gitignore")
    assert "INSERT INTO Jefe" not in seed
    assert "INSERT INTO Empleado" not in seed
    assert "UPDATE Cliente SET password" not in seed
    assert "cliente.demo@bodesmart.local" in seed
    assert "BODESMART_DEMO_SEED" in seed
    assert ".demo-credentials.json" in gitignore


def test_customer_web_is_wired_into_docker_compose():
    dockerfile = read("apps/customer-web/Dockerfile")
    local = read("apps/customer-web/Dockerfile.local")
    ignore = read("apps/customer-web/.dockerignore")
    compose = read("docker-compose.yml")
    assert "FROM node:22-alpine AS build" in dockerfile
    assert "COPY package*.json ./" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "FROM nginx:alpine" in dockerfile
    assert "COPY --from=build /app/dist /usr/share/nginx/html" in dockerfile
    assert "EXPOSE 5174" in local
    assert "npm run dev" in local
    assert "node_modules" in ignore and "dist" in ignore
    # The service must be part of the root compose and keep CORS in sync.
    assert "  customer-web:\n" in compose
    assert "context: ./apps/customer-web" in compose
    assert "dockerfile: ${CUSTOMER_DOCKERFILE:-Dockerfile}" in compose
    assert "VITE_API_BASE_URL: ${CUSTOMER_VITE_API_BASE_URL:-http://127.0.0.1:8000}" in compose
    assert "127.0.0.1:${CUSTOMER_PORT:-5174}:${CUSTOMER_CONTAINER_PORT:-80}" in compose
    assert "http://127.0.0.1:5174" in compose.split("CORS_ORIGINS:")[1].split("\n")[0]


def test_customer_api_contract_matches_router():
    api = read("apps/customer-web/src/lib/api.js")
    for path in ("/stores", "/offers", "/auth/register", "/auth/login", "/auth/me",
                 "/orders", "/simulate-payment", "/checkout", "/verify-payment"):
        assert path in api, path
    assert "${BASE}/customer${path}" in api
    assert 'bodesmart_customer_token' in api
