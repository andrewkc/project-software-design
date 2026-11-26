import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";

export function StoresPage({ users, stores, onNavigate }) {
  return <div className="page-content inner-page">
    <PageDate onProfile={() => onNavigate("profile")} />
    <section className="welcome-row">
      <div>
        <h1>Bodegas</h1>
        <p className="welcome-subtitle">Bodegas registradas en la plataforma y cuentas asignadas.</p>
      </div>
      <button type="button" className="button button-secondary add-top-button" onClick={() => onNavigate("users")}><Icon name="users" size={16} />Ver cuentas</button>
    </section>
    <section className="content-card">
      <div className="card-heading"><h2>Listado de bodegas</h2><span className="muted-count">{stores.length} registradas</span></div>
      <div className="store-list">
        {stores.map((store) => {
          const assigned = users.filter((account) => account.bodegaNombre === store.nombre);
          return <div className="store-row" key={store.id}>
            <span className="store-avatar"><Icon name="box" size={17} /></span>
            <span><strong>{store.nombre}</strong><small>{store.direccion || "Sin dirección registrada"}</small></span>
            <span className="store-count">{assigned.length} {assigned.length === 1 ? "cuenta" : "cuentas"}</span>
          </div>;
        })}
        {stores.length === 0 && <div className="empty-state"><strong>Sin bodegas registradas</strong><p>Crea una cuenta de jefe con bodega para comenzar.</p></div>}
      </div>
    </section>
  </div>;
}
