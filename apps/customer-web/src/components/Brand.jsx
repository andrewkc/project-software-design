import React, { useState } from "react";

const FULL_LOGO = "/assets/BodeSmart-Logo.png";
const MOBILE_LOGO = "/assets/BodeSmart-Mobile-Logo.png";

export function Brand({ mobile = false, className = "" }) {
  const [useFallback, setUseFallback] = useState(false);

  if (useFallback) return <span className={`brand ${className}`}>
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 9h16l-1.4-5H5.4L4 9Z" />
        <path d="M5 9v10h14V9M9 19v-6h6v6" />
      </svg>
    </span>
    <span className="brand-word">Bode<span className="brand-accent">Smart</span></span>
  </span>;

  return <img
    className={`brand-logo ${className}`}
    src={mobile ? MOBILE_LOGO : FULL_LOGO}
    alt="BodeSmart"
    onError={() => setUseFallback(true)}
  />;
}
