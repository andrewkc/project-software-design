import React from "react";
import bodeSmartLogo from "../assets/BodeSmart-Logo.png";
import bodeSmartMobileLogo from "../assets/BodeSmart-Mobile-Logo.png";

export function Brand({ mobile = false, className = "" }) {
  return <img className={`brand-logo ${className}`} src={mobile ? bodeSmartMobileLogo : bodeSmartLogo} alt="BodeSmart" />;
}
