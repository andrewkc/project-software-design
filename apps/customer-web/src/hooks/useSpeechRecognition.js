import { useCallback, useEffect, useRef, useState } from "react";

const ERROR_MESSAGES = {
  "not-allowed": "El navegador no tiene permiso para usar el micrófono.",
  "service-not-allowed": "El navegador no permite el dictado en esta página.",
  "audio-capture": "No encontramos un micrófono.",
  "no-speech": "No escuchamos nada. Inténtalo otra vez.",
  network: "El dictado necesita conexión a internet.",
};

const recognitionClass = () => (typeof window === "undefined" ? null : window.SpeechRecognition || window.webkitSpeechRecognition || null);

export function useSpeechRecognition(onFinal) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;
  const supported = Boolean(recognitionClass());

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  const start = useCallback(() => {
    const Recognition = recognitionClass();
    if (!Recognition || recognitionRef.current) return;
    const recognition = new Recognition();
    recognition.lang = "es-PE";
    recognition.interimResults = true;
    recognition.continuous = false;
    let finalText = "";
    recognition.onresult = (event) => {
      let partial = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        if (event.results[index].isFinal) finalText += event.results[index][0].transcript;
        else partial += event.results[index][0].transcript;
      }
      setInterim(`${finalText} ${partial}`.trim());
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") setError(ERROR_MESSAGES[event.error] || "No se pudo usar el dictado.");
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setListening(false);
      setInterim("");
      if (finalText.trim()) onFinalRef.current?.(finalText.trim());
    };
    setError("");
    setInterim("");
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  }, []);

  useEffect(() => () => recognitionRef.current?.abort(), []);

  return { supported, listening, interim, error, start, stop };
}
