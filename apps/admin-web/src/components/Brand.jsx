import React, { useState } from "react";
import { Icon } from "./Icon";

const FULL_LOGO = "/assets/BodeSmart-Logo.png";
const MOBILE_LOGO = "/assets/BodeSmart-Mobile-Logo.png";

export function Brand({ light = false, mobile = false, className = "" }) {
  const [useFallback, setUseFallback] = useState(false);

  if (useFallback) return <span className={`brand ${light ? "brand-light" : ""} ${className}`}>
    <span className="brand-mark"><Icon name="shield" size={20} /></span>
    Bode<span className="brand-accent">Smart</span>
  </span>;

  return <img
    className={`brand-logo ${light ? "brand-light" : ""} ${className}`}
    src={mobile ? MOBILE_LOGO : FULL_LOGO}
    alt="BodeSmart"
    onError={() => setUseFallback(true)}
  />;
}
