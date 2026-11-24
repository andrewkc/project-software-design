import React from "react";
import { Icon } from "../Icon";
import { isAdmin, isCliente, isJefe } from "../../lib/permissions";
import { useLayout } from "./LayoutContext";

export function PageDate({ onNotifications, notificationCount = 0 }) {
  const { user, activeTab, onNavigate } = useLayout();
  const showProfileShortcut = (isJefe(user) || isAdmin(user)) && activeTab !== "profile";
  return <div className="page-date">
    <span className="today-label">{new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span>
    <div className="page-date-actions">
      {!isCliente(user) && !isAdmin(user) && <button type="button" className="icon-button notification-button" aria-label="Notificaciones" onClick={onNotifications}><Icon name="bell" size={19} />{notificationCount > 0 && <i />}</button>}
      {showProfileShortcut && <button type="button" className="icon-button profile-shortcut" aria-label="Perfil" onClick={() => onNavigate("profile")}><Icon name="users" size={19} /></button>}
    </div>
  </div>;
}
