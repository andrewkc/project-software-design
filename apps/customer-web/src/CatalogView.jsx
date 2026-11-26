import React, { useEffect, useMemo, useRef, useState } from "react";
import { daysUntilExpiry, filterOffers, groupOffersByStore, sortOffersByPrice } from "./catalog";
import "./catalog.css";

const money = (value) => `S/ ${Number(value || 0).toFixed(2)}`;
const dateLabel = (value) => new Date(`${value}T12:00:00`).toLocaleDateString("es-PE", { day: "numeric", month: "long" });

function StoreIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 9h18l-1.5-5h-15L3 9Z" /><path d="M4 9v10h16V9M8 19v-6h8v6M3 9c0 2 3 3 4.5 1.5C9 12 11 11 12 9c1 2 3 3 4.5 1.5C18 12 21 11 21 9" /></svg>;
}

function SearchIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg>;
}

function ChevronIcon() {
  return <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3.5 6 4.5 4 4.5-4" /></svg>;
}

function ProductCard({ offer, onAdd }) {
  const days = daysUntilExpiry(offer.expiry_date);
  return <article className="product-card">
    <div className="product-visual" aria-hidden="true"><span>{offer.icon || "📦"}</span></div>
    <div className="product-content">
      <h3>{offer.product_name}</h3>
      <p className="product-meta">{offer.category || "Producto"} · Vence el {dateLabel(offer.expiry_date)}</p>
      {days !== null && <p className="expiry-note">{days === 0 ? "Vence hoy" : `Vence en ${days} ${days === 1 ? "día" : "días"}`}</p>}
      <div className="price-row"><div><strong>{money(offer.current_price)}</strong>
        {Number(offer.original_price) > Number(offer.current_price) && <del>{money(offer.original_price)}</del>}
        <small>por {offer.unit || "unidad"}</small></div>
        <button type="button" className="catalog-add" onClick={() => onAdd(offer)} aria-label={`Agregar ${offer.product_name} de ${offer.store_name} y ver la bodega`}>Agregar</button>
      </div>
      <div className="stock-note">{offer.available} disponibles</div>
    </div>
  </article>;
}

export default function CatalogView({ mode, stores, offers, selectedStoreId, onOpenStore, onBack, onAdd,
                                      query, onQueryChange, minPrice, onMinPriceChange, maxPrice, onMaxPriceChange,
                                      priceMode, onPriceModeChange,
                                      maxDays, onMaxDaysChange, filterStoreId, onFilterStoreIdChange, onClearFilters }) {
  const [openFilter, setOpenFilter] = useState(null);
  const [browseLayout, setBrowseLayout] = useState("offers");
  const toolbarRef = useRef(null);
  const hasFilters = Boolean(query.trim() || priceMode !== "none" || maxDays !== "" || filterStoreId !== null);
  const filtered = useMemo(() => filterOffers(offers, { query, minPrice: priceMode === "range" ? minPrice : "", maxPrice: priceMode === "range" ? maxPrice : "", maxDays, storeId: filterStoreId }),
    [offers, query, minPrice, maxPrice, priceMode, maxDays, filterStoreId]);
  const sorted = useMemo(() => sortOffersByPrice(filtered, priceMode), [filtered, priceMode]);
  const grouped = useMemo(() => groupOffersByStore(stores, sorted, !hasFilters, priceMode), [stores, sorted, hasFilters, priceMode]);

  function choosePriceMode(nextMode) {
    if (nextMode !== "range") { onMinPriceChange(""); onMaxPriceChange(""); setOpenFilter(null); }
    onPriceModeChange(nextMode);
  }

  useEffect(() => {
    if (!openFilter) return;
    const closeOnOutside = (event) => { if (!toolbarRef.current?.contains(event.target)) setOpenFilter(null); };
    const closeOnEscape = (event) => { if (event.key === "Escape") setOpenFilter(null); };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [openFilter]);

  if (mode === "store") {
    const store = stores.find((item) => item.id === selectedStoreId);
    if (!store) return <section className="empty"><h1>Bodega no disponible</h1><button className="primary" onClick={onBack}>Ver bodegas</button></section>;
    const storeOffers = offers.filter((offer) => offer.store_id === store.id);
    return <section className="store-page">
      <button className="back-link" onClick={onBack}>← Todas las bodegas</button>
      <div className="store-banner"><div className="store-identity"><span className="store-symbol store-symbol-light"><StoreIcon /></span><div><p>Bodega</p><h1>{store.nombre}</h1><span>{store.direccion || "Dirección disponible al confirmar el pedido"}</span></div></div>
        <div className="store-offer-count"><strong>{storeOffers.length}</strong><span>{storeOffers.length === 1 ? "oferta disponible" : "ofertas disponibles"}</span></div></div>
      <div className="store-catalog-heading"><div><h2>Productos de {store.nombre}</h2><p>Agrega productos de esta bodega a tu cesta.</p></div></div>
      {storeOffers.length ? <div className="product-grid">{storeOffers.map((offer) => <ProductCard key={offer.id} offer={offer} onAdd={onAdd} />)}</div>
        : <div className="empty"><h3>Esta bodega no tiene ofertas disponibles</h3><p>Vuelve a explorar otras bodegas.</p></div>}
    </section>;
  }

  return <section className="browse-page">
    <div className="browse-heading"><div><h1>Bodegas y ofertas</h1><p>Busca un producto en todas las bodegas y compara precios y vencimientos.</p></div>
      <div className="browse-heading-actions"><span>{stores.length} {stores.length === 1 ? "bodega" : "bodegas"}</span><div className="catalog-view-switch" role="group" aria-label="Vista de catálogo"><button type="button" className={browseLayout === "offers" ? "selected" : ""} aria-pressed={browseLayout === "offers"} onClick={() => setBrowseLayout("offers")}>Productos</button><button type="button" className={browseLayout === "stores" ? "selected" : ""} aria-pressed={browseLayout === "stores"} onClick={() => setBrowseLayout("stores")}>Solo bodegas</button></div></div></div>
    <div className="catalog-toolbar" ref={toolbarRef}>
      <label className="catalog-search"><SearchIcon /><input type="search" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Buscar producto o bodega" aria-label="Buscar producto o bodega" /></label>
      <div className="catalog-filter-actions">
        <div className="filter-menu">
          <button type="button" className={`filter-chip ${filterStoreId !== null ? "selected" : ""}`} aria-expanded={openFilter === "store"} onClick={() => setOpenFilter(openFilter === "store" ? null : "store")}><StoreIcon /><span>{filterStoreId === null ? "Bodegas" : stores.find((store) => store.id === filterStoreId)?.nombre || "Bodegas"}</span><ChevronIcon /></button>
          {openFilter === "store" && <div className="filter-popover filter-store-popover"><strong>Elegir bodega</strong><div className="filter-store-list"><button className={filterStoreId === null ? "chosen" : ""} onClick={() => { onFilterStoreIdChange(null); setOpenFilter(null); }}>Todas las bodegas</button>{stores.map((store) => <button key={store.id} className={filterStoreId === store.id ? "chosen" : ""} onClick={() => { onFilterStoreIdChange(store.id); setOpenFilter(null); }}><StoreIcon />{store.nombre}</button>)}</div></div>}
        </div>
        <div className="filter-menu">
          <button type="button" className={`filter-chip ${priceMode !== "none" ? "selected" : ""}`} aria-expanded={openFilter === "price"} onClick={() => setOpenFilter(openFilter === "price" ? null : "price")}><span>{priceMode === "asc" ? "Menor precio" : priceMode === "desc" ? "Mayor precio" : priceMode === "range" ? "Rango de precio" : "Precio"}</span><ChevronIcon /></button>
          {openFilter === "price" && <div className="filter-popover"><strong>Ordenar o filtrar precio</strong><div className="price-options"><button type="button" className={priceMode === "asc" ? "chosen" : ""} onClick={() => choosePriceMode("asc")}>Menor precio primero</button><button type="button" className={priceMode === "desc" ? "chosen" : ""} onClick={() => choosePriceMode("desc")}>Mayor precio primero</button><button type="button" className={priceMode === "range" ? "chosen" : ""} onClick={() => choosePriceMode("range")}>Elegir rango</button></div>{priceMode === "range" && <><div className="price-inputs"><label>Mínimo S/<input type="number" min="0" step="0.01" inputMode="decimal" value={minPrice} onChange={(event) => onMinPriceChange(event.target.value)} placeholder="0.00" /></label><label>Máximo S/<input type="number" min="0" step="0.01" inputMode="decimal" value={maxPrice} onChange={(event) => onMaxPriceChange(event.target.value)} placeholder="Sin límite" /></label></div><button className="filter-done" onClick={() => setOpenFilter(null)}>Listo</button></>}</div>}
        </div>
        <div className="filter-menu">
          <button type="button" className={`filter-chip ${maxDays !== "" ? "selected" : ""}`} aria-expanded={openFilter === "expiry"} onClick={() => setOpenFilter(openFilter === "expiry" ? null : "expiry")}><span>{maxDays === "" ? "Vencimiento" : `Hasta ${maxDays} días`}</span><ChevronIcon /></button>
          {openFilter === "expiry" && <div className="filter-popover"><strong>Días hasta vencer</strong><label className="expiry-input">Como máximo<input type="number" min="0" step="1" inputMode="numeric" value={maxDays} onChange={(event) => onMaxDaysChange(event.target.value)} placeholder="Ej. 10" /></label><div className="expiry-presets">{[7, 10, 15, 30].map((days) => <button key={days} className={maxDays === String(days) ? "chosen" : ""} onClick={() => onMaxDaysChange(String(days))}>{days} días</button>)}</div><button className="filter-done" onClick={() => setOpenFilter(null)}>Listo</button></div>}
        </div>
        {hasFilters && <button className="clear-filters" type="button" onClick={() => { onClearFilters(); setOpenFilter(null); }}>Limpiar</button>}
      </div>
    </div>
    {hasFilters && <p className="result-count" role="status">{browseLayout === "stores" ? `${grouped.length} ${grouped.length === 1 ? "bodega encontrada" : "bodegas encontradas"}` : `${filtered.length} ${filtered.length === 1 ? "producto encontrado" : "productos encontrados"} en ${grouped.length} ${grouped.length === 1 ? "bodega" : "bodegas"}`}</p>}
    {grouped.length && browseLayout === "stores" ? <div className="store-card-grid">{grouped.map((store) => <button type="button" className="store-card" key={store.id} onClick={() => onOpenStore(store.id)}><span className={`store-symbol tone-${store.id % 3}`}><StoreIcon /></span><strong>{store.nombre}</strong><span className="store-card-address">{store.direccion || "Recojo en bodega"}</span><span className="store-card-link">Ver bodega <span aria-hidden="true">→</span></span></button>)}</div> : null}
    {grouped.length && browseLayout === "offers" ? <div className="store-sections">{grouped.map((store) => <section className="store-section" key={store.id}>
      <div className="store-section-heading"><div className="store-identity"><span className={`store-symbol tone-${store.id % 3}`}><StoreIcon /></span><div><h2>{store.nombre}</h2><p>{store.direccion || "Recojo en bodega"} · {store.offers.length} {store.offers.length === 1 ? "oferta" : "ofertas"}</p></div></div>
        <button type="button" onClick={() => onOpenStore(store.id)}>Ver bodega <span aria-hidden="true">→</span></button></div>
      {store.offers.length ? <div className="product-grid">{store.offers.map((offer) => <ProductCard key={offer.id} offer={offer} onAdd={onAdd} />)}</div>
        : <p className="store-empty">Sin ofertas disponibles por ahora.</p>}
    </section>)}</div> : null}
    {!grouped.length && <div className="empty"><h3>{browseLayout === "stores" ? "No encontramos bodegas con esos filtros" : "No encontramos productos con esos filtros"}</h3><p>Prueba otro precio, más días hasta el vencimiento o una búsqueda distinta.</p><button className="primary" onClick={onClearFilters}>Limpiar filtros</button></div>}
  </section>;
}
