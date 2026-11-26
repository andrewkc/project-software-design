import React from "react";
import { Icon } from "../Icon";

export function PageDate({ onProfile, showProfileShortcut = true }) {
  return <div className="page-date">
    <span className="today-label">
      {new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}
    </span>
    {showProfileShortcut && <div className="page-date-actions">
      <button type="button" className="icon-button" aria-label="Ir al perfil" onClick={onProfile}>
        <Icon name="users" size={19} />
      </button>
    </div>}
  </div>;
}
