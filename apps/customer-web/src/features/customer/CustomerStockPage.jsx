import React, { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { EmptyState } from "../../components/common/InventoryRows";
import { customerCatalog, stockChanges } from "../../lib/liveStock";
import { fold } from "../../lib/textTools";
import "./customer.css";

const HIGHLIGHT_MS = 3500;
const AVAILABILITY = {
  available: { label: "Disponible", tone: "ok" },
  low: { label: "Últimas unidades", tone: "low" },
  out: { label: "Agotado", tone: "out" },
};

export function CustomerStockPage({ products, user }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [changes, setChanges] = useState({});
  const [announcement, setAnnouncement] = useState("");
  const previous = useRef(products);
  const catalog = useMemo(() => customerCatalog(products), [products]);
  const categories = useMemo(() => [...new Set(catalog.map((item) => item.category))].sort((a, b) => a.localeCompare(b, "es")), [catalog]);
  const visible = catalog.filter((item) => (!category || item.category === category) && fold(item.name).includes(fold(search.trim())));

  useEffect(() => {
    const diff = stockChanges(previous.current, products);
    previous.current = products;
    const ids = Object.keys(diff);
    if (!ids.length) return undefined;
    setChanges((current) => ({ ...current, ...diff }));
    const names = ids.map((id) => products.find((item) => String(item.id) === id)).filter(Boolean);
    setAnnouncement(names.map((item) => `${item.name}: quedan ${item.stock} ${item.unit}`).join(". "));
    const timer = window.setTimeout(() => setChanges((current) => Object.fromEntries(Object.entries(current).filter(([id]) => !ids.includes(id)))), HIGHLIGHT_MS);
    return () => window.clearTimeout(timer);
  }, [products]);

  return <div className="page-content inner-page customer-page">
    <section className="welcome-row customer-heading">
      <div><h1>Stock de tu bodega</h1><p className="welcome-subtitle">Vinculado a <strong>{user?.store || "tu bodega"}</strong></p></div>
      <span className="live-badge"><i aria-hidden="true" /> En vivo</span>
    </section>
    <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
    <div className="customer-tools">
      <label className="search-field customer-search"><Icon name="search" size={17} /><input aria-label="Buscar en la bodega" placeholder="Buscar producto" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      <div className="customer-categories">
        <button type="button" className={!category ? "active" : ""} aria-pressed={!category} onClick={() => setCategory("")}>Todo</button>
        {categories.map((name) => <button type="button" key={name} className={category === name ? "active" : ""} aria-pressed={category === name} onClick={() => setCategory(name)}>{name}</button>)}
      </div>
    </div>
    <section className="stock-tiles" aria-label="Cuadros de stock">{visible.map((item) => {
      const state = AVAILABILITY[item.availability];
      const delta = changes[item.id];
      return <article key={item.id} aria-label={item.name} className={`stock-tile stock-tile-${state.tone} ${delta !== undefined ? "stock-tile-changed" : ""}`}>
        <div className="stock-tile-top"><span className="product-emoji">{item.icon}</span><span className={`stock-state stock-state-${state.tone}`}>{state.label}</span></div>
        <h2>{item.name}</h2>
        <small>{item.category}</small>
        <div className="stock-tile-count"><strong>{item.stock}</strong><span>{item.unit}</span>{delta !== undefined && <em>{delta > 0 ? `+${delta}` : delta}</em>}</div>
        <b>S/ {Number(item.price).toFixed(2)}</b>
      </article>;
    })}</section>
    {visible.length === 0 && <EmptyState icon="search" title="No encontramos productos" text="Prueba con otro nombre o categoría." />}
  </div>;
}
