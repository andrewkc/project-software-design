import React, { useState } from "react";
import { Icon } from "../Icon";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition";

export function VoiceInput({ example, onText }) {
  const [typed, setTyped] = useState("");
  const [heard, setHeard] = useState("");
  const speech = useSpeechRecognition((text) => {
    setHeard(text);
    onText(text);
  });

  function interpretTyped(event) {
    event.preventDefault();
    const text = typed.trim();
    if (!text) return;
    setHeard(text);
    onText(text);
    setTyped("");
  }

  const status = speech.listening ? "Te escuchamos… toca para terminar" : speech.supported ? "Toca el micrófono y habla" : "Este navegador no permite dictar";
  return <div className={`voice-capture voice-input ${speech.listening ? "listening" : ""}`}>
    {speech.supported && <button type="button" className="mic-button" aria-pressed={speech.listening} aria-label={speech.listening ? "Terminar dictado" : "Empezar dictado"} onClick={speech.listening ? speech.stop : speech.start}><Icon name={speech.listening ? "close" : "mic"} size={22} /></button>}
    <strong>{status}</strong>
    <small>Ejemplo: «{example}»</small>
    {speech.interim && <p className="voice-transcript" aria-live="polite">{speech.interim}</p>}
    {!speech.interim && heard && <p className="voice-transcript">Entendimos: «{heard}»</p>}
    {speech.error && <p className="voice-error" role="alert">{speech.error}</p>}
    <form className="voice-typed" onSubmit={interpretTyped}>
      <input aria-label="Texto para interpretar" value={typed} onChange={(event) => setTyped(event.target.value)} placeholder="O escríbelo aquí" />
      <button type="submit">Interpretar</button>
    </form>
  </div>;
}
