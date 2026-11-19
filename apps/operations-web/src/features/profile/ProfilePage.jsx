import React, { useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";

export function ProfilePage({ user, onLogout, onBackToJefe, onChangePassword }) {
  const name = user?.name || "Kelvin Cahuana";
  const email = user?.email || "Sin correo registrado";
  const store = user?.store || "Mi bodega";
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  function handlePasswordChange(event) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setError("");
    if (onChangePassword(currentPassword, newPassword)) {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    }
  }

  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row">
      <div>
        <h1>Perfil</h1><p className="welcome-subtitle">Administra la información de tu cuenta y tu bodega.</p>
      </div>
    </section>
    <section className="profile-page-card">
      <div className="profile-page-avatar">{name.charAt(0).toUpperCase()}</div>
      <div className="profile-page-info"><h2>{name}</h2><p>{user?.role === "empleado" ? "Empleado" : "Jefe de Bodega"}</p><dl><div><dt>Correo electrónico</dt><dd>{email}</dd></div><div><dt>Bodega</dt><dd>{store}</dd></div></dl></div>
      <div className="profile-page-actions">
        {user?.role === "empleado" && <button className="button button-secondary" type="button" onClick={onBackToJefe}>Volver a la cuenta del jefe</button>}
        <button className="button button-secondary profile-logout" type="button" onClick={onLogout}>Cerrar sesión</button>
      </div>
    </section>
    {user?.role === "empleado" && <section className="content-card employees-card">
      <h2>Cambiar contraseña</h2>
      <form className="employee-form" onSubmit={handlePasswordChange}>
        <label className="auth-field"><span>Contraseña actual</span><input className="employee-input" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
        <label className="auth-field"><span>Nueva contraseña</span><input className="employee-input" type="password" minLength="8" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
        <label className="auth-field"><span>Confirmar contraseña</span><input className="employee-input" type="password" minLength="8" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></label>
        <button className="button button-primary" type="submit"><Icon name="shield" size={16} />Actualizar contraseña</button>
      </form>
      {error && <p className="password-error">{error}</p>}
      {/* <p className="employees-note">Cambiar la contraseña es opcional; puedes conservar la que te entregó el jefe.</p> */}
    </section>}
  </div>;
}
