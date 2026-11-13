import React from "react";
import { Icon } from "../Icon";

export function InsightCard({ number, icon, title, text, takeaway, tone }) {
  return <article className={`insight-card insight-${tone}`}><div className="insight-card-top"><span><Icon name={icon} size={19} /></span><small>HALLAZGO {number}</small></div><h2>{title}</h2><p>{text}</p><div className="insight-takeaway"><strong>&iquest;Qu&eacute; significa para el dise&ntilde;o?</strong><span>{takeaway}</span></div></article>;
}
