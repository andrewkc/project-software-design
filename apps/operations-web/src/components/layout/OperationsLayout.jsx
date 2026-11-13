import React from "react";
import { Brand } from "../Brand";
import { Icon } from "../Icon";
import { mobileNavigation, navigation } from "../../data/demoData";

export function OperationsLayout({ user, activeTab, expiringCount, onNavigate, onRegister, onLogout, children }) {
  const title = navigation.find((item) => item.id === activeTab)?.label || "Inicio";
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand sidebar-brand" href="#" onClick={(event) => event.preventDefault()}><Brand /></a>
      <div className="store-switcher"><span className="store-avatar">B</span><span className="store-label"><strong>{user?.store || "Mi bodega"}</strong><small>Mi negocio</small></span><span className="switch-arrow">⌄</span></div>
      <span className="nav-caption">MEN&Uacute; PRINCIPAL</span>
      <nav className="side-nav" aria-label="Navegaci&oacute;n principal">{navigation.map((item) => <button key={item.id} type="button" className={`nav-link ${activeTab === item.id ? "active" : ""}`} onClick={() => onNavigate(item.id)}><Icon name={item.icon} size={19} /><span>{item.label}</span>{item.id === "alerts" && expiringCount > 0 && <span className="nav-count">{expiringCount}</span>}</button>)}</nav>
      <div className="sidebar-help"><span className="help-illustration"><Icon name="sparkles" size={21} /></span><strong>Un paso a la vez</strong><p>Registra tus productos y mant&eacute;n tu inventario al d&iacute;a.</p><button type="button" onClick={onRegister}>Agregar producto <Icon name="arrow" size={15} /></button></div>
      <button className="profile-card" type="button" onClick={onLogout}><span className="profile-avatar">{(user?.name || "M").charAt(0).toUpperCase()}</span><span><strong>{user?.name || "Mar&iacute;a L&oacute;pez"}</strong><small>Jefa de bodega</small></span><span className="profile-dots">&middot;&middot;&middot;</span></button>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="breadcrumb"><span>Mi negocio</span><span className="breadcrumb-slash">/</span><strong>{title}</strong></div><div className="topbar-actions"><span className="today-label">{new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span><button type="button" className="icon-button notification-button" aria-label="Notificaciones" onClick={() => onNavigate("alerts")}><Icon name="bell" size={19} />{expiringCount > 0 && <i />}</button>
      {/* <span className="top-avatar">{(user?.name || "M").charAt(0).toUpperCase()}</span> */}
      </div></header>
      {children}
      <MobileNav activeTab={activeTab} expiringCount={expiringCount} onNavigate={onNavigate} onRegister={onRegister} onLogout={onLogout} />
    </main>
  </div>;
}

function MobileNav({ activeTab, expiringCount, onNavigate, onRegister, onLogout }) {
  return <nav className="mobile-nav" aria-label="Navegaci&oacute;n m&oacute;vil">{mobileNavigation.map((item) => <button key={item.id} type="button" className={activeTab === item.id ? "active" : ""} onClick={() => { if (item.id === "register") return onRegister(); if (item.id === "profile") return onLogout(); onNavigate(item.id); }}><Icon name={item.icon} size={19} /><span>{item.label}</span>{item.id === "alerts" && expiringCount > 0 && <i />}</button>)}</nav>;
}
