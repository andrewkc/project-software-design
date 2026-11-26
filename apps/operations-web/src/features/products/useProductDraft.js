import { useCallback, useState } from "react";
import { api } from "../../lib/api";

const EMPTY_DRAFT = {
  productName: "",
  icon: "📦",
  category: "Abarrotes",
  quantity: "",
  unit: "unid.",
  price: "",
  expires: "",
  codigoBarras: "",
  fuente: "",
};

const FIELD_MAP = {
  nombre: "productName",
  icono: "icon",
  categoria: "category",
  cantidad: "quantity",
  unidad: "unit",
  precio_venta: "price",
  fecha_vencimiento: "expires",
  codigo_barras: "codigoBarras",
  fuente: "fuente",
};

function newDraft() {
  return { ...EMPTY_DRAFT };
}

export function useProductDraft() {
  const [draft, setDraft] = useState(newDraft);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [aiModel, setAiModel] = useState("");

  const setField = useCallback((field, value) => {
    setDraft((current) => ({ ...current, [field]: value }));
  }, []);

  const clear = useCallback(() => {
    setDraft(newDraft());
    setStatus("");
    setError("");
  }, []);

  const applyFields = useCallback((fields = {}) => {
    setDraft((current) => {
      const next = { ...current };
      Object.entries(fields).forEach(([key, value]) => {
        const field = FIELD_MAP[key];
        if (field && value !== null && value !== undefined && value !== "") next[field] = value;
      });
      return next;
    });
  }, []);

  const applyProduct = useCallback((product) => {
    setDraft({
      ...newDraft(),
      productName: product.name || "",
      icon: product.icon || "📦",
      category: product.category || "Abarrotes",
      quantity: product.stock || "",
      unit: product.unit || "unid.",
      price: product.price || "",
      expires: product.expires || "",
    });
    setStatus("Datos de un producto anterior copiados. Revísalos antes de guardar.");
    setError("");
  }, []);

  const analyze = useCallback(async (modo, media, modelo = aiModel) => {
    if (media?.error) {
      setStatus("");
      setError(media.error);
      return null;
    }
    setStatus(
      modo === "barcode"
        ? "Consultando el código en Open Food Facts..."
        : `Analizando con IA (${modo === "voice" ? "voz" : "foto"})...`
    );
    setError("");
    try {
      const result = await api.extractProduct({
        modo,
        ...media,
        ...(modelo ? { modelo } : {}),
      });
      applyFields(result.campos || {});
      setStatus(result.mensaje || "Borrador listo; revisa los campos antes de guardar.");
      return result;
    } catch (caught) {
      setStatus("");
      setError(caught.message || "No se pudo analizar la multimedia.");
      return null;
    }
  }, [applyFields, aiModel]);

  return {
    draft, setField, setError, clear, applyFields, applyProduct,
    analyze, aiModel, setAiModel, status, error,
  };
}
