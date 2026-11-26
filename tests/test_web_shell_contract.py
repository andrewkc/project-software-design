"""Static contract checks for the shared mobile shell and favicon.

No browser, server or database is needed. These checks keep the three web
apps aligned with ADR-009 and detect documentation that still describes the
old four/five-section bottom bar or the removed local demo mode.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_APPS = ("operations-web", "customer-web", "admin-web")

LAYOUTS = {
    "operations-web": "apps/operations-web/src/components/layout/OperationsLayout.jsx",
    "customer-web": "apps/customer-web/src/components/layout/CustomerLayout.jsx",
    "admin-web": "apps/admin-web/src/components/layout/AdminLayout.jsx",
}


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_three_web_apps_serve_the_shared_favicon():
    for app in WEB_APPS:
        html = read(f"apps/{app}/index.html")
        assert '<link rel="icon" type="image/png" href="/favicon.png" />' in html, app

        favicon = ROOT / "apps" / app / "public" / "favicon.png"
        assert favicon.is_file(), f"{app} no incluye public/favicon.png"
        data = favicon.read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n"), f"{app}: no es un PNG"
        assert len(data) > 1000, f"{app}: el favicon parece vacío"
        # Las tres copias comparten el mismo identificador de asset; no se
        # exige igualdad byte a byte porque el PNG puede llevar metadatos.
        assert "54d1aab3-d2b6-4476-99d1-1e89f61f2f0b" in data.decode("latin-1"), app


def test_mobile_navigation_is_a_hamburger_dropdown_not_a_fixed_bar():
    for app, layout_path in LAYOUTS.items():
        layout = read(layout_path)
        css = read(f"apps/{app}/src/styles.css")
        for token in (
            'className="mobile-menu-trigger"',
            'aria-haspopup="menu"',
            "aria-expanded={open}",
            'role="menu"',
            'Icon name={open ? "close" : "menu"}',
            "setOpen(false)",
        ):
            assert token in layout, f"{app}: falta {token}"
        assert ".mobile-menu-panel" in css, app
        assert ".mobile-menu-trigger" in css, app
        assert re.search(r"\.mobile-nav \{[^}]*grid-template-columns", css) is None, (
            f"{app} todavía dibuja una barra inferior con varias secciones"
        )


def test_dropdown_lists_every_section_allowed_for_the_role():
    admin = read(LAYOUTS["admin-web"])
    for label in ("Panel", "Cuentas", "Bodegas", "Mi cuenta"):
        assert label in admin, label
    assert 'label: "Perfil"' not in admin  # no entrada redundante

    navigation = read("apps/customer-web/src/data/navigation.js")
    customer = read(LAYOUTS["customer-web"])
    for label in ("Inicio", "Bodegas", "Mi cesta", "Mis pedidos"):
        assert f'label: "{label}"' in navigation, label
    assert "Mi cuenta" in customer
    assert 'label: "Perfil"' not in navigation

    operations_data = read("apps/operations-web/src/data/demoData.js")
    operations = read(LAYOUTS["operations-web"])
    for label in (
        "Inicio", "Inventario", "Registrar", "Vencimientos", "Ventas",
        "Recomendaciones", "Empleados", "Perfil",
    ):
        assert f'label: "{label}"' in operations_data, label
    assert "mobileNavigation.filter" in operations
    assert "jefeOnly" in operations and "empleadoOnly" in operations


def test_mobile_type_scale_is_proportional_and_legible():
    for app in WEB_APPS:
        css = read(f"apps/{app}/src/styles.css")
        assert "--font-scale: 1.4" in css, app
        mobile = css.split("/* Menú móvil")[1]
        assert "@media (max-width: 720px)" in mobile, app
        assert "body { --font-scale: 1.55; }" in mobile, app
        assert ".signup-shell { --font-scale: 1.4; }" in mobile, app
        assert "calc(9px * var(--font-scale))" in mobile, app
        assert "calc(6px * var(--font-scale))" not in mobile, app


def test_documentation_matches_backend_database_and_three_frontends():
    scope = read("docs/01-product/scope.md")
    assert "No existe modo de exploración local" in scope
    assert "menú desplegable de hamburguesa" in scope

    adr7 = read("docs/04-architecture/decisions/ADR-007-cliente-web-pago-prueba.md")
    assert "Ambas se retiraron por completo" in adr7
    assert "barra inferior de cuatro secciones" in adr7  # contexto histórico

    sales_spec = read("docs/05-specifications/ventas-historial/spec.md")
    assert "`customer-web` sigue sin implementar" not in sales_spec
    assert "menú desplegable de hamburguesa" in sales_spec

    backend = read("apps/backend/README.md")
    assert "GET` | `/customer/payment-methods`" in backend
    assert "`payment_mode`" in backend

    database = read("apps/database/README.md")
    assert "interfaz de `customer-web` y `admin-web`" not in database

    for app in WEB_APPS:
        app_readme = read(f"apps/{app}/README.md")
        assert "ADR-009" in app_readme, app
        assert "favicon" in app_readme.lower(), app
        assert "hamburguesa" in app_readme.lower(), app


def test_adr_index_and_quality_report_include_mobile_shell():
    index = read("docs/04-architecture/decisions/README.md")
    assert "[ADR-009](ADR-009-shell-movil-favicon.md)" in index

    adr = read("docs/04-architecture/decisions/ADR-009-shell-movil-favicon.md")
    for token in ("hamburguesa", "favicon", "1.55", "Mi cuenta", "Pendiente"):
        assert token in adr, token

    quality = read("docs/06-quality/README.md")
    assert "Validación del shell móvil y favicon" in quality
    assert "tests/test_web_shell_contract.py" in quality


def test_compose_still_serves_five_services():
    compose = read("docker-compose.yml")
    for service in ("database:", "backend:", "operations-web:", "customer-web:", "admin-web:"):
        assert service in compose, service


def test_web_tab_titles_use_middle_dot():
    operations = read("apps/operations-web/index.html")
    assert "<title>BodeSmart · Control y operaciones</title>" in operations
    assert "<title>BodeSmart</title>" not in operations

    customer = read("apps/customer-web/index.html")
    assert "<title>BodeSmart · Tienda para clientes</title>" in customer
    assert "BodeSmart — Tienda para clientes" not in customer

    admin = read("apps/admin-web/index.html")
    assert "<title>BodeSmart · Administración</title>" in admin
