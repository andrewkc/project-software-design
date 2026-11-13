import React from "react";
import { Icon } from "../../components/Icon";
import { EmptyState } from "../../components/common/InventoryRows";

export function HomePage({ user, products, expiringProducts, stockTotal, stockSeries, categoryTotals, maxCategoryTotal, onRegister, onNavigate }) {
  return <div className="page-content"><section className="welcome-row"><div><h1>&iexcl;Hola, {user?.name?.split(" ")[0] || "Mar&iacute;a"}!</h1><p className="welcome-subtitle">Un vistazo r&aacute;pido a c&oacute;mo va tu <strong>{user?.store || "tu bodega"}</strong> hoy.</p></div>
  {/* <button type="button" className="button button-primary add-top-button" onClick={onRegister}><Icon name="plus" size={18} /> Registrar mercader&iacute;a</button> */}
  </section>
    <SummaryCards productCount={products.length} stockTotal={stockTotal} expiringCount={expiringProducts.length} onNavigate={onNavigate} />
    <section className="home-analytics-grid" aria-label="An&aacute;lisis del inventario"><StockChart stockSeries={stockSeries} /><CategoryCard categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} /><AttentionCard expiringProducts={expiringProducts} onNavigate={onNavigate} /></section>
  </div>;
}

function SummaryCards({ productCount, stockTotal, expiringCount, onNavigate }) {
  return <section className="home-summary-grid" aria-label="Resumen de inventario"><SummaryCard tone="alert" label="Por vencer pronto" value={expiringCount} onClick={() => onNavigate("alerts")} /><SummaryCard tone="products" label="Total de productos &uacute;nicos" value={productCount} onClick={() => onNavigate("inventory")} /><SummaryCard tone="units" label="Total de unidades" value={stockTotal} onClick={() => onNavigate("inventory")} /></section>;
}

function SummaryCard({ tone, label, value, onClick }) {
  return <article className={`home-summary-card home-summary-${tone}`}><span className="summary-card-label">{label}</span><strong>{value}</strong><button type="button" onClick={onClick}>Revisar</button></article>;
}

function StockChart({ stockSeries }) {
  return <article className="content-card home-chart-card"><div className="home-card-heading"><div>
    {/* <span className="section-kicker">INVENTARIO ACTUAL</span> */}
  <h2>Unidades por producto</h2></div></div><div className="line-chart-wrap"><svg className="line-chart" viewBox="0 0 300 140" role="img" aria-label="Gr&aacute;fica de unidades por producto"><line x1="20" y1="32" x2="280" y2="32" /><line x1="20" y1="75" x2="280" y2="75" /><line x1="20" y1="118" x2="280" y2="118" /><polyline className="chart-line" points={stockSeries.polyline} />{stockSeries.points.map((point) => <circle key={point.id} cx={point.x} cy={point.y} r="4" />)}</svg><div className="chart-labels">{stockSeries.points.map((point) => <span key={point.id}>{point.name.split(" ")[0]}</span>)}</div></div></article>;
}

function CategoryCard({ categoryTotals, maxCategoryTotal }) {
  return <article className="content-card category-card"><div className="home-card-heading"><div><span className="section-kicker">DISTRIBUCI&Oacute;N</span><h2>Unidades por categor&iacute;a</h2></div></div><div className="category-list">{categoryTotals.map(([category, total]) => <div className="category-row" key={category}><div><span>{category}</span><strong>{total}</strong></div><span className="category-track"><i style={{ width: `${(total / maxCategoryTotal) * 100}%` }} /></span></div>)}</div></article>;
}

function AttentionCard({ expiringProducts, onNavigate }) {
  return <article className="content-card attention-card"><div className="home-card-heading"><div><span className="section-kicker">ATENCI&Oacute;N</span><h2>Productos para revisar</h2></div><button type="button" className="text-link" onClick={() => onNavigate("alerts")}>Ver todo <Icon name="arrow" size={15} /></button></div>{expiringProducts.length ? <div className="attention-list">{expiringProducts.slice(0, 3).map((product) => <div className="attention-row" key={product.id}><span className="attention-dot" /><span>{product.name}</span><strong>{product.stock} {product.unit}</strong></div>)}</div> : <EmptyState icon="check" title="Todo bajo control" text="No tienes productos pr&oacute;ximos a vencer." />}</article>;
}
