import React, { useState } from "react";
import { Icon } from "../../components/Icon";
import { PageDate } from "../../components/layout/PageDate";
import { api } from "../../lib/api";

const tipoLabels = {
  descuento: "Descuento sugerido",
  aumento: "Ajuste al alza",
  reposicion: "Reposición referencial",
};

export function RecommendationsPage({ user, recommendations, onRecommendationsChange, onApplyPrice, onNotify }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);
  const [price, setPrice] = useState("");

  if (user?.role !== "jefe") return null;

  const items = recommendations?.items || [];
  const generatedAt = recommendations?.generatedAt || "";
  const hasGenerated = Boolean(recommendations?.hasGenerated);

  async function generate() {
    setLoading(true);
    setError("");
    try {
      const result = await api.generateRecommendations();
      onRecommendationsChange({
        items: result.recomendaciones || [],
        generatedAt: result.generadas_en || "",
        hasGenerated: true,
      });
      onNotify?.(result.aviso || "Recomendaciones generadas.");
    } catch (requestError) {
      // Keep the previous cards if a regeneration fails.
      setError(requestError.message || "No se pudieron generar recomendaciones.");
      onNotify?.(requestError.message || "No se pudieron generar recomendaciones.");
    } finally {
      setLoading(false);
    }
  }

  function openEditor(item) {
    setEditing(item);
    setPrice(item.precio_sugerido != null ? String(item.precio_sugerido) : "");
  }

  async function savePrice(event) {
    event.preventDefault();
    if (!editing) return;
    const value = Number(price);
    if (!Number.isFinite(value) || value <= 0) {
      onNotify?.("Ingresa un precio positivo.");
      return;
    }
    const saved = await onApplyPrice(editing.id_producto, { price: value });
    if (saved) {
      onRecommendationsChange((current) => ({
        ...current,
        items: (current.items || []).map((item) => (
          item.id_producto === editing.id_producto && item.tipo === editing.tipo
            ? { ...item, precio_actual: value, precio_sugerido: value }
            : item
        )),
      }));
      setEditing(null);
      onNotify?.("Precio revisado y guardado. La decisión fue tuya, no de la IA.");
    }
  }

  return <div className="page-content inner-page"><PageDate /><section className="welcome-row">
    <div>
      <h1>Recomendaciones de precios</h1>
      <p className="welcome-subtitle">Sugerencias de apoyo para tu decisión, no decisiones automáticas.</p>
    </div>
    <span className="ai-badge"><Icon name="sparkles" size={16} /> Gemini</span>
  </section>

  <section className="content-card recommendations-card">
    <div className="card-heading"><div>
      <span className="section-kicker">SOLO PARA EL JEFE</span>
      <h2>Propuestas para revisar</h2>
    </div>
    <button
      type="button"
      className={`button ${hasGenerated ? "button-soft" : "button-primary"}`}
      onClick={generate}
      disabled={loading}
    >
      {loading ? "Generando..." : hasGenerated ? "Volver a generar recomendaciones" : "Generar recomendaciones"}
    </button>
    </div>

    <p className="prototype-disclaimer">
      La IA usa precio, stock, vencimiento, categoría y estado. No hay datos de costo ni historial de ventas,
      así que las sugerencias no son predicciones validadas. Nada se aplica automáticamente: una reposición
      aprobada no genera compras ni modifica el inventario.
    </p>

    {error && <p className="recommendation-error" role="alert">{error}</p>}

    {!error && !items.length && !loading && (
      <p className="recommendation-empty">Todavía no hay propuestas. Generá una recomendación para verlas.</p>
    )}

    {!!items.length && <div className="recommendation-grid">{items.map((item, index) => (
      <article className="suggestion-card recommendation-item" key={`${item.id_producto}-${item.tipo}-${index}`}>
        <div className="suggestion-topline">
          <span className="suggestion-icon"><Icon name="sparkles" size={16} /></span>
          <span className="suggestion-label">{tipoLabels[item.tipo] || item.tipo}</span>
        </div>
        <div className="recommendation-title">
          <span className="recommendation-icon" aria-hidden="true">{item.icono || "📦"}</span>
          <h2>{item.nombre}</h2>
        </div>
        <p>{item.justificacion}</p>
        {item.tipo === "reposicion" ? (
          <p className="recommendation-value">Stock actual: <strong>{item.stock_actual ?? "—"}</strong> · Cantidad referencial: <strong>{item.cantidad_sugerida ?? "—"}</strong></p>
        ) : (
          <p className="recommendation-value">Precio actual: <strong>S/ {item.precio_actual ?? "—"}</strong> · Sugerido: <strong>S/ {item.precio_sugerido ?? "—"}</strong></p>
        )}
        {item.tipo === "reposicion" ? (
          <span className="suggestion-footnote">Solo referencia interna. No genera pedidos ni cambia stock.</span>
        ) : (
          <button type="button" className="suggestion-action" onClick={() => openEditor(item)}>
            <Icon name="edit" size={14} /> Revisar precio
          </button>
        )}
      </article>
    ))}</div>}

    {generatedAt && <span className="suggestion-footnote">Generadas: {new Date(generatedAt).toLocaleString()}</span>}
  </section>

  {editing && <div className="modal-backdrop" role="dialog" aria-modal="true">
    <form className="product-modal" onSubmit={savePrice}>
      <div className="modal-header">
        <span className="modal-method-icon"><Icon name="edit" size={19} /></span>
        <h2>Revisar precio</h2>
        <p>{editing.nombre}. La IA propuso S/ {editing.precio_sugerido}; podés modificarlo antes de guardar.</p>
      </div>
      <label className="full-field">Precio de venta
        <div className="input-with-prefix"><span>S/</span><input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} required /></div>
      </label>
      <div className="modal-actions">
        <button type="button" className="button button-secondary" onClick={() => setEditing(null)}>Descartar</button>
        <button type="submit" className="button button-primary">Guardar precio</button>
      </div>
    </form>
  </div>}
  </div>;
}
