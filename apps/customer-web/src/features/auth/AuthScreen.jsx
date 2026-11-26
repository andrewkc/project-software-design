import React from "react";
import { Brand } from "../../components/Brand";

export function AuthScreen({ mode, busy = false, onModeChange, onLogin, onSignup, onDemo }) {
  return <main className="signup-shell">
    <section className="signup-art" aria-label="Presentación de BodeSmart">
      <div className="art-brand"><Brand className="brand-light" /></div>
      <div className="art-copy"><span className="eyebrow">OFERTAS CERCA DE TI</span><h1>Compra mejor.<br />Aprovecha más.</h1><p>Descubre productos de las bodegas de tu barrio, compara precios y elige lo que se consume antes de que venza.</p></div>
      <div className="art-note"><span className="note-icon">🛍️</span><span><strong>Tu cesta, tus pedidos y tus ofertas en un solo lugar.</strong></span></div>
      <span className="art-orb orb-one" /><span className="art-orb orb-two" />
    </section>
    <section className="signup-panel"><div className="signup-form-wrap">
      <div className="mobile-brand"><Brand mobile /></div>
      {mode === "signup" ? <SignupForm busy={busy} onSubmit={onSignup} onLogin={() => onModeChange("login")} /> : <LoginForm busy={busy} onSubmit={onLogin} onSignup={() => onModeChange("signup")} />}
      {onDemo && <button className="demo-explore" type="button" onClick={onDemo}>Explorar la tienda con datos de demostración</button>}
      <small className="demo-note">Demo académica · Pagos de prueba</small>
    </div></section>
  </main>;
}

function LoginForm({ busy, onSubmit, onSignup }) {
  return <><h2>Ingresar como cliente</h2><p className="form-intro">Ingresa para guardar tus pedidos y continuar con tu compra.</p>
    <form className="signup-form auth-form" onSubmit={onSubmit}>
      <label className="auth-field" htmlFor="customer-login-email"><span>Correo electrónico</span><input id="customer-login-email" name="correo" type="email" placeholder="tu@correo.com" autoComplete="email" required /></label>
      <label className="auth-field" htmlFor="customer-login-password"><span>Contraseña</span><input id="customer-login-password" name="password" type="password" placeholder="Ingresa tu contraseña" autoComplete="current-password" required /></label>
      <button className="button button-primary button-full" type="submit" disabled={busy}>{busy ? "Ingresando..." : "Iniciar sesión"}</button>
    </form>
    <div className="auth-divider" />
    <button className="button button-outline button-full create-account-button" type="button" onClick={onSignup}>Crear cuenta de cliente</button>
  </>;
}

function SignupForm({ busy, onSubmit, onLogin }) {
  return <div className="register-auth"><div className="step-indicator"><span className="step-current" /><span /></div><h2>Crear cuenta de cliente</h2>
    <form className="signup-form register-form" onSubmit={onSubmit}>
      <label>Nombres<input name="nombres" type="text" placeholder="Tus nombres" autoComplete="given-name" required /></label>
      <label>Apellidos<input name="apellidos" type="text" placeholder="Tus apellidos" autoComplete="family-name" required /></label>
      <label>Correo electrónico<input name="correo" type="email" placeholder="tu@correo.com" autoComplete="email" required /></label>
      <label>Crea una contraseña<input name="password" type="password" placeholder="Mínimo 8 caracteres" minLength="8" autoComplete="new-password" required /></label>
      <button className="button button-primary button-full" type="submit" disabled={busy}>{busy ? "Creando cuenta..." : "Crear mi cuenta"}</button>
    </form>
    <div className="signup-login">¿Ya tienes cuenta? <button type="button" onClick={onLogin}>Inicia sesión</button></div>
  </div>;
}
