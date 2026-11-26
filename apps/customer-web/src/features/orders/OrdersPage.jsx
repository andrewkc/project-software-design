import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { money, orderStatus, orderSummary, orderTitle } from "../../lib/format";

export function OrdersPage({ orders, activeOrder, busy, stores, onSelectOrder, onBack, onPay, onVerify, onNavigate }) {
  if (activeOrder) return <OrderDetail order={activeOrder} busy={busy} stores={stores} onBack={onBack} onPay={onPay} onVerify={onVerify} onNavigate={onNavigate} />;

  const pending = orders.filter((order) => order.state === "pendiente");
  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row"><div><h1>Mis pedidos</h1><p className="welcome-subtitle">Compras confirmadas, pagos en curso y pedidos cerrados, todos en un mismo lugar.</p></div>{pending.length > 0 && <span className="alert-counter"><Icon name="info" size={15} /> {pending.length} {pending.length === 1 ? "pendiente" : "pendientes"}</span>}</section>
    {orders.length ? <section className="content-card history-card"><div className="card-heading"><h2>Historial de pedidos</h2><span className="muted-count">Todos los estados</span></div>
      <div className="history-list">{orders.map((order) => <button className="history-row" type="button" key={order.id} onClick={() => onSelectOrder(order)}>
        <span className="history-icon"><Icon name="receipt" size={18} /></span>
        <span className="history-info"><strong>Pedido #{order.id}</strong><small>{order.store_name || "Bodega"} · {order.lines?.length || 0} {order.lines?.length === 1 ? "producto" : "productos"}</small></span>
        <strong className="history-total">{money(order.total)}</strong><em className={`status ${order.state}`}>{orderStatus(order.state)}</em><Icon name="arrow" size={17} />
      </button>)}</div>
    </section> : <div className="empty-state"><span>🧾</span><strong>Aún no tienes pedidos</strong><p>Cuando crees un pedido aparecerá aquí con su estado.</p><button className="button button-primary" type="button" onClick={() => onNavigate("home")}>Explorar ofertas</button></div>}
  </div>;
}

function OrderDetail({ order, busy, stores, onBack, onPay, onVerify, onNavigate }) {
  const storeName = order.store_name || stores.find((store) => store.id === order.store_id)?.nombre || "Bodega";
  const canPay = order.state === "pendiente";
  return <div className="page-content inner-page">
    <button className="back-link" type="button" onClick={onBack}><Icon name="chevronLeft" size={16} />Mis pedidos</button>
    <section className="welcome-row"><div><span className="date-greeting">PEDIDO #{order.id}</span><h1>{orderTitle(order.state)}</h1><p className="welcome-subtitle">{orderSummary(order.state)}</p></div></section>
    <section className="order-layout">
      <div className="content-card order-card"><div className="card-heading"><h2>Detalle del pedido</h2><span className="muted-count">{storeName}</span></div>
        <div className="order-lines">{(order.lines || []).map((line) => <div className="order-line" key={line.offer_id || line.product_name}>
          <span className="product-emoji" aria-hidden="true">{line.icon || "📦"}</span>
          <span className="order-line-name"><strong>{line.product_name}</strong><small>{line.quantity} × {money(line.unit_price ?? line.current_price ?? 0)}</small></span>
          <strong>{money(line.amount ?? (Number(line.quantity || 0) * Number(line.unit_price || line.current_price || 0)))}</strong>
        </div>)}</div>
        <div className="order-line order-total"><span>Total</span><strong>{money(order.total)}</strong></div>
        <div className="pickup"><strong><Icon name="mapPin" size={16} /> Recojo en {storeName}</strong><p>{order.pickup_address || stores.find((store) => store.id === order.store_id)?.direccion || "Consulta la dirección con la bodega."}</p><small>El recojo se muestra como información; no requiere confirmación en esta demo.</small></div>
      </div>
      <aside className="content-card summary-card"><h2>Estado del pedido</h2><div className={`status ${order.state}`}>{orderStatus(order.state)}</div>
        {canPay && <><p className="summary-note">Reserva hasta: {order.reservation_until ? new Date(order.reservation_until).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" }) : "diez minutos desde la creación"}</p>
          <button className="button button-primary button-full" type="button" disabled={busy} onClick={onPay}>{busy ? "Espera..." : order.payment_mode === "MERCADOPAGO_TEST" ? "Pagar con Mercado Pago de prueba" : "Simular pago"}</button>
          <button className="button button-secondary button-full" type="button" disabled={busy} onClick={onVerify}>Comprobar estado</button></>}
        {!canPay && <button className="button button-secondary button-full" type="button" onClick={() => onNavigate("home")}>Volver a las ofertas</button>}
      </aside>
    </section>
  </div>;
}
