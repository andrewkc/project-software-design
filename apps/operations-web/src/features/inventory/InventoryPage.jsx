import React, { useMemo } from "react";
import { Icon } from "../../components/Icon";
import { EmptyState, ProductTableRow } from "../../components/common/InventoryRows";
import { PageDate } from "../../components/layout/PageDate";

export function InventoryPage({ products, filteredProducts, stockTotal, expiringProducts, query, onQueryChange, onRegister }) {
  const categoryCards = useMemo(() => {
    const totals = products.reduce((result, product) => {
      const category = product.category || "Sin categoría";
      const current = result[category] || { name: category, products: 0, units: 0 };
      current.products += 1;
      current.units += Number(product.stock) || 0;
      result[category] = current;
      return result;
    }, {});
    return Object.values(totals).sort((first, second) => second.products - first.products || first.name.localeCompare(second.name, "es"));
  }, [products]);

  return <div className="page-content inner-page">
    <PageDate />
    <section className="welcome-row"><div><h1>Categorías más comunes</h1></div>
    {/* <button type="button" className="button button-primary" onClick={onRegister}><Icon name="plus" size={18} /> Agregar producto</button> */}
    </section>
    <section className="inventory-categories">
      {/* <div className="inventory-section-heading"><h2>Categor&iacute;as m&aacute;s comunes</h2></div> */}
      <div className="category-card-grid">{categoryCards.map((category, index) => <article className={`inventory-category-card category-tone-${index % 6}`} key={category.name}><div className="category-card-art" aria-hidden="true" /><div className="category-card-content"><h3>{category.name}</h3></div></article>)}</div>
      {categoryCards.length === 0 && <EmptyState icon="box" title="A&uacute;n no tienes categor&iacute;as" text="Registra un producto para empezar a organizar tu inventario." />}
      <a className="view-all-products" href="#product-catalog">Ver todos los productos <Icon name="arrow" size={15} /></a>
    </section>
    {/* <section className="content-card inventory-card" id="product-catalog"><div className="inventory-toolbar"><div><span className="section-kicker">CAT&Aacute;LOGO DE PRODUCTOS</span><h2>{products.length} productos <span className="muted-count">&middot; {stockTotal} unidades</span></h2></div><label className="search-field"><Icon name="search" size={17} /><input aria-label="Buscar producto" placeholder="Buscar producto" value={query} onChange={(event) => onQueryChange(event.target.value)} /></label></div><div className="table-wrap"><table><thead><tr><th>PRODUCTO</th><th>STOCK</th><th>PRECIO DE VENTA</th><th>VENCIMIENTO</th><th>ESTADO</th></tr></thead><tbody>{filteredProducts.map((product) => <ProductTableRow key={product.id} product={product} expiring={expiringProducts.some((item) => item.id === product.id)} />)}</tbody></table>{filteredProducts.length === 0 && <EmptyState icon="search" title="No encontramos ese producto" text="Prueba con otro nombre o registra uno nuevo." />}</div></section> */}
    {/* <div className="note-card"><Icon name="shield" size={18} /> */}
    {/* <span><strong>Un registro a la vez.</strong> Cada entrada se suma a tu stock; las ventas y mermas se registran por separado en el flujo completo.</span> */}
    {/* </div> */}
  </div>;
}
