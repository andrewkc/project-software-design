import React from "react";
import { Icon } from "../Icon";

export function PageDate({ onNotifications, notificationCount = 0 }) {
  return <div className="page-date"><span className="today-label">{new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span><button type="button" className="icon-button notification-button" aria-label="Notificaciones" onClick={onNotifications}><Icon name="bell" size={19} />{notificationCount > 0 && <i />}</button></div>;
}
