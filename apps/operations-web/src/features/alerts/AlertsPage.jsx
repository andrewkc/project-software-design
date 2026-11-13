import React from "react";
import { Icon } from "../../components/Icon";
import { EmptyState, ProductRow } from "../../components/common/InventoryRows";

export function AlertsPage({ expiringProducts }) {
  return <div className="page-content inner-page"><section className="welcome-row"><div><p className="date-greeting">CUIDA LO QUE YA COMPRASTE</p><h1>Fechas importantes</h1><p className="welcome-subtitle">Revisa lo que est&aacute; pr&oacute;ximo a vencer y decide qu&eacute; hacer.</p></div><span className="alert-counter"><Icon name="clock" size={18} /> {expiringProducts.length} por revisar</span></section><section className="content-card alerts-card"><div className="card-heading"><div><span className="section-kicker">PR&Oacute;XIMOS 7 D&Iacute;AS</span><h2>Productos que necesitan atenci&oacute;n</h2></div></div>{expiringProducts.length ? <div className="product-list">{expiringProducts.map((product) => <ProductRow key={product.id} product={product} type="expiry" />)}</div> : <EmptyState icon="check" title="&iexcl;Todo bajo control!" text="No tienes productos pr&oacute;ximos a vencer." />}</section><div className="gentle-reminder"><span>&#128161;</span><p><strong>Un recordatorio &uacute;til</strong><br />La alerta usa la fecha de vencimiento que registraste. Recuerda revisar el estado del producto antes de decidir venderlo o retirarlo.</p></div></div>;
}
