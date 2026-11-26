import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { displayName, initials } from "../../lib/ui";

export function AdminProfilePage({ user, onLogout }) {
  const name = displayName(user);
  const fullName = user?.nombre || name;
  return <div className="page-content inner-page">
    <PageDate showProfileShortcut={false} />
    <section className="welcome-row">
      <div><h1>Perfil</h1><p className="welcome-subtitle">Datos de la cuenta de administración.</p></div>
    </section>
    <section className="profile-page-card">
      <div className="profile-page-avatar">{initials(name)}</div>
      <div className="profile-page-info">
        <h2>{name}</h2>
        <p>Admin</p>
        <dl>
          <div><dt>Nombre completo</dt><dd>{fullName}</dd></div>
          <div><dt>Correo electrónico</dt><dd>{user?.correo || "Sin correo registrado"}</dd></div>
          <div><dt>Ámbito</dt><dd>Plataforma BodeSmart</dd></div>
        </dl>
      </div>
      <div className="profile-page-actions">
        <button className="button button-secondary profile-logout" type="button" onClick={onLogout}><Icon name="lock" size={16} />Cerrar sesión</button>
      </div>
    </section>
    <p className="note-card"><Icon name="shield" size={18} /><span><strong>Autoprotección.</strong> Puedes editar tu propia cuenta, pero no desactivarla ni modificar la de otros administradores desde este panel.</span></p>
  </div>;
}
