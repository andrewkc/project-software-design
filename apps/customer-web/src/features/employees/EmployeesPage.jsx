import React, { useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { generatePassword } from "../../lib/accountSecurity";

export function EmployeesPage({ employees, movements, onCreateEmployee, onRevokeEmployee }) {
  const [password, setPassword] = useState(() => generatePassword());
  const [credentials, setCredentials] = useState(null);
  const [copied, setCopied] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showCredentialsPassword, setShowCredentialsPassword] = useState(false);
  const activeEmployees = employees.filter((employee) => employee.activo !== false);
  const revokedEmployees = employees.filter((employee) => employee.activo === false);

  function handleSubmit(event) {
    const data = new FormData(event.currentTarget);
    const nombres = String(data.get("nombres") || "").trim();
    const apellidos = String(data.get("apellidos") || "").trim();
    const name = `${nombres} ${apellidos}`.trim();
    const email = String(data.get("email") || "").trim().toLowerCase();
    if (!onCreateEmployee(event, password)) return;
    setCredentials({ name, email, password });
    setCopied(false);
    setShowPassword(false);
    setShowCredentialsPassword(false);
    setPassword(generatePassword());
  }

  async function copyCredentials() {
    if (!credentials) return;
    try {
      await navigator.clipboard.writeText(`Correo: ${credentials.email}\nContraseña: ${credentials.password}`);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row">
      <div><h1>Empleados</h1><p className="welcome-subtitle">Crea cuentas para tu equipo y controla el acceso a tu bodega.</p></div>
    </section>
    <section className="content-card employees-card">
      <h2>Nuevo empleado</h2>
      <form className="employee-form" onSubmit={handleSubmit}>
        <label className="auth-field"><span>Nombres</span><input className="employee-input" name="nombres" type="text" placeholder="Nombres del empleado" required /></label>
        <label className="auth-field"><span>Apellidos</span><input className="employee-input" name="apellidos" type="text" placeholder="Apellidos del empleado" required /></label>
        <label className="auth-field"><span>Correo electrónico</span><input className="employee-input" name="email" type="email" placeholder="empleado@correo.com" required /></label>
        <div className="password-generator">
          <span className="field-caption">Contraseña inicial</span>
          <div className="generated-password-row">
            <input className="employee-input generated-password" type={showPassword ? "text" : "password"} readOnly value={password} aria-label="Contraseña inicial generada" />
            <button className="row-action password-action password-refresh" type="button" title="Generar otra contraseña" aria-label="Generar otra contraseña" onClick={() => setPassword(generatePassword())}><Icon name="refresh" size={15} /></button>
            <button className="row-action password-action password-reveal" type="button" title={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setShowPassword((current) => !current)}><Icon name={showPassword ? "eyeOff" : "eye"} size={15} /></button>
          </div>
          {/* <small>Generada automáticamente. Entrega las credenciales al empleado.</small> */}
        </div>
        <button className="button button-primary" type="submit"><Icon name="plus" size={16} />Crear cuenta</button>
      </form>
      {credentials && <div className="credentials-card" role="status">
        <div><strong>Credenciales de {credentials.name}</strong><span>Correo: {credentials.email}</span><span className="credentials-password">Contraseña: <code>{showCredentialsPassword ? credentials.password : "•".repeat(credentials.password.length)}</code><button className="row-action" type="button" title={showCredentialsPassword ? "Ocultar contraseña" : "Mostrar contraseña"} aria-label={showCredentialsPassword ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setShowCredentialsPassword((current) => !current)}><Icon name={showCredentialsPassword ? "eyeOff" : "eye"} size={14} /></button></span></div>
        <button className="button button-secondary" type="button" onClick={copyCredentials}><Icon name={copied ? "check" : "options"} size={15} />{copied ? "Copiado" : "Copiar"}</button>
      </div>}
      {/* <p className="employees-note">El empleado edita solo sus filas. Credenciales guardadas en este prototipo local.</p> */}
    </section>
    <section className="content-card employees-card">
      <h2>Cuentas activas <span className="muted-count">&nbsp;{activeEmployees.length}</span></h2>
      <div className="employee-list">
        {activeEmployees.map((employee) => <div className="employee-row" key={employee.id}>
          <span className="employee-avatar">{employee.name.charAt(0).toUpperCase()}</span>
          <span className="employee-info"><strong>{employee.name}</strong><small>{employee.email}</small></span>
          <span className="employee-role">Empleado</span>
          <button className="row-action row-action-delete" type="button" aria-label={`Revocar acceso de ${employee.name}`} title="Revocar acceso" onClick={() => onRevokeEmployee(employee.id)}><Icon name="trash" size={15} /></button>
        </div>)}
        {activeEmployees.length === 0 && <p className="employees-empty">Todavía no creaste cuentas de empleado.</p>}
      </div>
      {revokedEmployees.length > 0 && <div className="revoked-section">
        <h3>Accesos revocados</h3>
        <div className="employee-list">
          {revokedEmployees.map((employee) => <div className="employee-row revoked" key={employee.id}>
            <span className="employee-avatar">{employee.name.charAt(0).toUpperCase()}</span>
            <span className="employee-info"><strong>{employee.name}</strong><small>{employee.email}</small></span>
            <span className="employee-role">Acceso revocado</span>
          </div>)}
        </div>
      </div>}
    </section>
    <section className="content-card employees-card">
      <h2>Ajustes de stock recientes</h2>
      <div className="employee-list">
        {movements.slice(0, 8).map((movement) => <div className="employee-row" key={movement.id}>
          <span className="employee-info"><strong>{movement.productoNombre}</strong><small>{movement.responsableNombre} &middot; {new Date(movement.fechaHora).toLocaleString("es-PE")}</small></span>
          <span className={`movement-delta ${movement.diferencia > 0 ? "positive" : "negative"}`}>{movement.diferencia > 0 ? "+" : ""}{movement.diferencia}</span>
        </div>)}
        {movements.length === 0 && <p className="employees-empty">Todav&iacute;a no se registraron ajustes de stock.</p>}
      </div>
    </section>
  </div>;
}
