import React from "react";
import { Icon } from "../../components/Icon";
import { dateLabel, money } from "../../lib/format";
import { daysUntilExpiry } from "../../lib/catalog";

export function OfferCard({ offer, storeName, onAdd }) {
  const days = daysUntilExpiry(offer.expiry_date);
  const hasDiscount = Number(offer.original_price) > Number(offer.current_price);
  const percent = hasDiscount ? Math.round((1 - Number(offer.current_price) / Number(offer.original_price)) * 100) : 0;
  return <article className="offer-card">
    <div className="offer-visual" aria-hidden="true"><span>{offer.icon || "📦"}</span>{percent > 0 && <span className="offer-discount">-{percent}%</span>}</div>
    <div className="offer-body">
      <span className="offer-store">{storeName || "Bodega"}</span>
      <h3>{offer.product_name}</h3>
      <p className="offer-meta">{offer.category || "Producto"} · Vence el {dateLabel(offer.expiry_date)}</p>
      {days !== null && days >= 0 && <p className={`expiry-note ${days <= 3 ? "expiry-soon" : ""}`}>
        <Icon name="clock" size={13} /> {days === 0 ? "Vence hoy" : `Vence en ${days} ${days === 1 ? "día" : "días"}`}
      </p>}
      <div className="offer-price-row">
        <div className="offer-price"><strong>{money(offer.current_price)}</strong>{hasDiscount && <del>{money(offer.original_price)}</del>}<small>por {offer.unit || "unidad"}</small></div>
        <button className="button button-primary offer-add" type="button" disabled={Number(offer.available) <= 0} onClick={() => onAdd(offer)} aria-label={`Agregar ${offer.product_name} a la cesta`}><Icon name="plus" size={15} />Agregar</button>
      </div>
      <p className="offer-stock">{offer.available} disponibles</p>
    </div>
  </article>;
}
