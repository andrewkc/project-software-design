import React, { useCallback, useEffect, useState } from "react";
import { OperationsLayout } from "./components/layout/OperationsLayout";
import { productMethods } from "./data/demoData";
import { useInventorySummary } from "./hooks/useInventorySummary";
import { AuthScreen } from "./features/auth/AuthScreen";
import { HomePage } from "./features/home/HomePage";
import { InventoryPage } from "./features/inventory/InventoryPage";
import { AlertsPage } from "./features/alerts/AlertsPage";
import { InsightsPage } from "./features/insights/InsightsPage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { ProductModal } from "./features/products/ProductModal";
import { useProductDraft } from "./features/products/useProductDraft";
import { RegisterPage } from "./features/register/RegisterPage";
import { EmployeesPage } from "./features/employees/EmployeesPage";
import { RecommendationsPage } from "./features/recommendations/RecommendationsPage";
import { SalesPage } from "./features/sales/SalesPage";
import { Icon } from "./components/Icon";
import { workspaceCopy } from "./lib/workspaceCopy";
import { api, clearToken, getToken, setToken, toProduct, toProfile, toUser } from "./lib/api";

function App() {
  const [screen, setScreen] = useState(() => (getToken() ? "app" : "auth"));
  const [user, setUser] = useState(null);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [jefeProfile, setJefeProfile] = useState(null);
  const [sales, setSales] = useState([]);
  const [aiModels, setAiModels] = useState([]);
  const [loading, setLoading] = useState(() => Boolean(getToken()));
  const [authMode, setAuthMode] = useState("login");
  const [authBusy, setAuthBusy] = useState(false);
  const [activeTab, setActiveTab] = useState("home");
  const [method, setMethod] = useState(null);
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");
  const [recommendations, setRecommendations] = useState({ items: [], generatedAt: "", hasGenerated: false });
  const draft = useProductDraft();

  const { expiringProducts, stockTotal, categoryTotals, stockSeries } = useInventorySummary(products);
  const maxCategoryTotal = Math.max(...categoryTotals.map(([, total]) => total), 1);

  // Sales and stock change in another app. Reload them instead of trusting a
  // snapshot taken when the manager signed in.
  const refreshData = useCallback(async () => {
    if (!getToken()) return;
    const [productsResult, categoriesResult, salesResult] = await Promise.allSettled([
      api.listProducts(),
      api.listCategories(),
      api.listSales(),
    ]);
    if (productsResult.status === "fulfilled") setProducts(productsResult.value.map(toProduct));
    if (categoriesResult.status === "fulfilled") setCategories(categoriesResult.value);
    if (salesResult.status === "fulfilled") setSales(salesResult.value);
    if (user?.role === "jefe") {
      try {
        const profiles = (await api.listProfiles()).map(toProfile);
        setEmployees(profiles.filter((profile) => profile.role === "empleado"));
        setJefeProfile(profiles.find((profile) => profile.role === "jefe") || null);
      } catch {
        // El historial y el inventario ya se actualizaron; se conserva lo demás.
      }
    }
  }, [user?.role]);

  useEffect(() => {
    if (screen !== "app" || !getToken()) {
      setLoading(false);
      return undefined;
    }
    let active = true;
    setLoading(true);
    Promise.all([
      api.getMe(),
      api.listProducts(),
      api.listCategories().catch(() => []),
      api.listSales(),
      api.listAiModels().catch(() => ({ modelos: [], default: "" })),
    ])
      .then(async ([me, productRows, categoryRows, saleRows, modelRows]) => {
        if (!active) return;
        const current = toUser(me);
        setUser(current);
        setProducts(productRows.map(toProduct));
        setCategories(categoryRows);
        setSales(saleRows);
        const availableModels = Array.isArray(modelRows?.modelos) ? modelRows.modelos : [];
        setAiModels(availableModels);
        const defaultModel = modelRows?.default || availableModels[0]?.id || "";
        draft.setAiModel((current) => current || defaultModel);
        if (current.role === "jefe") {
          const profileRows = await api.listProfiles();
          if (!active) return;
          const profiles = profileRows.map(toProfile);
          setEmployees(profiles.filter((profile) => profile.role === "empleado"));
          setJefeProfile(profiles.find((profile) => profile.role === "jefe") || null);
        }
        setScreen("app");
      })
      .catch((error) => {
        if (!active) return;
        setToast(error.message || "No se pudo cargar la información.");
        if (error.status === 401) handleLogout();
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [screen]);

  useEffect(() => {
    if (screen !== "app" || loading || !getToken()) return undefined;
    const onFocus = () => { refreshData(); };
    window.addEventListener("focus", onFocus);
    const timer = window.setInterval(() => {
      if (!document.hidden) refreshData();
    }, 15000);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.clearInterval(timer);
    };
  }, [screen, loading, refreshData]);

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
    setAuthBusy(true);
    try {
      const result = await api.signup({
        nombres,
        apellidos,
        correo: String(data.get("email") || "").trim().toLowerCase(),
        password: data.get("password") || "",
        nombre_bodega: String(data.get("store") || "").trim(),
      });
      setToken(result.token);
      setUser(toUser(result.perfil));
      setScreen("app");
      setActiveTab("home");
      setToast(`¡Bienvenido, ${nombres}! Tu bodega está lista.`);
    } catch (error) {
      setToast(error.message || "No se pudo crear la cuenta.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function finishLogin(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setAuthBusy(true);
    try {
      const result = await api.login({
        correo: String(data.get("email") || "").trim().toLowerCase(),
        password: data.get("password") || "",
      });
      setToken(result.token);
      setUser(toUser(result.perfil));
      setScreen("app");
      setActiveTab("home");
      setToast(`¡Bienvenido, ${toUser(result.perfil)?.name?.split(" ")[0] || ""}!`);
    } catch (error) {
      setToast(error.message || "Correo o contraseña incorrectos.");
    } finally {
      setAuthBusy(false);
    }
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setProducts([]);
    setCategories([]);
    setEmployees([]);
    setJefeProfile(null);
    setRecommendations({ items: [], generatedAt: "", hasGenerated: false });
    draft.clear();
    setScreen("auth");
    setAuthMode("login");
    setActiveTab("home");
    setQuery("");
  }

  function openMethod(id) {
    setMethod(id);
    draft.clear();
  }

  function productChanges(changes) {
    const payload = {};
    if (changes.name !== undefined) payload.nombre = changes.name;
    if (changes.category !== undefined) payload.categoria = changes.category;
    if (changes.stock !== undefined) payload.stock = Number(changes.stock);
    if (changes.unit !== undefined) payload.unidad_medida = changes.unit;
    if (changes.price !== undefined) payload.precio_venta = Number(changes.price);
    if (changes.expires !== undefined) payload.fecha_vencimiento = changes.expires || null;
    if (changes.activo !== undefined) payload.estado = changes.activo ? "activo" : "inactivo";
    if (changes.bloqueado !== undefined) payload.bloqueado = changes.bloqueado;
    return payload;
  }

  async function addCategory(nombre) {
    const created = await api.createCategory({ nombre });
    const value = typeof created === "string" ? created : created?.nombre;
    if (!value) throw new Error("No se pudo agregar la categoría.");
    setCategories((current) => (
      current.some((item) => item.toLocaleLowerCase("es") === String(value).toLocaleLowerCase("es"))
        ? current
        : [...current, value]
    ));
    return value;
  }

  async function addProduct(values) {
    const name = String(values?.productName || "").trim();
    const quantity = Number(values?.quantity);
    if (!name || !Number.isFinite(quantity) || quantity < 1) {
      setToast("Ingresa un nombre y una cantidad positiva.");
      return;
    }
    try {
      const created = await api.createProduct({
        icono: values.icon || "📦",
        nombre: name,
        categoria: values.category || "Abarrotes",
        unidad_medida: values.unit || "unid.",
        stock: quantity,
        precio_venta: Number(values.price) || 0,
        fecha_vencimiento: values.expires || null,
      });
      setProducts((current) => [toProduct(created), ...current]);
      setMethod(null);
      draft.clear();
      setActiveTab("inventory");
      setToast(`${name} se agregó a ${workspaceCopy(user).addedTarget}.`);
    } catch (error) {
      setToast(error.message || "No se pudo registrar el producto.");
    }
  }

  async function patchProduct(id, changes) {
    try {
      const updated = await api.updateProduct(id, productChanges(changes));
      setProducts((current) => current.map((product) => product.id === id ? toProduct(updated) : product));
      return true;
    } catch (error) {
      setToast(error.message || "No se pudo guardar el cambio.");
      return false;
    }
  }

  async function updateProduct(id, changes) {
    if (await patchProduct(id, changes)) setToast("Cambios guardados.");
  }

  async function setProductActive(id, activo) {
    if (await patchProduct(id, { activo })) setToast(activo ? "Producto reactivado." : "Producto desactivado. Su historial se conserva.");
  }

  async function toggleProductLock(id) {
    const target = products.find((product) => product.id === id);
    if (!target) return;
    const bloqueado = !target.bloqueado;
    if (await patchProduct(id, { bloqueado })) setToast(bloqueado ? "Fila bloqueada. Solo tú puedes editarla." : "Fila desbloqueada.");
  }

  async function createEmployee(event, password) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const nombres = String(data.get("nombres") || "").trim();
    const apellidos = String(data.get("apellidos") || "").trim();
    const name = `${nombres} ${apellidos}`.trim();
    const email = String(data.get("email") || "").trim().toLowerCase();
    if (!name || !email || !password || password.length < 8) return false;
    try {
      const created = await api.createEmployee({ nombres, apellidos, correo: email, password });
      setEmployees((current) => [...current, toProfile(created)]);
      form.reset();
      setToast(`Cuenta de ${name} creada. Entrega las credenciales al empleado.`);
      return true;
    } catch (error) {
      setToast(error.message || "No se pudo crear la cuenta.");
      return false;
    }
  }

  async function revokeEmployee(id) {
    const target = employees.find((employee) => employee.id === id);
    if (!target || target.activo === false) return;
    if (!window.confirm(`¿Revocar el acceso de ${target.name}? Sus registros se conservarán y sus filas quedarán bloqueadas.`)) return;
    try {
      await api.revokeEmployee(id);
      setEmployees((current) => current.map((employee) => employee.id === id ? { ...employee, activo: false } : employee));
      setProducts((current) => current.map((product) => product.creadoPor === id ? { ...product, bloqueado: true, bloqueadoPor: user?.id || null } : product));
      setToast("Acceso revocado. Las filas del empleado quedaron bloqueadas.");
    } catch (error) {
      setToast(error.message || "No se pudo revocar el acceso.");
    }
  }

  async function changeEmployeePassword(currentPassword, newPassword) {
    if (user?.role !== "empleado" || !newPassword || newPassword.length < 8) return false;
    try {
      await api.changePassword({ password_actual: currentPassword, password_nueva: newPassword });
      setToast("Contraseña actualizada.");
      return true;
    } catch (error) {
      setToast(error.message || "La contraseña actual no es correcta.");
      return false;
    }
  }

  if (screen === "auth") return <>
    <AuthScreen mode={authMode} busy={authBusy} onModeChange={setAuthMode} onLogin={finishLogin} onSignup={finishSignup} onForgotPassword={() => setToast("La recuperación de contraseña estará disponible pronto.")} />
    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
  </>;

  if (loading && !user) return <main className="signup-shell"><div className="toast-message" role="status">Cargando información de la bodega...</div></main>;

  return <>
    <OperationsLayout user={user} activeTab={activeTab} expiringCount={expiringProducts.length} onNavigate={setActiveTab} onRegister={() => setActiveTab("register")} onLogout={handleLogout}>
      {activeTab === "home" && <HomePage user={user} products={products} expiringProducts={expiringProducts} stockTotal={stockTotal} stockSeries={stockSeries} categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} onRegister={() => setActiveTab("register")} onNavigate={setActiveTab} />}
      {activeTab === "inventory" && <InventoryPage products={products} categories={categories} stockTotal={stockTotal} expiringProducts={expiringProducts} query={query} onQueryChange={setQuery} user={user} employees={employees} jefeProfile={jefeProfile} onUpdateProduct={updateProduct} onSetProductActive={setProductActive} onToggleLock={toggleProductLock} onRefresh={refreshData} onRegister={() => openMethod("text")} />}
      {activeTab === "register" && <RegisterPage products={products} user={user} onSubmit={addProduct} draft={draft} categories={categories} onCreateCategory={addCategory} aiModels={aiModels} />}
      {activeTab === "alerts" && <AlertsPage expiringProducts={expiringProducts} />}
      {activeTab === "sales" && <SalesPage sales={sales} onRefresh={refreshData} />}
      {activeTab === "insights" && <InsightsPage />}
      {activeTab === "employees" && <EmployeesPage employees={employees} onCreateEmployee={createEmployee} onRevokeEmployee={revokeEmployee} />}
      {activeTab === "recommendations" && <RecommendationsPage user={user} recommendations={recommendations} onRecommendationsChange={setRecommendations} onApplyPrice={patchProduct} onNotify={setToast} />}
      {activeTab === "profile" && <ProfilePage user={user} onLogout={handleLogout} onChangePassword={changeEmployeePassword} />}
    </OperationsLayout>
    {method && <ProductModal method={productMethods.find((item) => item.id === method)} user={user} onClose={() => { setMethod(null); draft.clear(); }} onSubmit={addProduct} draft={draft} categories={categories} onCreateCategory={addCategory} aiModels={aiModels} />}
    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
  </>;
}

export default App;
