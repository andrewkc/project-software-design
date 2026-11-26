import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { money } from "../../lib/format";

export function CartPage({ cart, stores, onChangeQuantity, onRemove, onCheckout, onNavigate, user, busy }) {
  const count = cart.reduce((sum, line) => sum + line.quantity, 0);
  const total = cart.reduce((sum, line) => sum + Number(line.current_price) * line.quantity, 0);
  const storeName = stores.find((store) => store.id === cart[0]?.store_id)?.nombre || cart[0]?.store_name || "Bodega";

  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row"><div><h1>Tu cesta</h1><p className="welcome-subtitle">Una compra por bodega, con recojo en tienda.</p></div>{cart.length > 0 && <button className="button button-secondary" type="button" onClick={() => onNavigate("home")}><Icon name="plus" size={15} />Seguir comprando</button>}</section>
    {cart.length ? <section className="checkout-grid">
      <div className="content-card basket-card"><div className="card-heading"><h2>{storeName}</h2><span className="muted-count">{count} {count === 1 ? "producto" : "productos"}</span></div>
        <div className="basket-list">{cart.map((line) => <article className="basket-row" key={line.id}>
          <span className="product-emoji" aria-hidden="true">{line.icon || "📦"}</span>
          <div className="basket-detail"><strong>{line.product_name}</strong><span>{money(line.current_price)} por {line.unit || "unidad"} · {line.available} disponibles</span></div>
          <div className="quantity-control"><button type="button" onClick={() => onChangeQuantity(line.id, line.quantity - 1)} aria-label={`Quitar una unidad de ${line.product_name}`}><Icon name="minus" size={14} /></button><b>{line.quantity}</b><button type="button" onClick={() => onChangeQuantity(line.id, line.quantity + 1)} aria-label={`Agregar una unidad de ${line.product_name}`}><Icon name="plus" size={14} /></button></div>
          <strong className="basket-line-total">{money(Number(line.current_price) * line.quantity)}</strong>
          <button className="row-action" type="button" onClick={() => onRemove(line.id)} aria-label={`Quitar ${line.product_name} de la cesta`}><Icon name="trash" size={16} /></button>
        </article>)}</div>
      </div>
      <aside className="content-card summary-card"><h2>Resumen del pedido</h2><div className="summary-row"><span>Bodega</span><strong>{storeName}</strong></div><div className="summary-row"><span>Productos</span><strong>{count}</strong></div><div className="summary-row summary-total"><span>Total</span><strong>{money(total)}</strong></div><p className="summary-note"><Icon name="info" size={14} /> El recojo es informativo. El pedido se confirma al aprobar el pago de prueba.</p>
        <button className="button button-primary button-full" type="button" disabled={busy} onClick={onCheckout}>{busy ? "Preparando..." : user ? "Continuar al pedido" : "Ingresar para comprar"}</button>
      </aside>
    </section> : <div className="empty-state"><span>🛒</span><strong>Tu cesta está vacía</strong><p>Explora las ofertas para comenzar.</p><button className="button button-primary" type="button" onClick={() => onNavigate("home")}>Ver ofertas</button></div>}
  </div>;
}
