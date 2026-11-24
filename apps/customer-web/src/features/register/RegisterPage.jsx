import React, { useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { BarcodeCapture, PhotoCapture, ProductForm, VoiceCapture } from "../products/ProductModal";
import { workspaceCopy } from "../../lib/workspaceCopy";

const registerModes = [
  { id: "photo", label: "Foto", icon: "camera", description: "Captura una etiqueta o boleta" },
  { id: "scan", label: "Código", icon: "scan", description: "Lee el código de barras" },
  { id: "search", label: "Buscar", icon: "search", description: "Reutiliza un producto pasado" },
  { id: "text", label: "Texto", icon: "edit", description: "Escribe los datos manualmente" },
  { id: "voice", label: "Voz", icon: "mic", description: "Dicta los datos del producto" },
];

export function RegisterPage({ products, user, onSubmit }) {
  const copy = workspaceCopy(user);
  const [mode, setMode] = useState("text");
  const [search, setSearch] = useState("");
  const [photoName, setPhotoName] = useState("");
  const [barcode, setBarcode] = useState("");
  const [voiceCaptured, setVoiceCaptured] = useState(false);
  const [prefill, setPrefill] = useState(false);

  const matchingProducts = useMemo(() => products.filter((product) => product.name.toLowerCase().includes(search.toLowerCase())), [products, search]);

  function changeMode(nextMode) {
    setMode(nextMode);
    setVoiceCaptured(false);
    setPhotoName("");
    setBarcode("");
    setPrefill(false);
  }

  function selectPastProduct(product) {
    setMode("text");
    setPrefill(true);
    setSearch(product.name);
  }

  return <div className="page-content inner-page register-page"><PageDate /><section className="welcome-row register-heading"><div>
    {/* <p className="date-greeting">NUEVO PRODUCTO</p> */}
    <h1>Registrar producto</h1><p className="welcome-subtitle">{copy.registerSubtitle}</p></div></section><div className="register-workspace"><nav className="register-subnav" aria-label="Métodos para registrar producto">{registerModes.map((item) => <button type="button" className={mode === item.id ? "active" : ""} key={item.id} onClick={() => changeMode(item.id)}><span className="register-subnav-icon"><Icon name={item.icon} size={18} /></span><span><strong>{item.label}</strong></span></button>)}</nav><section className="register-panel">{mode === "text" && <RegisterTextPanel copy={copy} prefill={prefill} onSubmit={onSubmit} />}{mode === "photo" && 
    <RegisterCapturePanel title="Toma una foto al producto" description="Enfoca el producto dentro del recuadro." capture={<PhotoCapture photoName={photoName} setPhotoName={setPhotoName} />} onSubmit={onSubmit} prefill={prefill} />}{mode === "scan" && <RegisterCapturePanel title="Escanea el código de barras" description="Enfoca el código del producto o escríbelo manualmente." capture={<BarcodeCapture barcode={barcode} setBarcode={setBarcode} onExample={() => { setBarcode("7750182003412"); setPrefill(true); }} />} onSubmit={onSubmit} prefill={prefill} />}{mode === "voice" && <RegisterCapturePanel title="Registra con tu voz" description="Toca el micrófono y dicta los datos del producto." capture={<VoiceCapture captured={voiceCaptured} onCapture={() => { setVoiceCaptured(true); setPrefill(true); }} />} onSubmit={onSubmit} prefill={prefill} />}{mode === "search" && <RegisterSearchPanel products={matchingProducts} search={search} onSearch={setSearch} onSelect={selectPastProduct} />}</section></div></div>;
}

function RegisterTextPanel({ copy, prefill, onSubmit }) {
  return <div className="register-mode-content"><div className="register-mode-heading"><span className="register-mode-icon mode-mint"><Icon name="edit" size={24} /></span><div>
    {/* <span className="section-kicker">REGISTRO MANUAL</span> */}
    <h2>Escribe los datos del producto</h2><p>{copy.registerFormHint}</p></div></div><ProductForm prefill={prefill} onSubmit={onSubmit} onClose={() => {}} /></div>;
}

function RegisterCapturePanel({ title, description, capture, onSubmit, prefill }) {
  return <div className="register-mode-content"><div className="register-mode-heading"><span className="register-mode-icon mode-peach"><Icon name="camera" size={24} /></span><div>
    {/* <span className="section-kicker">CAPTURA ASISTIDA</span> */}
    <h2>{title}</h2><p>{description}</p></div></div><div className="register-capture-area">{capture}</div><ProductForm prefill={prefill} onSubmit={onSubmit} onClose={() => {}} /></div>;
}

function RegisterSearchPanel({ products, search, onSearch, onSelect }) {
  return <div className="register-mode-content"><div className="register-mode-heading"><span className="register-mode-icon mode-lavender"><Icon name="search" size={24} /></span><div>
    {/* <span className="section-kicker">PRODUCTOS PASADOS</span> */}
    <h2>Buscar un producto</h2><p>Encuentra un producto registrado para volver a usar sus datos.</p></div></div><label className="register-search-field"><Icon name="search" size={18} /><input autoFocus value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Buscar por nombre" /></label><div className="register-product-list">{products.map((product) => <button type="button" key={product.id} onClick={() => onSelect(product)}><span className="product-emoji">{product.icon}</span><span><strong>{product.name}</strong><small>{product.category} &middot; {product.stock} {product.unit}</small></span><Icon name="arrow" size={17} /></button>)}{products.length === 0 && <p className="register-empty-search">No encontramos productos con ese nombre.</p>}</div></div>;
}
