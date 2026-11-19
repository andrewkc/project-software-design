import React, { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { workspaceCopy } from "../../lib/workspaceCopy";

export function ProductModal({ method, user, onClose, onSubmit, voiceCaptured, setVoiceCaptured, photoName, setPhotoName, barcode, setBarcode }) {
  const [prefill, setPrefill] = useState(false);
  const copy = workspaceCopy(user);
  const title = method?.id === "photo" ? "Registra con una foto" : method?.id === "voice" ? "Registra con tu voz" : method?.id === "scan" ? "Escanea el c&oacute;digo" : "Escribe los detalles";
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-header"><span className={`modal-method-icon method-${method?.tint}`}><Icon name={method?.icon} size={21} /></span><button type="button" className="icon-button close-modal" aria-label="Cerrar" onClick={onClose}><Icon name="close" size={20} /></button><span className="section-kicker">NUEVA MERCADER&Iacute;A</span><h2 id="modal-title">{title}</h2><p>{copy.modalHint}</p></div>{method?.id === "photo" && <PhotoCapture photoName={photoName} setPhotoName={setPhotoName} />}{method?.id === "voice" && <VoiceCapture captured={voiceCaptured} onCapture={() => { setVoiceCaptured(true); setPrefill(true); }} />}{method?.id === "scan" && <BarcodeCapture barcode={barcode} setBarcode={setBarcode} onExample={() => { setBarcode("7750182003412"); setPrefill(true); }} />}<ProductForm key={prefill ? "prefilled" : "empty"} prefill={prefill} onSubmit={onSubmit} onClose={onClose} /></section></div>;
}

export function PhotoCapture({ photoName, setPhotoName }) {
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

  return <div className={`photo-camera ${photoName ? "has-photo" : ""}`}><div className="photo-camera-preview">{capturedImage ? <img src={capturedImage} alt="Producto capturado" /> : cameraReady ? <video ref={videoRef} autoPlay muted playsInline aria-label="Vista previa de la cámara" /> : <span>Activa la cámara para enfocar el producto</span>}</div><div className="photo-camera-controls"><button type="button" className="photo-gallery-button" aria-label="Elegir una foto de la galería" onClick={() => galleryInput.current?.click()}><Icon name="image" size={22} /></button>{capturedImage ? <button type="button" className="photo-retake-button photo-shutter-replacement" aria-label="Repetir toma de foto" onClick={repeatPhoto}><Icon name="refresh" size={21} /></button> : <button type="button" className="photo-shutter" aria-label="Tomar foto" onClick={capturePhoto}><span /></button>}<button type="button" className="photo-flash-button" aria-label="Flash desactivado" disabled><Icon name="flash" size={21} /></button></div><p className="photo-ai-note"><Icon name="sparkles" size={14} /> La IA reconocer&aacute; el producto en la imagen.</p><input ref={cameraInput} className="photo-file-input" type="file" accept="image/*" capture="environment" onChange={handleSelectedFile} /><input ref={galleryInput} className="photo-file-input" type="file" accept="image/*" onChange={handleSelectedFile} /></div>;
}

export function VoiceCapture({ captured, onCapture }) { return <div className={`voice-capture ${captured ? "recorded" : ""}`}><button type="button" className="mic-button" aria-label={captured ? "Ejemplo de voz transcrito" : "Probar grabaci&oacute;n de voz"} onClick={onCapture}><Icon name={captured ? "check" : "mic"} size={22} /></button><strong>{captured ? "¡Listo! Te escuchamos" : "Toca el micrófono para empezar"}</strong>
{/* <small>{captured ? "Agrega 6 yogures naturales &middot; ejemplo de demostración" : "Prueba una grabación de ejemplo"}</small> */}
</div>; }

export function BarcodeCapture({ barcode, setBarcode, onExample }) {
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
        setScanMessage("No se pudo activar la c�mara. Ingresa el Código manualmente.");
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
      if (results[0]?.rawValue) { setBarcode(results[0].rawValue); setScanMessage("Código obtenido correctamente."); stopCamera(); }
      else setScanMessage("No encontramos un código. Intenta nuevamente.");
    } catch {
      setScanMessage("No se pudo leer el código. Puedes ingresarlo manualmente.");
    }
  }

  return <><div className="barcode-zone barcode-camera-zone"><div className="barcode-camera-preview">{cameraReady ? <video ref={videoRef} autoPlay muted playsInline aria-label="Vista previa del escáner" /> : <span><Icon name="scan" size={25} /> Cámara desactivada</span>}</div><button type="button" className="barcode-scan-button" onClick={scanCode}><Icon name="scan" size={18} /> Escanear código</button>{scanMessage && <p className="barcode-scan-message">{scanMessage}</p>}</div><label className="barcode-manual-label">Buscar código directamente<div className="barcode-manual-input"><input value={barcode} onChange={(event) => setBarcode(event.target.value)} placeholder="Código de barras" aria-label="Código de barras" /><button type="button" aria-label="Buscar Código" onClick={() => setScanMessage(barcode.trim() ? "Código listo para registrar." : "Ingresa un Código primero.")}><Icon name="search" size={17} /></button></div></label></>;
}

export function ProductForm({ prefill, onSubmit, onClose }) { return <form className="product-form" onSubmit={onSubmit}><label className="full-field">Nombre del producto<input name="productName" placeholder="Ej. Yogurt natural" defaultValue={prefill ? "Yogurt natural" : ""} required /></label><label>Icono / emoji<input name="icon" type="text" placeholder="📦" maxLength="8" defaultValue={prefill ? "🥛" : "📦"} /></label><label>Categor&iacute;a<select name="category" defaultValue="Abarrotes"><option>Abarrotes</option><option>L&aacute;cteos</option><option>Frutas</option><option>Bebidas</option><option>Limpieza</option><option>Otros</option></select></label><label>Cantidad<div className="input-with-suffix"><input name="quantity" type="number" min="1" defaultValue={prefill ? "6" : ""} placeholder="0" required /><select name="unit" aria-label="Unidad"><option>unid.</option><option>kg</option><option>paq.</option><option>caja</option><option>litro</option></select></div></label><label>Precio de venta<div className="input-with-prefix"><span>S/</span><input name="price" type="number" min="0" step="0.10" placeholder="0.00" /></div></label><label>Fecha de vencimiento<input name="expires" type="date" /></label><p className="modal-prototype-note" /><div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancelar</button><button type="submit" className="button button-primary">Guardar en inventario</button></div></form>; }
