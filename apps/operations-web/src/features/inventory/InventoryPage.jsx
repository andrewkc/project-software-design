import React, { useEffect, useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { EmptyState } from "../../components/common/InventoryRows";
import { PageDate } from "../../components/layout/PageDate";

const PAGE_SIZE = 10;
const columns = [["name", "Producto"], ["category", "CATEGORÍA"], ["stock", "Stock"], ["price", "Precio"], ["expires", "Vencimiento"], ["status", "Estado"]];

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

export function InventoryPage({ products, stockTotal, expiringProducts, query, onQueryChange }) {
  const [showCatalog, setShowCatalog] = useState(false);
  const [sort, setSort] = useState({ key: "name", direction: "asc" });
  const [filters, setFilters] = useState(emptyFilters);
  const [openFilter, setOpenFilter] = useState(null);
  const [page, setPage] = useState(1);
  const expiringIds = useMemo(() => new Set(expiringProducts.map((product) => product.id)), [expiringProducts]);

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
  }

  function openCatalog() {
    setShowCatalog(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function closeCatalog() {
    setShowCatalog(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const catalogView = <>
    <button type="button" className="back-to-categories" onClick={closeCatalog}><span aria-hidden="true">←</span> Categor&iacute;as m&aacute;s comunes</button>
    <section className="welcome-row inventory-catalog-heading"><div><h1>Todo tu inventario</h1><p className="welcome-subtitle">Busca, filtra y ordena tus productos.</p></div></section>
    <section className="content-card inventory-card inventory-catalog" id="product-catalog"><div className="inventory-toolbar"><div><h2>{tableProducts.length} resultados <span className="muted-count">&middot; {stockTotal} unidades</span></h2></div><label className="search-field"><Icon name="search" size={17} /><input aria-label="Buscar producto" placeholder="Buscar producto o categor&iacute;a" value={query} onChange={(event) => onQueryChange(event.target.value)} /></label></div><div className="table-toolbar"><span>Filtros por columna</span><button type="button" className="button button-secondary clear-filters" onClick={clearFilters}>Limpiar filtros</button></div><div className="table-wrap"><table className="notion-table"><thead><tr>{columns.map(([key, label]) => <th key={key}><div className="table-header-actions"><button type="button" className="table-sort-button" onClick={() => toggleSort(key)}>{label}<span>{sort.key === key ? sort.direction === "asc" ? "↑" : "↓" : "↕"}</span></button><button type="button" className={`table-filter-button ${filters[key].value ? "active" : ""}`} aria-label={`Filtrar ${label}`} onClick={() => setOpenFilter((current) => current === key ? null : key)}>≡</button></div>{openFilter === key && <div className="column-filter-menu"><select value={filters[key].operator} onChange={(event) => updateFilter(key, "operator", event.target.value)}><option value="contains">Contiene</option><option value="notContains">No contiene</option><option value="is">Es exactamente</option><option value="isNot">No es</option>{(key === "stock" || key === "price") && <><option value="greater">Mayor o igual a</option><option value="less">Menor o igual a</option></>}</select><input autoFocus value={filters[key].value} placeholder="Filtrar valor..." onChange={(event) => updateFilter(key, "value", event.target.value)} /><button type="button" onClick={() => updateFilter(key, "value", "")}>Limpiar</button></div>}</th>)}</tr></thead><tbody>{visibleProducts.map((product) => <tr key={product.id}><td><span className="table-product-icon">{product.icon}</span><span className="table-product-name"><strong>{product.name}</strong></span></td><td>{product.category}</td><td><strong>{product.stock} {product.unit}</strong></td><td>S/ {Number(product.price || 0).toFixed(2)}</td><td>{formatDate(product.expires)}</td><td><span className={`table-status ${getStatus(product, expiringIds) !== "Disponible" ? "table-status-warn" : ""}`}><i />{getStatus(product, expiringIds)}</span></td></tr>)}</tbody></table>{visibleProducts.length === 0 && <EmptyState icon="search" title="No encontramos productos" text="Prueba con otros filtros o registra un producto nuevo." />}</div>{tableProducts.length > 0 && <div className="inventory-pagination"><div>{Array.from({ length: totalPages }, (_, index) => <button type="button" className={page === index + 1 ? "active" : ""} key={index + 1} onClick={() => setPage(index + 1)}>{index * PAGE_SIZE + 1}-{Math.min((index + 1) * PAGE_SIZE, tableProducts.length)}</button>)}</div></div>}</section>
  </>;

  const categoriesView = <><section className="welcome-row"><div><h1>Categor&iacute;as m&aacute;s comunes</h1></div><button type="button" className="button button-primary" onClick={openCatalog}><Icon name="search" size={18} />Ver todos los productos</button></section><section className="inventory-categories"><div className="category-card-grid">{categoryCards.map((category, index) => <article className={`inventory-category-card category-tone-${index % 6}`} key={category.name}><div className="category-card-art" aria-hidden="true" /><div className="category-card-content"><h3>{category.name}</h3></div></article>)}</div>{categoryCards.length === 0 && <EmptyState icon="box" title="A&uacute;n no tienes categor&iacute;as" text="Registra un producto para empezar a organizar tu inventario." />}</section></>;

  return <div className="page-content inner-page"><PageDate />{showCatalog ? catalogView : categoriesView}</div>;
}
