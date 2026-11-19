import React, { useEffect, useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { EmptyState } from "../../components/common/InventoryRows";
import { PageDate } from "../../components/layout/PageDate";
import { JEFE_ID, canEditProduct, currentUserId, isJefe } from "../../lib/permissions";
import { profileNames } from "../../lib/profileNames";
import { workspaceCopy } from "../../lib/workspaceCopy";

const PAGE_SIZE = 10;
const columns = [["id", "ID"], ["name", "Producto"], ["category", "CATEGORÍA"], ["stock", "Stock"], ["price", "Precio"], ["expires", "Vencimiento"], ["status", "Estado"]];
const operatorLabels = { contains: "Contiene", notContains: "No contiene", is: "Es exactamente", isNot: "No es", greater: "Mayor o igual a", less: "Menor o igual a" };
const unitOptions = ["unid.", "kg", "paq.", "caja", "litro"];
const baseCategories = ["Abarrotes", "Lácteos", "Frutas", "Bebidas", "Limpieza", "Snacks", "Conservas", "Cuidado personal", "Otros"];

function getStatus(product, expiringIds) {
  if (expiringIds.has(product.id)) return "Por vencer";
  if (Number(product.stock) <= 5) return "Stock bajo";
  return "Disponible";
}

function formatDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" }) : "Sin fecha";
}

function getColumnValue(product, key, expiringIds) {
  if (key === "status") return getStatus(product, expiringIds);
  return product[key] || "";
}

function matchesFilter(value, filter) {
  if (!filter.value) return true;
  const current = String(value).toLowerCase();
  const target = filter.value.toLowerCase();
  if (["greater", "less"].includes(filter.operator)) {
    const currentNumber = Number(value);
    const targetNumber = Number(filter.value);
    return filter.operator === "greater" ? currentNumber >= targetNumber : currentNumber <= targetNumber;
  }
  if (filter.operator === "is") return current === target;
  if (filter.operator === "isNot") return current !== target;
  if (filter.operator === "notContains") return !current.includes(target);
  return current.includes(target);
}

const emptyFilters = Object.fromEntries(columns.map(([key]) => [key, { operator: key === "stock" || key === "price" ? "greater" : "contains", value: "" }]));

export function InventoryPage({ products, expiringProducts, query, onQueryChange, user, employees, jefeProfile, onUpdateProduct, onSetProductActive, onToggleLock }) {
  const [showCatalog, setShowCatalog] = useState(false);
  const [sort, setSort] = useState({ key: "name", direction: "asc" });
  const [filters, setFilters] = useState(emptyFilters);
  const [openFilter, setOpenFilter] = useState(null);
  const [openOperator, setOpenOperator] = useState(null);
  const [page, setPage] = useState(1);
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState({});
  const expiringIds = useMemo(() => new Set(expiringProducts.map((product) => product.id)), [expiringProducts]);
  const categoryOptions = useMemo(() => Array.from(new Set([...baseCategories, ...products.map((product) => product.category).filter(Boolean)])), [products]);
  const jefe = isJefe(user);
  const copy = workspaceCopy(user);
  const userId = currentUserId(user);
  const canEdit = (product) => canEditProduct(product, user);
  const toggleLock = (product) => {
    if (!jefe) return;
    if (editingId === product.id) cancelEditing();
    onToggleLock(product.id);
  };

  function ownerLabel(product) {
    if (product.creadoPor === userId) return "Agregado por usted";
    const employee = employees.find((item) => item.id === product.creadoPor);
    if (employee) return `Agregado por ${profileNames(employee).displayName}`;
    const jefe = jefeProfile || (isJefe(user) ? user : null);
    if (jefe && (product.creadoPor === jefe.id || product.creadoPor === JEFE_ID)) {
      return `Agregado por ${profileNames(jefe).displayName}`;
    }
    return "Agregado por empleado retirado";
  }

  function startEditing(product) {
    setEditingId(product.id);
    setDraft({ name: product.name, category: product.category, stock: product.stock, unit: product.unit, price: product.price, expires: product.expires || "" });
    setOpenFilter(null);
  }

  function cancelEditing() {
    setEditingId(null);
    setDraft({});
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function saveEditing() {
    const name = String(draft.name || "").trim();
    const stock = Number(draft.stock);
    const price = Number(draft.price);
    if (!name || !Number.isFinite(stock) || stock < 0 || !Number.isFinite(price) || price < 0) return;
    const target = products.find((product) => product.id === editingId);
    if (!canEdit(target)) return;
    onUpdateProduct(editingId, { name, category: draft.category, stock, unit: draft.unit, price, expires: draft.expires });
    cancelEditing();
  }

  function confirmDeactivate(product) {
    if (!jefe) return;
    const message = product.activo === false
      ? `¿Reactivar "${product.name}" en el inventario?`
      : `¿Desactivar "${product.name}"? La fila se conservará en el historial.`;
    if (!window.confirm(message)) return;
    if (editingId === product.id) cancelEditing();
    onSetProductActive(product.id, product.activo === false);
  }

  const categoryCards = useMemo(() => {
    const totals = products.reduce((result, product) => {
      const category = product.category || "Sin categoría";
      const current = result[category] || { name: category, products: 0 };
      current.products += 1;
      result[category] = current;
      return result;
    }, {});
    return Object.values(totals).sort((first, second) => second.products - first.products || first.name.localeCompare(second.name, "es"));
  }, [products]);

  const tableProducts = useMemo(() => {
    const filtered = products.filter((product) => {
      const matchesGlobalSearch = `${product.name} ${product.category}`.toLowerCase().includes(query.toLowerCase());
      return matchesGlobalSearch && columns.every(([key]) => matchesFilter(getColumnValue(product, key, expiringIds), filters[key]));
    });
    return filtered.sort((first, second) => {
      const firstValue = getColumnValue(first, sort.key, expiringIds);
      const secondValue = getColumnValue(second, sort.key, expiringIds);
      const comparison = sort.key === "stock" || sort.key === "price" ? Number(firstValue) - Number(secondValue) : String(firstValue).localeCompare(String(secondValue), "es", { numeric: true, sensitivity: "base" });
      return sort.direction === "asc" ? comparison : -comparison;
    });
  }, [products, query, filters, sort, expiringIds]);

  const totalPages = Math.max(1, Math.ceil(tableProducts.length / PAGE_SIZE));
  const visibleProducts = tableProducts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const filteredStockTotal = useMemo(() => tableProducts.reduce((total, product) => total + (Number(product.stock) || 0), 0), [tableProducts]);

  useEffect(() => setPage(1), [query, filters, sort]);

  function updateFilter(key, property, value) {
    setFilters((current) => ({ ...current, [key]: { ...current[key], [property]: value } }));
  }

  function toggleSort(key) {
    setSort((current) => current.key === key ? { key, direction: current.direction === "asc" ? "desc" : "asc" } : { key, direction: "asc" });
  }

  function clearFilters() {
    setFilters(emptyFilters);
    onQueryChange("");
    setOpenFilter(null);
    setOpenOperator(null);
  }

  function openCatalog(category) {
    if (category) setFilters((current) => ({ ...current, category: { operator: "is", value: category } }));
    else setFilters(emptyFilters);
    setShowCatalog(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function closeCatalog() {
    setShowCatalog(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const catalogView = <>
    <button type="button" className="back-to-categories" onClick={closeCatalog}><span aria-hidden="true">←</span> Categorías más comunes</button>
    <section className="welcome-row inventory-catalog-heading"><div><h1>{copy.inventoryTitle}</h1><p className="welcome-subtitle">{copy.inventorySubtitle}</p></div></section>
    <section className="content-card inventory-card inventory-catalog" id="product-catalog"><div className="inventory-toolbar"><div>
      <h2>{tableProducts.length} resultados <span className="muted-count">&nbsp;{filteredStockTotal} unidades</span></h2>
      </div><label className="search-field"><Icon name="search" size={17} /><input aria-label="Buscar producto" placeholder="Buscar producto o categor&iacute;a" value={query} onChange={(event) => onQueryChange(event.target.value)} /></label></div><div className="table-toolbar"><
        span>Filtros por columna</span>
      <span className="table-toolbar-break" aria-hidden="true" />
      {!jefe && <span className="permission-hint">Puedes editar solo las filas que creaste</span>}<button type="button" className="button button-secondary clear-filters" onClick={clearFilters}>Limpiar filtros</button>
      </div><div className="table-wrap"><table className="notion-table"><thead><tr>{columns.map(([key, label]) => <th key={key}><div className="table-header-actions"><button type="button" className="table-sort-button" onClick={() => toggleSort(key)}>{label}<span>{sort.key === key ? sort.direction === "asc" ? "↑" : "↓" : "↕"}</span></button><button type="button" className={`table-filter-button ${filters[key].value ? "active" : ""}`} aria-label={`Filtrar ${label}`} onClick={() => setOpenFilter((current) => current === key ? null : key)}><Icon name={openFilter === key ? "close" : "filter"} size={12} /></button></div>{openFilter === key && <div className="column-filter-menu"><div className="filter-operator"><button type="button" className="filter-operator-trigger" onClick={() => setOpenOperator((current) => current === key ? null : key)}>{operatorLabels[filters[key].operator]}<Icon name="options" size={14} /></button>{openOperator === key && <div className="filter-operator-options">{Object.entries(operatorLabels).filter(([operator]) => (key === "stock" || key === "price") || !["greater", "less"].includes(operator)).map(([operator, label]) => <button type="button" className={filters[key].operator === operator ? "selected" : ""} key={operator} onClick={() => { updateFilter(key, "operator", operator); setOpenOperator(null); }}>{label}</button>)}</div>}</div><input autoFocus value={filters[key].value} placeholder="Filtrar valor..." onChange={(event) => updateFilter(key, "value", event.target.value)} /><button type="button" onClick={() => updateFilter(key, "value", "")}>Limpiar</button></div>}</th>)}<th className="row-actions-head"><span className="sr-only">Acciones</span></th></tr></thead>
<tbody>{visibleProducts.map((product) => <tr key={product.id}><td className="row-id-cell">#{product.id}</td><td><span className="table-product-icon">{product.icon}</span><span className="table-product-name">{editingId === product.id ? <input className="cell-input cell-input-name" value={draft.name} onChange={(event) => updateDraft("name", event.target.value)} aria-label="Nombre del producto" /> : <strong className={product.activo === false ? "product-inactive" : ""}>{product.name}</strong>}{product.bloqueado && <span className="row-flag row-flag-lock" title="Bloqueado por el jefe"><Icon name="lock" size={11} /></span>}{product.activo === false && <span className="row-flag" title="Producto desactivado">Inactivo</span>}{jefe && <span className="row-flag row-flag-owner" title="Creado por">{ownerLabel(product)}</span>}</span></td><td>{editingId === product.id ? <select className="cell-input cell-select" value={draft.category} onChange={(event) => updateDraft("category", event.target.value)} aria-label="Categoría">{categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}</select> : product.category}</td><td>{editingId === product.id ? <span className="cell-inline-group"><input className="cell-input cell-input-number" type="number" min="0" value={draft.stock} onChange={(event) => updateDraft("stock", event.target.value)} aria-label="Stock" /><select className="cell-input cell-select cell-select-unit" value={draft.unit} onChange={(event) => updateDraft("unit", event.target.value)} aria-label="Unidad">{unitOptions.map((unit) => <option key={unit} value={unit}>{unit}</option>)}</select></span> : <strong>{product.stock} {product.unit}</strong>}</td><td>{editingId === product.id ? <span className="cell-prefix"><span>S/</span><input className="cell-input cell-input-number" type="number" min="0" step="0.01" value={draft.price} onChange={(event) => updateDraft("price", event.target.value)} aria-label="Precio" /></span> : `S/ ${Number(product.price || 0).toFixed(2)}`}</td><td>{editingId === product.id ? <input className="cell-input cell-input-date" type="date" value={draft.expires} onChange={(event) => updateDraft("expires", event.target.value)} aria-label="Fecha de vencimiento" /> : formatDate(product.expires)}</td><td><span className={`table-status ${getStatus(product, expiringIds) !== "Disponible" ? "table-status-warn" : ""}`}><i />{getStatus(product, expiringIds)}</span></td>
<td className="row-actions-cell">{editingId === product.id ? <span className="row-actions"><button type="button" className="row-action row-action-save" aria-label="Guardar cambios" onClick={saveEditing}><Icon name="check" size={14} /></button><button type="button" className="row-action" aria-label="Cancelar edición" onClick={cancelEditing}><Icon name="close" size={14} /></button></span> : <span className="row-actions">{jefe && <button type="button" className={`row-action row-action-lock ${product.bloqueado ? "locked" : ""}`} aria-label={product.bloqueado ? "Desbloquear " + product.name : "Bloquear " + product.name} title={product.bloqueado ? "Desbloquear fila" : "Bloquear fila: solo el jefe podrá editarla"} onClick={() => toggleLock(product)}><Icon name={product.bloqueado ? "lock" : "unlock"} size={14} /></button>}{canEdit(product) && <button type="button" className="row-action" aria-label={"Editar " + product.name} onClick={() => startEditing(product)}><Icon name="edit" size={14} /></button>}{jefe && <button type="button" className="row-action row-action-delete" aria-label={product.activo === false ? "Reactivar " + product.name : "Desactivar " + product.name} title={product.activo === false ? "Reactivar producto" : "Desactivar producto"} onClick={() => confirmDeactivate(product)}><Icon name={product.activo === false ? "refresh" : "trash"} size={14} /></button>}</span>}</td></tr>)}</tbody></table>{visibleProducts.length === 0 && <EmptyState icon="search" title="No encontramos productos" text="Prueba con otros filtros o registra un producto nuevo." />}</div>{tableProducts.length > 0 && <div className="inventory-pagination"><div>{Array.from({ length: totalPages }, (_, index) => <button type="button" className={page === index + 1 ? "active" : ""} key={index + 1} onClick={() => setPage(index + 1)}>{index * PAGE_SIZE + 1}-{Math.min((index + 1) * PAGE_SIZE, tableProducts.length)}</button>)}</div></div>}
      </section>
  </>;

  const categoriesView = <><section className="welcome-row"><div><h1>Categorías más comunes</h1></div><button type="button" className="button button-primary" onClick={() => openCatalog()}><Icon name="search" size={18} />Ver todos los productos</button></section><section className="inventory-categories"><div className="category-card-grid">{categoryCards.map((category, index) => <button type="button" className={`inventory-category-card category-tone-${index % 6}`} key={category.name} onClick={() => openCatalog(category.name)}><div className="category-card-art" aria-hidden="true" /><div className="category-card-content"><h3>{category.name}</h3></div></button>)}</div>{categoryCards.length === 0 && <EmptyState icon="box" title={copy.noCategoriesTitle} text={copy.noCategoriesText} />}</section></>;

  return <div className="page-content inner-page"><PageDate />{showCatalog ? catalogView : categoriesView}</div>;
}
