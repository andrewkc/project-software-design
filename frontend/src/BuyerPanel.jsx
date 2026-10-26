import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "./api";
import "./buyer-panel.css";

const money = (value) => `S/ ${Number(value).toFixed(2)}`;
const formValues = (event) => Object.fromEntries(new FormData(event.currentTarget));

export default function BuyerPanel({ onExit }) {
  const [stores, setStores] = useState([]);
  const [offers, setOffers] = useState([]);
  const [storeId, setStoreId] = useState("");
  const [user, setUser] = useState(null);
  const [basket, setBasket] = useState({});
  const [orders, setOrders] = useState([]);
  const [activeOrder, setActiveOrder] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [message, setMessage] = useState("");
  const [chatReply, setChatReply] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [nextStores, nextOffers] = await Promise.all([apiGet("/stores"), apiGet("/offers")]);
    setStores(nextStores);
    setOffers(nextOffers);
    setStoreId((current) => current || nextStores[0]?.id || "");
  }, []);
  const refreshOrders = useCallback(async () => setOrders(await apiGet("/orders")), []);

  useEffect(() => {
    refresh().catch((error) => setMessage(error.message));
    apiGet("/auth/me").then(setUser).catch(() => setUser(null));
  }, [refresh]);
  useEffect(() => {
    if (user?.role === "CUSTOMER") refreshOrders().catch((error) => setMessage(error.message));
  }, [user, refreshOrders]);

  const visible = offers.filter((offer) => offer.store_id === storeId);
  const chosen = offers.filter((offer) => basket[offer.id] && offer.store_id === storeId);
  const total = useMemo(() => chosen.reduce((sum, offer) => sum + basket[offer.id] * Number(offer.current_price), 0), [chosen, basket]);

  function add(offer) {
    setBasket((current) => ({ ...current, [offer.id]: Math.min((current[offer.id] || 0) + 1, offer.available_steps) }));
  }

  function remove(offer) {
    setBasket((current) => {
      const next = { ...current };
      next[offer.id] -= 1;
      if (next[offer.id] <= 0) delete next[offer.id];
      return next;
    });
  }

  async function authenticate(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const data = formValues(event);
      if (registering) await apiPost("/auth/register", data);
      setUser(await apiPost("/auth/login", { email: data.email, password: data.password }));
      setRegistering(false);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await apiPost("/auth/logout");
    setUser(null);
    setOrders([]);
    setActiveOrder(null);
  }

  async function createOrder() {
    setBusy(true);
    setMessage("");
    try {
      const order = await apiPost("/orders", {
        idempotency_key: crypto.randomUUID(),
        lines: chosen.map((offer) => ({ offer_id: offer.id, base_quantity: basket[offer.id] * offer.sale_step })),
      });
      setActiveOrder(order);
      setBasket({});
      await Promise.all([refresh(), refreshOrders()]);
      setMessage("Pedido reservado. El pago de esta fase es una simulación local.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function simulate(decision) {
    setBusy(true);
    setMessage("");
    try {
      const order = await apiPost(`/orders/${activeOrder.id}/simulate-payment`, { decision });
      setActiveOrder(order);
      await Promise.all([refresh(), refreshOrders()]);
      setMessage(order.state === "PAID" ? "Compra simulada completada. Recojo informativo en bodega." :
        order.state === "EXPIRED" ? "La reserva venció; el stock fue liberado." : "Pago simulado rechazado; el stock fue liberado.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return <div className="buyer-shell">
    <header className="buyer-header"><strong>Bodega Clara · Compras</strong><div>{user && <span>{user.name}</span>}{user && <button onClick={() => logout().catch((error) => setMessage(error.message))}>Salir de cuenta</button>}<button onClick={onExit}>Volver</button></div></header>
    <main className="buyer-main">
      <section className="buyer-hero"><div><span className="buyer-tag">DEMO LOCAL · SIN DINERO REAL</span><h1>Ofertas para recoger en bodega</h1><p>Elige una bodega, arma tu cesta y prueba la compra. Las cantidades y precios vienen de la API Python.</p></div></section>
      {message && <p role="status" className="buyer-message">{message}</p>}
      <label className="buyer-select">Bodega <select value={storeId} onChange={(event) => { setStoreId(event.target.value); setBasket({}); }}><option value="">Selecciona una bodega</option>{stores.map((store) => <option key={store.id} value={store.id}>{store.name} · {store.address}</option>)}</select></label>
      <div className="buyer-layout"><section><h2>Ofertas disponibles</h2><div className="buyer-products">{visible.map((offer) => <article className="buyer-card" key={offer.id}><span className="buyer-category">{offer.category}</span><h3>{offer.product_name}</h3><p>Vence {offer.expiry_date} · {offer.storage_conditions}</p><p>Por {offer.sale_step} {offer.unit} · disponibles {offer.available_steps} pasos</p><div className="buyer-card-bottom"><strong>{money(offer.current_price)}</strong><button disabled={busy || basket[offer.id] >= offer.available_steps} onClick={() => add(offer)}>Añadir</button></div></article>)}</div>{visible.length === 0 && <p>No hay ofertas publicadas con stock en esta bodega.</p>}</section>
      <aside className="buyer-basket"><h2>Tu cesta</h2>{chosen.map((offer) => <div className="buyer-line" key={offer.id}><span>{offer.product_name}<small>{basket[offer.id] * offer.sale_step} {offer.unit} · {money(basket[offer.id] * Number(offer.current_price))}</small></span><span><button aria-label={`Quitar ${offer.product_name}`} onClick={() => remove(offer)}>−</button><b>{basket[offer.id]}</b><button aria-label={`Añadir ${offer.product_name}`} disabled={basket[offer.id] >= offer.available_steps} onClick={() => add(offer)}>+</button></span></div>)}{chosen.length === 0 && <p>Agrega productos de una sola bodega.</p>}<p className="buyer-total">Total estimado <strong>{money(total)}</strong></p><small>El precio final se congela al crear el pedido. La reserva dura hasta 10 minutos.</small>{user?.role === "CUSTOMER" && <button className="buyer-primary" disabled={busy || chosen.length === 0} onClick={createOrder}>Crear pedido y reservar</button>}{user && user.role !== "CUSTOMER" && <p>Ingresa con una cuenta de comprador para pedir.</p>}</aside></div>
      {!user && <section className="buyer-auth"><h2>{registering ? "Crear cuenta de comprador" : "Ingresar para comprar"}</h2><form onSubmit={authenticate}>{registering && <label>Nombre<input name="name" required /></label>}<label>Correo<input name="email" type="email" required /></label><label>Contraseña<input name="password" type="password" minLength="8" required /></label><button disabled={busy}>{registering ? "Registrarme" : "Ingresar"}</button></form><button className="buyer-link" onClick={() => setRegistering(!registering)}>{registering ? "Ya tengo cuenta" : "Crear cuenta"}</button></section>}
      {activeOrder && <section className="buyer-order"><h2>Pedido {activeOrder.id.slice(0, 8)}</h2><p>Estado: <strong>{activeOrder.state}</strong> · Total: {money(activeOrder.total)}</p><p>Recojo informativo: {activeOrder.pickup_address}</p>{activeOrder.state === "PENDING" && <><p>Reserva hasta {new Date(activeOrder.reservation_until).toLocaleString("es-PE")}</p><div className="buyer-actions"><button disabled={busy} onClick={() => simulate("APPROVE")}>Simular pago aprobado</button><button disabled={busy} onClick={() => simulate("REJECT")}>Simular rechazo</button></div></>}<small>Simulación interna de fase 3; Mercado Pago se conecta en la fase 4.</small></section>}
      {user?.role === "CUSTOMER" && <section className="buyer-history"><h2>Mis pedidos</h2>{orders.map((order) => <button key={order.id} onClick={async () => setActiveOrder(await apiGet(`/orders/${order.id}`))}>{order.id.slice(0, 8)} · {order.state} · {money(order.total)}</button>)}{orders.length === 0 && <p>Aún no tienes pedidos.</p>}</section>}
      <section className="buyer-auth"><h2>Asistente de ofertas</h2><p>Respuesta local de demostración, basada en las ofertas públicas. Gemini se conectará en la fase 4.</p><form onSubmit={async (event) => { event.preventDefault(); try { setChatReply((await apiPost("/chat", { question: formValues(event).question })).answer); } catch (error) { setChatReply(error.message); } }}><label>Pregunta<input name="question" maxLength="1000" placeholder="¿Qué ofertas hay?" required /></label><button>Consultar</button></form>{chatReply && <p role="status">{chatReply}</p>}</section>
    </main>
  </div>;
}
