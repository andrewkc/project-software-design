import React, { useEffect, useId, useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { FIELDS, OPERATORS, ROLE_LABELS, applyQuery, buildProfile, deleteBlockReason, fieldOf, operatorOf, validateProfile } from "../../lib/adminProfiles";
import "./admin.css";

// La vista principal son los jefes de bodega: son los clientes directos de BodeSmart.
const VIEWS = [
  { id: "jefe", label: "Jefes de bodega" },
  { id: "empleado", label: "Empleados" },
  { id: "cliente", label: "Clientes" },
  { id: "admin", label: "Administradores" },
  { id: "all", label: "Todos" },
];
const STORE_ROLES = ["jefe", "empleado", "cliente"];
const dateFormat = new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "short", year: "numeric" });
const formatDate = (value) => (value ? dateFormat.format(new Date(value)) : "—");

function FilterValue({ field, filter, index, onChange }) {
  const label = `Valor del filtro ${index + 1}`;
  if (operatorOf(field.type, filter.operator)?.unary) return <span />;
  if (field.type === "select") {
    return <select aria-label={label} value={filter.value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Elegir…</option>
      {Object.entries(ROLE_LABELS).map(([id, text]) => <option key={id} value={id}>{text}</option>)}
    </select>;
  }
  if (field.type === "boolean") {
    return <select aria-label={label} value={filter.value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Elegir…</option><option value="true">Activo</option><option value="false">Inactivo</option>
    </select>;
  }
  return <input aria-label={label} type={field.type === "date" ? "date" : "text"} placeholder="Valor" value={filter.value} onChange={(event) => onChange(event.target.value)} />;
}

function QueryRules({ kind, rules, setRules }) {
  const update = (index, changes) => setRules(rules.map((rule, position) => (position === index ? { ...rule, ...changes } : rule)));
  const remove = (index) => setRules(rules.filter((_, position) => position !== index));
  const filter = kind === "filtro";
  return <div className="adm-rules">{rules.map((rule, index) => {
    const field = fieldOf(rule.field);
    return <div className="adm-rule" key={index}>
      <span className="adm-rule-join">{index === 0 ? (filter ? "Donde" : "Ordenar por") : (filter ? "y" : "luego")}</span>
      <select aria-label={`Campo del ${kind} ${index + 1}`} value={rule.field} onChange={(event) => update(index, filter ? { field: event.target.value, operator: OPERATORS[fieldOf(event.target.value).type][0].id, value: "" } : { field: event.target.value })}>
        {FIELDS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
      </select>
      {filter
        ? <select aria-label={`Operador del filtro ${index + 1}`} value={rule.operator} onChange={(event) => update(index, { operator: event.target.value })}>
          {OPERATORS[field.type].map((operator) => <option key={operator.id} value={operator.id}>{operator.label}</option>)}
        </select>
        : <select aria-label={`Dirección del orden ${index + 1}`} value={rule.direction} onChange={(event) => update(index, { direction: event.target.value })}>
          <option value="asc">Ascendente</option><option value="desc">Descendente</option>
        </select>}
      {filter ? <FilterValue field={field} filter={rule} index={index} onChange={(value) => update(index, { value })} /> : <span />}
      <button type="button" className="adm-icon-button" aria-label={`Quitar ${kind} ${index + 1}`} onClick={() => remove(index)}><Icon name="close" size={15} /></button>
    </div>;
  })}</div>;
}

// Etiqueta asociada por id: así el lector de pantalla anuncia solo "Rol", no "Rol Jefe de bodega".
function Field({ id, label, children }) {
  return <div className="adm-field"><label htmlFor={id}>{label}</label>{React.cloneElement(children, { id })}</div>;
}

function ProfilePanel({ profile, profiles, stores, history, selfId, onClose, onSave, onDelete }) {
  const ids = useId();
  const creating = !profile.id;
  const isSelf = profile.id === selfId;
  const [draft, setDraft] = useState({ nombres: profile.nombres || "", apellidos: profile.apellidos || "", email: profile.email || "", role: profile.role, store: profile.store || "", password: "", activo: profile.activo !== false });
  const [error, setError] = useState("");
  const [blockedByHistory, setBlockedByHistory] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const set = (key) => (event) => setDraft((current) => ({ ...current, [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value }));

  useEffect(() => {
    const onKey = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function submit(event) {
    event.preventDefault();
    const problem = validateProfile(draft, profiles, { editingId: profile.id || null, selfId });
    if (problem) return setError(problem);
    onSave(buildProfile(draft, creating ? null : profile));
    return undefined;
  }

  function remove() {
    const reason = deleteBlockReason(profile, history, selfId);
    setConfirming(false);
    if (!reason) return onDelete(profile);
    setError(reason);
    setBlockedByHistory(true);
    return undefined;
  }

  const title = creating ? "Nuevo perfil" : "Editar perfil";
  return <div className="adm-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="adm-panel" role="dialog" aria-modal="true" aria-label={title}>
      <header className="adm-panel-head">
        <span className="adm-kicker">{creating ? "CREAR CUENTA" : ROLE_LABELS[profile.role].toUpperCase()}</span>
        <h2>{creating ? title : profile.name}</h2>
        <button type="button" className="adm-icon-button adm-panel-close" aria-label="Cerrar" onClick={onClose}><Icon name="close" size={17} /></button>
      </header>
      <form className="adm-form" onSubmit={submit} noValidate>
        <div className="adm-form-pair">
          <Field id={`${ids}-nombres`} label="Nombres"><input value={draft.nombres} onChange={set("nombres")} maxLength={60} autoComplete="off" /></Field>
          <Field id={`${ids}-apellidos`} label="Apellidos"><input value={draft.apellidos} onChange={set("apellidos")} maxLength={60} autoComplete="off" /></Field>
        </div>
        <Field id={`${ids}-email`} label="Correo"><input type="email" value={draft.email} onChange={set("email")} autoComplete="off" /></Field>
        <Field id={`${ids}-role`} label="Rol"><select value={draft.role} onChange={set("role")} disabled={isSelf}>
          {Object.entries(ROLE_LABELS).map(([id, text]) => <option key={id} value={id}>{text}</option>)}
        </select></Field>
        {STORE_ROLES.includes(draft.role) && <Field id={`${ids}-store`} label="Bodega"><input list={`${ids}-stores`} value={draft.store} onChange={set("store")} placeholder={draft.role === "jefe" ? "Nombre de la bodega" : "Bodega a la que pertenece"} autoComplete="off" /></Field>}
        <datalist id={`${ids}-stores`}>{stores.map((store) => <option key={store} value={store} />)}</datalist>
        <Field id={`${ids}-password`} label={creating ? "Contraseña" : <>Nueva contraseña <small>(opcional)</small></>}><input type="password" value={draft.password} onChange={set("password")} autoComplete="new-password" placeholder="Mínimo 8 caracteres" /></Field>
        {!creating && <label className="adm-check"><input type="checkbox" checked={draft.activo} onChange={set("activo")} disabled={isSelf} />Cuenta activa</label>}
        {isSelf && <p className="adm-hint">Es tu propia cuenta: no puedes cambiar tu rol, desactivarla ni eliminarla.</p>}
        {error && <div className="adm-error" role="alert">{error}</div>}
        {blockedByHistory && profile.activo !== false && <button type="button" className="adm-secondary" onClick={() => onSave(buildProfile({ ...draft, nombres: profile.nombres, apellidos: profile.apellidos, email: profile.email, role: profile.role, store: profile.store, password: "", activo: false }, profile))}>Desactivar en su lugar</button>}
        <div className="adm-form-actions">
          <button type="submit" className="button button-primary">{creating ? "Crear perfil" : "Guardar cambios"}</button>
          <button type="button" className="adm-secondary" onClick={onClose}>Cancelar</button>
        </div>
      </form>
      {!creating && !isSelf && <footer className="adm-danger-zone">
        {confirming
          ? <><p>¿Eliminar definitivamente a {profile.name}? Si tiene historial, solo podrás desactivarla.</p>
            <div className="adm-form-actions"><button type="button" className="adm-danger" onClick={remove}>Sí, eliminar</button><button type="button" className="adm-secondary" onClick={() => setConfirming(false)}>No</button></div></>
          : <button type="button" className="adm-danger-link" aria-label="Eliminar perfil" onClick={() => setConfirming(true)}><Icon name="trash" size={15} />Eliminar</button>}
      </footer>}
    </aside>
  </div>;
}

export function AdminPage({ user, profiles, history, onSave, onDelete }) {
  const [view, setView] = useState("jefe");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState([]);
  const [sorts, setSorts] = useState([]);
  const [editing, setEditing] = useState(null);
  const counts = useMemo(() => Object.fromEntries(VIEWS.map((item) => [item.id, item.id === "all" ? profiles.length : profiles.filter((profile) => profile.role === item.id).length])), [profiles]);
  const rows = useMemo(() => applyQuery(profiles, { role: view === "all" ? null : view, search, filters, sorts }), [profiles, view, search, filters, sorts]);
  const stores = useMemo(() => [...new Set(profiles.map((profile) => profile.store).filter(Boolean))].sort((a, b) => a.localeCompare(b, "es")), [profiles]);
  const activeStores = new Set(profiles.filter((profile) => profile.role === "jefe" && profile.activo !== false).map((profile) => profile.store)).size;

  function toggleHeaderSort(key) {
    const current = sorts.length === 1 && sorts[0].field === key ? sorts[0].direction : null;
    setSorts(current === "asc" ? [{ field: key, direction: "desc" }] : current === "desc" ? [] : [{ field: key, direction: "asc" }]);
  }

  function save(profile) {
    onSave(profile);
    setEditing(null);
  }

  function remove(profile) {
    onDelete(profile);
    setEditing(null);
  }

  return <div className="page-content inner-page adm-page">
    <PageDate />
    <section className="welcome-row"><div><h1>Perfiles de BodeSmart</h1><p className="welcome-subtitle">Gestiona las cuentas de jefes de bodega, empleados y clientes. No ves los datos internos de cada bodega.</p></div></section>
    <div className="adm-stats">
      <div><strong>{activeStores}</strong><span>Bodegas con jefe activo</span></div>
      <div><strong>{counts.empleado}</strong><span>Empleados</span></div>
      <div><strong>{counts.cliente}</strong><span>Clientes</span></div>
      <div><strong>{profiles.filter((profile) => profile.activo === false).length}</strong><span>Cuentas inactivas</span></div>
    </div>
    <section className="content-card adm-database">
      <div className="adm-tabs" role="tablist" aria-label="Vistas de perfiles">{VIEWS.map((item) => <button key={item.id} type="button" role="tab" aria-selected={view === item.id} className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}>{item.label}<span className="adm-count">{counts[item.id]}</span></button>)}</div>
      <div className="adm-toolbar">
        <label className="search-field adm-search"><Icon name="search" size={17} /><input type="search" aria-label="Buscar perfiles" placeholder="Buscar por nombre, correo o bodega" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <div className="adm-toolbar-actions">
          <button type="button" className={filters.length ? "active" : ""} onClick={() => setFilters([...filters, { field: "name", operator: "contains", value: "" }])}><Icon name="filter" size={16} />Filtro{filters.length ? ` · ${filters.length}` : ""}</button>
          <button type="button" className={sorts.length ? "active" : ""} onClick={() => setSorts([...sorts, { field: "name", direction: "asc" }])}><Icon name="options" size={16} />Ordenar{sorts.length ? ` · ${sorts.length}` : ""}</button>
          <button type="button" className="button button-primary adm-new" onClick={() => setEditing({ role: view === "all" ? "jefe" : view, activo: true })}><Icon name="plus" size={16} />Nuevo perfil</button>
        </div>
      </div>
      {filters.length > 0 && <QueryRules kind="filtro" rules={filters} setRules={setFilters} />}
      {sorts.length > 0 && <QueryRules kind="orden" rules={sorts} setRules={setSorts} />}
      <div className="adm-table-wrap">
        <table>
          <thead><tr>{FIELDS.map((field) => {
            const sort = sorts.length === 1 && sorts[0].field === field.key ? sorts[0].direction : null;
            return <th key={field.key} aria-sort={sort === "asc" ? "ascending" : sort === "desc" ? "descending" : undefined}><button type="button" onClick={() => toggleHeaderSort(field.key)}>{field.label}{sort === "asc" ? " ↑" : sort === "desc" ? " ↓" : ""}</button></th>;
          })}</tr></thead>
          <tbody>{rows.map((profile) => <tr key={profile.id} onClick={() => setEditing(profile)}>
            <td><span className="adm-name-cell"><button type="button" className="adm-row-open" data-initial={profile.name.charAt(0).toUpperCase()} onClick={(event) => { event.stopPropagation(); setEditing(profile); }}>{profile.name}</button>{profile.id === user?.id && <span className="adm-you">tú</span>}</span></td>
            <td>{profile.email}</td>
            <td><span className={`adm-pill adm-role-${profile.role}`}>{ROLE_LABELS[profile.role]}</span></td>
            <td>{profile.store || "—"}</td>
            <td><span className={`adm-status ${profile.activo !== false ? "on" : "off"}`}>{profile.activo !== false ? "Activo" : "Inactivo"}</span></td>
            <td>{formatDate(profile.creadoEn)}</td>
          </tr>)}</tbody>
        </table>
        {rows.length === 0 && <p className="adm-empty">Ningún perfil coincide con esta consulta.</p>}
      </div>
      <p className="adm-footer">Mostrando {rows.length} de {counts[view]} perfiles</p>
    </section>
    {editing && <ProfilePanel key={editing.id || "new"} profile={editing} profiles={profiles} stores={stores} history={history} selfId={user?.id} onClose={() => setEditing(null)} onSave={save} onDelete={remove} />}
  </div>;
}
