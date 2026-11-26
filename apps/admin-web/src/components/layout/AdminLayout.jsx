import React from "react";
import { Brand } from "../Brand";
import { Icon } from "../Icon";
import { displayName, initials } from "../../lib/ui";

// The bottom-left account card opens the profile; a separate "Perfil" entry
// was redundant, so it is not part of the menu in either sidebar or mobile nav.
const navigation = [
  { id: "dashboard", label: "Panel", icon: "home" },
  { id: "users", label: "Cuentas", icon: "users" },
  { id: "stores", label: "Bodegas", icon: "box" },
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
      <MobileNav activeTab={activeTab} onNavigate={onNavigate} />
    </main>
  </div>;
}

function MobileNav({ activeTab, onNavigate }) {
  const [open, setOpen] = React.useState(false);
  const sections = [...navigation, { id: "profile", label: "Mi cuenta", icon: "user" }];
  const current = sections.find((item) => item.id === activeTab);
  const choose = (id) => {
    setOpen(false);
    onNavigate(id);
  };
  return <div className="mobile-nav">
    <button type="button" className="mobile-menu-trigger" aria-haspopup="menu" aria-expanded={open} aria-controls="admin-mobile-sections" aria-label={open ? "Cerrar menú de secciones" : "Abrir menú de secciones"} onClick={() => setOpen((value) => !value)}>
      <Icon name={open ? "close" : "menu"} size={21} />
      <span>Menú</span>
      {current && <small>{current.label}</small>}
    </button>
    {open && <div className="mobile-menu-panel" id="admin-mobile-sections" role="menu" aria-label="Secciones de administración">
      <p className="mobile-menu-caption">Secciones</p>
      {sections.map((item) => (
        <button key={item.id} type="button" role="menuitem" className={activeTab === item.id ? "active" : ""} onClick={() => choose(item.id)}>
          <Icon name={item.icon} size={19} /><span>{item.label}</span>
        </button>
      ))}
    </div>}
  </div>;
}
