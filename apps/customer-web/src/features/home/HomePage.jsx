import React, { useMemo } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { OfferCard } from "../catalog/OfferCard";
import { CatalogToolbar } from "../catalog/CatalogToolbar";
import { daysUntilExpiry, filterOffers, groupOffersByStore, sortOffersByPrice } from "../../lib/catalog";
import { shortName } from "../../lib/format";

export function HomePage({ user, stores, offers, filters, onFiltersChange, onClearFilters, onAdd, onNavigate, onOpenStore, onCart, cartCount }) {
  const filtered = useMemo(() => filterOffers(offers, filters), [offers, filters]);
  const sorted = useMemo(() => sortOffersByPrice(filtered, filters.priceMode), [filtered, filters.priceMode]);
  const grouped = useMemo(() => groupOffersByStore(stores, sorted, false, filters.priceMode), [stores, sorted, filters.priceMode]);
  const expiringSoon = offers.filter((offer) => { const days = daysUntilExpiry(offer.expiry_date); return days !== null && days >= 0 && days <= 7; }).length;
  const hasFilters = Boolean(filters.query.trim() || filters.priceMode !== "none" || filters.maxDays !== "" || filters.storeId !== null);

  return <div className="page-content">
    <PageDate onCart={onCart} cartCount={cartCount} />
    <section className="welcome-row">
      <div><h1>Hola, {shortName(user).split(" ")[0] || "cliente"} <span className="wave">👋</span></h1><p className="welcome-subtitle">Ofertas de bodegas cercanas, con precios y vencimientos a la vista.</p></div>
      <button className="button button-primary add-top-button" type="button" onClick={() => onNavigate("stores")}><Icon name="store" size={16} />Ver bodegas</button>
    </section>
    <section className="home-summary-grid" aria-label="Resumen de ofertas">
      <article className="home-summary-card home-summary-products"><span className="summary-card-label">Ofertas activas</span><strong>{offers.length}</strong><button type="button" onClick={() => onNavigate("stores")}>Explorar</button></article>
      <article className="home-summary-card home-summary-units"><span className="summary-card-label">Bodegas disponibles</span><strong>{stores.length}</strong><button type="button" onClick={() => onNavigate("stores")}>Ver todas</button></article>
      <article className="home-summary-card home-summary-alert"><span className="summary-card-label">Vencen en 7 días</span><strong>{expiringSoon}</strong><button type="button" onClick={() => onFiltersChange({ ...filters, maxDays: "7" })}>Ver ofertas</button></article>
    </section>
    <section className="content-card catalog-card">
      <div className="card-heading"><div><h2>{hasFilters ? "Resultados de tu búsqueda" : "Ofertas disponibles"}</h2><p className="card-note">Compara precios y elige productos con fecha de vencimiento futura.</p></div></div>
      <CatalogToolbar stores={stores} {...filters} onQueryChange={(value) => onFiltersChange({ ...filters, query: value })} onMinPriceChange={(value) => onFiltersChange({ ...filters, minPrice: value })} onMaxPriceChange={(value) => onFiltersChange({ ...filters, maxPrice: value })} onPriceModeChange={(value) => onFiltersChange({ ...filters, priceMode: value })} onMaxDaysChange={(value) => onFiltersChange({ ...filters, maxDays: value })} onStoreIdChange={(value) => onFiltersChange({ ...filters, storeId: value })} onClear={onClearFilters} resultLabel={`${filtered.length} ${filtered.length === 1 ? "producto encontrado" : "productos encontrados"}`} />
      {grouped.length ? <div className="store-sections">{grouped.map((store) => <section className="store-section" key={store.id}>
        <div className="store-section-heading"><div className="store-identity"><span className={`store-symbol tone-${store.id % 3}`}><Icon name="store" size={18} /></span><div><h2>{store.nombre}</h2><p>{store.direccion || "Recojo en bodega"} · {store.offers.length} {store.offers.length === 1 ? "oferta" : "ofertas"}</p></div></div>
          <button className="text-link" type="button" onClick={() => onOpenStore(store.id)}>Ver bodega <Icon name="arrow" size={14} /></button></div>
        <div className="offer-grid">{store.offers.map((offer) => <OfferCard key={offer.id} offer={offer} storeName={store.nombre} onAdd={onAdd} />)}</div>
      </section>)}</div> : <div className="empty-state"><span>🔎</span><strong>No encontramos ofertas con esos filtros</strong><p>Prueba otro precio, más días hasta el vencimiento o una búsqueda distinta.</p><button className="button button-secondary" type="button" onClick={onClearFilters}>Limpiar filtros</button></div>}
    </section>
  </div>;
}
