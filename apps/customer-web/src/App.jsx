import React, { useEffect, useMemo, useState } from "react";
import { OperationsLayout } from "./components/layout/OperationsLayout";
import { readSaved } from "./lib/storage";
import { demoAccounts, starterProducts, productMethods } from "./data/demoData";
import { useInventorySummary } from "./hooks/useInventorySummary";
import { AuthScreen } from "./features/auth/AuthScreen";
import { HomePage } from "./features/home/HomePage";
import { InventoryPage } from "./features/inventory/InventoryPage";
import { AlertsPage } from "./features/alerts/AlertsPage";
import { InsightsPage } from "./features/insights/InsightsPage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { ProductModal } from "./features/products/ProductModal";
import { RegisterPage } from "./features/register/RegisterPage";
import { Icon } from "./components/Icon";
import { EmployeesPage } from "./features/employees/EmployeesPage";
import { SalesPage } from "./features/sales/SalesPage";
import { CustomerStockPage } from "./features/customer/CustomerStockPage";
import { JEFE_ID, currentUserId, isCliente, isJefe, withProductDefaults, withUserDefaults } from "./lib/permissions";
import { subscribeToKeys } from "./lib/liveStock";
import { registerSale, SaleError } from "./lib/sales";
import { findProfileByEmail, listProfiles, saveProfile, updateProfile } from "./lib/profileDb";
import { workspaceCopy } from "./lib/workspaceCopy";

const LIVE_KEYS = ["bodega-products", "bodega-movements", "bodega-employees"];
const DEFAULT_STORE = "Bodega San Martín";
const homeTab = (profile) => isCliente(profile) ? "stock" : "home";

// La sesión vive por pestaña: así jefe y cliente pueden verse a la vez en el mismo navegador.
function readSessionUser() {
  try {
    return withUserDefaults(JSON.parse(sessionStorage.getItem("bodega-session-user")));
  } catch {
    return null;
  }
}

function readSavedProducts() {
  const saved = readSaved("bodega-products", []);
  return Array.isArray(saved) ? saved.map(withProductDefaults) : [];
}

function savedClients() {
  const saved = readSaved("bodega-clients", []);
  return Array.isArray(saved) ? saved : [];
}

function App() {
  const [user, setUser] = useState(readSessionUser);
  const [products, setProducts] = useState(() => {
    const savedProducts = readSaved("bodega-products", starterProducts);
    const isLegacyDemo = Array.isArray(savedProducts) && savedProducts.length <= 20 && savedProducts.every((product) => product.id >= 1 && product.id <= 20);
    const selected = isLegacyDemo ? starterProducts : Array.isArray(savedProducts) ? savedProducts : starterProducts;
    return selected.map(withProductDefaults);
  });
  const [employees, setEmployees] = useState(() => {
    const saved = readSaved("bodega-employees", []);
    return Array.isArray(saved) ? saved : [];
  });
  const [jefeProfile, setJefeProfile] = useState(() => readSaved("bodega-jefe", null));
  const [movements, setMovements] = useState(() => {
    const saved = readSaved("bodega-movements", []);
    return Array.isArray(saved) ? saved : [];
  });
  const [screen, setScreen] = useState(() => sessionStorage.getItem("bodega-screen") === "app" && readSessionUser() ? "app" : "auth");
  const [authMode, setAuthMode] = useState("login");
  const [authBusy, setAuthBusy] = useState(false);
  const [activeTab, setActiveTab] = useState(() => homeTab(readSessionUser()));
  const [method, setMethod] = useState(null);
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");
  const [photoName, setPhotoName] = useState("");
  const [barcode, setBarcode] = useState("");
  const { expiringProducts, stockTotal, categoryTotals, stockSeries } = useInventorySummary(products);
  const filteredProducts = useMemo(() => products.filter((product) => product.name.toLowerCase().includes(query.toLowerCase())), [products, query]);
  const maxCategoryTotal = Math.max(...categoryTotals.map(([, total]) => total), 1);

  useEffect(() => {
    let active = true;
    listProfiles().then((profiles) => {
      if (!active) return;
      const jefe = profiles.find((profile) => profile.role === "jefe");
      if (jefe) {
        localStorage.setItem("bodega-jefe", JSON.stringify(jefe));
        setJefeProfile(jefe);
      }
      setEmployees(profiles.filter((profile) => profile.role === "empleado"));
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => localStorage.setItem("bodega-products", JSON.stringify(products)), [products]);
  useEffect(() => {
    if (user) sessionStorage.setItem("bodega-session-user", JSON.stringify(user));
    else sessionStorage.removeItem("bodega-session-user");
  }, [user]);
  useEffect(() => subscribeToKeys(LIVE_KEYS, (key, value) => {
    if (!Array.isArray(value)) return;
    if (key === "bodega-products") setProducts(value.map(withProductDefaults));
    if (key === "bodega-movements") setMovements(value);
    if (key === "bodega-employees") setEmployees(value);
  }), []);
  useEffect(() => { if (user && isJefe(user) && !user.demo) { localStorage.setItem("bodega-jefe", JSON.stringify(user)); setJefeProfile(user); } }, [user]);
  useEffect(() => localStorage.setItem("bodega-employees", JSON.stringify(employees)), [employees]);
  useEffect(() => localStorage.setItem("bodega-movements", JSON.stringify(movements)), [movements]);
  useEffect(() => { sessionStorage.setItem("bodega-screen", screen); }, [screen]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  async function finishSignup(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const nombres = String(data.get("nombres") || "").trim();
    const apellidos = String(data.get("apellidos") || "").trim();
    if (!nombres || !apellidos) {
      setToast("Ingresa tus nombres y apellidos.");
      return;
    }
    const role = data.get("role") === "cliente" ? "cliente" : "jefe";
    const profile = withUserDefaults({
      id: role === "cliente" ? `cli-${Date.now()}` : JEFE_ID,
      role,
      name: `${nombres} ${apellidos}`.trim(),
      nombres,
      apellidos,
      email: data.get("email").trim().toLowerCase(),
      password: data.get("password") || "",
      store: data.get("store").trim(),
      creadoEn: new Date().toISOString(),
    });
    setAuthBusy(true);
    try {
      let existing = null;
      try {
        existing = await findProfileByEmail(profile.email);
      } catch {
        existing = null;
      }
      if (existing) {
        setToast("Ya existe una cuenta con ese correo.");
        return;
      }
      try {
        await saveProfile(profile);
      } catch {
        if (role === "cliente") localStorage.setItem("bodega-clients", JSON.stringify([...savedClients(), profile]));
        else localStorage.setItem("bodega-jefe", JSON.stringify(profile));
      }
      setUser(profile);
      setActiveTab(homeTab(profile));
      setScreen("app");
    setToast(`\u00a1Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}! Tu bodega est\u00e1 lista.`);
    } finally {
      setAuthBusy(false);
    }
  }

  async function finishLogin(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = data.get("email").trim().toLowerCase();
    const password = data.get("password") || "";
    setAuthBusy(true);
    try {
      let account = null;
      try {
        account = await findProfileByEmail(email);
      } catch {
        account = null;
      }
      if (!account) {
        const savedEmployees = readSaved("bodega-employees", []);
        const savedJefe = readSaved("bodega-jefe", null);
        const local = [...(Array.isArray(savedEmployees) ? savedEmployees : []), ...savedClients(), ...(savedJefe ? [savedJefe] : [])];
        account = local.find((item) => item.email?.toLowerCase() === email) || null;
      }
      if (!account || password !== account.password) {
        setToast("Correo o contraseña incorrectos.");
        return;
      }
      if (account.activo === false) {
        setToast("Esa cuenta ya no tiene acceso a la bodega.");
        return;
      }
      const profile = withUserDefaults(account);
      setUser(profile);
      setActiveTab(homeTab(profile));
      setScreen("app");
    setToast(`\u00a1Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}!`);
    } finally {
      setAuthBusy(false);
    }
  }

  function handleLogout() {
    setUser(null);
    setScreen("auth");
    setAuthMode("login");
    setActiveTab("home");
  }

  function enterDemo(account) {
    const profile = withUserDefaults(account);
    setUser(profile);
    setActiveTab(homeTab(profile));
    setScreen("app");
  }

  function submitSale(cart) {
    // Se relee el stock guardado para no vender sobre datos viejos si otra pestaña acaba de vender.
    const latest = readSavedProducts();
    try {
      const result = registerSale(latest.length ? latest : products, cart, user);
      const saved = readSaved("bodega-movements", []);
      const nextMovements = [result.movement, ...(Array.isArray(saved) ? saved : [])];
      localStorage.setItem("bodega-products", JSON.stringify(result.products));
      localStorage.setItem("bodega-movements", JSON.stringify(nextMovements));
      setProducts(result.products);
      setMovements(nextMovements);
      setToast(`Venta registrada por S/ ${result.movement.total.toFixed(2)}.`);
      return { ok: true };
    } catch (error) {
      if (!(error instanceof SaleError)) throw error;
      if (latest.length) setProducts(latest);
      return { ok: false, error: error.message };
    }
  }

  function openMethod(id) {
    setMethod(id);
    setPhotoName("");
    setBarcode("");
  }

  function addProduct(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = data.get("productName").trim();
    const quantity = Number(data.get("quantity"));
    if (!name || !(quantity > 0)) return;
    const category = data.get("category");
    const icon = String(data.get("icon") || "").trim() || (category === "Frutas" ? "\u{1F34E}" : category === "L\u00e1cteos" ? "\u{1F95B}" : "\u{1F4E6}");
    setProducts((current) => [{ id: Date.now(), name, category, icon, stock: quantity, unit: data.get("unit"), price: Number(data.get("price")) || 0, expires: data.get("expires") || "", barcode: String(data.get("barcode") || "").trim(), creadoPor: currentUserId(user), bloqueado: false, bloqueadoPor: null, activo: true }, ...current]);
    setMethod(null);
    setActiveTab("inventory");
    setToast(`${name} se agregó a ${workspaceCopy(user).addedTarget}.`);
  }

  function updateProduct(id, changes) {
    const previous = products.find((product) => product.id === id);
    if (previous && Number(previous.stock) !== Number(changes.stock)) {
      setMovements((current) => [{
        id: Date.now(),
        fechaHora: new Date().toISOString(),
        tipo: "ajuste",
        motivo: "Edición directa de stock",
        responsable: currentUserId(user),
        responsableNombre: user?.name || "Jefe de Bodega",
        productoId: id,
        productoNombre: previous.name,
        stockAnterior: Number(previous.stock),
        stockNuevo: Number(changes.stock),
        diferencia: Number(changes.stock) - Number(previous.stock),
      }, ...current]);
    }
    setProducts((current) => current.map((product) => product.id === id ? { ...product, ...changes } : product));
    setToast("Cambios guardados.");
  }

  function setProductActive(id, activo) {
    setProducts((current) => current.map((product) => product.id === id ? { ...product, activo } : product));
    setToast(activo ? "Producto reactivado." : "Producto desactivado. Su historial se conserva.");
  }

  function toggleProductLock(id) {
    const target = products.find((product) => product.id === id);
    if (!target) return;
    const bloqueado = !target.bloqueado;
    setProducts((current) => current.map((product) => product.id === id ? { ...product, bloqueado, bloqueadoPor: bloqueado ? currentUserId(user) : null } : product));
    setToast(bloqueado ? "Fila bloqueada. Solo tú puedes editarla." : "Fila desbloqueada.");
  }

  async function createEmployee(event, password) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const nombres = String(data.get("nombres") || "").trim();
    const apellidos = String(data.get("apellidos") || "").trim();
    const name = `${nombres} ${apellidos}`.trim();
    const email = data.get("email").trim().toLowerCase();
    if (!name || !email || !password || password.length < 8) return false;
    if (user?.email?.toLowerCase() === email || employees.some((employee) => employee.email.toLowerCase() === email)) {
      setToast("Ya existe una cuenta con ese correo.");
      return false;
    }
    const account = {
      id: `emp-${Date.now()}`,
      nombres,
      apellidos,
      name,
      email,
      store: user?.store || "Bodega San Martín",
      role: "empleado",
      password,
      activo: true,
      creadoEn: new Date().toISOString(),
    };
    try {
      const existing = await findProfileByEmail(email);
      if (existing) {
        setToast("Ya existe una cuenta con ese correo.");
        return false;
      }
      await saveProfile(account);
    } catch {
      setToast("SQLite no disponible; la cuenta se guardó solo en este navegador.");
    }
    setEmployees((current) => [...current, account]);
    event.currentTarget.reset();
    setToast(`Cuenta de ${name} creada. Entrega las credenciales al empleado.`);
    return true;
  }

  async function revokeEmployee(id) {
    const target = employees.find((employee) => employee.id === id);
    if (!target || target.activo === false) return;
    if (!window.confirm(`¿Revocar el acceso de ${target.name}? Sus registros se conservarán y sus filas quedarán bloqueadas.`)) return;
    const revocadoEn = new Date().toISOString();
    try {
      await updateProfile(id, { activo: 0, revocado_en: revocadoEn });
    } catch {
      setToast("SQLite no disponible; el cambio se guardó solo en este navegador.");
    }
    setEmployees((current) => current.map((employee) => employee.id === id ? { ...employee, activo: false, revocadoEn } : employee));
    setProducts((current) => current.map((product) => product.creadoPor === id ? { ...product, bloqueado: true, bloqueadoPor: JEFE_ID } : product));
    setToast("Acceso revocado. Las filas del empleado quedaron bloqueadas.");
  }

  async function changeEmployeePassword(currentPassword, newPassword) {
    if (user?.role !== "empleado" || !newPassword || newPassword.length < 8) return false;
    let account = employees.find((employee) => employee.id === user.id);
    try {
      account = (await findProfileByEmail(user.email)) || account;
    } catch {
      account = account || null;
    }
    if (!account || account.password !== currentPassword) {
      setToast("La contraseña actual no es correcta.");
      return false;
    }
    try {
      await updateProfile(account.id, { password: newPassword });
    } catch {
      setToast("SQLite no disponible; la contraseña se actualizó solo en este navegador.");
    }
    setEmployees((current) => current.map((employee) => employee.id === account.id ? { ...employee, password: newPassword } : employee));
    setUser({ ...user, password: newPassword });
    setToast("Contraseña actualizada.");
    return true;
  }

  if (screen === "auth") return <AuthScreen mode={authMode} busy={authBusy} stores={[...new Set([jefeProfile?.store, DEFAULT_STORE].filter(Boolean))]} demoAccounts={import.meta.env.DEV ? demoAccounts : []} onDemoLogin={enterDemo} onModeChange={setAuthMode} onLogin={finishLogin} onSignup={finishSignup} onForgotPassword={() => setToast("La recuperaci\u00f3n de contrase\u00f1a estar\u00e1 disponible pronto.")} />;
  return <>
    <OperationsLayout user={user} activeTab={activeTab} expiringCount={expiringProducts.length} onNavigate={setActiveTab} onRegister={() => setActiveTab("register")} onLogout={handleLogout}>
      {isCliente(user) ? <>
        {activeTab === "profile" ? <ProfilePage user={user} onLogout={handleLogout} onChangePassword={changeEmployeePassword} /> : <CustomerStockPage products={products} user={user} />}
      </> : <>
      {activeTab === "home" && <HomePage user={user} products={products} expiringProducts={expiringProducts} stockTotal={stockTotal} stockSeries={stockSeries} categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} onRegister={() => setActiveTab("register")} onNavigate={setActiveTab} />}
      {activeTab === "inventory" && <InventoryPage products={products} filteredProducts={filteredProducts} stockTotal={stockTotal} expiringProducts={expiringProducts} query={query} onQueryChange={setQuery} user={user} employees={employees} jefeProfile={jefeProfile} onUpdateProduct={updateProduct} onSetProductActive={setProductActive} onToggleLock={toggleProductLock} onRegister={() => openMethod("text")} />}
      {activeTab === "register" && <RegisterPage products={products} user={user} onSubmit={addProduct} />}
      {activeTab === "sales" && <SalesPage products={products} movements={movements} user={user} onRegisterSale={submitSale} />}
      {activeTab === "alerts" && <AlertsPage expiringProducts={expiringProducts} />}
      {activeTab === "insights" && <InsightsPage />}
      {activeTab === "employees" && <EmployeesPage employees={employees} movements={movements} onCreateEmployee={createEmployee} onRevokeEmployee={revokeEmployee} />}
      {activeTab === "profile" && <ProfilePage user={user} onLogout={handleLogout} onChangePassword={changeEmployeePassword} />}
      </>}
    </OperationsLayout>
    {method && <ProductModal method={productMethods.find((item) => item.id === method)} user={user} onClose={() => setMethod(null)} onSubmit={addProduct} photoName={photoName} setPhotoName={setPhotoName} barcode={barcode} setBarcode={setBarcode} />}
    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
  </>;
}

export default App;
