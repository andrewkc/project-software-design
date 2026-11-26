import React from "react";
import { Brand } from "../Brand";
import { Icon } from "../Icon";
import { displayName, initials } from "../../lib/ui";

const navigation = [
  { id: "dashboard", label: "Panel", icon: "home" },
  { id: "users", label: "Cuentas", icon: "users" },
  { id: "stores", label: "Bodegas", icon: "box" },
  { id: "profile", label: "Perfil", icon: "shield" },
];

export function AdminLayout({ user, activeTab, onNavigate, children }) {
  const name = displayName(user);
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="sidebar-brand"><Brand mobile /></div>
      <div className="store-switcher">
        <span className="store-avatar">B</span>
        <span className="store-label"><strong>Plataforma BodeSmart</strong><small>Consola de administración</small></span>
      </div>
      <p className="nav-caption">MENÚ ADMIN</p>
      <nav className="side-nav" aria-label="Navegación principal">
        {navigation.map((item) => (
          <button key={item.id} type="button" className={`nav-link ${activeTab === item.id ? "active" : ""}`} onClick={() => onNavigate(item.id)}>
            <Icon name={item.icon} size={19} /><span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-help">
        <strong>Gestión de accesos</strong>
        <p>Crea y actualiza cuentas. La baja siempre es una desactivación para conservar el historial.</p>
        <span className="role-pill role-admin">Rol Admin</span>
      </div>
      <button className="profile-card" type="button" onClick={() => onNavigate("profile")}>
        <span className="profile-avatar">{initials(name)}</span>
        <span><strong>{name}</strong><small>Admin</small></span>
        <span className="profile-dots">···</span>
      </button>
    </aside>
    <main className="main-area">
      {children}
      <nav className="mobile-nav" aria-label="Navegación móvil">
        {navigation.map((item) => (
          <button key={item.id} type="button" className={activeTab === item.id ? "active" : ""} onClick={() => onNavigate(item.id)}>
            <Icon name={item.icon} size={19} /><span>{item.label}</span>
          </button>
        ))}
      </nav>
    </main>
  </div>;
}
