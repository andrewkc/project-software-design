import React, { useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";

const money = (value) => new Intl.NumberFormat("es-PE", {
  style: "currency",
  currency: "PEN",
}).format(Number(value) || 0);

const formatDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const paymentLabel = (method) => ({
  LOCAL_SIMULATION: "Simulación local",
  MERCADOPAGO_TEST: "Mercado Pago de prueba",
}[method] || method || "Registro interno");

export function SalesPage({ sales, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false);
  const total = sales.reduce((sum, sale) => sum + (Number(sale.total) || 0), 0);
  const units = sales.reduce(
    (sum, sale) => sum + sale.lineas.reduce((inner, line) => inner + (Number(line.cantidad) || 0), 0),
    0,
  );

  async function handleRefresh() {
    if (!onRefresh) return;
    setRefreshing(true);
    try { await onRefresh(); } finally { setRefreshing(false); }
  }

  return <div className="page-content inner-page"><PageDate />
    <section className="welcome-row"><div>
      <h1>Ventas</h1>
      <p className="welcome-subtitle">Historial de compras realizadas por clientes de la bodega.</p>
    </div>
      <button className="button button-secondary" type="button" disabled={refreshing} onClick={handleRefresh}>{refreshing ? "Actualizando..." : "Actualizar"}</button>
    </section>

    <div className="sales-summary">
      <div className="sales-summary-card"><span>Compras pagadas</span><strong>{sales.length}</strong><small>Solo pedidos confirmados</small></div>
      <div className="sales-summary-card"><span>Total vendido</span><strong>{money(total)}</strong><small>Precios congelados al comprar</small></div>
      <div className="sales-summary-card"><span>Unidades vendidas</span><strong>{units}</strong><small>Ya descontadas del stock</small></div>
    </div>

    <p className="sales-coherence"><Icon name="check" size={15} /> Solo se muestran compras pagadas: cada una descontó el stock en la misma transacción en que se guardó la venta.</p>

    <section className="content-card sales-card"><div className="card-heading"><div>
      <span className="section-kicker">HISTORIAL</span>
      <h2>Compras de clientes</h2>
    </div><span className="muted-count">{sales.length} registros</span></div>

    {sales.length ? <div className="sales-list">{sales.map((sale) => <article key={sale.id} className="sale-card">
      <header className="sale-card-head"><div>
        <span className="section-kicker">PEDIDO #{sale.id}</span>
        <h3>{sale.cliente}</h3>
        <p>{formatDate(sale.fechaPago)} · {paymentLabel(sale.metodoPago)}</p>
      </div><strong className="sale-total">{money(sale.total)}</strong></header>
      <div className="sale-lines">{sale.lineas.map((line) => <div key={line.id} className="sale-line">
        <span className="sale-line-icon">{line.icono}</span>
        <span className="sale-line-name"><strong>{line.nombre}</strong><small>{line.cantidad} {line.unidad} × {money(line.precioUnitario)}</small></span>
        <strong>{money(line.subtotal)}</strong>
      </div>)}</div>
    </article>)}</div> : <div className="empty-state"><span>🧾</span><strong>Aún no hay compras pagadas</strong><p>Las compras aparecerán aquí cuando se confirmen desde la tienda de clientes.</p></div>}
    </section>
  </div>;
}
