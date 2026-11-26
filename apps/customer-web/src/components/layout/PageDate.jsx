import React from "react";
import { Icon } from "../Icon";
import { useLayout } from "./LayoutContext";

export function PageDate({ onCart, cartCount = 0 }) {
  const { activeTab } = useLayout();
  return <div className="page-date">
    <span className="today-label">{new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span>
    <div className="page-date-actions">
      {onCart && activeTab !== "cart" && <button type="button" className="icon-button cart-shortcut" aria-label={`Ver cesta, ${cartCount} productos`} onClick={onCart}>
        <Icon name="cart" size={19} />
        {cartCount > 0 && <i />}
      </button>}
    </div>
  </div>;
}
