import React, { useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { ROLE_LABELS, ROLE_OPTIONS, initials } from "../../lib/ui";

const emptyForm = {
  nombres: "", apellidos: "", correo: "", password: "", rol: "empleado", id_bodega: "", estado: "activo",
};

export function UsersPage({ user, users, stores, onCreate, onUpdate, onDeactivate, onNavigate }) {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("todos");
  const [sort, setSort] = useState({ key: "nombre", direction: 1 });
  const [drawer, setDrawer] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [confirmation, setConfirmation] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  const currentId = `${user?.rol}:${user?.id}`;
  const isOtherAdmin = (account) => account.rol === "admin" && account.id !== currentId;
  const isSelf = (account) => account.id === currentId;

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    return users
      .filter((account) => role === "todos" || account.rol === role)
      .filter((account) => !term || [account.nombre, account.correo, account.bodegaNombre].some((value) => String(value || "").toLowerCase().includes(term)))
      .slice()
      .sort((a, b) => {
        const left = String(a[sort.key] || "").toLowerCase();
        const right = String(b[sort.key] || "").toLowerCase();
        return left.localeCompare(right) * sort.direction;
      });
  }, [users, query, role, sort]);

  function openCreate() {
    setForm({ ...emptyForm, id_bodega: stores[0]?.id ?? "" });
    setDrawer({ mode: "create" });
    setError("");
  }

  function openEdit(account) {
    const bodega = stores.find((store) => store.nombre === account.bodegaNombre);
    setForm({
      nombres: account.nombres || "",
      apellidos: account.apellidos || "",
      correo: account.correo || "",
      password: "",
      rol: account.rol,
      id_bodega: bodega?.id ?? "",
      estado: account.activo ? "activo" : "inactivo",
    });
    setDrawer({ mode: "edit", account });
    setError("");
  }

  function changeField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function save(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    const payload = {
      nombres: form.nombres,
      apellidos: form.apellidos,
      correo: form.correo,
    };
    if (form.password) payload.password = form.password;
    if (drawer.mode === "create") {
      payload.rol = form.rol;
      if (form.rol === "jefe" || form.rol === "empleado") payload.id_bodega = form.id_bodega;
    } else {
      if (!isSelf(drawer.account)) payload.estado = form.estado;
      if (form.rol === "jefe" || form.rol === "empleado") payload.id_bodega = form.id_bodega;
    }
    try {
      if (drawer.mode === "create") await onCreate(payload);
      else await onUpdate(drawer.account.id, payload);
      setToast(drawer.mode === "create" ? "Cuenta creada correctamente." : "Cuenta actualizada correctamente.");
      setDrawer(null);
    } catch (err) {
      setError(err.message || "No se pudo guardar la cuenta");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDeactivate() {
    setSaving(true);
    setError("");
    try {
      await onDeactivate(confirmation.id);
      setToast("La cuenta se desactivó. Su historial se conserva.");
      setConfirmation(null);
    } catch (err) {
      setError(err.message || "No se pudo desactivar la cuenta");
    } finally {
      setSaving(false);
    }
  }

  function toggleSort(key) {
    setSort((current) => ({ key, direction: current.key === key ? -current.direction : 1 }));
  }

  return <div className="page-content inner-page">
    <PageDate onProfile={() => onNavigate("profile")} />
    <section className="welcome-row">
      <div>
        <h1>Cuentas</h1>
        <p className="welcome-subtitle">Administra accesos de <strong>admin, jefe, empleado y cliente</strong>. Nunca se muestran contraseñas.</p>
      </div>
      <button className="button button-primary add-top-button" type="button" onClick={openCreate}><Icon name="plus" size={16} />Nueva cuenta</button>
    </section>

    <section className="content-card">
      <div className="inventory-toolbar">
        <div><h2>Cuentas registradas</h2><span className="muted-count">{visible.length} de {users.length}</span></div>
        <label className="search-field"><Icon name="search" size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nombre, correo o bodega" /></label>
      </div>
      <div className="role-tabs">
        <button type="button" className={`role-tab ${role === "todos" ? "active" : ""}`} onClick={() => setRole("todos")}>Todos <span>{users.length}</span></button>
        {ROLE_OPTIONS.map((option) => (
          <button key={option.value} type="button" className={`role-tab ${role === option.value ? "active" : ""}`} onClick={() => setRole(option.value)}>
            {option.label} <span>{users.filter((account) => account.rol === option.value).length}</span>
          </button>
        ))}
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr>
            <th><button type="button" className="table-sort-button" onClick={() => toggleSort("nombre")}>Cuenta {sort.key === "nombre" ? (sort.direction > 0 ? "↑" : "↓") : ""}</button></th>
            <th><button type="button" className="table-sort-button" onClick={() => toggleSort("rol")}>Rol {sort.key === "rol" ? (sort.direction > 0 ? "↑" : "↓") : ""}</button></th>
            <th>Bodega</th>
            <th>Estado</th>
            <th style={{ textAlign: "right" }}>Acciones</th>
          </tr></thead>
          <tbody>
            {visible.map((account) => {
              const blocked = isOtherAdmin(account);
              return <tr key={account.id}>
                <td><div className="account-name"><span className="account-avatar">{initials(account.nombre)}</span><span><strong>{account.nombre}</strong><small>{account.correo}</small></span></div></td>
                <td><span className={`role-pill role-${account.rol}`}>{ROLE_LABELS[account.rol] || account.rol}</span></td>
                <td>{account.bodegaNombre || "—"}</td>
                <td><span className={`status-pill ${account.activo ? "status-active" : "status-inactive"}`}>{account.activo ? "Activo" : "Inactivo"}</span></td>
                <td><div className="row-actions" style={{ justifyContent: "flex-end" }}>
                  <button type="button" className="row-action" title={blocked ? "No puedes editar a otro admin" : "Editar"} disabled={blocked} onClick={() => openEdit(account)}><Icon name="edit" size={16} /></button>
                  <button type="button" className="row-action row-action-delete" title={blocked ? "No puedes desactivar a otro admin" : isSelf(account) ? "No puedes desactivar tu propia cuenta" : "Desactivar"} disabled={blocked || isSelf(account)} onClick={() => { setError(""); setConfirmation(account); }}><Icon name="trash" size={16} /></button>
                </div></td>
              </tr>;
            })}
          </tbody>
        </table>
        {visible.length === 0 && <div className="empty-state"><strong>Sin resultados</strong><p>Ajusta la búsqueda o el filtro de rol.</p></div>}
      </div>
    </section>

    {drawer && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDrawer(null); }}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={drawer.mode === "create" ? "Nueva cuenta" : "Editar cuenta"}>
        <div className="drawer-header">
          <div><h2>{drawer.mode === "create" ? "Nueva cuenta" : "Editar cuenta"}</h2><p>{drawer.mode === "create" ? "La contraseña se guarda cifrada en el backend." : drawer.account.correo}</p></div>
          <button type="button" className="icon-button" aria-label="Cerrar" onClick={() => setDrawer(null)}><Icon name="close" size={18} /></button>
        </div>
        {drawer.mode === "edit" && drawer.account.rol === "admin" && <p className="drawer-warning">Tu cuenta de administrador se puede editar, pero no desactivar. Otros administradores no son editables desde esta cuenta.</p>}
        <form className="admin-form" onSubmit={save}>
          <label className="admin-field"><span>Nombres</span><input value={form.nombres} onChange={(event) => changeField("nombres", event.target.value)} required /></label>
          <label className="admin-field"><span>Apellidos</span><input value={form.apellidos} onChange={(event) => changeField("apellidos", event.target.value)} required /></label>
          <label className="admin-field full"><span>Correo</span><input type="email" value={form.correo} onChange={(event) => changeField("correo", event.target.value)} required /></label>
          <label className="admin-field"><span>Contraseña {drawer.mode === "edit" && <span className="muted-count">(dejar vacía para mantener)</span>}</span><input type="password" minLength={drawer.mode === "create" ? 8 : undefined} value={form.password} onChange={(event) => changeField("password", event.target.value)} required={drawer.mode === "create"} /></label>
          {drawer.mode === "create" && <label className="admin-field"><span>Rol</span><select value={form.rol} onChange={(event) => changeField("rol", event.target.value)}>{ROLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>}
          {(form.rol === "jefe" || form.rol === "empleado") && <label className="admin-field full"><span>Bodega</span><select value={form.id_bodega} onChange={(event) => changeField("id_bodega", event.target.value)} required>
            <option value="">Selecciona una bodega</option>
            {stores.map((store) => <option key={store.id} value={store.id}>{store.nombre}</option>)}
          </select></label>}
          {drawer.mode === "edit" && !isSelf(drawer.account) && <label className="admin-field full"><span>Estado</span><select value={form.estado} onChange={(event) => changeField("estado", event.target.value)}><option value="activo">Activo</option><option value="inactivo">Inactivo</option></select></label>}
          {error && <p className="auth-error full" role="alert">{error}</p>}
          <div className="drawer-actions full">
            <button type="button" className="button button-secondary" onClick={() => setDrawer(null)}>Cancelar</button>
            <button type="submit" className="button button-primary" disabled={saving}>{saving ? "Guardando…" : "Guardar cuenta"}</button>
          </div>
        </form>
      </aside>
    </div>}

    {confirmation && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setConfirmation(null); }}>
      <div className="confirm-card" role="dialog" aria-modal="true">
        <h2>Desactivar cuenta</h2>
        <p>Se desactivará <strong>{confirmation.nombre}</strong>. La cuenta no podrá iniciar sesión, pero su historial se conserva.</p>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <div className="drawer-actions">
          <button type="button" className="button button-secondary" onClick={() => setConfirmation(null)}>Cancelar</button>
          <button type="button" className="button button-primary" disabled={saving} onClick={confirmDeactivate}>{saving ? "Desactivando…" : "Desactivar"}</button>
        </div>
      </div>
    </div>}

    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={16} /></span>{toast}<button type="button" className="row-action" aria-label="Cerrar aviso" onClick={() => setToast("")}><Icon name="close" size={14} /></button></div>}
  </div>;
}
