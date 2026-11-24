import React, { useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { EmptyState } from "../../components/common/InventoryRows";
import { VoiceInput } from "../../components/common/VoiceInput";
import { PageDate } from "../../components/layout/PageDate";
import { BarcodeCapture } from "../products/ProductModal";
import { isJefe } from "../../lib/permissions";
import { addToCart, cartTotal, saleBlockReason, setCartQuantity } from "../../lib/sales";
import { parseSaleSpeech } from "../../lib/voiceParser";
import { fold } from "../../lib/textTools";
import "./sales.css";

const RECENT_LIMIT = 8;
const soles = (value) => `S/ ${Number(value || 0).toFixed(2)}`;
const stepFor = (unit) => (["kg", "litro"].includes(unit) ? 0.5 : 1);
const timeLabel = (value) => new Date(value).toLocaleString("es-PE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

export function SalesPage({ products, movements, user, onRegisterSale }) {
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState("");
  const [assist, setAssist] = useState(null);
  const [error, setError] = useState("");
  const [voice, setVoice] = useState({ ambiguous: [], unknown: [] });
  const [barcode, setBarcode] = useState("");

  const visible = useMemo(() => products
    .filter((product) => product.activo !== false && fold(`${product.name} ${product.category}`).includes(fold(search.trim())))
    .sort((first, second) => Number(Boolean(saleBlockReason(first))) - Number(Boolean(saleBlockReason(second))) || first.name.localeCompare(second.name, "es")), [products, search]);
  const lines = cart.map((line) => ({ ...line, product: products.find((item) => item.id === line.productId) })).filter((line) => line.product);
  const total = cartTotal(cart, products);
  const recent = useMemo(() => movements
    .filter((movement) => movement.tipo === "salida" && movement.motivo === "Venta" && (isJefe(user) || movement.responsable === user?.id))
    .slice(0, RECENT_LIMIT), [movements, user]);

  function addCapped(current, product, quantity) {
    const inCart = current.find((line) => line.productId === product.id)?.quantity || 0;
    const stock = Number(product.stock);
    if (inCart + quantity > stock) {
      setError(`Solo hay ${stock} ${product.unit} de ${product.name}.`);
      return stock > inCart ? addToCart(current, product.id, stock - inCart) : current;
    }
    return addToCart(current, product.id, quantity);
  }

  function addProduct(product, quantity = stepFor(product.unit)) {
    setError("");
    setCart(addCapped(cart, product, quantity));
  }

  function changeQuantity(product, value) {
    const quantity = Number(value);
    setError("");
    if (quantity > Number(product.stock)) {
      setError(`Solo hay ${product.stock} ${product.unit} de ${product.name}.`);
      setCart((current) => setCartQuantity(current, product.id, Number(product.stock)));
      return;
    }
    setCart((current) => setCartQuantity(current, product.id, quantity));
  }

  function interpretVoice(text) {
    const result = parseSaleSpeech(text, products);
    setError("");
    const blocked = [];
    const nextCart = result.lines.reduce((next, line) => {
      const product = products.find((item) => item.id === line.productId);
      const reason = saleBlockReason(product);
      if (reason) {
        blocked.push(`${product.name}: ${reason.toLowerCase()}`);
        return next;
      }
      return addCapped(next, product, line.quantity);
    }, cart);
    setCart(nextCart);
    setVoice({ ambiguous: result.ambiguous, unknown: [...result.unknown, ...blocked] });
  }

  function chooseAmbiguous(entry, product) {
    addProduct(product, entry.quantity);
    setVoice((current) => ({ ...current, ambiguous: current.ambiguous.filter((item) => item !== entry) }));
  }

  function scanCode(code) {
    const product = products.find((item) => item.barcode && item.barcode === code.trim());
    if (!product) return setError("Ese código no está asociado a un producto.");
    const reason = saleBlockReason(product);
    if (reason) return setError(`${product.name}: ${reason.toLowerCase()}.`);
    setBarcode("");
    return addProduct(product);
  }

  function submitSale() {
    const result = onRegisterSale(cart);
    if (!result?.ok) return setError(result?.error || "No se pudo registrar la venta.");
    setCart([]);
    setError("");
    setVoice({ ambiguous: [], unknown: [] });
    return undefined;
  }

  return <div className="page-content inner-page sales-page">
    <PageDate />
    <section className="welcome-row"><div><h1>Registrar venta</h1><p className="welcome-subtitle">Arma la cesta y confirma. El stock se descuenta una sola vez.</p></div></section>
    <div className="sales-layout">
      <section className="content-card sales-catalog" aria-label="Productos para vender">
        <div className="sales-tools">
          <label className="search-field sales-search"><Icon name="search" size={17} /><input aria-label="Buscar producto para vender" placeholder="Buscar producto" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          <button type="button" className={`sales-tool ${assist === "voice" ? "active" : ""}`} aria-pressed={assist === "voice"} onClick={() => setAssist((current) => current === "voice" ? null : "voice")}><Icon name="mic" size={17} /> Dictar venta</button>
          <button type="button" className={`sales-tool ${assist === "scan" ? "active" : ""}`} aria-pressed={assist === "scan"} onClick={() => setAssist((current) => current === "scan" ? null : "scan")}><Icon name="scan" size={17} /> Escanear</button>
        </div>
        {assist === "voice" && <div className="sales-assist">
          <VoiceInput example="vende dos arroz y un atún" onText={interpretVoice} />
          {voice.ambiguous.map((entry) => <div className="sales-choice" key={entry.heard}><span>¿Cuál «{entry.heard}»?</span>{entry.productIds.map((id) => products.find((item) => item.id === id)).filter((product) => product && !saleBlockReason(product)).map((product) => <button type="button" key={product.id} aria-label={`Elegir ${product.name}`} onClick={() => chooseAmbiguous(entry, product)}>{product.icon} {product.name}</button>)}</div>)}
          {voice.unknown.length > 0 && <p className="sales-unknown">No se agregó: {voice.unknown.join(", ")}</p>}
        </div>}
        {assist === "scan" && <div className="sales-assist"><BarcodeCapture barcode={barcode} setBarcode={setBarcode} onDetected={scanCode} /></div>}
        <div className="sales-grid">{visible.map((product) => {
          const reason = saleBlockReason(product);
          return <button type="button" key={product.id} className="sales-product" disabled={Boolean(reason)} aria-label={reason ? `${product.name} no disponible: ${reason}` : `Agregar ${product.name}`} onClick={() => addProduct(product)}>
            <span className="product-emoji">{product.icon}</span>
            <span className="sales-product-name"><strong>{product.name}</strong><small>{reason || `${product.stock} ${product.unit}`}</small></span>
            <b>{soles(product.price)}</b>
          </button>;
        })}</div>
        {visible.length === 0 && <EmptyState icon="search" title="No encontramos productos" text="Prueba con otro nombre." />}
      </section>
      <aside className="content-card sales-cart" aria-label="Cesta de venta">
        <h2>Cesta</h2>
        {lines.length === 0 ? <p className="sales-empty">La cesta está vacía</p> : <ul className="sales-lines">{lines.map(({ product, quantity }) => <li key={product.id}>
          <span className="sales-line-name"><strong>{product.icon} {product.name}</strong><small>{soles(product.price)} · {product.unit}</small></span>
          <input aria-label={`Cantidad de ${product.name}`} type="number" min={stepFor(product.unit)} step={stepFor(product.unit)} max={product.stock} value={quantity} onChange={(event) => changeQuantity(product, event.target.value)} />
          <b>{soles(quantity * product.price)}</b>
          <button type="button" aria-label={`Quitar ${product.name}`} onClick={() => setCart((current) => setCartQuantity(current, product.id, 0))}><Icon name="close" size={15} /></button>
        </li>)}</ul>}
        {error && <p className="sales-error" role="alert">{error}</p>}
        <div className="sales-total" data-testid="sale-total"><span>Total</span><strong>{soles(total)}</strong></div>
        <button type="button" className="button button-primary button-full" disabled={!lines.length} onClick={submitSale}>Registrar venta</button>
        <p className="sales-responsible">Responsable: {user?.name}</p>
      </aside>
    </div>
    <section className="content-card sales-history" role="region" aria-label="Ventas recientes">
      <h2>{isJefe(user) ? "Ventas recientes de la bodega" : "Tus ventas recientes"}</h2>
      {recent.length === 0 ? <p className="sales-empty">Aún no hay ventas registradas.</p> : <ul>{recent.map((movement) => <li key={movement.id}>
        <span><strong>{movement.detalles.map((item) => `${item.cantidad} ${item.productoNombre}`).join(", ")}</strong><small>{timeLabel(movement.fechaHora)} · {movement.responsableNombre}</small></span>
        <b>{soles(movement.total)}</b>
      </li>)}</ul>}
    </section>
  </div>;
}
