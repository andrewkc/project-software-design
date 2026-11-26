import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { fullName, initial, shortName } from "../../lib/format";

export function ProfilePage({ user, orderCount, onLogout, onNavigate }) {
  const email = user?.correo || user?.email || "Sin correo registrado";

  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row"><div><h1>Perfil</h1><p className="welcome-subtitle">Administra la información de tu cuenta de cliente.</p></div></section>

    {/* Misma tarjeta que la esquina inferior izquierda de la barra lateral. */}
    <section className="profile-card profile-card-page" aria-label="Resumen del perfil">
      <span className="profile-avatar">{initial(user)}</span>
      <span><strong>{shortName(user)}</strong><small>Cliente</small></span>
      <span className="profile-dots" aria-hidden="true">&middot;&middot;&middot;</span>
    </section>

    <section className="content-card profile-details-card">
      <div className="card-heading"><h2>Datos de la cuenta</h2></div>
      <dl className="profile-details">
        <div><dt>Nombre completo</dt><dd>{fullName(user)}</dd></div>
        <div><dt>Correo electrónico</dt><dd>{email}</dd></div>
        <div><dt>Teléfono</dt><dd>{user?.telefono || "No registrado"}</dd></div>
        <div><dt>Pedidos pagados</dt><dd>{orderCount}</dd></div>
      </dl>
      <div className="profile-page-actions">
        <button className="button button-secondary profile-logout" type="button" onClick={onLogout}><Icon name="logout" size={15} />Cerrar sesión</button>
      </div>
    </section>

    <section className="content-card profile-orders-card">
      <div className="card-heading"><div><h2>Mis compras</h2><p className="card-note">Consulta el detalle y el estado de todos tus pedidos.</p></div></div>
      <button className="button button-outline" type="button" onClick={() => onNavigate("orders")}><Icon name="receipt" size={16} />Ver mis pedidos</button>
    </section>
  </div>;
}
