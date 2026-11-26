import React from "react";
import { Brand } from "../Brand";
import { Icon } from "../Icon";
import { mobileNavigation, navigation } from "../../data/navigation";
import { LayoutContext } from "./LayoutContext";
import { initial, shortName } from "../../lib/format";

export function CustomerLayout({ user, activeTab, cartCount, onNavigate, children }) {
  const displayName = shortName(user) || "Cliente BodeSmart";
  return <LayoutContext.Provider value={{ user, activeTab, onNavigate, cartCount }}>
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand sidebar-brand" type="button" onClick={() => onNavigate("home")} aria-label="Ir al inicio"><Brand mobile /></button>
        <div className="store-switcher">
          <span className="store-avatar">B</span>
          <span className="store-label"><strong>BodeSmart</strong><small>Tienda para clientes</small></span>
        </div>
        <span className="nav-caption">MENÚ PRINCIPAL</span>
        <nav className="side-nav" aria-label="Navegación principal">
          {navigation.map((item) => <button key={item.id} type="button" className={`nav-link ${activeTab === item.id ? "active" : ""}`} onClick={() => onNavigate(item.id)}>
            <Icon name={item.icon} size={19} />
            <span>{item.label}</span>
            {item.id === "cart" && cartCount > 0 && <span className="nav-count">{cartCount}</span>}
          </button>)}
        </nav>
        <button className="profile-card" type="button" onClick={() => onNavigate("profile")}>
          <span className="profile-avatar">{initial(user)}</span>
          <span><strong>{displayName}</strong><small>Cliente</small></span>
          <span className="profile-dots">&middot;&middot;&middot;</span>
        </button>
      </aside>
      <main className="main-area">
        {children}
        <MobileNav user={user} activeTab={activeTab} cartCount={cartCount} onNavigate={onNavigate} />
      </main>
    </div>
  </LayoutContext.Provider>;
}

function MobileNav({ activeTab, cartCount, onNavigate }) {
  const [open, setOpen] = React.useState(false);
  const sections = [...mobileNavigation, { id: "profile", label: "Mi cuenta", icon: "user" }];
  const current = sections.find((item) => item.id === activeTab);
  const choose = (id) => {
    setOpen(false);
    onNavigate(id);
  };
  return <div className="mobile-nav" data-count={sections.length}>
    <button type="button" className="mobile-menu-trigger" aria-haspopup="menu" aria-expanded={open} aria-controls="customer-mobile-sections" aria-label={open ? "Cerrar menú de secciones" : "Abrir menú de secciones"} onClick={() => setOpen((value) => !value)}>
      <Icon name={open ? "close" : "menu"} size={21} />
      <span>Menú</span>
      {current && <small>{current.label}</small>}
    </button>
    {open && <div className="mobile-menu-panel" id="customer-mobile-sections" role="menu" aria-label="Secciones de la tienda">
      <p className="mobile-menu-caption">Secciones</p>
      {sections.map((item) => <button key={item.id} type="button" role="menuitem" className={activeTab === item.id ? "active" : ""} onClick={() => choose(item.id)}>
        <Icon name={item.icon} size={19} />
        <span>{item.label}</span>
        {item.id === "cart" && cartCount > 0 && <span className="nav-count">{cartCount}</span>}
      </button>)}
    </div>}
  </div>;
}
