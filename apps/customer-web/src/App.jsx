import React, { useEffect, useMemo, useRef, useState } from "react";
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
import { AdminPage } from "./features/admin/AdminPage";
import { JEFE_ID, currentUserId, isAdmin, isCliente, withProductDefaults, withUserDefaults } from "./lib/permissions";
import { subscribeToKeys } from "./lib/liveStock";
import { registerSale, SaleError } from "./lib/sales";
import { OrderError, acceptOrder, cancelOrder, createOrder, pendingOrders, rejectOrder, visibleOrders } from "./lib/orders";
import { DIRECTORY_KEYS, findAccount, mergeProfiles, readDirectory, writeDirectory } from "./lib/directory";
import { deleteProfile, findProfileByEmail, listProfiles, saveProfile, updateProfile } from "./lib/profileDb";
import { workspaceCopy } from "./lib/workspaceCopy";

const DIRECTORY_KEY_LIST = Object.values(DIRECTORY_KEYS);
const LIVE_KEYS = ["bodega-products", "bodega-movements", "bodega-orders", ...DIRECTORY_KEY_LIST];
const DEFAULT_STORE = "Bodega San Martín";
const homeTab = (profile) => isAdmin(profile) ? "admin" : isCliente(profile) ? "stock" : "home";
const withoutDemoFields = ({ label, demo, ...profile }) => profile;

// La sesión vive por pestaña: así jefe y cliente pueden verse a la vez en el mismo navegador.
function readSessionUser() {
  try {
    return withUserDefaults(JSON.parse(sessionStorage.getItem("bodega-session-user")));
  } catch {
    return null;
  }
}

function readSavedList(key) {
  const saved = readSaved(key, []);
  return Array.isArray(saved) ? saved : [];
}

function readSavedProducts() {
  return readSavedList("bodega-products").map(withProductDefaults);
}

// SQLite del navegador es una copia de respaldo: si no carga, la cuenta sigue en el directorio local.
function mirrorToSqlite(action) {
  action().catch(() => {});
}

function App() {
  const [user, setUser] = useState(readSessionUser);
  const [products, setProducts] = useState(() => {
    const savedProducts = readSaved("bodega-products", starterProducts);
    const isLegacyDemo = Array.isArray(savedProducts) && savedProducts.length <= 20 && savedProducts.every((product) => product.id >= 1 && product.id <= 20);
    const selected = isLegacyDemo ? starterProducts : Array.isArray(savedProducts) ? savedProducts : starterProducts;
    return selected.map(withProductDefaults);
  });
  const [directory, setDirectory] = useState(() => readDirectory());
  const [movements, setMovements] = useState(() => readSavedList("bodega-movements"));
  const [orders, setOrders] = useState(() => readSavedList("bodega-orders"));
  const [screen, setScreen] = useState(() => sessionStorage.getItem("bodega-screen") === "app" && readSessionUser() ? "app" : "auth");
  const [authMode, setAuthMode] = useState("login");
  const [authBusy, setAuthBusy] = useState(false);
  const [activeTab, setActiveTab] = useState(() => homeTab(readSessionUser()));
  const [method, setMethod] = useState(null);
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");
  const [photoName, setPhotoName] = useState("");
  const [barcode, setBarcode] = useState("");
  const userRef = useRef(user);
  const { expiringProducts, stockTotal, categoryTotals, stockSeries } = useInventorySummary(products);
  const filteredProducts = useMemo(() => products.filter((product) => product.name.toLowerCase().includes(query.toLowerCase())), [products, query]);
  const maxCategoryTotal = Math.max(...categoryTotals.map(([, total]) => total), 1);
  const employees = useMemo(() => directory.filter((profile) => profile.role === "empleado" && (!user?.store || profile.store === user.store)), [directory, user]);
  const jefeProfile = useMemo(() => directory.find((profile) => profile.role === "jefe" && profile.store === user?.store) || directory.find((profile) => profile.role === "jefe") || null, [directory, user]);
  const stores = useMemo(() => [...new Set([...directory.filter((profile) => profile.role === "jefe" && profile.activo !== false).map((profile) => profile.store), DEFAULT_STORE].filter(Boolean))], [directory]);
  const myOrders = useMemo(() => visibleOrders(orders, user), [orders, user]);
  const waitingOrders = useMemo(() => pendingOrders(orders, user), [orders, user]);

  useEffect(() => {
    let active = true;
    listProfiles().then((profiles) => {
      if (active) setDirectory((current) => mergeProfiles(current, profiles));
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => { userRef.current = user; }, [user]);
  useEffect(() => localStorage.setItem("bodega-products", JSON.stringify(products)), [products]);
  useEffect(() => {
    if (user) sessionStorage.setItem("bodega-session-user", JSON.stringify(user));
    else sessionStorage.removeItem("bodega-session-user");
  }, [user]);
  useEffect(() => subscribeToKeys(LIVE_KEYS, (key, value) => {
    if (!Array.isArray(value)) return;
    if (key === "bodega-products") setProducts(value.map(withProductDefaults));
    if (key === "bodega-movements") setMovements(value);
    if (key === "bodega-orders") setOrders(value);
    if (DIRECTORY_KEY_LIST.includes(key)) {
      const next = readDirectory();
      setDirectory(next);
      // Si el administrador desactiva o elimina la cuenta, la sesión abierta se cierra.
      const current = userRef.current;
      const me = current && next.find((profile) => profile.id === current.id);
      if (current && ((me && me.activo === false) || (!me && !current.demo))) {
        setUser(null);
        setScreen("auth");
        setToast("Tu cuenta ya no tiene acceso. Habla con el administrador.");
      }
    }
  }), []);
  useEffect(() => writeDirectory(directory), [directory]);
  useEffect(() => localStorage.setItem("bodega-movements", JSON.stringify(movements)), [movements]);
  useEffect(() => localStorage.setItem("bodega-orders", JSON.stringify(orders)), [orders]);
  useEffect(() => { sessionStorage.setItem("bodega-screen", screen); }, [screen]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function enterApp(profile, message) {
    setUser(profile);
    setActiveTab(homeTab(profile));
    setScreen("app");
    if (message) setToast(message);
  }

  async function findAnyAccount(email) {
    const local = findAccount(readDirectory(), email) || findAccount(directory, email);
    if (local) return local;
    try {
      return await findProfileByEmail(email);
    } catch {
      return null;
    }
  }

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
    const jefeId = directory.some((profile) => profile.id === JEFE_ID) ? `jefe-${Date.now()}` : JEFE_ID;
    const profile = withUserDefaults({
      id: role === "cliente" ? `cli-${Date.now()}` : jefeId,
      role,
      name: `${nombres} ${apellidos}`.trim(),
      nombres,
      apellidos,
      email: data.get("email").trim().toLowerCase(),
      password: data.get("password") || "",
      store: data.get("store").trim(),
      activo: true,
      creadoEn: new Date().toISOString(),
    });
    setAuthBusy(true);
    try {
      if (await findAnyAccount(profile.email)) {
        setToast("Ya existe una cuenta con ese correo.");
        return;
      }
      setDirectory((current) => [...current, profile]);
      mirrorToSqlite(() => saveProfile(profile));
      enterApp(profile, `¡Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}! ${role === "cliente" ? "Ya ves el stock de tu bodega." : "Tu bodega está lista."}`);
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
      const account = await findAnyAccount(email);
      if (!account || password !== account.password) {
        setToast("Correo o contraseña incorrectos.");
        return;
      }
      if (account.activo === false) {
        setToast("Esa cuenta ya no tiene acceso.");
        return;
      }
      const profile = withUserDefaults(account);
      enterApp(profile, `¡Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}!`);
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

  // Solo en desarrollo: las cuentas demo se guardan en el directorio para que el administrador las vea.
  function enterDemo(account) {
    const saved = directory.find((profile) => profile.id === account.id);
    if (saved?.activo === false) {
      setToast("Esa cuenta fue desactivada por el administrador.");
      return;
    }
    const missing = demoAccounts.filter((demo) => !directory.some((profile) => profile.id === demo.id)).map((demo) => ({ ...withoutDemoFields(demo), activo: true, creadoEn: new Date().toISOString() }));
    if (missing.length) setDirectory((current) => [...current, ...missing]);
    enterApp(withUserDefaults({ ...(saved || withoutDemoFields(account)), demo: true }));
  }

  // Escribe en el almacenamiento antes de actualizar el estado: así otras pestañas lo ven en el acto.
  function store(key, value, setter) {
    localStorage.setItem(key, JSON.stringify(value));
    setter(value);
  }

  function submitSale(cart) {
    // Se relee el stock guardado para no vender sobre datos viejos si otra pestaña acaba de vender.
    const latest = readSavedProducts();
    try {
      const result = registerSale(latest.length ? latest : products, cart, user);
      store("bodega-products", result.products, setProducts);
      store("bodega-movements", [result.movement, ...readSavedList("bodega-movements")], setMovements);
      setToast(`Venta registrada por S/ ${result.movement.total.toFixed(2)}.`);
      return { ok: true };
    } catch (error) {
      if (!(error instanceof SaleError)) throw error;
      if (latest.length) setProducts(latest);
      return { ok: false, error: error.message };
    }
  }

  function updateOrder(id, change) {
    const latest = readSavedList("bodega-orders");
    const target = latest.find((order) => order.id === id);
    if (!target) return { ok: false, error: "Ese pedido ya no existe." };
    try {
      const result = change(target);
      store("bodega-orders", latest.map((order) => order.id === id ? result.order : order), setOrders);
      if (result.message) setToast(result.message);
      return { ok: true };
    } catch (error) {
      if (!(error instanceof OrderError) && !(error instanceof SaleError)) throw error;
      setOrders(latest);
      return { ok: false, error: error.message };
    }
  }

  function placeOrder(cart) {
    try {
      const order = createOrder(readSavedProducts(), cart, user);
      store("bodega-orders", [order, ...readSavedList("bodega-orders")], setOrders);
      setToast(`Pedido enviado a ${user.store}. Te avisaremos aquí cuando lo atiendan.`);
      return { ok: true };
    } catch (error) {
      if (!(error instanceof OrderError)) throw error;
      return { ok: false, error: error.message };
    }
  }

  function acceptCustomerOrder(id) {
    return updateOrder(id, (order) => {
      const result = acceptOrder(order, readSavedProducts(), user);
      store("bodega-products", result.products, setProducts);
      store("bodega-movements", [result.movement, ...readSavedList("bodega-movements")], setMovements);
      return { order: result.order, message: `Pedido de ${order.clienteNombre} aceptado. Venta registrada por S/ ${result.movement.total.toFixed(2)}.` };
    });
  }

  const rejectCustomerOrder = (id, motivo) => updateOrder(id, (order) => ({ order: rejectOrder(order, user, motivo), message: `Pedido de ${order.clienteNombre} rechazado.` }));
  const cancelCustomerOrder = (id) => updateOrder(id, (order) => ({ order: cancelOrder(order, user), message: "Pedido cancelado." }));

  function saveDirectoryProfile(profile) {
    const previous = directory.find((item) => item.id === profile.id);
    setDirectory((current) => previous ? current.map((item) => item.id === profile.id ? profile : item) : [...current, profile]);
    mirrorToSqlite(() => saveProfile(profile));
    // Igual que al revocar desde Empleados: las filas del empleado desactivado quedan bloqueadas.
    if (profile.role === "empleado" && profile.activo === false && previous?.activo !== false) {
      setProducts((current) => current.map((product) => product.creadoPor === profile.id ? { ...product, bloqueado: true, bloqueadoPor: JEFE_ID } : product));
    }
    if (profile.id === user?.id) setUser(withUserDefaults({ ...user, ...profile }));
    setToast(previous ? `Perfil de ${profile.name} actualizado.` : `Perfil de ${profile.name} creado.`);
  }

  function deleteDirectoryProfile(profile) {
    setDirectory((current) => current.filter((item) => item.id !== profile.id));
    mirrorToSqlite(() => deleteProfile(profile.id));
    setToast(`Perfil de ${profile.name} eliminado.`);
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
    const icon = String(data.get("icon") || "").trim() || (category === "Frutas" ? "\u{1F34E}" : category === "Lácteos" ? "\u{1F95B}" : "\u{1F4E6}");
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
    const form = event.currentTarget;
    const data = new FormData(form);
    const nombres = String(data.get("nombres") || "").trim();
    const apellidos = String(data.get("apellidos") || "").trim();
    const name = `${nombres} ${apellidos}`.trim();
    const email = data.get("email").trim().toLowerCase();
    if (!name || !email || !password || password.length < 8) return false;
    if (user?.email?.toLowerCase() === email || await findAnyAccount(email)) {
      setToast("Ya existe una cuenta con ese correo.");
      return false;
    }
    const account = {
      id: `emp-${Date.now()}`,
      nombres,
      apellidos,
      name,
      email,
      store: user?.store || DEFAULT_STORE,
      role: "empleado",
      password,
      activo: true,
      creadoEn: new Date().toISOString(),
    };
    setDirectory((current) => [...current, account]);
    mirrorToSqlite(() => saveProfile(account));
    form.reset();
    setToast(`Cuenta de ${name} creada. Entrega las credenciales al empleado.`);
    return true;
  }

  async function revokeEmployee(id) {
    const target = employees.find((employee) => employee.id === id);
    if (!target || target.activo === false) return;
    if (!window.confirm(`¿Revocar el acceso de ${target.name}? Sus registros se conservarán y sus filas quedarán bloqueadas.`)) return;
    const revocadoEn = new Date().toISOString();
    mirrorToSqlite(() => updateProfile(id, { activo: 0, revocado_en: revocadoEn }));
    setDirectory((current) => current.map((employee) => employee.id === id ? { ...employee, activo: false, revocadoEn } : employee));
    setProducts((current) => current.map((product) => product.creadoPor === id ? { ...product, bloqueado: true, bloqueadoPor: JEFE_ID } : product));
    setToast("Acceso revocado. Las filas del empleado quedaron bloqueadas.");
  }

  async function changeEmployeePassword(currentPassword, newPassword) {
    if (user?.role !== "empleado" || !newPassword || newPassword.length < 8) return false;
    const account = directory.find((employee) => employee.id === user.id) || await findAnyAccount(user.email);
    if (!account || account.password !== currentPassword) {
      setToast("La contraseña actual no es correcta.");
      return false;
    }
    mirrorToSqlite(() => updateProfile(account.id, { password: newPassword }));
    setDirectory((current) => current.map((employee) => employee.id === account.id ? { ...employee, password: newPassword } : employee));
    setUser({ ...user, password: newPassword });
    setToast("Contraseña actualizada.");
    return true;
  }

  if (screen === "auth") return <>
    <AuthScreen mode={authMode} busy={authBusy} stores={stores} demoAccounts={import.meta.env.DEV ? demoAccounts : []} onDemoLogin={enterDemo} onModeChange={setAuthMode} onLogin={finishLogin} onSignup={finishSignup} onForgotPassword={() => setToast("La recuperación de contraseña estará disponible pronto.")} />
    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
  </>;
  const history = { products, movements, orders };
  return <>
    <OperationsLayout user={user} activeTab={activeTab} expiringCount={expiringProducts.length} pendingCount={waitingOrders.length} onNavigate={setActiveTab} onRegister={() => setActiveTab("register")} onLogout={handleLogout}>
      {isAdmin(user) ? <>
        {activeTab === "profile" ? <ProfilePage user={user} onLogout={handleLogout} onChangePassword={changeEmployeePassword} /> : <AdminPage user={user} profiles={directory} history={history} onSave={saveDirectoryProfile} onDelete={deleteDirectoryProfile} />}
      </> : isCliente(user) ? <>
        {activeTab === "profile" ? <ProfilePage user={user} onLogout={handleLogout} onChangePassword={changeEmployeePassword} /> : <CustomerStockPage products={products} user={user} orders={myOrders} onPlaceOrder={placeOrder} onCancelOrder={cancelCustomerOrder} />}
      </> : <>
      {activeTab === "home" && <HomePage user={user} products={products} expiringProducts={expiringProducts} stockTotal={stockTotal} stockSeries={stockSeries} categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} onRegister={() => setActiveTab("register")} onNavigate={setActiveTab} />}
      {activeTab === "inventory" && <InventoryPage products={products} filteredProducts={filteredProducts} stockTotal={stockTotal} expiringProducts={expiringProducts} query={query} onQueryChange={setQuery} user={user} employees={employees} jefeProfile={jefeProfile} onUpdateProduct={updateProduct} onSetProductActive={setProductActive} onToggleLock={toggleProductLock} onRegister={() => openMethod("text")} />}
      {activeTab === "register" && <RegisterPage products={products} user={user} onSubmit={addProduct} />}
      {activeTab === "sales" && <SalesPage products={products} movements={movements} user={user} onRegisterSale={submitSale} pendingOrders={waitingOrders} onAcceptOrder={acceptCustomerOrder} onRejectOrder={rejectCustomerOrder} />}
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
