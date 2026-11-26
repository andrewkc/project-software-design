import React, { useEffect, useMemo, useRef, useState } from "react";
import { CustomerLayout } from "./components/layout/CustomerLayout";
import { Icon } from "./components/Icon";
import { AuthScreen } from "./features/auth/AuthScreen";
import { HomePage } from "./features/home/HomePage";
import { StoresPage } from "./features/catalog/StoresPage";
import { CartPage } from "./features/cart/CartPage";
import { OrdersPage } from "./features/orders/OrdersPage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { api, getToken, saveToken } from "./lib/api";
import { daysUntilExpiry } from "./lib/catalog";
import { fullName, money, shortName } from "./lib/format";

const emptyFilters = { query: "", minPrice: "", maxPrice: "", priceMode: "none", maxDays: "", storeId: null };

function profileFrom(result, fallback = {}) {
  return result?.profile || result?.perfil || result?.cliente || (result?.correo ? result : fallback);
}

export default function App() {
  const [screen, setScreen] = useState(() => (getToken() ? "app" : "auth"));
  const [user, setUser] = useState(null);
  const [stores, setStores] = useState([]);
  const [offers, setOffers] = useState([]);
  const [paymentMethods, setPaymentMethods] = useState([
    { id: "LOCAL_SIMULATION", label: "Pago local de prueba", detalle: "Aprobación inmediata. La venta y el stock se registran al confirmar.", disponible: true },
    { id: "MERCADOPAGO_TEST", label: "Mercado Pago de prueba", disponible: false },
  ]);
  const [paymentMethod, setPaymentMethod] = useState("LOCAL_SIMULATION");
  const [cart, setCart] = useState([]);
  const [orders, setOrders] = useState([]);
  const [activeOrder, setActiveOrder] = useState(null);
  const [selectedStoreId, setSelectedStoreId] = useState(null);
  const [activeTab, setActiveTab] = useState("home");
  const [authMode, setAuthMode] = useState("login");
  const [filters, setFilters] = useState(emptyFilters);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [toast, setToast] = useState("");
  const [notice, setNotice] = useState(null);
  const pendingKeyRef = useRef(null);

  const cartCount = cart.reduce((sum, line) => sum + line.quantity, 0);
  const cartStoreId = cart.length ? cart[0].store_id : null;

  useEffect(() => {
    let active = true;
    (async () => {
      const [storesResult, offersResult, methodsResult] = await Promise.allSettled([
        api.stores(), api.offers(), api.paymentMethods(),
      ]);
      if (!active) return;
      const offline = storesResult.status === "rejected" || offersResult.status === "rejected";
      if (offline) {
        setLoadError("No se pudo conectar con el backend. No hay catálogo local: vuelve a intentar cuando esté disponible.");
      } else {
        setStores(storesResult.value);
        setOffers(offersResult.value);
      }
      if (methodsResult.status === "fulfilled" && Array.isArray(methodsResult.value?.metodos)) {
        const methods = methodsResult.value.metodos;
        setPaymentMethods(methods);
        if (!methods.some((method) => method.id === paymentMethod && method.disponible)) {
          setPaymentMethod(methods.find((method) => method.disponible)?.id || "LOCAL_SIMULATION");
        }
      }
      if (getToken()) {
        const [meResult, ordersResult] = await Promise.allSettled([api.me(), api.orders()]);
        if (!active) return;
        if (meResult.status === "fulfilled") {
          setUser(profileFrom(meResult.value));
          setScreen("app");
        } else {
          saveToken(null);
          setScreen("auth");
          setLoadError("Tu sesión no se pudo verificar. Inicia sesión de nuevo.");
        }
        if (ordersResult.status === "fulfilled") setOrders(ordersResult.value);
      }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(null), 9000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    if (screen !== "app" || activeOrder?.state !== "pendiente" || !activeOrder?.payment_started) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const updated = await api.verifyPayment(activeOrder.id);
        setActiveOrder(updated);
        if (updated.state === "pagado") {
          setCart([]);
          pendingKeyRef.current = null;
          await reloadOrders();
        }
      } catch {
        // La comprobación en segundo plano no interrumpe la navegación.
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [screen, activeOrder?.id, activeOrder?.state, activeOrder?.payment_started]);

  async function reloadOrders() {
    try {
      setOrders(await api.orders());
    } catch {
      // Se conserva el historial ya cargado.
    }
  }

  async function authenticate(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    try {
      const result = authMode === "login" ? await api.login(data) : await api.register(data);
      saveToken(result.token);
      setUser(profileFrom(result, data));
      setScreen("app");
      setActiveTab(cart.length ? "cart" : "home");
      setToast(`¡Bienvenido, ${shortName(profileFrom(result, data)).split(" ")[0] || "cliente"}!`);
      await reloadOrders();
    } catch (error) {
      setToast(error.message || "No se pudo iniciar sesión.");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    saveToken(null);
    setUser(null);
    setCart([]);
    setOrders([]);
    setActiveOrder(null);
    setSelectedStoreId(null);
    setFilters(emptyFilters);
    setScreen("auth");
    setAuthMode("login");
    setActiveTab("home");
  }

  function addToCart(offer, replaceCart = false) {
    const days = daysUntilExpiry(offer.expiry_date);
    if (days === null || days < 0 || Number(offer.available) <= 0) {
      setToast("Este producto ya no está disponible.");
      return;
    }
    if (cartStoreId && cartStoreId !== offer.store_id && !replaceCart) {
      setNotice({ text: "Tu cesta contiene productos de otra bodega. Puedes vaciarla para comprar aquí.", actionLabel: "Vaciar cesta y agregar", onAction: () => addToCart(offer, true) });
      return;
    }
    const current = cart.find((line) => line.id === offer.id);
    if ((current?.quantity || 0) >= Number(offer.available)) {
      setToast("No quedan más unidades disponibles.");
      return;
    }
    setCart((previous) => replaceCart ? [{ ...offer, quantity: 1 }] : current
      ? previous.map((line) => line.id === offer.id ? { ...line, quantity: line.quantity + 1 } : line)
      : [...previous, { ...offer, quantity: 1 }]);
    setNotice(null);
    setToast(`${offer.product_name} se agregó a tu cesta.`);
  }

  function changeQuantity(id, quantity) {
    if (quantity < 1) {
      removeFromCart(id);
      return;
    }
    const offer = offers.find((item) => item.id === id) || cart.find((item) => item.id === id);
    if (quantity > Number(offer?.available || 0)) {
      setToast("No hay suficientes unidades disponibles.");
      return;
    }
    setCart((previous) => previous.map((line) => line.id === id ? { ...line, quantity } : line));
  }

  function removeFromCart(id) {
    setCart((previous) => previous.filter((line) => line.id !== id));
  }

  async function placeOrder() {
    if (!cart.length) { setToast("Agrega un producto antes de continuar."); return; }
    if (!user) { setAuthMode("login"); setScreen("auth"); setToast("Ingresa para continuar con tu compra."); return; }
    setBusy(true);
    const key = pendingKeyRef.current || crypto.randomUUID();
    try {
      const order = await api.createOrder({
        idempotency_key: key,
        metodo_pago: paymentMethod,
        lines: cart.map((line) => ({ offer_id: line.id, quantity: line.quantity })),
      });
      pendingKeyRef.current = key;
      setActiveOrder(order);
      setActiveTab("orders");
      setNotice(null);
      await reloadOrders();
      setToast("Pedido creado. Completa el pago para confirmarlo.");
    } catch (error) {
      setToast(error.message || "No se pudo crear el pedido.");
    } finally {
      setBusy(false);
    }
  }

  async function pay() {
    if (!activeOrder) return;
    setBusy(true);
    try {
      if (activeOrder.payment_mode === "MERCADOPAGO_TEST") {
        const result = await api.checkout(activeOrder.id);
        const updated = await api.order(activeOrder.id);
        setActiveOrder(updated);
        await reloadOrders();
        if (!result?.checkout_url) throw new Error("Mercado Pago no devolvió una URL de pago.");
        const paymentTab = window.open(result.checkout_url, "bodesmart-mercadopago");
        if (paymentTab) paymentTab.opener = null;
        else window.location.assign(result.checkout_url);
        setToast("Completa el pago de prueba en Mercado Pago y vuelve aquí. Comprobaremos el resultado automáticamente.");
      } else {
        const updated = await api.simulatePayment(activeOrder.id);
        setActiveOrder(updated);
        setCart([]);
        pendingKeyRef.current = null;
        await reloadOrders();
        setToast("Pago aprobado. ¡Compra confirmada!");
      }
    } catch (error) {
      setToast(error.message || "No se pudo procesar el pago.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshOrder() {
    if (!activeOrder) return;
    try {
      const updated = activeOrder.payment_started ? await api.verifyPayment(activeOrder.id) : await api.order(activeOrder.id);
      setActiveOrder(updated);
      if (updated.state === "pagado") { setCart([]); pendingKeyRef.current = null; await reloadOrders(); }
    } catch (error) {
      setToast(error.message || "No se pudo comprobar el estado del pedido.");
    }
  }

  function changePaymentMethod(id) {
    setPaymentMethod(id);
    pendingKeyRef.current = null;
  }

  function navigate(tab) {
    if (tab !== "orders") setActiveOrder(null);
    if (tab !== "stores") setSelectedStoreId(null);
    setActiveTab(tab);
  }

  const profile = user || { nombres: "Cliente", apellidos: "" };

  if (screen === "auth") return <>
    <AuthScreen mode={authMode} busy={busy} onModeChange={setAuthMode} onLogin={authenticate} onSignup={authenticate} />
    {loadError && <div className="auth-error" role="alert">{loadError}</div>}
    {toast && <Toast text={toast} />}
  </>;

  if (loading) return <main className="signup-shell"><div className="toast-message" role="status">Cargando la tienda...</div></main>;

  return <>
    <CustomerLayout user={profile} activeTab={activeTab} cartCount={cartCount} onNavigate={navigate}>
      {loadError && <div className="auth-error" role="alert">{loadError}</div>}
      {activeTab === "home" && <HomePage user={profile} stores={stores} offers={offers} filters={filters} onFiltersChange={setFilters} onClearFilters={() => setFilters(emptyFilters)} onAdd={addToCart} onNavigate={navigate} onOpenStore={(id) => { setSelectedStoreId(id); setActiveTab("stores"); }} onCart={() => navigate("cart")} cartCount={cartCount} />}
      {activeTab === "stores" && <StoresPage stores={stores} offers={offers} selectedStoreId={selectedStoreId} onOpenStore={setSelectedStoreId} onBack={() => setSelectedStoreId(null)} onAdd={addToCart} onCart={() => navigate("cart")} cartCount={cartCount} />}
      {activeTab === "cart" && <CartPage cart={cart} stores={stores} onChangeQuantity={changeQuantity} onRemove={removeFromCart} onCheckout={placeOrder} onNavigate={navigate} user={user} busy={busy} paymentMethods={paymentMethods} paymentMethod={paymentMethod} onPaymentMethodChange={changePaymentMethod} />}
      {activeTab === "orders" && <OrdersPage orders={orders} activeOrder={activeOrder} busy={busy} stores={stores} onSelectOrder={setActiveOrder} onBack={() => setActiveOrder(null)} onPay={pay} onVerify={refreshOrder} onNavigate={navigate} />}
      {activeTab === "profile" && <ProfilePage user={profile} orderCount={orders.filter((order) => order.state === "pagado").length} onLogout={logout} onNavigate={navigate} />}
    </CustomerLayout>
    {notice && <div className="toast-message notice-toast" role="status"><span><Icon name="info" size={17} /></span><span>{notice.text}</span>{notice.actionLabel && <button className="toast-action" type="button" onClick={notice.onAction}>{notice.actionLabel}</button>}<button className="toast-close" type="button" aria-label="Cerrar aviso" onClick={() => setNotice(null)}><Icon name="close" size={15} /></button></div>}
    {toast && <Toast text={toast} />}
  </>;
}

function Toast({ text }) {
  return <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{text}</div>;
}
