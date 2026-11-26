import React, { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { workspaceCopy } from "../../lib/workspaceCopy";
import { AiModelPicker } from "./AiModelPicker";

function readAsDataURL(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("No se pudo leer el archivo."));
    reader.readAsDataURL(blob);
  });
}

function mimeFromDataURL(dataURL) {
  const match = /^data:([^;,]+)/.exec(dataURL || "");
  return match ? match[1] : "";
}

export function ProductModal({ method, user, onClose, onSubmit, draft, categories = [], onCreateCategory, aiModels = [] }) {
  const [voiceCaptured, setVoiceCaptured] = useState(false);
  const [photoName, setPhotoName] = useState("");
  const copy = workspaceCopy(user);
  const title = method?.id === "photo" ? "Registra con una foto" : method?.id === "voice" ? "Registra con tu voz" : method?.id === "scan" ? "Escanea el código" : "Escribe los detalles";
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-header"><span className={`modal-method-icon method-${method?.tint}`}><Icon name={method?.icon} size={21} /></span><button type="button" className="icon-button close-modal" aria-label="Cerrar" onClick={onClose}><Icon name="close" size={20} /></button><span className="section-kicker">NUEVA MERCADERÍA</span><h2 id="modal-title">{title}</h2><p>{copy.modalHint}</p></div>
    {method?.id === "photo" && <><AiModelPicker models={aiModels} value={draft.aiModel} onChange={draft.setAiModel} /><PhotoCapture photoName={photoName} setPhotoName={setPhotoName} onMedia={(media) => media.error ? draft.setError(media.error) : draft.analyze("photo", media)} /></>}
    {method?.id === "voice" && <><AiModelPicker models={aiModels} value={draft.aiModel} onChange={draft.setAiModel} /><VoiceCapture captured={voiceCaptured} onCapture={() => setVoiceCaptured(true)} onAudio={({ data, mime_type, duracion }) => draft.analyze("voice", { data, mime_type, duracion })} onError={draft.setError} /></>}
    {method?.id === "scan" && <BarcodeCapture barcode={draft.draft.codigoBarras} setBarcode={(value) => draft.setField("codigoBarras", value)} onImage={({ data, mime_type, codigo }) => draft.analyze("barcode", { data, mime_type, codigo })} />}
    <ProductForm value={draft.draft} onChange={draft.setField} onSubmit={onSubmit} onClose={onClose} status={draft.status} error={draft.error} categories={categories} onCreateCategory={onCreateCategory} />
  </section></div>;
}

export function PhotoCapture({ photoName, setPhotoName, onMedia }) {
  const cameraInput = useRef(null);
  const galleryInput = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [capturedImage, setCapturedImage] = useState("");

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

  async function handleSelectedFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const data = await readAsDataURL(file);
      setPhotoName(file.name);
      setCapturedImage(data);
      stopCamera();
      onMedia?.({ data, mime_type: file.type || mimeFromDataURL(data) });
    } catch (error) {
      onMedia?.({ error: error.message });
    } finally {
      event.target.value = "";
    }
  }

  function capturePhoto() {
    if (!cameraReady || !videoRef.current) return cameraInput.current?.click();
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL("image/jpeg", 0.9);
    setCapturedImage(data);
    setPhotoName("foto-producto.jpg");
    stopCamera();
    onMedia?.({ data, mime_type: "image/jpeg" });
  }

  async function repeatPhoto() {
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

  return <div className={`photo-camera ${photoName ? "has-photo" : ""}`}><div className="photo-camera-preview">{capturedImage ? <img src={capturedImage} alt="Producto capturado" /> : cameraReady ? <video ref={videoRef} autoPlay muted playsInline aria-label="Vista previa de la cámara" /> : <span>Activa la cámara para enfocar el producto</span>}</div><div className="photo-camera-controls"><button type="button" className="photo-gallery-button" aria-label="Elegir una foto de la galería" onClick={() => galleryInput.current?.click()}><Icon name="image" size={22} /></button>{capturedImage ? <button type="button" className="photo-retake-button photo-shutter-replacement" aria-label="Repetir toma de foto" onClick={repeatPhoto}><Icon name="refresh" size={21} /></button> : <button type="button" className="photo-shutter" aria-label="Tomar foto" onClick={capturePhoto}><span /></button>}<button type="button" className="photo-flash-button" aria-label="Flash desactivado" disabled><Icon name="flash" size={21} /></button></div><p className="photo-ai-note"><Icon name="sparkles" size={14} /> La IA propondrá datos; revísalos antes de guardar.</p><input ref={cameraInput} className="photo-file-input" type="file" accept="image/*" capture="environment" onChange={handleSelectedFile} /><input ref={galleryInput} className="photo-file-input" type="file" accept="image/*" onChange={handleSelectedFile} /></div>;
}

export function VoiceCapture({ captured, onCapture, onAudio, onError }) {
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const limitRef = useRef(null);
  const secondsRef = useRef(0);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => () => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    if (limitRef.current) window.clearTimeout(limitRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.onstop = null;
      recorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError?.("Este navegador no permite grabar audio. Puedes registrar el producto con texto.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus", "audio/wav"].find((type) => MediaRecorder.isTypeSupported?.(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => { if (event.data?.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        if (timerRef.current) window.clearInterval(timerRef.current);
        if (limitRef.current) window.clearTimeout(limitRef.current);
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setRecording(false);
        const elapsed = Math.max(1, Math.round(secondsRef.current));
        secondsRef.current = 0;
        setSeconds(0);
        if (!chunksRef.current.length) return;
        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || "audio/webm" });
          const data = await readAsDataURL(blob);
          onAudio?.({ data, mime_type: blob.type || mimeFromDataURL(data), duracion: elapsed });
          onCapture?.();
        } catch (error) {
          onError?.(error.message || "No se pudo leer la grabación.");
        }
      };
      recorder.start();
      setRecording(true);
      secondsRef.current = 0;
      setSeconds(0);
      timerRef.current = window.setInterval(() => {
        secondsRef.current += 1;
        setSeconds(secondsRef.current);
      }, 1000);
      limitRef.current = window.setTimeout(() => {
        if (recorder.state !== "inactive") recorder.stop();
      }, 60000);
    } catch {
      onError?.("No se pudo activar el micrófono. Revisa los permisos del navegador.");
    }
  }

  function stopRecording() {
    if (recorderRef.current && recorderRef.current.state !== "inactive") recorderRef.current.stop();
  }

  return <div className={`voice-capture ${captured ? "recorded" : ""} ${recording ? "recording" : ""}`}><button type="button" className="mic-button" aria-label={recording ? "Detener grabación" : "Empezar grabación"} onClick={recording ? stopRecording : startRecording}><Icon name={recording ? "close" : "mic"} size={22} /></button><strong>{recording ? `Grabando ${seconds}s. Toca para terminar.` : captured ? "Grabación lista para analizar" : "Toca el micrófono y dicta el producto"}</strong><small>Máximo 60 segundos · la IA solo propone datos</small></div>;
}

export function BarcodeCapture({ barcode, setBarcode, onImage }) {
  const videoRef = useRef(null);
  const fileInput = useRef(null);
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
        setScanMessage("No se pudo activar la cámara. Puedes subir una imagen del código.");
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
    if (!cameraReady || !videoRef.current) {
      setScanMessage("Enciende la cámara con el botón de en medio y enfoca el código.");
      return;
    }
    if (!("BarcodeDetector" in window)) {
      setScanMessage("Este navegador no detecta códigos automáticamente. Sube una imagen del código.");
      return;
    }
    try {
      const detector = new window.BarcodeDetector();
      const results = await detector.detect(videoRef.current);
      if (results[0]?.rawValue) {
        setBarcode(results[0].rawValue);
        setScanMessage("Dígitos obtenidos. Ahora toca «Usar imagen del código» para consultar Open Food Facts.");
      } else {
        setScanMessage("No encontramos un código. Intenta nuevamente o sube una imagen.");
      }
    } catch {
      setScanMessage("No se pudo leer el código. Puedes subir la imagen o escribirlo.");
    }
  }

  async function restartCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setScanMessage("Este navegador no permite usar la cámara. Puedes subir una imagen.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
      streamRef.current = stream;
      setCameraReady(true);
      setScanMessage("Cámara encendida. Enfoca el código y toca «Usar imagen del código».");
    } catch {
      setCameraReady(false);
      setScanMessage("No se pudo activar la cámara. Puedes subir una imagen del código.");
    }
  }

  async function captureFrame() {
    if (!cameraReady || !videoRef.current) {
      await restartCamera();
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    if (!canvas.width || !canvas.height) {
      setScanMessage("La cámara todavía no está lista. Intenta de nuevo en un momento.");
      return;
    }
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL("image/jpeg", 0.9);

    let detected = "";
    if ("BarcodeDetector" in window) {
      try {
        const results = await new window.BarcodeDetector().detect(canvas);
        detected = String(results[0]?.rawValue || "").trim();
      } catch {
        detected = "";
      }
    }
    const digits = detected || String(barcode || "").trim();
    stopCamera();
    if (!digits) {
      setScanMessage("No se pudo leer el código en la foto. Enciende la cámara otra vez o escribe los dígitos.");
      return;
    }
    if (detected && detected !== barcode) setBarcode(detected);
    setScanMessage("Imagen del código enviada. Toca el botón para volver a encender la cámara.");
    onImage?.({ data, mime_type: "image/jpeg", codigo: digits });
  }

  async function handleFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const data = await readAsDataURL(file);
      stopCamera();
      setScanMessage("Imagen del código enviada a analizar.");
      onImage?.({ data, mime_type: file.type || mimeFromDataURL(data), codigo: barcode });
    } catch (error) {
      setScanMessage(error.message || "No se pudo leer la imagen.");
    } finally {
      event.target.value = "";
    }
  }

  return <><div className="barcode-zone barcode-camera-zone"><div className="barcode-camera-preview">{cameraReady ? <video ref={videoRef} autoPlay muted playsInline aria-label="Vista previa del escáner" /> : <span><Icon name="scan" size={25} /> Cámara desactivada</span>}</div><div className="barcode-actions"><button type="button" className="barcode-scan-button" onClick={scanCode}><Icon name="scan" size={18} /> Leer dígitos</button><button type="button" className="barcode-scan-button button-soft" onClick={captureFrame} aria-label={cameraReady ? "Tomar foto del código" : "Encender cámara para tomar foto del código"}><Icon name="camera" size={18} /> {cameraReady ? "Usar imagen del código" : "Encender cámara"}</button><button type="button" className="barcode-scan-button button-soft" onClick={() => fileInput.current?.click()}><Icon name="image" size={18} /> Subir imagen</button></div>{scanMessage && <p className="barcode-scan-message">{scanMessage}</p>}<input ref={fileInput} className="photo-file-input" type="file" accept="image/*" onChange={handleFile} /></div><label className="barcode-manual-label">Pista de dígitos (opcional)<div className="barcode-manual-input"><input value={barcode} onChange={(event) => setBarcode(event.target.value)} placeholder="Código de barras" aria-label="Código de barras" /></div></label></>;
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
  { emoji: "🍏", keywords: "manzana verde fruta" },
  { emoji: "🥭", keywords: "mango fruta" },
  { emoji: "🍈", keywords: "melon fruta" },
  { emoji: "🫒", keywords: "aceituna oliva aceite" },
  { emoji: "🌰", keywords: "castana nuez fruto seco" },
  { emoji: "🍠", keywords: "camote batata papa dulce" },
  { emoji: "🍜", keywords: "fideos noodles ramen" },
  { emoji: "🍟", keywords: "papas fritas papa frita" },
  { emoji: "🥪", keywords: "sandwich emparedado" },
  { emoji: "🥨", keywords: "pretzel galleta salada" },
  { emoji: "🥒", keywords: "pepino verdura" },
  { emoji: "🫑", keywords: "pimiento verdura" },
  { emoji: "🥗", keywords: "ensalada verdura" },
  { emoji: "🍲", keywords: "sopa caldo olla" },
  { emoji: "🍛", keywords: "curry arroz comida" },
  { emoji: "🦐", keywords: "camaron marisco" },
  { emoji: "🍤", keywords: "camaron frito marisco" },
  { emoji: "🍣", keywords: "sushi pescado arroz" },
  { emoji: "🥓", keywords: "tocino bacon carne" },
  { emoji: "🍔", keywords: "hamburguesa carne pan" },
  { emoji: "🌭", keywords: "hotdog salchicha perro caliente" },
  { emoji: "🍕", keywords: "pizza" },
  { emoji: "🌮", keywords: "taco tortilla comida" },
  { emoji: "🫚", keywords: "jengibre especia" },
  { emoji: "🌿", keywords: "hierba especia condimento" },
  { emoji: "🫖", keywords: "tetera te" },
  { emoji: "🧊", keywords: "hielo frio" },
  { emoji: "🍺", keywords: "cerveza bebida" },
  { emoji: "🍷", keywords: "vino bebida" },
  { emoji: "🍽️", keywords: "plato comida" },
  { emoji: "🥄", keywords: "cuchara utensilio" },
  { emoji: "🍴", keywords: "tenedor utensilio" },
  { emoji: "🔪", keywords: "cuchillo utensilio" },
  { emoji: "🧯", keywords: "extintor seguridad" },
  { emoji: "💡", keywords: "bombillo luz lampara" },
  { emoji: "🔦", keywords: "linterna luz" },
  { emoji: "🪥", keywords: "cepillo dental higiene" },
  { emoji: "🧾", keywords: "recibo boleta comprobante" },
  { emoji: "⚖️", keywords: "balanza peso medida" },
  { emoji: "🧰", keywords: "herramientas caja herramienta" },
  { emoji: "🔧", keywords: "herramienta llave reparacion" },
  { emoji: "🐾", keywords: "mascota animal huella" },
  { emoji: "🦴", keywords: "hueso mascota perro" },
  { emoji: "🌱", keywords: "planta semilla" },
  { emoji: "🪴", keywords: "maceta planta" },
  { emoji: "🎁", keywords: "regalo obsequio" },
  { emoji: "✏️", keywords: "lapiz papeleria utiles" },
  { emoji: "📚", keywords: "libros libro papeleria" },
  { emoji: "🧸", keywords: "juguete peluche" },
  { emoji: "⚽", keywords: "balon futbol deporte" },
  { emoji: "🎲", keywords: "dados juego azar" },
  { emoji: "💻", keywords: "computadora laptop tecnologia" },
  { emoji: "📱", keywords: "celular telefono tecnologia" },
  { emoji: "🔋", keywords: "bateria pila" },
  { emoji: "💊", keywords: "medicina pastilla farmacia" },
  { emoji: "🩹", keywords: "vendaje curita farmacia" },
  { emoji: "🧪", keywords: "laboratorio quimica prueba" },
  { emoji: "🚿", keywords: "ducha regadera bano" },
  { emoji: "🛁", keywords: "bano tina higiene" },
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

export function CategoryPicker({ value, onChange, categories = [], onCreateCategory }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
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

  const term = query.trim();
  const key = term.toLocaleLowerCase("es");
  const options = categories.filter((item) => !key || String(item).toLocaleLowerCase("es").includes(key));
  const exists = categories.some((item) => String(item).toLocaleLowerCase("es") === key);

  async function addCategory() {
    if (!term || busy) return;
    setBusy(true);
    setError("");
    try {
      const created = await onCreateCategory?.(term);
      if (!created) throw new Error("No se pudo agregar la categoría.");
      onChange(created);
      setQuery("");
      setOpen(false);
    } catch (caught) {
      setError(caught.message || "No se pudo agregar la categoría.");
    } finally {
      setBusy(false);
    }
  }

  return <div className="category-picker" ref={rootRef}>
    <button type="button" className="category-picker-trigger" aria-haspopup="dialog" aria-expanded={open} aria-label="Elegir categoría del producto" onClick={() => setOpen((current) => !current)}><span>{value || "Abarrotes"}</span><span aria-hidden="true">▾</span></button>
    <input type="hidden" name="category" value={value || "Abarrotes"} />
    {open && <div className="category-picker-popover" role="dialog" aria-label="Elegir categoría">
      <div className="icon-picker-search"><Icon name="search" size={15} /><input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar o crear categoría..." aria-label="Buscar categoría" /></div>
      <div className="category-picker-options">{options.map((item) => <button type="button" key={item} className={`category-picker-option ${value === item ? "selected" : ""}`} onClick={() => { onChange(item); setQuery(""); setOpen(false); }}>{item}</button>)}</div>
      {term && !exists && <button type="button" className="category-picker-create" onClick={addCategory} disabled={busy}><Icon name="plus" size={14} /> Agregar nueva categoría «{term}»</button>}
      {options.length === 0 && !term && <p className="icon-picker-empty">Todavía no hay categorías.</p>}
      {error && <p className="category-picker-error" role="alert">{error}</p>}
    </div>}
  </div>;
}

export function ProductForm({ value, onChange, onSubmit, onClose, status, error, categories = [], onCreateCategory }) {
  return <form className="product-form" onSubmit={(event) => { event.preventDefault(); onSubmit(value); }}>
    <label className="full-field">Nombre del producto<input name="productName" value={value.productName} onChange={(event) => onChange("productName", event.target.value)} placeholder="Nombre del producto" required /></label>
    <div className="full-field product-icon-field"><span className="field-label">Ícono</span><ProductIconPicker value={value.icon} onChange={(icon) => onChange("icon", icon)} /></div>
    <div className="full-field product-category-field"><span className="field-label">Categoría</span><CategoryPicker value={value.category} onChange={(category) => onChange("category", category)} categories={categories} onCreateCategory={onCreateCategory} /></div>
    <label>Cantidad<div className="input-with-suffix"><input name="quantity" type="number" min="1" value={value.quantity} onChange={(event) => onChange("quantity", event.target.value)} placeholder="0" required /><select name="unit" aria-label="Unidad" value={value.unit} onChange={(event) => onChange("unit", event.target.value)}><option>unid.</option><option>kg</option><option>paq.</option><option>caja</option><option>litro</option></select></div></label>
    <label>Precio de venta<div className="input-with-prefix"><span>S/</span><input name="price" type="number" min="0" step="0.10" value={value.price} onChange={(event) => onChange("price", event.target.value)} placeholder="0.00" /></div></label>
    <label>Fecha de vencimiento<input name="expires" type="date" value={value.expires} onChange={(event) => onChange("expires", event.target.value)} /></label>
    <label className="full-field">Código de barras (opcional)<input name="codigoBarras" inputMode="numeric" value={value.codigoBarras} onChange={(event) => onChange("codigoBarras", event.target.value.replace(/\D/g, ""))} placeholder="Solo como referencia" /></label>
    {value.fuente && <p className="full-field ai-source">Fuente sugerida: <a href={value.fuente} target="_blank" rel="noreferrer">{value.fuente}</a></p>}
    <p className="full-field ai-feedback" role="status">{status}</p>
    <p className="full-field ai-error" role="alert">{error}</p>
    <p className="full-field modal-prototype-note">La IA solo propone datos. Revísalos y corrígelos antes de guardar.</p>
    <div className="full-field modal-actions">{onClose && <button type="button" className="button button-secondary" onClick={onClose}>Cancelar</button>}<button type="submit" className="button button-primary">Guardar en inventario</button></div>
  </form>;
}
