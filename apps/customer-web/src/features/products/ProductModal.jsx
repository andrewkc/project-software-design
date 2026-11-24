import React, { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { VoiceInput } from "../../components/common/VoiceInput";
import { analyzeProductImage } from "../../lib/imageAnalysis";
import { localToday } from "../../lib/sales";
import { parseProductSpeech } from "../../lib/voiceParser";
import { workspaceCopy } from "../../lib/workspaceCopy";

export function ProductModal({ method, user, onClose, onSubmit, photoName, setPhotoName, barcode, setBarcode }) {
  const [suggestion, setSuggestion] = useState(null);
  const copy = workspaceCopy(user);
  const title = method?.id === "photo" ? "Registra con una foto" : method?.id === "voice" ? "Registra con tu voz" : method?.id === "scan" ? "Escanea el c&oacute;digo" : "Escribe los detalles";
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-header"><span className={`modal-method-icon method-${method?.tint}`}><Icon name={method?.icon} size={21} /></span><button type="button" className="icon-button close-modal" aria-label="Cerrar" onClick={onClose}><Icon name="close" size={20} /></button><span className="section-kicker">NUEVA MERCADER&Iacute;A</span><h2 id="modal-title">{title}</h2><p>{copy.modalHint}</p></div>{method?.id === "photo" && <PhotoCapture photoName={photoName} setPhotoName={setPhotoName} onSuggestion={setSuggestion} />}{method?.id === "voice" && <VoiceCapture onSuggestion={setSuggestion} />}{method?.id === "scan" && <BarcodeCapture barcode={barcode} setBarcode={setBarcode} />}<ProductForm key={JSON.stringify(suggestion)} suggestion={suggestion} barcode={barcode} onSubmit={onSubmit} onClose={onClose} /></section></div>;
}

export function PhotoCapture({ photoName, setPhotoName, onSuggestion }) {
  const cameraInput = useRef(null);
  const galleryInput = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [capturedImage, setCapturedImage] = useState("");
  const [analysis, setAnalysis] = useState({ busy: false, progress: 0, message: "" });

  async function analyzePhoto() {
    setAnalysis({ busy: true, progress: 0, message: "" });
    try {
      const result = await analyzeProductImage(capturedImage, (progress) => setAnalysis((current) => ({ ...current, progress })));
      const found = result.name || result.price !== null || result.expires;
      if (found) onSuggestion?.({ name: result.name, price: result.price, expires: result.expires, category: result.category, source: "foto" });
      setAnalysis({ busy: false, progress: 0, message: found ? "Datos leídos. Revísalos antes de guardar." : "No encontramos datos claros. Prueba con más luz o escríbelos." });
    } catch {
      setAnalysis({ busy: false, progress: 0, message: "No se pudo analizar la imagen. Revisa tu conexión o escribe los datos." });
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) return;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
        if (cancelled) return stream.getTracks().forEach((track) => track.stop());
        streamRef.current = stream;
        setCameraReady(true);
      } catch {
        setCameraReady(false);
      }
    }
    startCamera();
    return () => { cancelled = true; streamRef.current?.getTracks().forEach((track) => track.stop()); };
  }, []);

  useEffect(() => {
    if (cameraReady && videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
  }, [cameraReady]);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraReady(false);
  }

  function handleSelectedFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPhotoName(file.name);
    setCapturedImage(URL.createObjectURL(file));
    stopCamera();
  }

  function capturePhoto() {
    if (!cameraReady || !videoRef.current) return cameraInput.current?.click();
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    setCapturedImage(canvas.toDataURL("image/jpeg", 0.9));
    setPhotoName("foto-producto.jpg");
    stopCamera();
  }

  async function repeatPhoto() {
    setAnalysis({ busy: false, progress: 0, message: "" });
    setCapturedImage("");
    setPhotoName("");
    if (!navigator.mediaDevices?.getUserMedia) return;
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
      setCameraReady(true);
    } catch {
      setCameraReady(false);
    }
  }

  return <div className={`photo-camera ${photoName ? "has-photo" : ""}`}><div className="photo-camera-preview">{capturedImage ? <img src={capturedImage} alt="Producto capturado" /> : cameraReady ? <video ref={videoRef} autoPlay muted playsInline aria-label="Vista previa de la cámara" /> : <span>Activa la cámara para enfocar el producto</span>}</div><div className="photo-camera-controls"><button type="button" className="photo-gallery-button" aria-label="Elegir una foto de la galería" onClick={() => galleryInput.current?.click()}><Icon name="image" size={22} /></button>{capturedImage ? <button type="button" className="photo-retake-button photo-shutter-replacement" aria-label="Repetir toma de foto" onClick={repeatPhoto}><Icon name="refresh" size={21} /></button> : <button type="button" className="photo-shutter" aria-label="Tomar foto" onClick={capturePhoto}><span /></button>}<button type="button" className="photo-flash-button" aria-label="Flash desactivado" disabled><Icon name="flash" size={21} /></button></div>{capturedImage ? <div className="photo-analyze"><button type="button" disabled={analysis.busy} onClick={analyzePhoto}><Icon name="sparkles" size={15} /> {analysis.busy ? `Leyendo etiqueta… ${analysis.progress}%` : "Leer etiqueta con IA"}</button>{analysis.message && <p role="status">{analysis.message}</p>}</div> : <p className="photo-ai-note"><Icon name="sparkles" size={14} /> Enfoca la etiqueta: la IA leer&aacute; nombre, precio y vencimiento.</p>}<input ref={cameraInput} className="photo-file-input" type="file" accept="image/*" capture="environment" onChange={handleSelectedFile} /><input ref={galleryInput} className="photo-file-input" type="file" accept="image/*" onChange={handleSelectedFile} /></div>;
}

export function VoiceCapture({ onSuggestion }) {
  return <VoiceInput example="agrega seis yogures a 3.50 soles que vencen el 20 de diciembre" onText={(text) => onSuggestion({ ...parseProductSpeech(text, localToday()), source: "voz" })} />;
}

export function BarcodeCapture({ barcode, setBarcode, onDetected }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [scanMessage, setScanMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) return;
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
        if (cancelled) return stream.getTracks().forEach((track) => track.stop());
        streamRef.current = stream;
        setCameraReady(true);
      } catch {
        setScanMessage("No se pudo activar la cámara. Ingresa el Código manualmente.");
      }
    }
    startCamera();
    return () => { cancelled = true; streamRef.current?.getTracks().forEach((track) => track.stop()); };
  }, []);

  useEffect(() => {
    if (cameraReady && videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
  }, [cameraReady]);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraReady(false);
  }

  async function scanCode() {
    if (!("BarcodeDetector" in window) || !videoRef.current) {
      setScanMessage("Este navegador no detecta códigos automáticamente. Ingresa el código abajo.");
      return;
    }
    try {
      const detector = new window.BarcodeDetector();
      const results = await detector.detect(videoRef.current);
      if (results[0]?.rawValue) { setBarcode(results[0].rawValue); setScanMessage("Código obtenido correctamente."); stopCamera(); onDetected?.(results[0].rawValue); }
      else setScanMessage("No encontramos un código. Intenta nuevamente.");
    } catch {
      setScanMessage("No se pudo leer el código. Puedes ingresarlo manualmente.");
    }
  }

  return <><div className="barcode-zone barcode-camera-zone"><div className="barcode-camera-preview">{cameraReady ? <video ref={videoRef} autoPlay muted playsInline aria-label="Vista previa del escáner" /> : <span><Icon name="scan" size={25} /> Cámara desactivada</span>}</div><button type="button" className="barcode-scan-button" onClick={scanCode}><Icon name="scan" size={18} /> Escanear código</button>{scanMessage && <p className="barcode-scan-message">{scanMessage}</p>}</div><label className="barcode-manual-label">Buscar código directamente<div className="barcode-manual-input"><input value={barcode} onChange={(event) => setBarcode(event.target.value)} placeholder="Código de barras" aria-label="Código de barras" /><button type="button" aria-label="Buscar Código" onClick={() => { setScanMessage(barcode.trim() ? "Código listo." : "Ingresa un Código primero."); if (barcode.trim()) onDetected?.(barcode.trim()); }}><Icon name="search" size={17} /></button></div></label></>;
}

const PRODUCT_EMOJIS = [
  { emoji: "📦", keywords: "caja paquete empaque producto general" },
  { emoji: "🥛", keywords: "leche lacteos yogurt" },
  { emoji: "🍎", keywords: "manzana fruta" },
  { emoji: "🍊", keywords: "naranja fruta citrico" },
  { emoji: "🍋", keywords: "limon fruta citrico" },
  { emoji: "🍌", keywords: "platano banana fruta" },
  { emoji: "🍇", keywords: "uvas fruta" },
  { emoji: "🍓", keywords: "fresa fruta" },
  { emoji: "🍉", keywords: "sandia fruta" },
  { emoji: "🍍", keywords: "pina fruta" },
  { emoji: "🥝", keywords: "kiwi fruta" },
  { emoji: "🍑", keywords: "durazno melocoton fruta" },
  { emoji: "🍐", keywords: "pera fruta" },
  { emoji: "🍒", keywords: "cereza fruta" },
  { emoji: "🫐", keywords: "arandanos fruta" },
  { emoji: "🥑", keywords: "aguacate palta fruta" },
  { emoji: "🥥", keywords: "coco fruta" },
  { emoji: "🥚", keywords: "huevos" },
  { emoji: "🍞", keywords: "pan panaderia" },
  { emoji: "🥐", keywords: "croissant panaderia" },
  { emoji: "🥖", keywords: "baguette pan panaderia" },
  { emoji: "🧀", keywords: "queso lacteos" },
  { emoji: "🧈", keywords: "mantequilla lacteos" },
  { emoji: "🍖", keywords: "carne" },
  { emoji: "🥩", keywords: "carne bistec" },
  { emoji: "🍗", keywords: "pollo carne" },
  { emoji: "🐟", keywords: "pescado" },
  { emoji: "🥦", keywords: "brocoli verdura" },
  { emoji: "🥕", keywords: "zanahoria verdura" },
  { emoji: "🍅", keywords: "tomate verdura" },
  { emoji: "🥬", keywords: "lechuga verdura" },
  { emoji: "🌽", keywords: "maiz verdura" },
  { emoji: "🥔", keywords: "papa patata verdura" },
  { emoji: "🧅", keywords: "cebolla verdura" },
  { emoji: "🧄", keywords: "ajo" },
  { emoji: "🌶️", keywords: "chile aji picante" },
  { emoji: "🍚", keywords: "arroz" },
  { emoji: "🍝", keywords: "pasta fideos espaguetti" },
  { emoji: "🥫", keywords: "conserva lata" },
  { emoji: "🫙", keywords: "frasco conserva" },
  { emoji: "🧂", keywords: "sal" },
  { emoji: "🍯", keywords: "miel" },
  { emoji: "🍫", keywords: "chocolate dulce" },
  { emoji: "🍬", keywords: "caramelo dulce" },
  { emoji: "🍪", keywords: "galleta dulce" },
  { emoji: "🍩", keywords: "dona dulce" },
  { emoji: "🧁", keywords: "cupcake pastel" },
  { emoji: "🍰", keywords: "pastel torta" },
  { emoji: "🍦", keywords: "helado" },
  { emoji: "🥜", keywords: "mani nueces" },
  { emoji: "🍿", keywords: "palomitas" },
  { emoji: "☕", keywords: "cafe bebida" },
  { emoji: "🍵", keywords: "te bebida" },
  { emoji: "🧃", keywords: "jugo bebida" },
  { emoji: "🥤", keywords: "refresco gaseosa bebida" },
  { emoji: "💧", keywords: "agua bebida" },
  { emoji: "🧴", keywords: "shampoo limpieza locion" },
  { emoji: "🧼", keywords: "jabon limpieza" },
  { emoji: "🧽", keywords: "esponja limpieza" },
  { emoji: "🧻", keywords: "papel higienico limpieza" },
  { emoji: "🧹", keywords: "escoba limpieza" },
  { emoji: "🪣", keywords: "cubeta limpieza" },
  { emoji: "🧺", keywords: "canasta cesta" },
  { emoji: "🛒", keywords: "carrito compra" },
  { emoji: "🏷️", keywords: "etiqueta precio" },
];

export function ProductIconPicker({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef(null);
  const searchRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    searchRef.current?.focus();
    function handleOutside(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    }
    function handleKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const term = query.trim().toLowerCase();
  const results = term ? PRODUCT_EMOJIS.filter((item) => item.keywords.includes(term) || item.emoji === query.trim()) : PRODUCT_EMOJIS;

  return <div className="icon-picker" ref={rootRef}>
    <button type="button" className="icon-picker-trigger" aria-haspopup="dialog" aria-expanded={open} aria-label="Elegir ícono del producto" onClick={() => setOpen((current) => !current)}>
      <span className="icon-picker-current">{value || "📦"}</span>
      <span className="icon-picker-label">Cambiar ícono</span>
    </button>
    <input type="hidden" name="icon" value={value || "📦"} />
    {open && <div className="icon-picker-popover" role="dialog" aria-label="Elegir ícono">
      <div className="icon-picker-search"><Icon name="search" size={15} /><input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar un ícono..." aria-label="Buscar un ícono" />{query && <button type="button" aria-label="Limpiar búsqueda" onClick={() => setQuery("")}><Icon name="close" size={13} /></button>}</div>
      <p className="icon-picker-caption">{term ? "Resultados" : "Sugerencias"}</p>
      <div className="icon-picker-grid">{results.map((item) => <button type="button" key={item.emoji} className={`icon-picker-option ${value === item.emoji ? "selected" : ""}`} title={item.keywords} onClick={() => { onChange(item.emoji); setOpen(false); setQuery(""); }}>{item.emoji}</button>)}</div>
      {results.length === 0 && <p className="icon-picker-empty">No encontramos íconos para «{query.trim()}».</p>}
    </div>}
  </div>;
}

const FORM_CATEGORIES = ["Abarrotes", "Lácteos", "Frutas", "Bebidas", "Limpieza", "Snacks", "Conservas", "Cuidado personal", "Otros"];
const FORM_UNITS = ["unid.", "kg", "paq.", "caja", "litro"];

export function ProductForm({ suggestion, barcode = "", onSubmit, onClose }) {
  const [icon, setIcon] = useState(suggestion?.icon || "📦");
  const category = FORM_CATEGORIES.includes(suggestion?.category) ? suggestion.category : "Abarrotes";
  return <form className="product-form" onSubmit={onSubmit}><input type="hidden" name="barcode" value={barcode} />{suggestion?.source && <p className="ai-review-note"><Icon name="sparkles" size={14} /> Sugerido desde {suggestion.source}. Revisa los datos: nada se guarda hasta que confirmes.</p>}<label className="full-field">Nombre del producto<input name="productName" placeholder="Ej. Yogurt natural" defaultValue={suggestion?.name || ""} required /></label><div className="full-field product-icon-field"><span className="field-label">Ícono</span><ProductIconPicker value={icon} onChange={setIcon} /></div><label>Categor&iacute;a<select name="category" defaultValue={category}>{FORM_CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label><label>Cantidad<div className="input-with-suffix"><input name="quantity" type="number" min="0.01" step="any" defaultValue={suggestion?.quantity ?? ""} placeholder="0" required /><select name="unit" aria-label="Unidad" defaultValue={suggestion?.unit || "unid."}>{FORM_UNITS.map((item) => <option key={item}>{item}</option>)}</select></div></label><label>Precio de venta<div className="input-with-prefix"><span>S/</span><input name="price" type="number" min="0" step="0.01" placeholder="0.00" defaultValue={suggestion?.price ?? ""} /></div></label><label>Fecha de vencimiento<input name="expires" type="date" defaultValue={suggestion?.expires || ""} /></label><p className="modal-prototype-note" /><div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancelar</button><button type="submit" className="button button-primary">Guardar en inventario</button></div></form>;
}
