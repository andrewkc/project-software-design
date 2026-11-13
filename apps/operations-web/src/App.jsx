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
import { ProductModal } from "./features/products/ProductModal";
import { Icon } from "./components/Icon";

function App() {
  // console.log("DEBGUG 1");
  const [user, setUser] = useState(() => readSaved("bodega-user", null));
  const [products, setProducts] = useState(() => {
    const savedProducts = readSaved("bodega-products", starterProducts);
    return Array.isArray(savedProducts) ? savedProducts : starterProducts;
  });
  const [screen, setScreen] = useState(() => sessionStorage.getItem("bodega-screen") === "app" ? "app" : "auth");
  const [authMode, setAuthMode] = useState("login"); // by default
  const [activeTab, setActiveTab] = useState("home"); //  by default
  const [method, setMethod] = useState(null); // can be text, voice, photo, barcode
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
  useEffect(() => { sessionStorage.setItem("bodega-screen", screen); }, [screen]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function finishSignup(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const profile = { name: data.get("name").trim(), email: data.get("email").trim(), store: data.get("store").trim() };
    setUser(profile);
    setScreen("app");
    setToast(`\u00a1Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}! Tu bodega est\u00e1 lista.`);
  }

  function finishLogin(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const savedProfile = readSaved("bodega-user", null);
    const profile = savedProfile || { name: "Mar\u00eda", email: data.get("email").trim(), store: "Bodega San Mart\u00edn" };
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
    setProducts((current) => [{ id: Date.now(), name, category, icon, stock: quantity, unit: data.get("unit"), price: Number(data.get("price")) || 0, expires: data.get("expires") || "" }, ...current]);
    setMethod(null);
    setActiveTab("inventory");
    setToast(`${name} se agreg\u00f3 a tu inventario.`);
  }
  
  if (screen === "auth") return <AuthScreen mode={authMode} onModeChange={setAuthMode} onLogin={finishLogin} onSignup={finishSignup} onForgotPassword={() => setToast("La recuperaci\u00f3n de contrase\u00f1a estar\u00e1 disponible pronto.")} />;
  return <>
    <OperationsLayout user={user} activeTab={activeTab} expiringCount={expiringProducts.length} onNavigate={setActiveTab} onRegister={() => openMethod("text")} onLogout={handleLogout}>
      {activeTab === "home" && <HomePage user={user} products={products} expiringProducts={expiringProducts} stockTotal={stockTotal} stockSeries={stockSeries} categoryTotals={categoryTotals} maxCategoryTotal={maxCategoryTotal} onRegister={() => openMethod("text")} onNavigate={setActiveTab} />}
      {activeTab === "inventory" && <InventoryPage products={products} filteredProducts={filteredProducts} stockTotal={stockTotal} expiringProducts={expiringProducts} query={query} onQueryChange={setQuery} onRegister={() => openMethod("text")} />}
      {activeTab === "alerts" && <AlertsPage expiringProducts={expiringProducts} />}
      {activeTab === "insights" && <InsightsPage />}
    </OperationsLayout>
    {method && <ProductModal method={productMethods.find((item) => item.id === method)} onClose={() => setMethod(null)} onSubmit={addProduct} voiceCaptured={voiceCaptured} setVoiceCaptured={setVoiceCaptured} photoName={photoName} setPhotoName={setPhotoName} barcode={barcode} setBarcode={setBarcode} />}
    {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
  </>;
}

export default App;
