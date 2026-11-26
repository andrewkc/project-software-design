import React, { useState } from "react";
import { Brand } from "../../components/Brand";
import { Icon } from "../../components/Icon";

export function LoginPage({ onLogin }) {
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onLogin({ correo, password });
    } catch (err) {
      setError(err.message || "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return <div className="signup-shell">
    <section className="signup-art">
      <Brand light />
      <div className="art-copy">
        <p className="eyebrow">ADMINISTRACIÓN</p>
        <h1>Controla el acceso,<br />no el inventario.</h1>
        <p>Gestiona cuentas y bodegas desde un solo lugar. Las decisiones de precios, promociones y sugerencias siguen siendo del jefe.</p>
      </div>
      <div className="art-note">
        <span className="note-icon"><Icon name="shield" size={21} /></span>
        <span><strong>Perfil Admin</strong><small>Este panel no consulta costos ni ventas.</small></span>
      </div>
    </section>
    <section className="signup-panel">
      <div className="mobile-brand"><Brand mobile /></div>
      <div className="signup-form-wrap">
        <p className="form-kicker">ACCESO DE PLATAFORMA</p>
        <h2>Iniciar sesión</h2>
        <p className="form-intro">Ingresa con tu cuenta de administrador.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-field"><span>Correo</span><input type="email" autoComplete="username" value={correo} onChange={(event) => setCorreo(event.target.value)} placeholder="tu@correo.com" required /></label>
          <label className="auth-field"><span>Contraseña</span><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Tu contraseña" required /></label>
          <button className="button button-primary button-full" type="submit" disabled={loading}>
            <Icon name="lock" size={16} />{loading ? "Ingresando…" : "Ingresar al panel"}
          </button>
        </form>
        <p className="auth-error" role="alert">{error}</p>
      </div>
    </section>
  </div>;
}
