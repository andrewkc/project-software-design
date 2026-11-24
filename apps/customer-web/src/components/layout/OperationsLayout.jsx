import React from "react";
import { Brand } from "../Brand";
import { Icon } from "../Icon";
import { mobileNavigation, navigation } from "../../data/demoData";
import { isAdmin, isCliente, isJefe } from "../../lib/permissions";
import { workspaceCopy } from "../../lib/workspaceCopy";
import { profileNames } from "../../lib/profileNames";
import { LayoutContext } from "./LayoutContext";

const ROLE_LABELS = { jefe: "Jefe de Bodega", empleado: "Empleado", cliente: "Cliente", admin: "Administrador" };

function itemsFor(items, user) {
  if (isAdmin(user)) return items.filter((item) => item.adminOnly || item.id === "profile");
  if (isCliente(user)) return items.filter((item) => item.clienteOnly || item.id === "profile");
  const jefe = isJefe(user);
  return items.filter((item) => !item.clienteOnly && !item.adminOnly && (!item.jefeOnly || jefe) && (!item.empleadoOnly || !jefe));
}

function badgeFor(id, expiringCount, pendingCount) {
  if (id === "alerts") return expiringCount;
  if (id === "sales") return pendingCount;
  return 0;
}

export function OperationsLayout({ user, activeTab, expiringCount, pendingCount = 0, onNavigate, onRegister, onLogout, children }) {
  const copy = workspaceCopy(user);
  const { displayName, initial } = profileNames(user);
  return <LayoutContext.Provider value={{ user, activeTab, onNavigate }}><div className="app-shell">
    <aside className="sidebar">
      <a className="brand sidebar-brand" href="#" onClick={(event) => event.preventDefault()}><Brand mobile /></a>
      <div className="store-switcher"><span className="store-avatar">B</span><span className="store-label"><strong>{copy.storeName}</strong><small>{copy.storeCaption}</small></span>
      {/* <span className="switch-arrow">˅</span> */}
      </div>
      <span className="nav-caption">MENÚ PRINCIPAL</span>
      <nav className="side-nav" aria-label="Navegaci&oacute;n principal">{itemsFor(navigation, user).map((item) => {
        const badge = badgeFor(item.id, expiringCount, pendingCount);
        return <button key={item.id} type="button" className={`nav-link ${activeTab === item.id ? "active" : ""}`} onClick={() => item.id === "register" ? onRegister() : onNavigate(item.id)}><Icon name={item.icon} size={19} /><span>{item.label}</span>{badge > 0 && <span className="nav-count">{badge}</span>}</button>;
      })}</nav>
      <button className="profile-card" type="button" onClick={() => onNavigate("profile")}><span className="profile-avatar">{initial}</span><span><strong>{displayName}</strong><small>{ROLE_LABELS[user?.role] || ROLE_LABELS.jefe}</small></span><span className="profile-dots">&middot;&middot;&middot;</span></button>
    </aside>
    <main className="main-area">
      {/* <header className="topbar"> */}
        {/* <div className="breadcrumb"><span>Mi negocio</span><span className="breadcrumb-slash">/</span><strong>{title}</strong></div><div className="topbar-actions"><span className="today-label">{new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span><button type="button" className="icon-button notification-button" aria-label="Notificaciones" onClick={() => onNavigate("alerts")}><Icon name="bell" size={19} />{expiringCount > 0 && <i />}</button> */}
        {/* <span className="top-avatar">{(user?.name || "M").charAt(0).toUpperCase()}</span> */}
        {/* </div> */}
      {/* </header> */}
      {children}
      <MobileNav user={user} activeTab={activeTab} expiringCount={expiringCount} pendingCount={pendingCount} onNavigate={onNavigate} onRegister={onRegister} onLogout={onLogout} />
    </main>
  </div></LayoutContext.Provider>;
}

function MobileNav({ user, activeTab, expiringCount, pendingCount, onNavigate, onRegister }) {
  const items = itemsFor(mobileNavigation, user);
  return <nav className="mobile-nav" aria-label="Navegaci&oacute;n m&oacute;vil" data-count={items.length}>{items.map((item) => <button key={item.id} type="button" className={activeTab === item.id ? "active" : ""} onClick={() => { if (item.id === "register") return onRegister(); onNavigate(item.id); }}><Icon name={item.icon} size={19} /><span>{item.label}</span>{badgeFor(item.id, expiringCount, pendingCount) > 0 && <i />}</button>)}</nav>;
}
