import React from "react";
import { Icon } from "../Icon";

export function ProductRow({ product, type }) {
  const days = product.expires ? Math.ceil((new Date(`${product.expires}T00:00:00`) - new Date(new Date().toDateString())) / 86400000) : null;
  const expirationLabel = days === 0 ? "Vence hoy" : days === 1 ? "Vence ma\u00f1ana" : `En ${days} d\u00edas`;
  return <div className="product-row"><span className="product-emoji">{product.icon}</span><span className="product-name"><strong>{product.name}</strong><small>{product.category} \u00b7 {product.stock} {product.unit}</small></span><span className={`status-pill ${type === "expiry" ? "status-expiry" : ""}`}><i />{type === "expiry" ? expirationLabel : "Revisar stock"}</span></div>;
}

export function ProductTableRow({ product, expiring }) {
  return <tr><td><span className="table-product-icon">{product.icon}</span><span className="table-product-name"><strong>{product.name}</strong><small>{product.category}</small></span></td><td><strong>{product.stock} {product.unit}</strong><span className={`stock-indicator ${product.stock <= 5 ? "stock-low" : ""}`}>{product.stock <= 5 ? "Stock bajo" : "Disponible"}</span></td><td>S/ {Number(product.price || 0).toFixed(2)}</td><td>{product.expires ? new Date(`${product.expires}T00:00:00`).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" }) : "Sin fecha"}</td><td><span className={`table-status ${expiring ? "table-status-warn" : ""}`}><i />{expiring ? "Por vencer" : "En orden"}</span></td></tr>;
}

export function EmptyState({ icon, title, text }) {
  return <div className="empty-state"><span><Icon name={icon} size={21} /></span><strong>{title}</strong><p>{text}</p></div>;
}
