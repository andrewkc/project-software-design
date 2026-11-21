import React, { useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "./api";
import AdminPanel from "./AdminPanel";
import "./store-panel.css";

const newKey = () => crypto.randomUUID();
const values = (event) => Object.fromEntries(new FormData(event.currentTarget));
const recommendationReasons = {
  NO_STOCK: "Sin stock disponible", OUTSIDE_TRAINING_HORIZON: "Aún falta demasiado para el cierre",
  LOT_AGE_OUTSIDE_TRAINING: "Lote fuera del rango estudiado",
  INSUFFICIENT_HISTORY: "Faltan días de ventas para estimar",
  CATEGORY_OUTSIDE_TRAINING: "Categoría aún no cubierta",
  CURRENT_PRICE_COVERS_STOCK: "El precio actual ya cubre el stock",
  GAIN_BELOW_FIVE_POINTS: "El descuento no mejoraría lo suficiente",
  TARGET_COVERAGE: "Se espera vender al menos el 90 % del stock",
  MAX_EXPECTED_SALES: "Mejor venta esperada dentro del límite",
  LIMIT_UNAVAILABLE: "Configura los límites de precio",
};

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
  const [recommendations, setRecommendations] = useState([]);
  const [staffMembers, setStaffMembers] = useState([]);
  const [pricingPolicy, setPricingPolicy] = useState(null);
  const [autoConsent, setAutoConsent] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [chatReply, setChatReply] = useState("");
  const [chatBusy, setChatBusy] = useState(false);

  useEffect(() => setAutoConsent(false), [pricingPolicy?.mode]);

  const reload = useCallback(async (includeRecommendations = false) => {
    const [nextProducts, nextLots, nextOffers, nextMovements, nextRecommendations, nextPolicy, nextStaff] = await Promise.all([
      apiGet("/store/products"), apiGet("/store/lots"), apiGet("/store/offers"), apiGet("/store/movements"),
      includeRecommendations ? apiGet("/store/recommendations") : Promise.resolve([]),
      includeRecommendations ? apiGet("/store/pricing-policy") : Promise.resolve(null),
      includeRecommendations ? apiGet("/store/staff") : Promise.resolve([]),
    ]);
    setProducts(nextProducts);
    setLots(nextLots);
    setOffers(nextOffers);
    setMovements(nextMovements);
    setRecommendations(nextRecommendations);
    setPricingPolicy(nextPolicy);
    setStaffMembers(nextStaff);
  }, []);

  useEffect(() => {
    apiGet("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (user?.role === "OWNER" || user?.role === "EMPLOYEE") {
      reload(user.role === "OWNER").catch((error) => setMessage(error.message));
    }
  }, [user, reload]);

  async function run(action, successText) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      await reload(owner);
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
    try { await apiPost("/auth/logout"); } finally { setUser(null); setProducts([]); setLots([]); setOffers([]); setMovements([]); setRecommendations([]); }
  }

  const owner = user?.role === "OWNER";
  const staff = owner || user?.role === "EMPLOYEE";

  if (user?.role === "ADMIN") return <AdminPanel user={user} onExit={onExit} onLogout={logout} />;

  return <div className="ops-shell">
    <header className="ops-header"><div><strong>BodeSmart</strong><span> Gestión de bodega</span></div><div>{user && <span>{user.name} · {owner ? "Dueño" : user.role === "EMPLOYEE" ? "Empleado" : user.role}</span>}{user && <button type="button" onClick={logout}>Salir de cuenta</button>}<button type="button" onClick={onExit}>Volver a compras</button></div></header>
    <main className="ops-main">
      {loading && <p>Comprobando sesión…</p>}
      {!loading && !user && <ActionForm title="Ingresar a la bodega" onSubmit={login} button="Ingresar"><Field label="Correo" name="email" type="email" /><Field label="Contraseña" name="password" type="password" /></ActionForm>}
      {!loading && user && !staff && <p>Esta sección es para dueños y empleados. Usa «Comprar en bodegas» para ver el catálogo de cliente.</p>}
      {message && <p className="ops-message" role="status">{message}</p>}
      {staff && <>
        <section className="ops-intro"><h1>Inventario de tu bodega</h1><p>Los saldos y movimientos provienen de PostgreSQL. La venta presencial descuenta primero los lotes aptos más próximos a cerrar.</p></section>
        {owner && <section className="ops-card"><h2>Personal de la bodega</h2><form className="ops-form-grid" onSubmit={(event) => { event.preventDefault(); run(() => apiPost("/store/staff", values(event)), "Empleado creado."); event.currentTarget.reset(); }}><Field label="Nombre" name="name" /><Field label="Correo" name="email" type="email" /><Field label="Contraseña inicial" name="password" type="password" minLength="8" /><button disabled={busy}>Agregar empleado</button></form><div className="ops-table-wrap"><table><thead><tr><th>Nombre</th><th>Correo</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{staffMembers.map((member) => <tr key={member.id}><td>{member.name}</td><td>{member.email}</td><td>{member.active ? "Activo" : "Inactivo"}</td><td><button type="button" disabled={busy} onClick={() => run(() => apiPatch(`/store/staff/${member.id}`, { active: !member.active }), "Estado del empleado actualizado.")}>{member.active ? "Desactivar" : "Reactivar"}</button></td></tr>)}</tbody></table></div></section>}
        <section className="ops-card"><h2>Consulta tu inventario</h2><p>Pregunta por existencias, lotes o vencimientos de tu bodega. El asistente solo puede consultar datos.</p><form onSubmit={async (event) => { event.preventDefault(); setChatBusy(true); try { setChatReply((await apiPost("/chat", { question: values(event).question })).answer); } catch (error) { setChatReply(error.message); } finally { setChatBusy(false); } }}><label className="ops-field">Pregunta<input name="question" maxLength="1000" placeholder="¿Qué lotes vencen pronto?" required /></label><button disabled={chatBusy}>{chatBusy ? "Consultando…" : "Consultar"}</button></form>{chatReply && <p role="status">{chatReply}</p>}</section>
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
        {owner && <section className="ops-card"><h2>Recomendaciones de precio</h2><p>Modo actual: <strong>{pricingPolicy?.mode === "AUTOMATIC" ? "Automático de demo" : "Revisión manual"}</strong>. El historial simulado se indica en cada recomendación; las ventas reales no se inventan.</p>{pricingPolicy?.mode === "AUTOMATIC" ? <button type="button" disabled={busy} onClick={() => run(() => apiPost("/store/pricing-policy", { mode: "REVIEW" }), "Modo de revisión manual activado.")}>Desactivar automático</button> : <><label className="ops-field"><input type="checkbox" checked={autoConsent} onChange={(event) => setAutoConsent(event.target.checked)} /> Autorizo que esta bodega demo baje precios automáticamente dentro de los límites usando historial simulado.</label><button type="button" disabled={busy || !autoConsent} onClick={() => run(() => apiPost("/store/pricing-policy", { mode: "AUTOMATIC", confirm_demo_synthetic: true }), "Modo automático de demo activado. El análisis diario aplicará propuestas seguras.")}>Activar automático</button></>}<p>También puedes analizar ofertas y decidir cada propuesta manualmente. Sin historial suficiente, se conserva el precio.</p><button type="button" disabled={busy} onClick={() => run(() => apiPost("/store/analysis", {}), "Análisis actualizado.")}>Analizar ofertas</button> <button type="button" disabled={busy} onClick={() => run(() => apiPost("/store/analysis", { demo_history: true }), "Análisis de demo actualizado; el historial es simulado.")}>Analizar con historial simulado (solo demo)</button><div className="ops-offers">{recommendations.map((item) => <article key={item.id} className="ops-offer"><div><strong>{item.product_name}</strong><small>Lote {item.lot_code} · {item.state === "PENDING" ? "Pendiente" : item.state === "APPLIED" ? "Aplicada" : item.state === "REJECTED" ? "Rechazada" : item.state === "STALE" ? "Desactualizada" : "Mantener"}</small><p>Actual: <b>S/ {item.current_price}</b> · sugerido: <b>S/ {item.proposed_price}</b></p>{item.history_source === "synthetic_demo_history" && <small>Historial de ventas simulado para esta demo · </small>}<small>{recommendationReasons[item.reason] || item.reason || "Sin cambio"}</small>{item.current_coverage != null && <small> · Cobertura estimada: {Math.round(item.current_coverage * 100)} % → {Math.round(item.proposed_coverage * 100)} %</small>}</div>{item.state === "PENDING" && <div className="ops-offer-actions"><button disabled={busy} type="button" onClick={() => run(() => apiPost(`/store/recommendations/${item.id}/decision`, { decision: "APPROVE" }), "Decisión registrada; revisa el estado actualizado.")}>Aprobar precio</button><button disabled={busy} type="button" onClick={() => run(() => apiPost(`/store/recommendations/${item.id}/decision`, { decision: "REJECT" }), "Recomendación rechazada.")}>Rechazar</button></div>}</article>)}</div>{recommendations.length === 0 && <p>Aún no hay análisis de precios.</p>}</section>}
        <section className="ops-card"><h2>Movimientos recientes</h2><div className="ops-table-wrap"><table><thead><tr><th>Fecha</th><th>Tipo</th><th>Lotes</th><th>Total</th><th>Motivo</th></tr></thead><tbody>{movements.map((item) => <tr key={item.id}><td>{item.confirmed_at?.slice(0, 16)}</td><td>{item.kind}</td><td>{item.lines.map((line) => `${line.delta}`).join(", ")}</td><td>S/ {item.total}</td><td>{item.reason || "—"}</td></tr>)}</tbody></table>{movements.length === 0 && <p>Sin movimientos.</p>}</div></section>
      </>}
    </main>
  </div>;
}
