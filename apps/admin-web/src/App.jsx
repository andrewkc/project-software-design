import React, { useCallback, useEffect, useState } from "react";
import { adminApi, clearToken, getToken, setToken } from "./lib/api";
import { AdminLayout } from "./components/layout/AdminLayout";
import { LoginPage } from "./features/auth/LoginPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { UsersPage } from "./features/users/UsersPage";
import { StoresPage } from "./features/stores/StoresPage";
import { AdminProfilePage } from "./features/profile/AdminProfilePage";

export default function App() {
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [stores, setStores] = useState([]);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [loading, setLoading] = useState(Boolean(getToken()));
  const [loadError, setLoadError] = useState("");

  const loadData = useCallback(async () => {
    const [nextUsers, nextStores] = await Promise.all([adminApi.listUsers(), adminApi.listStores()]);
    setUsers(nextUsers);
    setStores(nextStores);
  }, []);

  useEffect(() => {
    if (!getToken()) return;
    let mounted = true;
    adminApi.me()
      .then(async (perfil) => {
        if (!mounted) return;
        setUser(perfil);
        await loadData();
      })
      .catch(() => {
        if (!mounted) return;
        clearToken();
        setUser(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [loadData]);

  async function handleLogin(payload) {
    const response = await adminApi.login(payload);
    setToken(response.token);
    setUser(response.perfil);
    setLoadError("");
    setLoading(true);
    try {
      await loadData();
      setActiveTab("dashboard");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setUsers([]);
    setStores([]);
    setActiveTab("dashboard");
  }

  async function handleCreate(payload) {
    await adminApi.createUser(payload);
    await loadData();
  }

  async function handleUpdate(id, payload) {
    await adminApi.updateUser(id, payload);
    await loadData();
  }

  async function handleDeactivate(id) {
    await adminApi.deactivateUser(id);
    await loadData();
  }

  if (loading) return <div className="signup-panel"><p className="form-intro">Cargando consola de administración…</p></div>;

  if (!user) return <LoginPage onLogin={handleLogin} />;

  let page;
  if (activeTab === "users") {
    page = <UsersPage user={user} users={users} stores={stores} onNavigate={setActiveTab} onCreate={handleCreate} onUpdate={handleUpdate} onDeactivate={handleDeactivate} />;
  } else if (activeTab === "stores") {
    page = <StoresPage users={users} stores={stores} onNavigate={setActiveTab} />;
  } else if (activeTab === "profile") {
    page = <AdminProfilePage user={user} onLogout={handleLogout} />;
  } else {
    page = <DashboardPage user={user} users={users} stores={stores} onNavigate={setActiveTab} />;
  }

  return <AdminLayout user={user} activeTab={activeTab} onNavigate={setActiveTab}>
    {loadError && <div className="page-content"><p className="auth-error" role="alert">{loadError}</p></div>}
    {page}
  </AdminLayout>;
}
