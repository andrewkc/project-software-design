import React from "react";
import { EmptyState } from "../../components/common/InventoryRows";
import { PageDate } from "../../components/layout/PageDate";
import { isJefe } from "../../lib/permissions";
import { money } from "../../lib/money";

export function HomePage({ user, products, expiringProducts, stockTotal, salesSeries, categoryTotals, maxCategoryTotal, onRegister, onNavigate }) {
  return <div className="page-content">
    <PageDate onNotifications={() => onNavigate("alerts")} notificationCount={expiringProducts.length} />
    <section className="welcome-row"><div><h1>&iexcl;Hola, {user?.name?.split(" ")[0] || "Mar&iacute;a"}!</h1><p className="welcome-subtitle">{isJefe(user) ? <>Un vistazo r&aacute;pido a c&oacute;mo va tu <strong>{user?.store || "la bodega"}</strong> hoy.</> : "Un vistazo rápido al estado de la bodega asignada."}</p></div>
    {/* <button type="button" className="button button-primary add-top-button" onClick={onRegister}><Icon name="plus" size={18} /> Registrar mercader&iacute;a</button> */}
    </section>
    <SummaryCards productCount={products.length} stockTotal={stockTotal} expiringCount={expiringProducts.length} onNavigate={onNavigate} />
    <section className="home-analytics-grid" aria-label="An&aacute;lisis de ventas e inventario"><SalesChart salesSeries={salesSeries} onNavigate={onNavigate} /><CategoryCard categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} /><AttentionCard expiringProducts={expiringProducts} onNavigate={onNavigate} /></section>
  </div>;
}

function SummaryCards({ productCount, stockTotal, expiringCount, onNavigate }) {
  return <section className="home-summary-grid" aria-label="Resumen de inventario"><SummaryCard tone="alert" label="Por vencer pronto" value={expiringCount} onClick={() => onNavigate("alerts")} /><SummaryCard tone="products" label="Total de productos &uacute;nicos" value={productCount} onClick={() => onNavigate("inventory")} /><SummaryCard tone="units" label="Total de unidades" value={stockTotal} onClick={() => onNavigate("inventory")} /></section>;
}

function SummaryCard({ tone, label, value, onClick }) {
  return <article className={`home-summary-card home-summary-${tone}`}><span className="summary-card-label">{label}</span><strong>{value}</strong><button type="button" onClick={onClick}>Revisar</button></article>;
}

function SalesChart({ salesSeries, onNavigate }) {
  const { points, polyline, total, purchaseCount, hiddenDayCount } = salesSeries;
  return <article className="content-card home-chart-card"><div className="home-card-heading"><div>
    <span className="section-kicker">VENTAS</span>
    <h2>Ventas acumuladas</h2>
  </div><button type="button" className="text-link" onClick={() => onNavigate("sales")}>Ver Ventas</button></div>
    {points.length ? <>
      <div className="line-chart-wrap"><svg className="line-chart" viewBox="0 0 300 140" role="img" aria-label="Gráfica de ventas acumuladas por día"><line x1="20" y1="32" x2="280" y2="32" /><line x1="20" y1="75" x2="280" y2="75" /><line x1="20" y1="118" x2="280" y2="118" /><polyline className="chart-line" points={polyline} />{points.map((point) => <circle key={point.key} cx={point.x} cy={point.y} r="4"><title>{`${point.label}: ${money(point.cumulative)} acumulados`}</title></circle>)}</svg><div className="chart-labels" style={{ gridTemplateColumns: `repeat(${points.length}, minmax(0, 1fr))` }}>{points.map((point) => <span key={point.key}>{point.label}</span>)}</div></div>
      <p className="sales-chart-caption"><strong>{money(total)}</strong> acumulados &middot; {purchaseCount} {purchaseCount === 1 ? "compra pagada" : "compras pagadas"}{hiddenDayCount ? ` · últimos ${points.length} días` : ""}</p>
    </> : <EmptyState icon="trending" title="Sin ventas registradas" text="Las compras pagadas aparecerán aquí y en la sección Ventas." />}
  </article>;
}

function CategoryCard({ categoryTotals, maxCategoryTotal }) {
  return <article className="content-card category-card"><div className="home-card-heading"><div><h2>Unidades por categor&iacute;a</h2></div></div><div className="category-list">{categoryTotals.map(([category, total]) => <div className="category-row" key={category}><div><span>{category}</span><strong>{total}</strong></div><span className="category-track"><i style={{ width: `${(total / maxCategoryTotal) * 100}%` }} /></span></div>)}</div></article>;
}

function AttentionCard({ expiringProducts, onNavigate }) {
  return <article className="content-card attention-card"><div className="home-card-heading"><div><h2>Productos para revisar</h2></div><button type="button" className="text-link" onClick={() => onNavigate("alerts")}>Ver todo</button></div>{expiringProducts.length ? <div className="attention-list">{expiringProducts.slice(0, 3).map((product) => <div className="attention-row" key={product.id}><span className="attention-dot" /><span>{product.name}</span><strong>{product.stock} {product.unit}</strong></div>)}</div> : <EmptyState icon="check" title="Todo bajo control" text="No hay productos pr&oacute;ximos a vencer." />}</article>;
}
