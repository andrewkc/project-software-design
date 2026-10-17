import React, { useEffect, useMemo, useState } from "react";

const starterProducts = [
  { id: 1, name: "Leche Gloria entera", category: "Lácteos", icon: "🥛", stock: 8, unit: "unid.", price: 4.5, expires: "2026-10-20" },
  { id: 2, name: "Yogurt natural", category: "Lácteos", icon: "🥣", stock: 5, unit: "unid.", price: 3.8, expires: "2026-10-21" },
  { id: 3, name: "Plátano de seda", category: "Frutas", icon: "🍌", stock: 12, unit: "kg", price: 3.5, expires: "2026-10-22" },
  { id: 4, name: "Arroz extra", category: "Abarrotes", icon: "🍚", stock: 24, unit: "unid.", price: 4.2, expires: "2027-06-10" },
];

const methods = [
  { id: "photo", title: "Toma una foto", subtitle: "De tu mercadería o boleta", icon: "camera", tint: "peach", tag: "Con imagen" },
  { id: "voice", title: "Habla para registrar", subtitle: "Cuéntanos qué ingresó", icon: "mic", tint: "lavender", tag: "Manos libres" },
  { id: "text", title: "Escribe para registrar", subtitle: "Agrega los datos a tu ritmo", icon: "edit", tint: "mint", tag: "Manual" },
  { id: "scan", title: "Escanea un producto", subtitle: "Usa el código de barras", icon: "scan", tint: "yellow", tag: "Código de barras" },
];

const navigation = [
  { id: "home", label: "Inicio", icon: "home" },
  { id: "inventory", label: "Inventario", icon: "box" },
  { id: "alerts", label: "Vencimientos", icon: "calendar" },
  { id: "insights", label: "Ideas para tu negocio", icon: "sparkles" },
];

const iconPaths = {
  home: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-6h6v6" /></>,
  box: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="M3 8v9l9 5 9-5V8M12 13v9" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M16 3v4M8 3v4M3 10h18m-13 5h2" /></>,
  sparkles: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14ZM5 15l.8 1.7L7.5 17.5l-1.7.8L5 20l-.8-1.7-1.7-.8 1.7-.8L5 15Z" /></>,
  camera: <><path d="M4 7h3l2-3h6l2 3h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z" /><circle cx="12" cy="13" r="3.5" /></>,
  mic: <><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8" /></>,
  edit: <><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" /></>,
  scan: <><path d="M4 7V5a1 1 0 0 1 1-1h2m11 0h1a1 1 0 0 1 1 1v2m0 10v2a1 1 0 0 1-1 1h-2m-11 0H5a1 1 0 0 1-1-1v-2M4 12h16" /><path d="M8 9v6m3-6v6m3-6v6m3-6v6" /></>,
  arrow: <><path d="M5 12h14m-6-6 6 6-6 6" /></>,
  plus: <><path d="M12 5v14m-7-7h14" /></>,
  search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4 4" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 12h4" /></>,
  close: <><path d="m18 6-12 12M6 6l12 12" /></>,
  check: <><path d="m5 12 4 4L19 6" /></>,
  back: <><path d="m15 18-6-6 6-6" /></>,
  leaf: <><path d="M20 4c-7 0-14 3-14 10a6 6 0 0 0 6 6c7 0 10-7 8-16Z" /><path d="M4 21c3-6 7-9 12-12" /></>,
  trending: <><path d="m3 17 6-6 4 4 8-9m-6 0h6v6" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm10 10v-2a4 4 0 0 0-3-3.9m-1-12a4 4 0 0 1 0 7.8" /></>,
  upload: <><path d="M12 16V4m-5 5 5-5 5 5M4 20h16" /></>,
  shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
};

function Icon({ name, size = 20, strokeWidth = 1.8, className = "" }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {iconPaths[name] || iconPaths.sparkles}
    </svg>
  );
}

function readSaved(key, fallback) {
  const value = localStorage.getItem(key);
  return value ? JSON.parse(value) : fallback;
}

function App() {
  const [user, setUser] = useState(() => readSaved("bodega-user", null));
  const [products, setProducts] = useState(() => readSaved("bodega-products", starterProducts));
  const [screen, setScreen] = useState(() => sessionStorage.getItem("bodega-screen") || "signup");
  const [activeTab, setActiveTab] = useState("home");
  const [method, setMethod] = useState(null);
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");
  const [suggestionVisible, setSuggestionVisible] = useState(true);
  const [priceReview, setPriceReview] = useState(false);
  const [voiceCaptured, setVoiceCaptured] = useState(false);
  const [photoName, setPhotoName] = useState("");
  const [barcode, setBarcode] = useState("");

  useEffect(() => localStorage.setItem("bodega-products", JSON.stringify(products)), [products]);
  useEffect(() => {
    if (user) localStorage.setItem("bodega-user", JSON.stringify(user));
  }, [user]);
  useEffect(() => {
    sessionStorage.setItem("bodega-screen", screen);
  }, [screen]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const expiringProducts = useMemo(() => products.filter((product) => {
    if (!product.expires) return false;
    const days = Math.ceil((new Date(`${product.expires}T00:00:00`) - new Date(new Date().toDateString())) / 86400000);
    return days >= 0 && days <= 7;
  }), [products]);
  const lowStockProducts = products.filter((product) => product.stock <= 8);
  const discountCandidate = expiringProducts.find((product) => Number(product.price) > 0);
  const filteredProducts = products.filter((product) => product.name.toLowerCase().includes(query.toLowerCase()));
  const stockTotal = products.reduce((total, product) => total + Number(product.stock), 0);

  function finishSignup(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const profile = {
      name: data.get("name").trim(),
      email: data.get("email").trim(),
      store: data.get("store").trim(),
    };
    setUser(profile);
    setScreen("app");
    setToast(`¡Bienvenido${profile.name ? `, ${profile.name.split(" ")[0]}` : ""}! Tu bodega está lista.`);
  }

  function addProduct(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = data.get("productName").trim();
    const quantity = Number(data.get("quantity"));
    if (!name || quantity < 1) return;
    setProducts((current) => [{
      id: Date.now(),
      name,
      category: data.get("category"),
      icon: data.get("category") === "Frutas" ? "🍎" : data.get("category") === "Lácteos" ? "🥛" : "📦",
      stock: quantity,
      unit: data.get("unit"),
      price: Number(data.get("price")) || 0,
      expires: data.get("expires") || "",
    }, ...current]);
    setMethod(null);
    setActiveTab("inventory");
    setToast(`${name} se agregó a tu inventario.`);
  }

  function openMethod(id) {
    setMethod(id);
    setVoiceCaptured(false);
    setPhotoName("");
    setBarcode("");
  }

  function approvePriceSuggestion(price) {
    setPriceReview(false);
    setSuggestionVisible(false);
    setToast(`Propuesta de S/ ${price} para ${discountCandidate.name} aprobada en esta demo; el precio real no cambió.`);
  }

  function dismissPriceSuggestion() {
    setPriceReview(false);
    setSuggestionVisible(false);
    setToast("Sugerencia descartada. El precio de venta no cambió.");
  }

  if (screen === "signup") {
    return (
      <main className="signup-shell">
        <section className="signup-art" aria-label="Presentación de Bodega Clara">
          <a className="brand brand-light" href="#" onClick={(event) => event.preventDefault()}>
            <span className="brand-mark"><Icon name="leaf" size={23} /></span>
            <span>Bodega<span className="brand-accent">Clara</span></span>
          </a>
          <div className="art-copy">
            <span className="eyebrow">MENOS PREOCUPACIONES, MÁS CONTROL</span>
            <h1>Tu bodega,<br />en orden.</h1>
            <p>Todo lo que entra, lo que sale y lo que está por vencer. En un solo lugar, sin complicarte.</p>
          </div>
          <div className="art-note">
            <span className="note-icon"><Icon name="bell" size={19} /></span>
            <span><strong>Que no se te pase la fecha</strong><small>Recibe alertas a tiempo y cuida tu inversión.</small></span>
          </div>
          <span className="art-orb orb-one" /><span className="art-orb orb-two" />
        </section>
        <section className="signup-panel">
          <div className="signup-form-wrap">
            <div className="mobile-brand"><a className="brand" href="#" onClick={(event) => event.preventDefault()}><span className="brand-mark"><Icon name="leaf" size={21} /></span><span>Bodega<span className="brand-accent">Clara</span></span></a></div>
            <div className="step-indicator"><span className="step-current" /><span /><span /></div>
            <p className="form-kicker">EMPECEMOS POR LO BÁSICO</p>
            <h2>Crea tu cuenta</h2>
            <p className="form-intro">Así podremos preparar el espacio de tu negocio.</p>
            <form className="signup-form" onSubmit={finishSignup}>
              <label>¿Cómo te llamas?<input name="name" type="text" placeholder="Tu nombre" autoComplete="name" required /></label>
              <label>Correo electrónico<input name="email" type="email" placeholder="tunombre@correo.com" autoComplete="email" required /></label>
              <label>Nombre de tu bodega<input name="store" type="text" placeholder="Ej. Bodega San Martín" required /></label>
              <label>Crea una contraseña<input name="password" type="password" placeholder="Mínimo 8 caracteres" minLength="8" autoComplete="new-password" required /></label>
              <button className="button button-primary button-full" type="submit">Crear mi cuenta <Icon name="arrow" size={18} /></button>
            </form>
            <p className="terms-copy">Al continuar, aceptas nuestros <a href="#terminos" onClick={(event) => event.preventDefault()}>Términos de uso</a> y <a href="#privacidad" onClick={(event) => event.preventDefault()}>Política de privacidad</a>.</p>
            <div className="signup-login">¿Ya tienes una cuenta? <button type="button" onClick={() => { setUser({ name: "María", email: "maria@bodega.pe", store: "Bodega San Martín" }); setScreen("app"); }}>Ingresa a la demo</button></div>
          </div>
          <span className="prototype-note"><Icon name="shield" size={15} /> Prototipo académico · tus datos se quedan en este dispositivo</span>
        </section>
      </main>
    );
  }

  const title = navigation.find((item) => item.id === activeTab)?.label || "Inicio";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand sidebar-brand" href="#" onClick={(event) => event.preventDefault()}>
          <span className="brand-mark"><Icon name="leaf" size={22} /></span>
          <span>Bodega<span className="brand-accent">Clara</span></span>
        </a>
        <div className="store-switcher"><span className="store-avatar">B</span><span className="store-label"><strong>{user?.store || "Mi bodega"}</strong><small>Mi negocio</small></span><span className="switch-arrow">⌄</span></div>
        <span className="nav-caption">MENÚ PRINCIPAL</span>
        <nav className="side-nav" aria-label="Navegación principal">
          {navigation.map((item) => (
            <button key={item.id} type="button" className={`nav-link ${activeTab === item.id ? "active" : ""}`} onClick={() => setActiveTab(item.id)}>
              <Icon name={item.icon} size={19} /><span>{item.label}</span>
              {item.id === "alerts" && expiringProducts.length > 0 && <span className="nav-count">{expiringProducts.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-help">
          <span className="help-illustration"><Icon name="sparkles" size={21} /></span>
          <strong>Un paso a la vez</strong>
          <p>Registra tus productos y mantén tu inventario al día.</p>
          <button type="button" onClick={() => openMethod("text")}>Agregar producto <Icon name="arrow" size={15} /></button>
        </div>
        <button className="profile-card" type="button" onClick={() => { setScreen("signup"); setActiveTab("home"); }}>
          <span className="profile-avatar">{(user?.name || "M").charAt(0).toUpperCase()}</span>
          <span><strong>{user?.name || "María López"}</strong><small>Jefa de bodega</small></span>
          <span className="profile-dots">···</span>
        </button>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Mi negocio</span><span className="breadcrumb-slash">/</span><strong>{title}</strong></div>
          <div className="topbar-actions">
            <span className="today-label">{new Intl.DateTimeFormat("es-PE", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</span>
            <button type="button" className="icon-button notification-button" aria-label="Notificaciones" onClick={() => setActiveTab("alerts")}><Icon name="bell" size={19} />{expiringProducts.length > 0 && <i />}</button>
            <span className="top-avatar">{(user?.name || "M").charAt(0).toUpperCase()}</span>
          </div>
        </header>

        {activeTab === "home" && (
          <div className="page-content">
            <section className="welcome-row">
              <div><p className="date-greeting">TU ESPACIO, MÁS ORDENADO</p><h1>¡Hola, {user?.name?.split(" ")[0] || "María"}! <span className="wave">✳</span></h1><p className="welcome-subtitle">Un vistazo rápido a cómo va <strong>{user?.store || "tu bodega"}</strong> hoy.</p></div>
              <button type="button" className="button button-primary add-top-button" onClick={() => document.getElementById("register-section")?.scrollIntoView({ behavior: "smooth" })}><Icon name="plus" size={18} /> Registrar mercadería</button>
            </section>

            <section className="stats-grid" aria-label="Resumen de tu negocio">
              <article className="stat-card"><span className="stat-icon stat-green"><Icon name="box" size={19} /></span><span className="stat-label">Productos en inventario</span><strong className="stat-number">{products.length}</strong><span className="stat-hint">en tu catálogo</span></article>
              <article className="stat-card"><span className="stat-icon stat-lilac"><Icon name="trending" size={19} /></span><span className="stat-label">Unidades disponibles</span><strong className="stat-number">{stockTotal}</strong><span className="stat-hint">sumando todos tus productos</span></article>
              <article className={`stat-card ${expiringProducts.length > 0 ? "stat-warn" : ""}`}><span className="stat-icon stat-amber"><Icon name="clock" size={19} /></span><span className="stat-label">Por vencer pronto</span><strong className="stat-number">{expiringProducts.length}</strong><span className="stat-hint">en los próximos 7 días</span></article>
            </section>

            <section className="register-section" id="register-section">
              <div className="section-heading"><div><span className="section-kicker">RÁPIDO Y SENCILLO</span><h2>¿Cómo quieres registrar?</h2><p>Elige la forma que te quede más cómoda.</p></div><span className="ai-badge"><Icon name="sparkles" size={14} /> Asistente inteligente</span></div>
              <div className="method-grid">
                {methods.map((item, index) => <button key={item.id} type="button" className={`method-card method-${item.tint}`} onClick={() => openMethod(item.id)}>
                  <span className="method-top"><span className="method-icon"><Icon name={item.icon} size={21} /></span><span className="method-number">0{index + 1}</span></span>
                  <strong>{item.title}</strong><span className="method-subtitle">{item.subtitle}</span>
                  <span className="method-bottom"><span>{item.tag}</span><span className="round-arrow"><Icon name="arrow" size={15} /></span></span>
                </button>)}
              </div>
              <p className="prototype-disclaimer"><Icon name="sparkles" size={14} /> Las opciones de voz, foto y escaneo muestran el flujo del prototipo; el análisis automático se conectará en una siguiente etapa.</p>
            </section>

            <div className="dashboard-columns">
              <section className="content-card expiring-card">
                <div className="card-heading"><div><span className="section-kicker">PARA QUE NO SE TE PASE</span><h2>Revisa estos productos</h2></div><button type="button" className="text-link" onClick={() => setActiveTab("alerts")}>Ver vencimientos <Icon name="arrow" size={15} /></button></div>
                {expiringProducts.length ? <div className="product-list compact-list">{expiringProducts.slice(0, 3).map((product) => <ProductRow key={product.id} product={product} type="expiry" />)}</div> : <EmptyState icon="check" title="¡Todo bajo control!" text="No tienes productos próximos a vencer." />}
              </section>
              {suggestionVisible && <section className="suggestion-card">
                <div className="suggestion-topline"><span className="suggestion-icon"><Icon name="sparkles" size={19} /></span><span className="suggestion-label">IDEA PARA TI</span><button type="button" className="dismiss-button" aria-label="Cerrar sugerencia" onClick={() => setSuggestionVisible(false)}><Icon name="close" size={16} /></button></div>
                {discountCandidate ? <>
                  <h2>Cuida tu inversión</h2>
                  <p><strong>{discountCandidate.name}</strong> vence pronto. Una promoción breve podría ayudarte a darle salida.</p>
                  <div className="suggestion-price"><span>Precio actual <strong>S/ {Number(discountCandidate.price).toFixed(2)}</strong></span><Icon name="arrow" size={14} /><span>Idea de promo <strong>S/ {(Number(discountCandidate.price) * 0.9).toFixed(2)}</strong></span></div>
                  <button type="button" className="suggestion-action" onClick={() => setPriceReview(true)}>Revisar descuento <Icon name="arrow" size={15} /></button>
                </> : <>
                  <h2>Cuida tu inversión</h2>
                  <p>Algunos productos tienen poco stock. Revisarlos a tiempo puede ayudarte a evitar quedarte sin ellos.</p>
                  <div className="suggestion-items">{lowStockProducts.slice(0, 2).map((product) => <span key={product.id}>{product.icon} {product.name}</span>)}</div>
                  <button type="button" className="suggestion-action" onClick={() => setActiveTab("inventory")}>Revisar inventario <Icon name="arrow" size={15} /></button>
                </>}
                <span className="suggestion-footnote">Idea referencial, no generada por IA real · tú decides qué hacer</span>
              </section>}
            </div>

            <section className="insight-strip">
              <span className="insight-strip-icon"><Icon name="users" size={19} /></span>
              <span><strong>¿Trabajan varias personas en tu bodega?</strong><small>Los registros deben indicar quién hizo cada movimiento.</small></span>
              <button type="button" onClick={() => setActiveTab("insights")}>Ver hallazgos <Icon name="arrow" size={15} /></button>
            </section>
          </div>
        )}

        {activeTab === "inventory" && (
          <div className="page-content inner-page">
            <section className="welcome-row"><div><p className="date-greeting">TODO EN UN SOLO LUGAR</p><h1>Tu inventario</h1><p className="welcome-subtitle">Consulta tus productos y mantén sus cantidades al día.</p></div><button type="button" className="button button-primary" onClick={() => openMethod("text")}><Icon name="plus" size={18} /> Agregar producto</button></section>
            <section className="content-card inventory-card">
              <div className="inventory-toolbar"><div><span className="section-kicker">CATÁLOGO DE PRODUCTOS</span><h2>{products.length} productos <span className="muted-count">· {stockTotal} unidades</span></h2></div><label className="search-field"><Icon name="search" size={17} /><input aria-label="Buscar producto" placeholder="Buscar producto" value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
              <div className="table-wrap"><table><thead><tr><th>PRODUCTO</th><th>STOCK</th><th>PRECIO DE VENTA</th><th>VENCIMIENTO</th><th>ESTADO</th></tr></thead><tbody>
                {filteredProducts.map((product) => <ProductTableRow key={product.id} product={product} expiring={expiringProducts.some((item) => item.id === product.id)} />)}
              </tbody></table>{filteredProducts.length === 0 && <EmptyState icon="search" title="No encontramos ese producto" text="Prueba con otro nombre o registra uno nuevo." />}</div>
            </section>
            <div className="note-card"><Icon name="shield" size={18} /><span><strong>Un registro a la vez.</strong> Cada entrada se suma a tu stock; las ventas y mermas se registran por separado en el flujo completo.</span></div>
          </div>
        )}

        {activeTab === "alerts" && (
          <div className="page-content inner-page">
            <section className="welcome-row"><div><p className="date-greeting">CUIDA LO QUE YA COMPRASTE</p><h1>Fechas importantes</h1><p className="welcome-subtitle">Revisa lo que está próximo a vencer y decide qué hacer.</p></div><span className="alert-counter"><Icon name="clock" size={18} /> {expiringProducts.length} por revisar</span></section>
            <section className="content-card alerts-card"><div className="card-heading"><div><span className="section-kicker">PRÓXIMOS 7 DÍAS</span><h2>Productos que necesitan atención</h2></div></div>
              {expiringProducts.length ? <div className="product-list">{expiringProducts.map((product) => <ProductRow key={product.id} product={product} type="expiry" />)}</div> : <EmptyState icon="check" title="¡Todo bajo control!" text="No tienes productos próximos a vencer." />}
            </section>
            <div className="gentle-reminder"><span>💡</span><p><strong>Un recordatorio útil</strong><br />La alerta usa la fecha de vencimiento que registraste. Recuerda revisar el estado del producto antes de decidir venderlo o retirarlo.</p></div>
          </div>
        )}

        {activeTab === "insights" && (
          <div className="page-content inner-page">
            <section className="welcome-row"><div><p className="date-greeting">ESCUCHAMOS A LOS COMERCIANTES</p><h1>Ideas que nacen del día a día</h1><p className="welcome-subtitle">Oportunidades para que el proyecto resuelva problemas reales.</p></div><span className="research-tag"><Icon name="users" size={17} /> Entrevistas exploratorias</span></section>
            <div className="insight-grid">
              <InsightCard number="01" icon="box" title="Anotar no siempre alcanza" text="El stock se controla de memoria o en papel, y las entradas se apuntan desde documentos de compra. Un registro rápido y centralizado reduce la doble tarea." takeaway="Diseñar para registrar en pocos pasos." tone="green" />
              <InsightCard number="02" icon="calendar" title="El vencimiento sí importa" text="Todos los participantes consultados hasta esta etapa consideraron útiles las alertas de productos próximos a vencer. También se mencionan pérdidas por productos vencidos." takeaway="Priorizar alertas claras, oportunas y accionables." tone="amber" />
              <InsightCard number="03" icon="trending" title="Las ventas dejan huecos" text="Las ventas se recuerdan de memoria, se apoyan en tickets o no se anotan. Sin registrar salidas, el inventario deja de reflejar lo que realmente queda." takeaway="Hacer fácil registrar ventas y mermas." tone="lavender" />
              <InsightCard number="04" icon="users" title="El equipo necesita trazabilidad" text="Familiares o empleados también realizan movimientos. El responsable necesita saber quién registró cada entrada, venta o retiro." takeaway="Guardar responsable y fecha en cada movimiento." tone="blue" />
            </div>
            <section className="provider-opportunity"><span className="provider-icon"><Icon name="shield" size={21} /></span><div><span className="section-kicker">OPORTUNIDAD PARA VALIDAR</span><h2>Cuando el proveedor no acepta devoluciones, la pérdida queda en la bodega.</h2><p>Un problema mencionado para esta propuesta es asumir el costo de productos vencidos o deteriorados que algunas marcas no reciben de vuelta. Una siguiente etapa podría registrar lote, fecha, evidencia y estado de cada reclamo, sin prometer una devolución ni incluir la gestión de proveedores en el MVP actual.</p><span className="opportunity-label">Idea de evolución · validar con más entrevistas</span></div></section>
            <p className="research-caveat">Estos hallazgos son exploratorios, no prueban que la app reduzca pérdidas. El archivo Entrevistas.csv no estaba disponible en el espacio de trabajo; conviene contrastar y ampliar estos temas con las respuestas originales.</p>
          </div>
        )}

        <nav className="mobile-nav" aria-label="Navegación móvil">{navigation.map((item) => <button key={item.id} type="button" className={activeTab === item.id ? "active" : ""} onClick={() => setActiveTab(item.id)}><Icon name={item.icon} size={19} /><span>{item.label === "Ideas para tu negocio" ? "Ideas" : item.label}</span>{item.id === "alerts" && expiringProducts.length > 0 && <i />}</button>)}</nav>
      </main>

      {method && <ProductModal method={methods.find((item) => item.id === method)} onClose={() => setMethod(null)} onSubmit={addProduct} voiceCaptured={voiceCaptured} setVoiceCaptured={setVoiceCaptured} photoName={photoName} setPhotoName={setPhotoName} barcode={barcode} setBarcode={setBarcode} />}
      {priceReview && discountCandidate && <SuggestionModal product={discountCandidate} onClose={() => setPriceReview(false)} onApprove={approvePriceSuggestion} onReject={dismissPriceSuggestion} />}
      {toast && <div className="toast-message" role="status"><span><Icon name="check" size={17} /></span>{toast}</div>}
    </div>
  );
}

function SuggestionModal({ product, onClose, onApprove, onReject }) {
  const suggestedPrice = (Number(product.price) * 0.9).toFixed(2);
  const [price, setPrice] = useState(suggestedPrice);
  const discount = Math.round((1 - Number(price) / Number(product.price)) * 100);
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="product-modal suggestion-modal" role="dialog" aria-modal="true" aria-labelledby="suggestion-title">
        <div className="modal-header"><span className="modal-method-icon method-mint"><Icon name="sparkles" size={21} /></span><button type="button" className="icon-button close-modal" aria-label="Cerrar" onClick={onClose}><Icon name="close" size={20} /></button><span className="section-kicker">PROPUESTA PARA REVISAR</span><h2 id="suggestion-title">Descuento por vencimiento próximo</h2><p>Revisa o ajusta la idea antes de decidir. No se aplicará automáticamente.</p></div>
        <div className="review-product"><span className="product-emoji">{product.icon}</span><span><strong>{product.name}</strong><small>{product.stock} {product.unit} · vence el {new Date(`${product.expires}T00:00:00`).toLocaleDateString("es-PE", { day: "numeric", month: "long" })}</small></span></div>
        <label className="review-price-label">Precio promocional sugerido<div className="input-with-prefix"><span>S/</span><input type="number" aria-label="Precio promocional sugerido" min="0.01" max={Number(product.price) - 0.01} step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} /></div></label>
        <div className="discount-summary"><span>Precio actual: <strong>S/ {Number(product.price).toFixed(2)}</strong></span><span>{discount > 0 && discount < 100 ? `${discount}% menos` : "Ajusta el precio"}</span></div>
        <p className="modal-prototype-note"><Icon name="sparkles" size={14} /> Ejemplo de interfaz con datos de muestra; no hay predicción ni promoción real conectada.</p>
        <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onReject}>Descartar</button><button type="button" className="button button-primary" disabled={!Number(price) || Number(price) >= Number(product.price)} onClick={() => onApprove(Number(price).toFixed(2))}>Aprobar idea <Icon name="check" size={16} /></button></div>
      </section>
    </div>
  );
}

function ProductModal({ method, onClose, onSubmit, voiceCaptured, setVoiceCaptured, photoName, setPhotoName, barcode, setBarcode }) {
  const [prefill, setPrefill] = useState(false);
  const title = method?.id === "photo" ? "Registra con una foto" : method?.id === "voice" ? "Registra con tu voz" : method?.id === "scan" ? "Escanea el código" : "Escribe los detalles";
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal-header"><span className={`modal-method-icon method-${method?.tint}`}><Icon name={method?.icon} size={21} /></span><button type="button" className="icon-button close-modal" aria-label="Cerrar" onClick={onClose}><Icon name="close" size={20} /></button><span className="section-kicker">NUEVA MERCADERÍA</span><h2 id="modal-title">{title}</h2><p>Agrega los datos básicos para actualizar tu inventario.</p></div>
        {method?.id === "photo" && <label className={`capture-zone ${photoName ? "has-file" : ""}`}><input type="file" accept="image/*" capture="environment" onChange={(event) => setPhotoName(event.target.files?.[0]?.name || "")} /><span className="capture-icon"><Icon name={photoName ? "check" : "camera"} size={22} /></span><strong>{photoName || "Toma o elige una foto"}</strong><small>{photoName ? "Foto lista para el prototipo" : "Producto, etiqueta o boleta"}</small></label>}
        {method?.id === "voice" && <div className={`voice-capture ${voiceCaptured ? "recorded" : ""}`}><button type="button" className="mic-button" aria-label={voiceCaptured ? "Ejemplo de voz transcrito" : "Probar grabación de voz"} onClick={() => { setVoiceCaptured(true); setPrefill(true); }}><Icon name={voiceCaptured ? "check" : "mic"} size={22} /></button><strong>{voiceCaptured ? "¡Listo! Te escuchamos" : "Toca el micrófono para empezar"}</strong><small>{voiceCaptured ? "“Agrega 6 yogures naturales” · ejemplo de demostración" : "Prueba una grabación de ejemplo"}</small></div>}
        {method?.id === "scan" && <div className="barcode-zone"><span className="barcode-visual"><Icon name="scan" size={31} /></span><strong>Enfoca el código de barras</strong><small>La cámara real se conectará en una siguiente etapa.</small><div className="barcode-input-wrap"><input value={barcode} onChange={(event) => { setBarcode(event.target.value); setPrefill(Boolean(event.target.value)); }} placeholder="O escribe el código aquí" aria-label="Código de barras" /><button type="button" onClick={() => { setBarcode("7750182003412"); setPrefill(true); }}>Probar ejemplo</button></div></div>}
        <form key={prefill ? "prefilled" : "empty"} className="product-form" onSubmit={onSubmit}>
          <label className="full-field">Nombre del producto<input name="productName" placeholder="Ej. Yogurt natural" defaultValue={prefill ? "Yogurt natural" : ""} required /></label>
          <label>Categoría<select name="category" defaultValue="Abarrotes"><option>Abarrotes</option><option>Lácteos</option><option>Frutas</option><option>Bebidas</option><option>Limpieza</option><option>Otros</option></select></label>
          <label>Cantidad<div className="input-with-suffix"><input name="quantity" type="number" min="1" defaultValue={prefill ? "6" : ""} placeholder="0" required /><select name="unit" aria-label="Unidad"><option>unid.</option><option>kg</option><option>paq.</option><option>caja</option><option>litro</option></select></div></label>
          <label>Precio de venta <span className="optional-label">(opcional)</span><div className="input-with-prefix"><span>S/</span><input name="price" type="number" min="0" step="0.10" placeholder="0.00" /></div></label>
          <label>Fecha de vencimiento <span className="optional-label">(opcional)</span><input name="expires" type="date" /></label>
          <p className="modal-prototype-note"><Icon name="sparkles" size={14} /> La IA no completa datos automáticamente en este prototipo. Revisa la información antes de guardar.</p>
          <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancelar</button><button type="submit" className="button button-primary">Guardar en inventario <Icon name="arrow" size={16} /></button></div>
        </form>
      </section>
    </div>
  );
}

function ProductRow({ product, type }) {
  const days = product.expires ? Math.ceil((new Date(`${product.expires}T00:00:00`) - new Date(new Date().toDateString())) / 86400000) : null;
  const expirationLabel = days === 0 ? "Vence hoy" : days === 1 ? "Vence mañana" : `En ${days} días`;
  return <div className="product-row"><span className="product-emoji">{product.icon}</span><span className="product-name"><strong>{product.name}</strong><small>{product.category} · {product.stock} {product.unit}</small></span><span className={`status-pill ${type === "expiry" ? "status-expiry" : ""}`}><i />{type === "expiry" ? expirationLabel : "Revisar stock"}</span></div>;
}

function ProductTableRow({ product, expiring }) {
  return <tr><td><span className="table-product-icon">{product.icon}</span><span className="table-product-name"><strong>{product.name}</strong><small>{product.category}</small></span></td><td><strong>{product.stock} {product.unit}</strong><span className={`stock-indicator ${product.stock <= 5 ? "stock-low" : ""}`}>{product.stock <= 5 ? "Stock bajo" : "Disponible"}</span></td><td>S/ {Number(product.price || 0).toFixed(2)}</td><td>{product.expires ? new Date(`${product.expires}T00:00:00`).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" }) : "Sin fecha"}</td><td><span className={`table-status ${expiring ? "table-status-warn" : ""}`}><i />{expiring ? "Por vencer" : "En orden"}</span></td></tr>;
}

function EmptyState({ icon, title, text }) {
  return <div className="empty-state"><span><Icon name={icon} size={21} /></span><strong>{title}</strong><p>{text}</p></div>;
}

function InsightCard({ number, icon, title, text, takeaway, tone }) {
  return <article className={`insight-card insight-${tone}`}><div className="insight-card-top"><span><Icon name={icon} size={19} /></span><small>HALLAZGO {number}</small></div><h2>{title}</h2><p>{text}</p><div className="insight-takeaway"><strong>¿Qué significa para el diseño?</strong><span>{takeaway}</span></div></article>;
}

export default App;
