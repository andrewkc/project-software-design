import React, { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";
import "./store-panel.css";

const newKey = () => crypto.randomUUID();
const values = (event) => Object.fromEntries(new FormData(event.currentTarget));

function Field({ label, name, type = "text", required = true, ...props }) {
  return <label className="ops-field">{label}<input name={name} type={type} required={required} {...props} /></label>;
}

function ActionForm({ title, onSubmit, children, button = "Guardar", disabled = false }) {
  return <form className="ops-card" onSubmit={onSubmit}><h2>{title}</h2><div className="ops-form-grid">{children}</div><button type="submit" disabled={disabled}>{button}</button></form>;
}

export default function StorePanel({ onExit }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [products, setProducts] = useState([]);
  const [lots, setLots] = useState([]);
  const [offers, setOffers] = useState([]);
  const [movements, setMovements] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const [nextProducts, nextLots, nextOffers, nextMovements] = await Promise.all([
      apiGet("/store/products"), apiGet("/store/lots"), apiGet("/store/offers"), apiGet("/store/movements"),
    ]);
    setProducts(nextProducts);
    setLots(nextLots);
    setOffers(nextOffers);
    setMovements(nextMovements);
  }, []);

  useEffect(() => {
    apiGet("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (user?.role === "OWNER" || user?.role === "EMPLOYEE") {
      reload().catch((error) => setMessage(error.message));
    }
  }, [user, reload]);

  async function run(action, successText) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      await reload();
      setMessage(successText);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    try {
      setUser(await apiPost("/auth/login", values(event)));
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    try { await apiPost("/auth/logout"); } finally { setUser(null); setProducts([]); setLots([]); setOffers([]); setMovements([]); }
  }

  const owner = user?.role === "OWNER";
  const staff = owner || user?.role === "EMPLOYEE";

  return <div className="ops-shell">
    <header className="ops-header"><div><strong>Bodega Clara</strong><span> Gestión real · fase 2</span></div><div>{user && <span>{user.name} · {owner ? "Dueño" : user.role === "EMPLOYEE" ? "Empleado" : user.role}</span>}{user && <button type="button" onClick={logout}>Salir de cuenta</button>}<button type="button" onClick={onExit}>Volver al prototipo</button></div></header>
    <main className="ops-main">
      {loading && <p>Comprobando sesión…</p>}
      {!loading && !user && <ActionForm title="Ingresar a la bodega" onSubmit={login} button="Ingresar"><Field label="Correo" name="email" type="email" /><Field label="Contraseña" name="password" type="password" /></ActionForm>}
      {!loading && user && !staff && <p>Esta sección es para dueños y empleados. Usa «Comprar en bodegas» para ver el catálogo de cliente.</p>}
      {message && <p className="ops-message" role="status">{message}</p>}
      {staff && <>
        <section className="ops-intro"><h1>Inventario de tu bodega</h1><p>Los saldos y movimientos provienen de PostgreSQL. La venta presencial descuenta primero los lotes aptos más próximos a cerrar.</p></section>
        <section className="ops-grid">
          {owner && <ActionForm title="Nuevo producto" disabled={busy} onSubmit={(event) => { event.preventDefault(); run(() => apiPost("/store/products", values(event)), "Producto creado."); event.currentTarget.reset(); }}>
            <Field label="Código" name="code" /><Field label="Nombre" name="name" /><Field label="Categoría" name="category" />
            <label className="ops-field">Unidad<select name="unit"><option value="G">Gramos</option><option value="UNIT">Unidades</option></select></label>
            <Field label="Paso de venta" name="sale_step" type="number" min="1" /><Field label="Precio por paso (S/)" name="reference_price" type="number" min="0.01" step="0.01" />
            <Field label="Conservación" name="storage_conditions" />
          </ActionForm>}
          {owner && <ActionForm title="Ingreso y nuevo lote" disabled={busy || products.length === 0} onSubmit={(event) => { event.preventDefault(); run(() => apiPost("/store/inbounds", { ...values(event), idempotency_key: newKey() }), "Lote ingresado."); event.currentTarget.reset(); }}>
            <label className="ops-field">Producto<select name="product_id" required>{products.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.sale_step} {item.unit}</option>)}</select></label>
            <Field label="Código de lote" name="code" /><Field label="Fecha de ingreso" name="received_date" type="date" /><Field label="Vencimiento" name="expiry_date" type="date" />
            <Field label="Cantidad base" name="quantity" type="number" min="1" /><Field label="Costo total (S/)" name="total_cost" type="number" min="0" step="0.01" />
          </ActionForm>}
          <ActionForm title="Venta presencial" disabled={busy || products.length === 0} onSubmit={(event) => { event.preventDefault(); run(() => apiPost("/store/local-sales", { ...values(event), idempotency_key: newKey() }), "Venta registrada y stock actualizado."); }} button="Registrar venta">
            <label className="ops-field">Producto<select name="product_id" required>{products.map((item) => <option key={item.id} value={item.id}>{item.name} · paso {item.sale_step} {item.unit}</option>)}</select></label>
            <Field label="Cantidad en unidad base" name="quantity" type="number" min="1" />
          </ActionForm>
          {owner && <ActionForm title="Merma" disabled={busy || lots.length === 0} onSubmit={(event) => { event.preventDefault(); run(() => apiPost("/store/waste", { ...values(event), idempotency_key: newKey() }), "Merma registrada."); }}>
            <label className="ops-field">Lote<select name="lot_id" required>{lots.map((item) => <option key={item.id} value={item.id}>{item.product_name} · {item.code} · disponible {item.available_qty}</option>)}</select></label>
            <Field label="Cantidad a retirar" name="quantity" type="number" min="1" /><Field label="Motivo" name="reason" />
          </ActionForm>}
          {owner && <ActionForm title="Ajuste por conteo" disabled={busy || lots.length === 0} onSubmit={(event) => { event.preventDefault(); run(() => apiPost("/store/adjustments", { ...values(event), idempotency_key: newKey() }), "Ajuste registrado."); }}>
            <label className="ops-field">Lote<select name="lot_id" required>{lots.map((item) => <option key={item.id} value={item.id}>{item.product_name} · {item.code}</option>)}</select></label>
            <Field label="Diferencia (+ o -)" name="delta" type="number" step="1" /><Field label="Motivo" name="reason" />
          </ActionForm>}
        </section>
        <section className="ops-card"><h2>Lotes y existencias</h2><div className="ops-table-wrap"><table><thead><tr><th>Producto / lote</th><th>Vence</th><th>Físico</th><th>Reservado</th><th>Disponible</th>{owner && <th>Costo total</th>}</tr></thead><tbody>{lots.map((item) => <tr key={item.id}><td>{item.product_name}<small>{item.code}</small></td><td>{item.expiry_date}</td><td>{item.physical_qty}</td><td>{item.reserved_qty}</td><td>{item.available_qty}</td>{owner && <td>S/ {item.total_cost}</td>}</tr>)}</tbody></table>{lots.length === 0 && <p>No hay lotes registrados.</p>}</div></section>
        <section className="ops-card"><h2>Ofertas y precios</h2><div className="ops-offers">{offers.map((item) => <article key={item.id} className="ops-offer"><div><strong>{item.product_name}</strong><small>Lote {item.lot_code} · vence {item.expiry_date} · {item.state}</small><p>Precio por paso: <b>S/ {item.current_price}</b> · original S/ {item.original_price}</p>{owner && item.limit && <small>Límite: {item.limit.max_discount_pct}% · piso efectivo S/ {item.limit.effective_floor}</small>}</div>{owner && <div className="ops-offer-actions"><button disabled={busy} type="button" onClick={() => run(() => apiPost(`/store/offers/${item.id}/${item.state === "PUBLISHED" ? "pause" : "publish"}`), "Estado de oferta actualizado.")}>{item.state === "PUBLISHED" ? "Pausar" : "Publicar"}</button><form onSubmit={(event) => { event.preventDefault(); const data = values(event); run(() => apiPost(`/store/offers/${item.id}/limits`, { ...data, below_cost_authorized: Boolean(data.below_cost_authorized) }), "Límites actualizados."); }}><input name="max_discount_pct" type="number" min="0" max="99.99" step="0.01" placeholder="Descuento máx. %" required /><input name="minimum_price" type="number" min="0.01" step="0.01" placeholder="Precio mínimo" required /><label><input type="checkbox" name="below_cost_authorized" /> Autorizar bajo costo</label><button disabled={busy}>Guardar límites</button></form><form onSubmit={(event) => { event.preventDefault(); run(() => apiPost(`/store/offers/${item.id}/price`, values(event)), "Precio actualizado."); }}><input name="new_price" type="number" min="0.01" step="0.01" placeholder="Nuevo precio" required /><input name="reason" placeholder="Motivo" required /><button disabled={busy}>Bajar precio</button></form></div>}</article>)}</div>{offers.length === 0 && <p>No hay ofertas.</p>}</section>
        <section className="ops-card"><h2>Movimientos recientes</h2><div className="ops-table-wrap"><table><thead><tr><th>Fecha</th><th>Tipo</th><th>Lotes</th><th>Total</th><th>Motivo</th></tr></thead><tbody>{movements.map((item) => <tr key={item.id}><td>{item.confirmed_at?.slice(0, 16)}</td><td>{item.kind}</td><td>{item.lines.map((line) => `${line.delta}`).join(", ")}</td><td>S/ {item.total}</td><td>{item.reason || "—"}</td></tr>)}</tbody></table>{movements.length === 0 && <p>Sin movimientos.</p>}</div></section>
      </>}
    </main>
  </div>;
}
