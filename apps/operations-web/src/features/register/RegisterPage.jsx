import React, { useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { BarcodeCapture, PhotoCapture, ProductForm, VoiceCapture } from "../products/ProductModal";
import { AiModelPicker } from "../products/AiModelPicker";
import { workspaceCopy } from "../../lib/workspaceCopy";

const registerModes = [
  { id: "photo", label: "Foto", icon: "camera", description: "Captura una etiqueta o boleta" },
  { id: "scan", label: "Código", icon: "scan", description: "Envía la imagen del código de barras" },
  { id: "search", label: "Buscar", icon: "search", description: "Reutiliza un producto pasado" },
  { id: "text", label: "Texto", icon: "edit", description: "Escribe los datos manualmente" },
  { id: "voice", label: "Voz", icon: "mic", description: "Dicta los datos del producto" },
];

export function RegisterPage({ products, user, onSubmit, draft, categories = [], onCreateCategory, aiModels = [] }) {
  const copy = workspaceCopy(user);
  const [mode, setMode] = useState("text");
  const [search, setSearch] = useState("");
  const [photoName, setPhotoName] = useState("");
  const [voiceCaptured, setVoiceCaptured] = useState(false);

  const matchingProducts = useMemo(() => products.filter((product) => product.name.toLowerCase().includes(search.toLowerCase())), [products, search]);

  function changeMode(nextMode) {
    setMode(nextMode);
    setVoiceCaptured(false);
    setPhotoName("");
    setSearch("");
    draft.clear();
  }

  function handleMedia(modo, media) {
    if (media?.error) {
      draft.setError(media.error);
      return;
    }
    draft.analyze(modo, media);
  }

  function selectPastProduct(product) {
    setMode("text");
    setSearch(product.name);
    draft.applyProduct(product);
  }

  return <div className="page-content inner-page register-page"><PageDate /><section className="welcome-row register-heading"><div><h1>Registrar producto</h1><p className="welcome-subtitle">{copy.registerSubtitle}</p></div></section><div className="register-workspace"><nav className="register-subnav" aria-label="Métodos para registrar producto">{registerModes.map((item) => <button type="button" className={mode === item.id ? "active" : ""} key={item.id} onClick={() => changeMode(item.id)}><span className="register-subnav-icon"><Icon name={item.icon} size={18} /></span><span><strong>{item.label}</strong></span></button>)}</nav><section className="register-panel">
    {mode === "text" && <RegisterTextPanel copy={copy} draft={draft} onSubmit={onSubmit} categories={categories} onCreateCategory={onCreateCategory} />}
    {mode === "photo" && <RegisterCapturePanel title="Toma una foto al producto" description="Enfoca el producto o su etiqueta. La IA propondrá datos y tú los revisarás." modelPicker={<AiModelPicker models={aiModels} value={draft.aiModel} onChange={draft.setAiModel} />} capture={<PhotoCapture photoName={photoName} setPhotoName={setPhotoName} onMedia={(media) => handleMedia("photo", media)} />} draft={draft} onSubmit={onSubmit} categories={categories} onCreateCategory={onCreateCategory} />}
    {mode === "scan" && <RegisterCapturePanel title="Envía la imagen del código de barras" description="Los dígitos del código se consultan en Open Food Facts. Si no se encuentra, regístralo manualmente. La cantidad la ingresas tú." capture={<BarcodeCapture barcode={draft.draft.codigoBarras} setBarcode={(value) => draft.setField("codigoBarras", value)} onImage={(media) => handleMedia("barcode", { ...media, codigo: media.codigo || draft.draft.codigoBarras })} />} draft={draft} onSubmit={onSubmit} categories={categories} onCreateCategory={onCreateCategory} />}
    {mode === "voice" && <RegisterCapturePanel title="Registra con tu voz" description="Dicta nombre, categoría, cantidad, precio de venta y fecha de vencimiento. La IA transcribe lo que digas; revísalo antes de guardar." modelPicker={<AiModelPicker models={aiModels} value={draft.aiModel} onChange={draft.setAiModel} />} capture={<VoiceCapture captured={voiceCaptured} onCapture={() => setVoiceCaptured(true)} onAudio={(media) => handleMedia("voice", media)} onError={draft.setError} />} draft={draft} onSubmit={onSubmit} categories={categories} onCreateCategory={onCreateCategory} />}
    {mode === "search" && <RegisterSearchPanel products={matchingProducts} search={search} onSearch={setSearch} onSelect={selectPastProduct} />}
  </section></div></div>;
}

function RegisterTextPanel({ copy, draft, onSubmit, categories, onCreateCategory }) {
  return <div className="register-mode-content"><div className="register-mode-heading"><span className="register-mode-icon mode-mint"><Icon name="edit" size={24} /></span><div><h2>Escribe los datos del producto</h2><p>{copy.registerFormHint}</p></div></div><ProductForm value={draft.draft} onChange={draft.setField} onSubmit={onSubmit} status={draft.status} error={draft.error} categories={categories} onCreateCategory={onCreateCategory} /></div>;
}

function RegisterCapturePanel({ title, description, modelPicker, capture, draft, onSubmit, categories, onCreateCategory }) {
  return <div className="register-mode-content"><div className="register-mode-heading"><span className="register-mode-icon mode-peach"><Icon name="camera" size={24} /></span><div><h2>{title}</h2><p>{description}</p></div></div>{modelPicker}<div className="register-capture-area">{capture}</div><ProductForm value={draft.draft} onChange={draft.setField} onSubmit={onSubmit} status={draft.status} error={draft.error} categories={categories} onCreateCategory={onCreateCategory} /></div>;
}

function RegisterSearchPanel({ products, search, onSearch, onSelect }) {
  return <div className="register-mode-content"><div className="register-mode-heading"><span className="register-mode-icon mode-lavender"><Icon name="search" size={24} /></span><div><h2>Buscar un producto</h2><p>Encuentra un producto registrado para volver a usar sus datos.</p></div></div><label className="register-search-field"><Icon name="search" size={18} /><input autoFocus value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Buscar por nombre" /></label><div className="register-product-list">{products.map((product) => <button type="button" key={product.id} onClick={() => onSelect(product)}><span className="product-emoji">{product.icon}</span><span><strong>{product.name}</strong><small>{product.category} &middot; {product.stock} {product.unit}</small></span><Icon name="arrow" size={17} /></button>)}{products.length === 0 && <p className="register-empty-search">No encontramos productos con ese nombre.</p>}</div></div>;
}
