import React, { useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "./api";
import "./store-panel.css";

const values = (event) => Object.fromEntries(new FormData(event.currentTarget));

function Input({ label, name, type = "text", ...props }) {
  return <label className="ops-field">{label}<input name={name} type={type} required {...props} /></label>;
}

export default function AdminPanel({ user, onExit, onLogout }) {
  const [stores, setStores] = useState([]);
  const [users, setUsers] = useState([]);
  const [editingStore, setEditingStore] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [nextStores, nextUsers] = await Promise.all([apiGet("/admin/stores"), apiGet("/admin/users")]);
    setStores(nextStores);
    setUsers(nextUsers);
  }, []);

  useEffect(() => { refresh().catch((error) => setMessage(error.message)); }, [refresh]);

  async function run(action, success) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      await refresh();
      setMessage(success);
      return true;
    } catch (error) {
      setMessage(error.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function createStore(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = values(event);
    if (!data.opening_hours) delete data.opening_hours;
    if (await run(() => apiPost("/admin/stores", data), "Bodega creada.")) form.reset();
  }

  async function createUser(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = values(event);
    if (!data.store_id) delete data.store_id;
    if (await run(() => apiPost("/admin/users", data), "Cuenta creada.")) form.reset();
  }

  async function saveStore(event) {
    event.preventDefault();
    if (await run(() => apiPatch(`/admin/stores/${editingStore.id}`, values(event)), "Bodega actualizada.")) {
      setEditingStore(null);
    }
  }

  async function saveUser(event) {
    event.preventDefault();
    if (await run(() => apiPatch(`/admin/users/${editingUser.id}`, values(event)), "Cuenta actualizada.")) {
      setEditingUser(null);
    }
  }

  return <div className="ops-shell">
    <header className="ops-header">
      <div><strong>BodeSmart</strong><span> Administración</span></div>
      <div><span>{user.name}</span><button type="button" onClick={onLogout}>Salir de cuenta</button>
        <button type="button" onClick={onExit}>Volver a compras</button></div>
    </header>
    <main className="ops-main">
      <section className="ops-intro"><h1>Tiendas y cuentas</h1>
        <p>Los cambios conservan el historial. Una tienda con reservas activas y el último administrador están protegidos.</p>
      </section>
      {message && <p className="ops-message" role="status">{message}</p>}
      <section className="ops-grid">
        <form className="ops-card" onSubmit={createStore}>
          <h2>Nueva bodega</h2><div className="ops-form-grid">
            <Input label="Nombre" name="name" /><Input label="Dirección" name="address" />
            <label className="ops-field">Horario<input name="opening_hours" placeholder="08:00–20:00" /></label>
          </div><button disabled={busy}>Crear bodega</button>
        </form>
        <form className="ops-card" onSubmit={createUser}>
          <h2>Nueva cuenta</h2><div className="ops-form-grid">
            <Input label="Nombre" name="name" /><Input label="Correo" name="email" type="email" />
            <Input label="Contraseña inicial" name="password" type="password" minLength="8" />
            <label className="ops-field">Rol<select name="role">
              <option value="OWNER">Dueño</option><option value="EMPLOYEE">Empleado</option>
              <option value="CUSTOMER">Cliente</option><option value="ADMIN">Administrador</option>
            </select></label>
            <label className="ops-field">Bodega para dueño o empleado<select name="store_id">
              <option value="">Sin bodega</option>
              {stores.filter((store) => store.active).map((store) =>
                <option key={store.id} value={store.id}>{store.name}</option>)}
            </select></label>
          </div><button disabled={busy}>Crear cuenta</button>
        </form>
      </section>
      <section className="ops-card"><h2>Bodegas</h2><div className="ops-table-wrap"><table>
        <thead><tr><th>Nombre</th><th>Dirección</th><th>Horario</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>{stores.map((store) => <tr key={store.id}>
          <td>{store.name}</td><td>{store.address}</td><td>{store.opening_hours}</td>
          <td>{store.active ? "Activa" : "Inactiva"}</td>
          <td><button type="button" disabled={busy} onClick={() => setEditingStore(store)}>Editar</button>{" "}
            <button type="button" disabled={busy} onClick={() => run(
              () => apiPatch(`/admin/stores/${store.id}`, { active: !store.active }), "Bodega actualizada.")}>{store.active ? "Desactivar" : "Reactivar"}</button></td>
        </tr>)}</tbody>
      </table></div></section>
      {editingStore && <form className="ops-card" key={editingStore.id} onSubmit={saveStore}>
        <h2>Editar bodega</h2><div className="ops-form-grid">
          <Input label="Nombre" name="name" defaultValue={editingStore.name} />
          <Input label="Dirección" name="address" defaultValue={editingStore.address} />
          <Input label="Horario" name="opening_hours" defaultValue={editingStore.opening_hours} />
        </div><button disabled={busy}>Guardar cambios</button>{" "}
        <button type="button" onClick={() => setEditingStore(null)}>Cancelar</button>
      </form>}
      <section className="ops-card"><h2>Cuentas</h2><div className="ops-table-wrap"><table>
        <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Bodega</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>{users.map((account) => <tr key={account.id}>
          <td>{account.name}</td><td>{account.email}</td><td>{account.role}</td>
          <td>{stores.find((store) => store.id === account.store_id)?.name || "—"}</td>
          <td>{account.active ? "Activa" : "Inactiva"}</td>
          <td><button type="button" disabled={busy} onClick={() => setEditingUser(account)}>Editar</button>{" "}
            <button type="button" disabled={busy} onClick={() => run(
              () => apiPatch(`/admin/users/${account.id}`, { active: !account.active }), "Cuenta actualizada.")}>{account.active ? "Desactivar" : "Reactivar"}</button></td>
        </tr>)}</tbody>
      </table></div></section>
      {editingUser && <form className="ops-card" key={editingUser.id} onSubmit={saveUser}>
        <h2>Editar cuenta</h2><div className="ops-form-grid">
          <Input label="Nombre" name="name" defaultValue={editingUser.name} />
        </div><button disabled={busy}>Guardar cambios</button>{" "}
        <button type="button" onClick={() => setEditingUser(null)}>Cancelar</button>
      </form>}
    </main>
  </div>;
}
