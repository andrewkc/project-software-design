import React, { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";

export function CatalogToolbar({ stores, query, onQueryChange, minPrice, onMinPriceChange, maxPrice, onMaxPriceChange,
                                 priceMode, onPriceModeChange, maxDays, onMaxDaysChange, storeId, onStoreIdChange, onClear, resultLabel }) {
  const [openFilter, setOpenFilter] = useState(null);
  const [priceSubmenu, setPriceSubmenu] = useState("options");
  const toolbarRef = useRef(null);
  const hasFilters = Boolean(query.trim() || priceMode !== "none" || maxDays !== "" || storeId !== null);

  useEffect(() => {
    if (!openFilter) return undefined;
    const closeOnOutside = (event) => { if (!toolbarRef.current?.contains(event.target)) setOpenFilter(null); };
    const closeOnEscape = (event) => { if (event.key === "Escape") setOpenFilter(null); };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [openFilter]);

  function choosePriceMode(nextMode) {
    if (nextMode !== "range") { onMinPriceChange(""); onMaxPriceChange(""); }
    onPriceModeChange(nextMode);
    setPriceSubmenu(nextMode === "range" ? "range" : "options");
    if (nextMode !== "range") setOpenFilter(null);
  }

  const priceLabel = priceMode === "asc" ? "Menor precio" : priceMode === "desc" ? "Mayor precio" : priceMode === "range" ? "Rango de precio" : "Precio";
  const storeLabel = storeId === null ? "Bodegas" : stores.find((store) => store.id === storeId)?.nombre || "Bodegas";

  return <div className="catalog-toolbar" ref={toolbarRef}>
    <label className="search-field catalog-search"><Icon name="search" size={17} /><input type="search" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Buscar producto o bodega" aria-label="Buscar producto o bodega" /></label>
    <div className="catalog-filter-actions">
      <div className="filter-menu">
        <button type="button" className={`filter-chip ${storeId !== null ? "selected" : ""}`} aria-expanded={openFilter === "store"} onClick={() => setOpenFilter(openFilter === "store" ? null : "store")}><Icon name="store" size={15} /><span>{storeLabel}</span><Icon name="chevronDown" size={14} /></button>
        {openFilter === "store" && <div className="filter-popover"><strong>Elegir bodega</strong><div className="filter-options">
          <button type="button" className={storeId === null ? "chosen" : ""} onClick={() => { onStoreIdChange(null); setOpenFilter(null); }}>Todas las bodegas</button>
          {stores.map((store) => <button type="button" key={store.id} className={storeId === store.id ? "chosen" : ""} onClick={() => { onStoreIdChange(store.id); setOpenFilter(null); }}>{store.nombre}</button>)}
        </div></div>}
      </div>
      <div className="filter-menu">
        <button type="button" className={`filter-chip ${priceMode !== "none" ? "selected" : ""}`} aria-expanded={openFilter === "price"} onClick={() => { if (openFilter !== "price") setPriceSubmenu(priceMode === "range" ? "range" : "options"); setOpenFilter(openFilter === "price" ? null : "price"); }}><Icon name="tag" size={15} /><span>{priceLabel}</span><Icon name="chevronDown" size={14} /></button>
        {openFilter === "price" && <div className="filter-popover"><strong>Ordenar o filtrar precio</strong>{priceSubmenu === "options" ? <div className="filter-options">
          <button type="button" className={priceMode === "asc" ? "chosen" : ""} onClick={() => choosePriceMode("asc")}>Menor precio primero</button>
          <button type="button" className={priceMode === "desc" ? "chosen" : ""} onClick={() => choosePriceMode("desc")}>Mayor precio primero</button>
          <button type="button" className={priceMode === "range" ? "chosen" : ""} onClick={() => setPriceSubmenu("range")}>Elegir rango</button>
        </div> : <><div className="price-range"><label>Desde S/<input type="number" min="0" step="0.01" inputMode="decimal" value={minPrice} onChange={(event) => onMinPriceChange(event.target.value)} placeholder="0.00" /></label><label>Hasta S/<input type="number" min="0" step="0.01" inputMode="decimal" value={maxPrice} onChange={(event) => onMaxPriceChange(event.target.value)} placeholder="Sin límite" /></label></div><button type="button" className="filter-done" onClick={() => setOpenFilter(null)}>Listo</button></>}</div>}
      </div>
      <div className="filter-menu">
        <button type="button" className={`filter-chip ${maxDays !== "" ? "selected" : ""}`} aria-expanded={openFilter === "expiry"} onClick={() => setOpenFilter(openFilter === "expiry" ? null : "expiry")}><Icon name="calendar" size={15} /><span>{maxDays === "" ? "Vencimiento" : `Hasta ${maxDays} días`}</span><Icon name="chevronDown" size={14} /></button>
        {openFilter === "expiry" && <div className="filter-popover"><strong>Días hasta vencer</strong><label className="expiry-input">Como máximo<input type="number" min="0" step="1" inputMode="numeric" value={maxDays} onChange={(event) => onMaxDaysChange(event.target.value)} placeholder="Ej. 10" /></label><div className="expiry-presets">{[7, 10, 15, 30].map((days) => <button type="button" key={days} className={maxDays === String(days) ? "chosen" : ""} onClick={() => onMaxDaysChange(String(days))}>{days} días</button>)}</div><button type="button" className="filter-done" onClick={() => setOpenFilter(null)}>Listo</button></div>}
      </div>
      {hasFilters && <button type="button" className="button button-secondary clear-filters" onClick={() => { onClear(); setOpenFilter(null); }}>Limpiar</button>}
    </div>
    {hasFilters && <p className="result-count" role="status">{resultLabel}</p>}
  </div>;
}
