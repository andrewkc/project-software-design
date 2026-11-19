import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";

export function ProfilePage({ user, onLogout }) {
  const name = user?.name || "Kelvin Cahuana";
  const email = user?.email || "Sin correo registrado";
  const store = user?.store || "Mi bodega";

  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row">
      <div>
        {/* <p className="date-greeting">MI CUENTA</p> */}
        <h1>Perfil</h1><p className="welcome-subtitle">Administra la información de tu cuenta y tu bodega.</p></div>
    </section>
    <section className="profile-page-card">
      <div className="profile-page-avatar">{name.charAt(0).toUpperCase()}</div>
      <div className="profile-page-info"><h2>{name}</h2><p>Jefe de Bodega</p><dl><div><dt>Correo electrónico</dt><dd>{email}</dd></div><div><dt>Bodega</dt><dd>{store}</dd></div></dl></div>
      <button className="button button-secondary profile-logout" type="button" onClick={onLogout}>Cerrar sesión</button>
    </section>
  </div>;
}
