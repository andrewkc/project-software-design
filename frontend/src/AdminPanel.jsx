import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "./api";
import { applyQuery, FIELDS, OPERATORS, ROLE_LABELS, fieldOf, operatorOf } from "./adminTable";
import "./admin-panel.css";

// The main view is the list of warehouse owners: they are BodeSmart's direct customers.
const VIEWS = [
  { id: "OWNER", label: "Jefes de bodega" },
  { id: "EMPLOYEE", label: "Empleados" },
  { id: "CUSTOMER", label: "Clientes" },
  { id: "ADMIN", label: "Administradores" },
  { id: "ALL", label: "Todos" },
];
const STAFF_ROLES = ["OWNER", "EMPLOYEE"];
const dateFormat = new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "short", year: "numeric" });
const formatDate = (value) => (value ? dateFormat.format(new Date(value)) : "—");
const values = (event) => Object.fromEntries(new FormData(event.currentTarget));

function FilterValue({ field, filter, index, onChange }) {
  const label = `Valor del filtro ${index + 1}`;
  if (operatorOf(field.type, filter.operator)?.unary) return null;
  if (field.type === "select") {
    return <select className="adm-rule-value" aria-label={label} value={filter.value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Elegir…</option>
      {Object.entries(ROLE_LABELS).map(([id, text]) => <option key={id} value={id}>{text}</option>)}
    </select>;
  }
  if (field.type === "boolean") {
    return <select className="adm-rule-value" aria-label={label} value={filter.value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Elegir…</option><option value="true">Activo</option><option value="false">Inactivo</option>
    </select>;
  }
  return <input className="adm-rule-value" aria-label={label} type={field.type === "date" ? "date" : "text"} value={filter.value} placeholder="Valor"
    onChange={(event) => onChange(event.target.value)} />;
}

function FilterRules({ filters, setFilters }) {
  const update = (index, changes) => setFilters(filters.map((item, position) => (position === index ? { ...item, ...changes } : item)));
  return <div className="adm-rules">
    {filters.map((filter, index) => {
      const field = fieldOf(filter.field);
      return <div className="adm-rule" key={index}>
        <span className="adm-rule-join">{index === 0 ? "Donde" : "y"}</span>
        <select aria-label={`Campo del filtro ${index + 1}`} value={filter.field}
          onChange={(event) => update(index, { field: event.target.value, operator: OPERATORS[fieldOf(event.target.value).type][0].id, value: "" })}>
          {FIELDS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
        <select aria-label={`Operador del filtro ${index + 1}`} value={filter.operator} onChange={(event) => update(index, { operator: event.target.value })}>
          {OPERATORS[field.type].map((operator) => <option key={operator.id} value={operator.id}>{operator.label}</option>)}
        </select>
        <FilterValue field={field} filter={filter} index={index} onChange={(value) => update(index, { value })} />
        <button type="button" className="adm-icon-button" aria-label={`Quitar filtro ${index + 1}`}
          onClick={() => setFilters(filters.filter((_, position) => position !== index))}>×</button>
      </div>;
    })}
  </div>;
}

function SortRules({ sorts, setSorts }) {
  const update = (index, changes) => setSorts(sorts.map((item, position) => (position === index ? { ...item, ...changes } : item)));
  return <div className="adm-rules">
    {sorts.map((sort, index) => <div className="adm-rule" key={index}>
      <span className="adm-rule-join">{index === 0 ? "Ordenar por" : "luego"}</span>
      <select aria-label={`Campo del orden ${index + 1}`} value={sort.field} onChange={(event) => update(index, { field: event.target.value })}>
        {FIELDS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
      </select>
      <select aria-label={`Dirección del orden ${index + 1}`} value={sort.direction} onChange={(event) => update(index, { direction: event.target.value })}>
        <option value="asc">Ascendente</option><option value="desc">Descendente</option>
      </select>
      <button type="button" className="adm-icon-button" aria-label={`Quitar orden ${index + 1}`}
        onClick={() => setSorts(sorts.filter((_, position) => position !== index))}>×</button>
    </div>)}
  </div>;
}

function ProfilePanel({ profile, stores, profiles, isSelf, onClose, onSave, onDelete, onDeactivate }) {
  const creating = !profile.id;
  // Stores whose single active owner is someone else; picking one for a new owner would be rejected.
  const ownedStores = new Set(profiles.filter((item) => item.role === "OWNER" && item.is_active && item.id !== profile.id)
    .map((item) => item.store_id));
  const defaultStore = profile.store_id || (stores.find((store) => store.active && !ownedStores.has(store.id)) || stores[0])?.id;
  const [role, setRole] = useState(profile.role);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    const onKey = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function attempt(action) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (failure) {
      setError(failure);
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    const data = values(event);
    const payload = { name: data.name, email: data.email };
    if (!isSelf) payload.role = role;
    if (STAFF_ROLES.includes(role)) payload.store_id = data.store_id;
    if (creating) payload.password = data.password;
    else {
      if (!isSelf) payload.is_active = data.is_active === "on";
      if (data.password) payload.password = data.password;
    }
    attempt(() => onSave(payload));
  }

  const title = creating ? "Nuevo perfil" : "Editar perfil";
  return <div className="adm-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="adm-panel" role="dialog" aria-modal="true" aria-label={title}>
      <header className="adm-panel-head">
        <span className="adm-kicker">{creating ? "CREAR CUENTA" : ROLE_LABELS[profile.role]?.toUpperCase()}</span>
        <h2>{creating ? title : profile.name}</h2>
        <button type="button" className="adm-icon-button adm-panel-close" aria-label="Cerrar" onClick={onClose}>×</button>
      </header>
      <form className="adm-form" onSubmit={submit}>
        <label>Nombre<input name="name" defaultValue={profile.name} maxLength={120} required /></label>
        <label>Correo<input name="email" type="email" defaultValue={profile.email} required /></label>
        <label>Rol<select name="role" value={role} disabled={isSelf} onChange={(event) => setRole(event.target.value)}>
          {Object.entries(ROLE_LABELS).map(([id, text]) => <option key={id} value={id}>{text}</option>)}
        </select></label>
        {STAFF_ROLES.includes(role) && <label>Bodega<select name="store_id" defaultValue={defaultStore} required>
          {stores.map((store) => <option key={store.id} value={store.id}>{store.name}{store.active ? "" : " (inactiva)"}
            {role === "OWNER" && ownedStores.has(store.id) ? " (ya tiene jefe)" : ""}</option>)}
        </select></label>}
        {creating
          ? <label>Contraseña<input name="password" type="password" minLength={8} autoComplete="new-password" required /></label>
          : <label><span>Nueva contraseña <small>(opcional)</small></span><input name="password" type="password" minLength={8} autoComplete="new-password" /></label>}
        {!creating && <label className="adm-check"><input name="is_active" type="checkbox" defaultChecked={profile.is_active} disabled={isSelf} /> Cuenta activa</label>}
        {isSelf && <p className="adm-hint">Es tu propia cuenta: no puedes cambiar tu rol, desactivarla ni eliminarla.</p>}
        {error && <div className="adm-error" role="alert">
          <p>{error.message}</p>
          {error.code === "HAS_HISTORY" && profile.is_active && <button type="button" disabled={busy} onClick={() => attempt(onDeactivate)}>Desactivar en su lugar</button>}
        </div>}
        <div className="adm-form-actions">
          <button type="submit" className="adm-primary" disabled={busy}>{creating ? "Crear perfil" : "Guardar cambios"}</button>
          <button type="button" onClick={onClose}>Cancelar</button>
        </div>
      </form>
      {!creating && !isSelf && <footer className="adm-danger-zone">
        {confirming
          ? <><p>¿Eliminar definitivamente a {profile.name}? Si tiene historial, solo podrás desactivarla.</p>
            <div className="adm-form-actions"><button type="button" className="adm-danger" disabled={busy} onClick={() => attempt(onDelete)}>Sí, eliminar</button><button type="button" onClick={() => setConfirming(false)}>No</button></div></>
          : <button type="button" className="adm-danger-link" onClick={() => setConfirming(true)}>Eliminar</button>}
      </footer>}
    </aside>
  </div>;
}

export default function AdminPanel({ onExit }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profiles, setProfiles] = useState(null);
  const [stores, setStores] = useState([]);
  const [view, setView] = useState("OWNER");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState([]);
  const [sorts, setSorts] = useState([]);
  const [editing, setEditing] = useState(null);
  const [message, setMessage] = useState("");

  const admin = user?.role === "ADMIN";

  const reload = useCallback(async () => {
    const [nextProfiles, nextStores] = await Promise.all([apiGet("/admin/users"), apiGet("/admin/stores")]);
    setProfiles(nextProfiles);
    setStores(nextStores);
  }, []);

  useEffect(() => {
    apiGet("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (admin) reload().catch((error) => setMessage(error.message));
  }, [admin, reload]);

  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(() => setMessage(""), 4000);
    return () => window.clearTimeout(timer);
  }, [message]);

  const loaded = profiles ?? [];
  const counts = useMemo(() => Object.fromEntries(VIEWS.map((item) => [item.id,
    item.id === "ALL" ? loaded.length : loaded.filter((profile) => profile.role === item.id).length])), [loaded]);
  const rows = useMemo(() => applyQuery(loaded, { role: view === "ALL" ? null : view, search, filters, sorts }),
    [loaded, view, search, filters, sorts]);

  async function login(event) {
    event.preventDefault();
    try {
      setUser(await apiPost("/auth/login", values(event)));
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function logout() {
    try { await apiPost("/auth/logout"); } finally { setUser(null); setProfiles(null); setStores([]); setEditing(null); }
  }

  function toggleHeaderSort(key) {
    const current = sorts.length === 1 && sorts[0].field === key ? sorts[0].direction : null;
    setSorts(current === "asc" ? [{ field: key, direction: "desc" }] : current === "desc" ? [] : [{ field: key, direction: "asc" }]);
  }

  async function finish(action, text) {
    await action();
    setEditing(null);
    setMessage(text);
    await reload();
  }

  const save = (payload) => finish(() => (editing.id ? apiPatch(`/admin/users/${editing.id}`, payload) : apiPost("/admin/users", payload)),
    editing.id ? "Perfil actualizado." : "Perfil creado.");
  const remove = () => finish(() => apiDelete(`/admin/users/${editing.id}`), "Perfil eliminado.");
  const deactivate = () => finish(() => apiPatch(`/admin/users/${editing.id}`, { is_active: false }), "Perfil desactivado; su historial se conserva.");
  const closePanel = useCallback(() => setEditing(null), []);

  return <div className="adm-shell">
    <header className="adm-header">
      <div className="adm-brand"><strong>Bode<span>Smart</span></strong><span>Administración</span></div>
      <div className="adm-header-actions">
        {user && <span className="adm-who">{user.name} · {admin ? "Administrador" : ROLE_LABELS[user.role] || user.role}</span>}
        {user && <button type="button" onClick={logout}>Salir de cuenta</button>}
        <button type="button" onClick={onExit}>Volver al inicio</button>
      </div>
    </header>
    <main className="adm-main">
      {loading && <p>Comprobando sesión…</p>}
      {!loading && !user && <form className="adm-login" onSubmit={login}>
        <h1>Ingresar como administrador</h1>
        <label>Correo<input name="email" type="email" required /></label>
        <label>Contraseña<input name="password" type="password" required /></label>
        <button type="submit" className="adm-primary">Ingresar</button>
      </form>}
      {!loading && user && !admin && <p className="adm-notice">Esta sección es solo para administradores de BodeSmart.</p>}
      {admin && <>
        <section className="adm-intro">
          <h1>Perfiles de la plataforma</h1>
          <p>Gestiona las cuentas de jefes de bodega, empleados y clientes. Como administrador no ves costos ni ventas de las bodegas.</p>
        </section>
        <section className="adm-database">
          <div className="adm-tabs" role="tablist" aria-label="Vistas de perfiles">
            {VIEWS.map((item) => <button key={item.id} type="button" role="tab" aria-selected={view === item.id}
              className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}>
              {item.label} <span className="adm-count">{counts[item.id]}</span>
            </button>)}
          </div>
          <div className="adm-toolbar">
            <input className="adm-search" type="search" aria-label="Buscar perfiles" placeholder="Buscar por nombre, correo o bodega"
              value={search} onChange={(event) => setSearch(event.target.value)} />
            <div className="adm-toolbar-actions">
              <button type="button" className={filters.length ? "active" : ""}
                onClick={() => setFilters([...filters, { field: "name", operator: "contains", value: "" }])}>
                Filtro{filters.length ? ` · ${filters.length}` : ""}</button>
              <button type="button" className={sorts.length ? "active" : ""}
                onClick={() => setSorts([...sorts, { field: "name", direction: "asc" }])}>
                Ordenar{sorts.length ? ` · ${sorts.length}` : ""}</button>
              <button type="button" className="adm-primary"
                onClick={() => setEditing({ name: "", email: "", role: view === "ALL" ? "OWNER" : view, store_id: null, is_active: true })}>
                + Nuevo perfil</button>
            </div>
          </div>
          {filters.length > 0 && <FilterRules filters={filters} setFilters={setFilters} />}
          {sorts.length > 0 && <SortRules sorts={sorts} setSorts={setSorts} />}
          {profiles === null ? <p className="adm-empty">Cargando perfiles…</p> : <div className="adm-table-wrap">
            <table>
              <thead><tr>{FIELDS.map((field) => {
                const sort = sorts.length === 1 && sorts[0].field === field.key ? sorts[0].direction : null;
                return <th key={field.key} aria-sort={sort === "asc" ? "ascending" : sort === "desc" ? "descending" : undefined}>
                  <button type="button" onClick={() => toggleHeaderSort(field.key)}>{field.label}{sort === "asc" ? " ↑" : sort === "desc" ? " ↓" : ""}</button>
                </th>;
              })}</tr></thead>
              <tbody>{rows.map((profile) => <tr key={profile.id} onClick={() => setEditing(profile)}>
                <td><div className="adm-name-cell">
                  <button type="button" className="adm-row-open" data-initial={profile.name.charAt(0).toUpperCase()}
                    onClick={(event) => { event.stopPropagation(); setEditing(profile); }}>{profile.name}</button>
                  {profile.id === user.id && <span className="adm-you">tú</span>}
                </div></td>
                <td>{profile.email}</td>
                <td><span className={`adm-pill adm-role-${profile.role.toLowerCase()}`}>{ROLE_LABELS[profile.role]}</span></td>
                <td>{profile.store_name || "—"}</td>
                <td><span className={`adm-status ${profile.is_active ? "on" : "off"}`}>{profile.is_active ? "Activo" : "Inactivo"}</span></td>
                <td>{formatDate(profile.last_login)}</td>
                <td>{formatDate(profile.created_at)}</td>
              </tr>)}</tbody>
            </table>
            {rows.length === 0 && <p className="adm-empty">Ningún perfil coincide con esta consulta.</p>}
          </div>}
          <p className="adm-footer">Mostrando {rows.length} de {counts[view]} perfiles</p>
        </section>
      </>}
      {message && <p className="adm-toast" role="status">{message}</p>}
    </main>
    {editing && <ProfilePanel key={editing.id || "new"} profile={editing} stores={stores} profiles={loaded} isSelf={editing.id === user?.id}
      onClose={closePanel} onSave={save} onDelete={remove} onDeactivate={deactivate} />}
  </div>;
}
