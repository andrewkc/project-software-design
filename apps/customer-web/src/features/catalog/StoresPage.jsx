import React from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { OfferCard } from "./OfferCard";
import { money } from "../../lib/format";
import { daysUntilExpiry } from "../../lib/catalog";

export function StoresPage({ stores, offers, selectedStoreId, onOpenStore, onBack, onAdd, onCart, cartCount }) {
  const selectedStore = stores.find((store) => store.id === selectedStoreId);

  if (selectedStore) {
    const storeProducts = offers.filter((offer) => offer.store_id === selectedStore.id && Number(offer.available) > 0 && (daysUntilExpiry(offer.expiry_date) ?? 0) >= 0);
    const discounted = storeProducts.filter((offer) => Number(offer.original_price) > Number(offer.current_price));
    const lowestPrice = storeProducts.length ? Math.min(...storeProducts.map((offer) => Number(offer.current_price))) : 0;
    return <div className="page-content inner-page">
      <PageDate onCart={onCart} cartCount={cartCount} />
      <button className="back-link" type="button" onClick={onBack}><Icon name="chevronLeft" size={16} />Todas las bodegas</button>
      <section className="store-banner">
        <div className="store-identity"><span className="store-symbol store-symbol-light"><Icon name="store" size={22} /></span><div><span className="date-greeting">BODEGA</span><h1>{selectedStore.nombre}</h1><p><Icon name="mapPin" size={14} /> {selectedStore.direccion || "Dirección disponible al confirmar el pedido"}</p></div></div>
        <div className="store-offer-count"><strong>{discounted.length}</strong><span>{discounted.length === 1 ? "oferta" : "ofertas"} · {storeProducts.length} {storeProducts.length === 1 ? "producto" : "productos"}</span></div>
      </section>
      <section className="content-card store-detail-card">
        <div className="card-heading"><div><h2>Productos de {selectedStore.nombre}</h2><p className="card-note">{storeProducts.length ? `${discounted.length} con descuento de ${storeProducts.length} productos. Desde ${money(lowestPrice)}; agrega a tu cesta para continuar.` : "Esta bodega no tiene productos disponibles por ahora."}</p></div></div>
        {storeProducts.length ? <div className="offer-grid">{storeProducts.map((offer) => <OfferCard key={offer.id} offer={offer} storeName={selectedStore.nombre} onAdd={onAdd} />)}</div> : <div className="empty-state"><span>📦</span><strong>Sin productos disponibles</strong><p>Vuelve a explorar otras bodegas.</p><button className="button button-secondary" type="button" onClick={onBack}>Ver bodegas</button></div>}
      </section>
    </div>;
  }

  return <div className="page-content inner-page">
    <PageDate onCart={onCart} cartCount={cartCount} />
    <section className="welcome-row"><div><h1>Bodegas y ofertas</h1><p className="welcome-subtitle">Elige una bodega para ver sus ofertas y su dirección de recojo.</p></div></section>
    <section className="store-card-grid">{stores.map((store) => {
      const products = offers.filter((offer) => offer.store_id === store.id && Number(offer.available) > 0 && (daysUntilExpiry(offer.expiry_date) ?? 0) >= 0);
      const deals = products.filter((offer) => Number(offer.original_price) > Number(offer.current_price));
      return <button key={store.id} className="store-card" type="button" onClick={() => onOpenStore(store.id)}>
        <span className={`store-symbol tone-${store.id % 3}`}><Icon name="store" size={22} /></span>
        <strong>{store.nombre}</strong>
        <span className="store-card-address">{store.direccion || "Recojo en bodega"}</span>
        <span className="store-card-link">{deals.length} {deals.length === 1 ? "oferta" : "ofertas"} · {products.length} {products.length === 1 ? "producto" : "productos"} · Ver bodega <Icon name="arrow" size={14} /></span>
      </button>;
    })}</section>
    {!stores.length && <div className="empty-state"><span>🏬</span><strong>Aún no hay bodegas disponibles</strong><p>Vuelve más tarde para descubrir ofertas cerca de ti.</p></div>}
  </div>;
}
