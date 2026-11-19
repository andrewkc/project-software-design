import React, { useEffect, useMemo, useState } from "react";
import { OperationsLayout } from "./components/layout/OperationsLayout";
import { readSaved } from "./lib/storage";
import { starterProducts, productMethods } from "./data/demoData";
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
import { JEFE_ID, currentUserId, isJefe, withProductDefaults, withUserDefaults } from "./lib/permissions";

function App() {
  const [user, setUser] = useState(() => withUserDefaults(readSaved("bodega-user", null)));
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
  const [movements, setMovements] = useState(() => {
    const saved = readSaved("bodega-movements", []);
    return Array.isArray(saved) ? saved : [];
  });
  const [screen, setScreen] = useState(() => sessionStorage.getItem("bodega-screen") === "app" ? "app" : "auth");
  const [authMode, setAuthMode] = useState("login");
  const [activeTab, setActiveTab] = useState("home");
  const [method, setMethod] = useState(null);
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");
  const [voiceCaptured, setVoiceCaptured] = useState(false);
  const [photoName, setPhotoName] = useState("");
  const [barcode, setBarcode] = useState("");
  const { expiringProducts, stockTotal, categoryTotals, stockSeries } = useInventorySummary(products);
  const filteredProducts = useMemo(() => products.filter((product) => product.name.toLowerCase().includes(query.toLowerCase())), [products, query]);
  const maxCategoryTotal = Math.max(...categoryTotals.map(([, total]) => total), 1);

  useEffect(() => localStorage.setItem("bodega-products", JSON.stringify(products)), [products]);
  useEffect(() => { if (user) localStorage.setItem("bodega-user", JSON.stringify(user)); }, [user]);
  useEffect(() => { if (user && isJefe(user)) localStorage.setItem("bodega-jefe", JSON.stringify(user)); }, [user]);
  useEffect(() => localStorage.setItem("bodega-employees", JSON.stringify(employees)), [employees]);
  useEffect(() => localStorage.setItem("bodega-movements", JSON.stringify(movements)), [movements]);
  useEffect(() => { sessionStorage.setItem("bodega-screen", screen); }, [screen]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function finishSignup(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const profile = withUserDefaults({ id: JEFE_ID, role: "jefe", name: data.get("name").trim(), email: data.get("email").trim(), store: data.get("store").trim() });
    setUser(profile);
    setScreen("app");
    setToast(`\u00a1Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}! Tu bodega est\u00e1 lista.`);
  }

  function finishLogin(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = data.get("email").trim().toLowerCase();
    const password = data.get("password") || "";
    const savedEmployees = readSaved("bodega-employees", []);
    const account = Array.isArray(savedEmployees) ? savedEmployees.find((employee) => employee.email.toLowerCase() === email) : null;
    let profile;
    if (account) {
      if (account.activo === false) {
        setToast("Esa cuenta ya no tiene acceso a la bodega.");
        return;
      }
      if (account.password && password !== account.password) {
        setToast("Correo o contraseña incorrectos.");
        return;
      }
      profile = withUserDefaults(account);
    } else {
      const jefe = readSaved("bodega-jefe", null);
      profile = withUserDefaults(jefe || { id: JEFE_ID, role: "jefe", name: "Kelvin Cahuana", email: data.get("email").trim(), store: "Bodega San Mart\u00edn" });
    }
    setUser(profile);
    setScreen("app");
    setToast(`\u00a1Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}!`);
  }

  function handleLogout() {
    setScreen("auth");
    setAuthMode("login");
    setActiveTab("home");
  }

  function openMethod(id) {
    setMethod(id);
    setVoiceCaptured(false);
    setPhotoName("");
    setBarcode("");
  }

  function addProduct(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = data.get("productName").trim();
    const quantity = Number(data.get("quantity"));
    if (!name || quantity < 1) return;
    const category = data.get("category");
    const icon = category === "Frutas" ? "\u{1F34E}" : category === "L\u00e1cteos" ? "\u{1F95B}" : "\u{1F4E6}";
    setProducts((current) => [{ id: Date.now(), name, category, icon, stock: quantity, unit: data.get("unit"), price: Number(data.get("price")) || 0, expires: data.get("expires") || "", creadoPor: currentUserId(user), bloqueado: false, bloqueadoPor: null, activo: true }, ...current]);
    setMethod(null);
    setActiveTab("inventory");
    setToast(`${name} se agreg\u00f3 a tu inventario.`);
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

  function createEmployee(event, password) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = `${String(data.get("nombres") || "").trim()} ${String(data.get("apellidos") || "").trim()}`.trim();
    const email = data.get("email").trim().toLowerCase();
    if (!name || !email || !password || password.length < 8) return false;
    if (user?.email?.toLowerCase() === email || employees.some((employee) => employee.email.toLowerCase() === email)) {
      setToast("Ya existe una cuenta con ese correo.");
      return false;
    }
    setEmployees((current) => [...current, { id: `emp-${Date.now()}`, name, email, store: user?.store || "Bodega San Martín", role: "empleado", password, activo: true, creadoEn: new Date().toISOString() }]);
    event.currentTarget.reset();
    setToast(`Cuenta de ${name} creada. Entrega las credenciales al empleado.`);
    return true;
  }

  function revokeEmployee(id) {
    const target = employees.find((employee) => employee.id === id);
    if (!target || target.activo === false) return;
    if (!window.confirm(`¿Revocar el acceso de ${target.name}? Sus registros se conservarán y sus filas quedarán bloqueadas.`)) return;
    setEmployees((current) => current.map((employee) => employee.id === id ? { ...employee, activo: false, revocadoEn: new Date().toISOString() } : employee));
    setProducts((current) => current.map((product) => product.creadoPor === id ? { ...product, bloqueado: true, bloqueadoPor: JEFE_ID } : product));
    if (user?.id === id) backToJefe();
    setToast("Acceso revocado. Las filas del empleado quedaron bloqueadas.");
  }

  function changeEmployeePassword(currentPassword, newPassword) {
    if (user?.role !== "empleado" || !newPassword || newPassword.length < 8) return false;
    const account = employees.find((employee) => employee.id === user.id);
    if (!account || account.password !== currentPassword) {
      setToast("La contraseña actual no es correcta.");
      return false;
    }
    setEmployees((current) => current.map((employee) => employee.id === user.id ? { ...employee, password: newPassword } : employee));
    setUser({ ...user, password: newPassword });
    setToast("Contraseña actualizada.");
    return true;
  }

  function switchUser(account) {
    setUser(withUserDefaults(account));
    setActiveTab("home");
    setToast(`Ahora estás viendo la bodega como ${account.name}.`);
  }

  function backToJefe() {
    const jefe = readSaved("bodega-jefe", null);
    setUser(withUserDefaults(jefe || { id: JEFE_ID, role: "jefe", name: "Kelvin Cahuana", email: "jefe@bodesmart.com", store: "Bodega San Martín" }));
    setActiveTab("home");
    setToast("Volviste a la cuenta del jefe.");
  }
  
  if (screen === "auth") return <AuthScreen mode={authMode} onModeChange={setAuthMode} onLogin={finishLogin} onSignup={finishSignup} onForgotPassword={() => setToast("La recuperaci\u00f3n de contrase\u00f1a estar\u00e1 disponible pronto.")} />;
  return <>
    <OperationsLayout user={user} activeTab={activeTab} expiringCount={expiringProducts.length} onNavigate={setActiveTab} onRegister={() => setActiveTab("register")} onLogout={handleLogout}>
      {activeTab === "home" && <HomePage user={user} products={products} expiringProducts={expiringProducts} stockTotal={stockTotal} stockSeries={stockSeries} categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} onRegister={() => setActiveTab("register")} onNavigate={setActiveTab} />}
      {activeTab === "inventory" && <InventoryPage products={products} filteredProducts={filteredProducts} stockTotal={stockTotal} expiringProducts={expiringProducts} query={query} onQueryChange={setQuery} user={user} employees={employees} onUpdateProduct={updateProduct} onSetProductActive={setProductActive} onToggleLock={toggleProductLock} onRegister={() => openMethod("text")} />}
      {activeTab === "register" && <RegisterPage products={products} onSubmit={addProduct} />}
      {activeTab === "alerts" && <AlertsPage expiringProducts={expiringProducts} />}
      {activeTab === "insights" && <InsightsPage />}
      {activeTab === "employees" && <EmployeesPage employees={employees} movements={movements} user={user} onCreateEmployee={createEmployee} onRevokeEmployee={revokeEmployee} onSwitchUser={switchUser} onBackToJefe={backToJefe} />}
      {activeTab === "profile" && <ProfilePage user={user} onLogout={handleLogout} onBackToJefe={backToJefe} onChangePassword={changeEmployeePassword} />}
    </OperationsLayout>
    {method && <ProductModal method={productMethods.find((item) => item.id === method)} onClose={() => setMethod(null)} onSubmit={addProduct} voiceCaptured={voiceCaptured} setVoiceCaptured={setVoiceCaptured} photoName={photoName} setPhotoName={setPhotoName} barcode={barcode} setBarcode={setBarcode} />}
    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
  </>;
}

export default App;
