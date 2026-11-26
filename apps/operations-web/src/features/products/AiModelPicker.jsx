import React from "react";
import { Icon } from "../../components/Icon";

/** Model selector backed by the backend allowlist; no key or URL reaches here. */
export function AiModelPicker({ models = [], value, onChange }) {
  if (!models.length) return null;
  const current = value || models.find((model) => model.activo)?.id || models[0].id;
  return <label className="ai-model-picker">
    <span><Icon name="sparkles" size={14} /> Modelo de IA</span>
    <select value={current} onChange={(event) => onChange(event.target.value)}>
      {models.map((model) => <option key={model.id} value={model.id}>
        {model.label || model.id}{model.activo ? " (actual)" : ""}
      </option>)}
    </select>
    <small>Solo modelos permitidos por el servidor. La clave de Gemini no sale del backend.</small>
  </label>;
}
