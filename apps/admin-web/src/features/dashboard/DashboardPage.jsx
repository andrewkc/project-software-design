import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { ROLE_LABELS } from "../../lib/ui";

export function DashboardPage({ user, users, stores, onNavigate }) {
  const count = (role) => users.filter((item) => item.rol === role).length;
  const active = users.filter((item) => item.activo).length;
  const cards = [
    { label: "Cuentas activas", value: active, hint: `${users.length} cuentas en total`, icon: "shield" },
    ...Object.entries(ROLE_LABELS).map(([role, label]) => ({
      label: `Perfiles ${label}`,
      value: count(role),
      hint: label === "Admin" ? "Incluye tu cuenta" : "Gestionables desde Cuentas",
      icon: role === "jefe" ? "box" : "users",
    })),
  ];

  return <div className="page-content">
    <PageDate onProfile={() => onNavigate("profile")} />
    <section className="welcome-row">
      <div>
        <h1>Panel de administración</h1>
        <p className="welcome-subtitle">Hola, <strong>{user?.nombre || "Admin"}</strong>. Este resumen solo muestra cuentas y bodegas.</p>
      </div>
      <button className="button button-primary add-top-button" type="button" onClick={() => onNavigate("users")}>
        <Icon name="plus" size={16} />Gestionar cuentas
      </button>
    </section>
    <section className="stats-grid">
      {cards.map((card) => (
        <article className="stat-card" key={card.label}>
          <span className="stat-icon"><Icon name={card.icon} size={18} /></span>
          <span className="stat-label">{card.label}</span>
          <strong className="stat-number">{card.value}</strong>
          <span className="stat-hint">{card.hint}</span>
        </article>
      ))}
    </section>
    <section className="content-card">
      <div className="card-heading">
        <h2>Bodegas registradas</h2>
        <button type="button" className="button button-secondary button-small" onClick={() => onNavigate("stores")}>Ver detalle <Icon name="arrow" size={14} /></button>
      </div>
      <div className="store-list">
        {stores.slice(0, 5).map((store) => <div className="store-row" key={store.id}>
          <span className="store-avatar"><Icon name="box" size={17} /></span>
          <span><strong>{store.nombre}</strong><small>{store.direccion || "Sin dirección registrada"}</small></span>
          <span className="store-count">{users.filter((item) => item.bodegaNombre === store.nombre).length} cuentas</span>
        </div>)}
        {stores.length === 0 && <div className="empty-state"><strong>Sin bodegas registradas</strong><p>Las bodegas aparecen aquí cuando se crean desde Cuentas.</p></div>}
      </div>
    </section>
    <p className="note-card"><Icon name="info" size={18} /><span><strong>Límite del panel.</strong> El administrador gestiona accesos; no consulta costos, ventas ni precios, y la IA nunca aplica cambios por sí sola.</span></p>
  </div>;
}
