import React, { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { EmptyState } from "../../components/common/InventoryRows";
import { customerCatalog, stockChanges } from "../../lib/liveStock";
import { addToCart, cartTotal, setCartQuantity } from "../../lib/sales";
import { fold } from "../../lib/textTools";
import "../sales/sales.css";
import "./customer.css";

const HIGHLIGHT_MS = 3500;
const AVAILABILITY = {
  available: { label: "Disponible", tone: "ok" },
  low: { label: "Últimas unidades", tone: "low" },
  out: { label: "Agotado", tone: "out" },
};
const ORDER_STATUS = {
  pendiente: { label: () => "Pendiente", tone: "low" },
  aceptado: { label: (order) => `Aceptado por ${order.atendidoPorNombre || "la bodega"}`, tone: "ok" },
  rechazado: { label: (order) => `Rechazado: ${order.motivoRechazo}`, tone: "out" },
  cancelado: { label: () => "Cancelado", tone: "muted" },
};
const soles = (value) => `S/ ${Number(value || 0).toFixed(2)}`;
const stepFor = (unit) => (["kg", "litro"].includes(unit) ? 0.5 : 1);
const timeLabel = (value) => new Date(value).toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

// El carrito sobrevive a cambiar de pantalla o recargar; si el almacenamiento falla, solo vive en memoria.
function readCart(key) {
  try {
    const saved = JSON.parse(localStorage.getItem(key));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export function CustomerStockPage({ products, user, orders = [], onPlaceOrder, onCancelOrder }) {
  const cartKey = `bodega-cart-${user?.id || "cliente"}`;
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [changes, setChanges] = useState({});
  const [announcement, setAnnouncement] = useState("");
  const [cart, setCart] = useState(() => readCart(cartKey));
  const [error, setError] = useState("");
  const previous = useRef(products);
  const catalog = useMemo(() => customerCatalog(products), [products]);
  const categories = useMemo(() => [...new Set(catalog.map((item) => item.category))].sort((a, b) => a.localeCompare(b, "es")), [catalog]);
  const visible = catalog.filter((item) => (!category || item.category === category) && fold(item.name).includes(fold(search.trim())));
  const lines = cart.map((line) => ({ ...line, product: catalog.find((item) => item.id === line.productId) })).filter((line) => line.product);
  const total = cartTotal(cart, catalog);

  useEffect(() => {
    try { localStorage.setItem(cartKey, JSON.stringify(cart)); } catch { /* sin almacenamiento, el carrito sigue en memoria */ }
  }, [cart, cartKey]);

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

  // Si otra persona compra mientras el cliente arma su pedido, el carrito se ajusta al stock en vivo.
  useEffect(() => {
    const notices = [];
    const next = cart.flatMap((line) => {
      const product = catalog.find((item) => item.id === line.productId);
      const stock = Number(product?.stock || 0);
      if (!product || stock <= 0) {
        notices.push(`${product?.name || "Un producto"} se agotó y salió de tu pedido.`);
        return [];
      }
      if (line.quantity > stock) {
        notices.push(`Ahora solo quedan ${stock} ${product.unit} de ${product.name}.`);
        return [{ ...line, quantity: stock }];
      }
      return [line];
    });
    if (!notices.length) return;
    setCart(next);
    setError(notices.join(" "));
  }, [catalog]); // eslint-disable-line react-hooks/exhaustive-deps

  function addProduct(product) {
    const inCart = cart.find((line) => line.productId === product.id)?.quantity || 0;
    const stock = Number(product.stock);
    const step = stepFor(product.unit);
    if (inCart + step > stock) {
      setError(`Solo quedan ${stock} ${product.unit} de ${product.name}.`);
      if (stock > inCart) setCart(addToCart(cart, product.id, stock - inCart));
      return;
    }
    setError("");
    setCart(addToCart(cart, product.id, step));
  }

  function changeQuantity(product, value) {
    const quantity = Number(value);
    if (quantity > Number(product.stock)) {
      setError(`Solo quedan ${product.stock} ${product.unit} de ${product.name}.`);
      setCart(setCartQuantity(cart, product.id, Number(product.stock)));
      return;
    }
    setError("");
    setCart(setCartQuantity(cart, product.id, quantity));
  }

  function submitOrder() {
    const result = onPlaceOrder?.(cart);
    if (!result?.ok) return setError(result?.error || "No se pudo enviar el pedido.");
    setCart([]);
    setError("");
    return undefined;
  }

  return <div className="page-content inner-page customer-page">
    <section className="welcome-row customer-heading">
      <div><h1>Stock de tu bodega</h1><p className="welcome-subtitle">Vinculado a <strong>{user?.store || "tu bodega"}</strong></p></div>
      <span className="live-badge"><i aria-hidden="true" /> En vivo</span>
    </section>
    <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
    <div className="customer-layout">
      <div className="customer-catalog">
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
          const inCart = cart.find((line) => line.productId === item.id)?.quantity;
          return <article key={item.id} aria-label={item.name} className={`stock-tile stock-tile-${state.tone} ${delta !== undefined ? "stock-tile-changed" : ""}`}>
            <div className="stock-tile-top"><span className="product-emoji">{item.icon}</span><span className={`stock-state stock-state-${state.tone}`}>{state.label}</span></div>
            <h2>{item.name}</h2>
            <small>{item.category}</small>
            <div className="stock-tile-count"><strong>{item.stock}</strong><span>{item.unit}</span>{delta !== undefined && <em>{delta > 0 ? `+${delta}` : delta}</em>}</div>
            <div className="stock-tile-foot">
              <b>{soles(item.price)}</b>
              {item.availability === "out"
                ? <button type="button" className="tile-add" disabled aria-label={`${item.name} agotado`}>Sin stock</button>
                : <button type="button" className="tile-add" aria-label={`Agregar ${item.name} al pedido`} onClick={() => addProduct(item)}><Icon name="plus" size={15} />{inCart ? inCart : "Agregar"}</button>}
            </div>
          </article>;
        })}</section>
        {visible.length === 0 && <EmptyState icon="search" title="No encontramos productos" text="Prueba con otro nombre o categoría." />}
      </div>
      <div className="customer-side">
      <aside id="customer-cart" className="content-card sales-cart customer-cart" aria-label="Tu pedido">
        <h2>Tu pedido</h2>
        {lines.length === 0 ? <p className="sales-empty">Tu pedido está vacío</p> : <ul className="sales-lines">{lines.map(({ product, quantity }) => <li key={product.id}>
          <span className="sales-line-name"><strong>{product.icon} {product.name}</strong><small>{soles(product.price)} · {product.unit}</small></span>
          <input aria-label={`Cantidad de ${product.name}`} type="number" min={stepFor(product.unit)} step={stepFor(product.unit)} max={product.stock} value={quantity} onChange={(event) => changeQuantity(product, event.target.value)} />
          <b>{soles(quantity * product.price)}</b>
          <button type="button" aria-label={`Quitar ${product.name}`} onClick={() => setCart(setCartQuantity(cart, product.id, 0))}><Icon name="close" size={15} /></button>
        </li>)}</ul>}
        {error && <p className="sales-error" role="alert">{error}</p>}
        <div className="sales-total" data-testid="order-total"><span>Total</span><strong>{soles(total)}</strong></div>
        <button type="button" className="button button-primary button-full" disabled={!lines.length} onClick={submitOrder}>Enviar pedido</button>
        <p className="sales-responsible">La bodega confirma tu pedido. El stock se descuenta cuando lo acepta.</p>
      </aside>
    <section className="content-card sales-history customer-orders" role="region" aria-label="Tus pedidos">
      <h2>Tus pedidos</h2>
      {orders.length === 0 ? <p className="sales-empty">Aún no has enviado pedidos.</p> : <ul>{orders.map((order) => {
        const status = ORDER_STATUS[order.estado] || ORDER_STATUS.pendiente;
        return <li key={order.id}>
          <span><strong>{order.lineas.map((line) => `${line.cantidad} ${line.productoNombre}`).join(", ")}</strong><small>{timeLabel(order.creadoEn)} · {soles(order.total)}</small></span>
          <span className="order-side">
            <span className={`stock-state stock-state-${status.tone}`}>{status.label(order)}</span>
            {order.estado === "pendiente" && <button type="button" className="order-cancel" onClick={() => onCancelOrder?.(order.id)}>Cancelar pedido</button>}
          </span>
        </li>;
      })}</ul>}
    </section>
      </div>
    </div>
    {lines.length > 0 && <button type="button" className="sales-mobile-bar" onClick={() => document.getElementById("customer-cart")?.scrollIntoView({ behavior: "smooth", block: "center" })}><span>Ver pedido · {lines.length}</span><strong>{soles(total)}</strong></button>}
  </div>;
}
