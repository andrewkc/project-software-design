import React, { useEffect, useRef, useState } from "react";
import { api, saveToken, token } from "./api";
import CatalogView from "./CatalogView";

const money = (value) => `S/ ${Number(value || 0).toFixed(2)}`;
const orderTitle = (state) => ({ pagado: "¡Compra confirmada!", pendiente: "Completa tu compra", pago_en_revision: "Pago en revisión", rechazado: "Pago rechazado", expirado: "Este pedido venció" })[state] || "Estado del pedido";
const orderSummary = (state) => ({ pagado: "Tu pago fue aprobado y el inventario quedó actualizado.", pendiente: "Reservamos tus productos por diez minutos mientras completas el pago.", pago_en_revision: "Mercado Pago acreditó el importe después de perderse la reserva. La bodega debe revisar este caso; no descontamos otros productos.", rechazado: "No se aprobó el pago. La reserva se liberó y puedes iniciar otro pedido.", expirado: "La reserva se liberó. Puedes iniciar otro pedido desde las ofertas." })[state] || "Consulta el estado de tu pedido.";
const orderStatus = (state) => ({ pagado: "Pago aprobado", pendiente: "Pendiente de pago", pago_en_revision: "Pago en revisión", rechazado: "Pago rechazado", expirado: "Reserva vencida" })[state] || state;

export default function App() {
  const [stores, setStores] = useState([]);
  const [offers, setOffers] = useState([]);
  const [selectedStoreId, setSelectedStoreId] = useState(null);
  const [query, setQuery] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [priceMode, setPriceMode] = useState("none");
  const [maxDays, setMaxDays] = useState("");
  const [filterStoreId, setFilterStoreId] = useState(null);
  const [cart, setCart] = useState([]);
  const [pendingOffer, setPendingOffer] = useState(null);
  const [profile, setProfile] = useState(null);
  const [view, setView] = useState("discover");
  const [authMode, setAuthMode] = useState("login");
  const [orders, setOrders] = useState([]);
  const [activeOrder, setActiveOrder] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [pendingKey, setPendingKey] = useState(null);
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef(null);

  async function reload() {
    const [allStores, allOffers] = await Promise.all([api.stores(), api.offers()]);
    setStores(allStores);
    setOffers(allOffers);
  }

  useEffect(() => {
    reload().catch((error) => setMessage(error.message));
    if (token()) api.me().then(setProfile).catch(() => saveToken(null));
  }, []);

  useEffect(() => {
    if (!accountOpen) return;
    const closeOnOutside = (event) => { if (!accountRef.current?.contains(event.target)) setAccountOpen(false); };
    const closeOnEscape = (event) => { if (event.key === "Escape") setAccountOpen(false); };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accountOpen]);

  useEffect(() => {
    if (view !== "order" || !activeOrder || activeOrder.state !== "pendiente" || !activeOrder.payment_started) return;
    const timer = setInterval(() => api.verifyPayment(activeOrder.id).then((updated) => {
      setActiveOrder(updated);
      if (updated.state === "pagado") { setCart([]); setPendingKey(null); reload(); }
    }).catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, [view, activeOrder?.id, activeOrder?.state, activeOrder?.payment_started]);

  const cartStore = cart.length ? cart[0].store_id : null;
  const cartCount = cart.reduce((sum, line) => sum + line.quantity, 0);
  const cartTotal = cart.reduce((sum, line) => sum + Number(line.current_price) * line.quantity, 0);

  function openStore(id) {
    setSelectedStoreId(id);
    setView("store");
  }

  function add(offer, replaceCart = false) {
    if (cartStore && cartStore !== offer.store_id && !replaceCart) {
      setPendingOffer(offer);
      setMessage("Tu cesta contiene productos de otra bodega. Puedes vaciarla para comprar aquí.");
      return;
    }
    const current = replaceCart ? null : cart.find((item) => item.id === offer.id);
    if ((current?.quantity || 0) >= offer.available) { setMessage("No quedan más unidades disponibles."); return; }
    setCart((previous) => replaceCart ? [{ ...offer, quantity: 1 }] : current
      ? previous.map((item) => item.id === offer.id ? { ...item, quantity: item.quantity + 1 } : item)
      : [...previous, { ...offer, quantity: 1 }]);
    setPendingKey(null);
    setPendingOffer(null);
    if (view !== "store" || selectedStoreId !== offer.store_id) openStore(offer.store_id);
    setMessage(`${offer.product_name} agregado a tu cesta.`);
  }

  function changeQuantity(id, quantity) {
    const offer = offers.find((item) => item.id === id);
    if (quantity > (offer?.available || 0)) { setMessage("No hay suficientes unidades disponibles."); return; }
    setCart((previous) => previous.map((item) => item.id === id ? { ...item, quantity } : item).filter((item) => item.quantity > 0));
    setPendingKey(null);
  }

  async function authenticate(event) {
    event.preventDefault();
    setBusy(true); setMessage("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const result = authMode === "login" ? await api.login(data) : await api.register(data);
      saveToken(result.token); setProfile(result.profile); setView(cart.length ? "cart" : "discover");
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }

  async function openOrders() {
    if (!profile) { setView("auth"); return; }
    setAccountOpen(false);
    try { setOrders((await api.orders()).filter((order) => order.state === "pagado")); setView("history"); }
    catch (error) { setMessage(error.message); }
  }

  function logout() {
    saveToken(null);
    setProfile(null);
    setAccountOpen(false);
    setCart([]);
    setActiveOrder(null);
    setView("discover");
  }

  async function placeOrder() {
    if (!cart.length) { setMessage("Agrega un producto antes de continuar."); return; }
    if (!profile) { setView("auth"); return; }
    setBusy(true); setMessage("");
    const key = pendingKey || crypto.randomUUID();
    setPendingKey(key);
    try {
      const order = await api.createOrder({ idempotency_key: key, lines: cart.map((item) => ({ offer_id: item.id, quantity: item.quantity })) });
      setActiveOrder(order); setView("order");
    } catch (error) { setMessage(error.message); await reload().catch(() => {}); }
    finally { setBusy(false); }
  }

  async function pay() {
    setBusy(true); setMessage("");
    const paymentTab = activeOrder.payment_mode === "MERCADOPAGO_TEST" ? window.open("about:blank", "bodesmart-mercadopago") : null;
    if (paymentTab) paymentTab.opener = null;
    try {
      if (activeOrder.payment_mode === "MERCADOPAGO_TEST") {
        const result = await api.checkout(activeOrder.id);
        const updated = await api.order(activeOrder.id);
        setActiveOrder(updated);
        if (paymentTab) paymentTab.location.href = result.checkout_url;
        else window.location.assign(result.checkout_url);
        setMessage("Completa el pago de prueba en Mercado Pago y vuelve aquí. Comprobaremos el resultado automáticamente.");
      } else {
        const updated = await api.simulatePayment(activeOrder.id);
        setActiveOrder(updated); setCart([]); setPendingKey(null); await reload();
      }
    } catch (error) { if (paymentTab) paymentTab.close(); setMessage(error.message); }
    finally { setBusy(false); }
  }

  async function refreshOrder() {
    try {
      const updated = activeOrder.payment_started ? await api.verifyPayment(activeOrder.id) : await api.order(activeOrder.id);
      setActiveOrder(updated);
      if (updated.state === "pagado") { setCart([]); setPendingKey(null); await reload(); }
    } catch (error) { setMessage(error.message); }
  }

  return <div className="app-shell">
    <header className="site-header"><div className="header-inner">
      <button className="brand" onClick={() => setView("discover")} aria-label="Ir al inicio"><img src="/logo.png" alt="BodeSmart" /></button>
      <nav aria-label="Navegación principal"><button className={view === "discover" || view === "store" ? "active" : ""} onClick={() => setView("discover")}>Bodegas y ofertas</button><button onClick={openOrders}>Mis pedidos</button></nav>
      <div className="header-actions"><button className="cart-button" onClick={() => setView("cart")} aria-label={`Ver cesta, ${cartCount} productos`}>🛒 <span>Cesta</span><b>{cartCount}</b></button>{profile ? <div className="account-wrap" ref={accountRef}>
        <button className="profile-button" type="button" aria-haspopup="menu" aria-expanded={accountOpen} onClick={() => setAccountOpen((open) => !open)}>Hola, {profile.nombres} <span aria-hidden="true">⌄</span></button>
        {accountOpen && <div className="account-menu" role="menu"><div className="account-identity"><strong>{profile.nombres} {profile.apellidos}</strong><small>{profile.correo}</small></div><button role="menuitem" onClick={openOrders}>Mis pedidos</button><button role="menuitem" onClick={logout}>Cerrar sesión</button></div>}
      </div> : <button className="sign-in" onClick={() => { setAuthMode("login"); setView("auth"); }}>Ingresar</button>}</div>
    </div></header>
    {message && <div className="notice" role="status"><span>{message}</span>{pendingOffer && <button className="notice-action" onClick={() => add(pendingOffer, true)}>Vaciar cesta y agregar</button>}<button onClick={() => { setMessage(""); setPendingOffer(null); }} aria-label="Cerrar aviso">×</button></div>}
    <main className="main-content">
      {(view === "discover" || view === "store") && <CatalogView
        mode={view}
        stores={stores}
        offers={offers}
        selectedStoreId={selectedStoreId}
        onOpenStore={openStore}
        onBack={() => setView("discover")}
        onAdd={add}
        query={query}
        onQueryChange={setQuery}
        minPrice={minPrice}
        onMinPriceChange={setMinPrice}
        maxPrice={maxPrice}
        onMaxPriceChange={setMaxPrice}
        priceMode={priceMode}
        onPriceModeChange={setPriceMode}
        maxDays={maxDays}
        onMaxDaysChange={setMaxDays}
        filterStoreId={filterStoreId}
        onFilterStoreIdChange={setFilterStoreId}
        onClearFilters={() => { setQuery(""); setMinPrice(""); setMaxPrice(""); setPriceMode("none"); setMaxDays(""); setFilterStoreId(null); }}
      />}
      {view === "cart" && <section className="page-grid"><div><p className="eyebrow">TU COMPRA</p><h1>Tu cesta</h1><p className="subhead">Una compra por bodega, con recojo en tienda.</p>{cart.length ? <div className="basket-list">{cart.map((item) => <article key={item.id} className="basket-row"><div className="basket-icon">{item.icon || "📦"}</div><div className="basket-detail"><strong>{item.product_name}</strong><span>{item.store_name} · {money(item.current_price)} por {item.unit || "unidad"}</span></div><div className="quantity"><button onClick={() => changeQuantity(item.id, item.quantity - 1)} aria-label={`Quitar un ${item.product_name}`}>−</button><b>{item.quantity}</b><button onClick={() => changeQuantity(item.id, item.quantity + 1)} aria-label={`Agregar un ${item.product_name}`}>+</button></div><strong>{money(Number(item.current_price) * item.quantity)}</strong></article>)}</div> : <div className="empty"><span>🛒</span><h3>Tu cesta está vacía</h3><p>Explora las ofertas para comenzar.</p><button className="primary" onClick={() => setView("discover")}>Ver ofertas</button></div>}</div>{cart.length > 0 && <aside className="summary-card"><h2>Resumen del pedido</h2><div><span>Bodega</span><strong>{cart[0].store_name}</strong></div><div><span>Productos</span><strong>{cartCount}</strong></div><div className="total"><span>Total</span><strong>{money(cartTotal)}</strong></div><p>El recojo es informativo. El pedido se completa cuando se aprueba el pago de prueba.</p><button className="primary wide" disabled={busy} onClick={placeOrder}>{busy ? "Preparando..." : profile ? "Continuar al pago" : "Ingresar para comprar"}</button></aside>}</section>}
      {view === "auth" && <section className="auth-layout"><div className="auth-message"><p className="eyebrow">BODESMART</p><h1>Compra cerca.<br/>Aprovecha más.</h1><p>Guarda tus pedidos y compra con seguridad. Para explorar ofertas no necesitas una cuenta.</p></div><div className="auth-card"><p className="eyebrow">CUENTA DE COMPRADOR</p><h2>{authMode === "login" ? "Bienvenido de nuevo" : "Crea tu cuenta"}</h2><p>{authMode === "login" ? "Ingresa para terminar tu compra." : "Solo necesitamos tus datos básicos."}</p><form onSubmit={authenticate}>{authMode === "register" && <><label>Nombres<input name="nombres" required autoComplete="given-name" /></label><label>Apellidos<input name="apellidos" required autoComplete="family-name" /></label></>}<label>Correo electrónico<input type="email" name="correo" required autoComplete="email" /></label><label>Contraseña<input type="password" name="password" minLength="8" required autoComplete={authMode === "login" ? "current-password" : "new-password"} /></label><button className="primary wide" disabled={busy}>{busy ? "Espera..." : authMode === "login" ? "Ingresar" : "Crear cuenta"}</button></form><p className="auth-toggle">{authMode === "login" ? "¿Aún no tienes cuenta?" : "¿Ya tienes cuenta?"} <button onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>{authMode === "login" ? "Regístrate" : "Ingresa"}</button></p></div></section>}
      {view === "order" && activeOrder && <section className="order-page"><p className="eyebrow">PEDIDO #{activeOrder.id}</p><h1>{orderTitle(activeOrder.state)}</h1><p className="subhead">{orderSummary(activeOrder.state)}</p><div className="order-layout"><div className="order-card"><h2>Detalle del pedido</h2>{activeOrder.lines.map((line) => <div key={line.offer_id} className="order-line"><span>{line.icon || "📦"} {line.product_name} × {line.quantity}</span><strong>{money(line.amount)}</strong></div>)}<div className="order-line order-total"><span>Total</span><strong>{money(activeOrder.total)}</strong></div><div className="pickup"><b>📍 Recojo en {activeOrder.store_name}</b><p>{activeOrder.pickup_address || "Consulta la dirección con la bodega."}</p><small>El recojo se muestra como información; no requiere confirmación en esta demo.</small></div></div><aside className="summary-card"><h2>Estado</h2><div className={`status ${activeOrder.state}`}>{orderStatus(activeOrder.state)}</div>{activeOrder.state === "pendiente" && <><p>Reserva hasta: {new Date(activeOrder.reservation_until).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })}</p><button className="primary wide" disabled={busy} onClick={pay}>{busy ? "Espera..." : activeOrder.payment_mode === "MERCADOPAGO_TEST" ? "Pagar con Mercado Pago de prueba" : "Simular pago"}</button><button className="secondary wide" onClick={refreshOrder}>Comprobar estado</button></>}<button className="text-button" onClick={() => setView("discover")}>Volver a las ofertas</button></aside></div></section>}
      {view === "history" && <section className="history-page"><p className="eyebrow">TU CUENTA</p><h1>Mis pedidos</h1><p className="subhead">Aquí aparecen tus compras pagadas.</p>{orders.length ? <div className="history-list">{orders.map((order) => <button key={order.id} onClick={() => { setActiveOrder(order); setView("order"); }}><span><b>Pedido #{order.id}</b><small>{order.store_name} · {order.lines.length} productos</small></span><strong>{money(order.total)}</strong><em>Pagado</em><span>→</span></button>)}</div> : <div className="empty"><span>🧾</span><h3>Aún no tienes compras completadas</h3><button className="primary" onClick={() => setView("discover")}>Explorar ofertas</button></div>}</section>}
    </main><footer><span>BodeSmart</span><p>Productos cercanos a vencer, mejores oportunidades en tu barrio.</p><small>Demo académica · Pagos de prueba</small></footer>
  </div>;
}
