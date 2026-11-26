import React from "react";

const iconPaths = {
  home: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-6h6v6" /></>,
  store: <><path d="M3 9h18l-1.5-5h-15L3 9Z" /><path d="M4 9v10h16V9M8 19v-6h8v6" /><path d="M3 9c0 2 3 3 4.5 1.5C9 12 11 11 12 9c1 2 3 3 4.5 1.5C18 12 21 11 21 9" /></>,
  cart: <><circle cx="9" cy="20" r="1.4" /><circle cx="18" cy="20" r="1.4" /><path d="M3 4h2l2.4 11h11.2l2-8H6" /></>,
  receipt: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z" /><path d="M9 8h6m-6 4h6m-6 4h3" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm10 10v-2a4 4 0 0 0-3-3.9m-1-12a4 4 0 0 1 0 7.8" /></>,
  box: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="M3 8v9l9 5 9-5V8M12 13v9" /></>,
  search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4 4" /></>,
  filter: <><path d="M4 6h16M7 12h10m-7 6h4" /></>,
  chevronDown: <path d="m5 9 7 7 7-7" />,
  chevronLeft: <path d="m14 6-6 6 6 6" />,
  arrow: <><path d="M5 12h14m-6-6 6 6-6 6" /></>,
  plus: <><path d="M12 5v14m-7-7h14" /></>,
  minus: <path d="M5 12h14" />,
  close: <><path d="m18 6-12 12M6 6l12 12" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M16 3v4M8 3v4M3 10h18m-13 5h2" /></>,
  tag: <><path d="M3 12V4h8l10 10-8 8L3 12Z" /><circle cx="7.5" cy="7.5" r="1.3" /></>,
  shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
  sparkles: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14ZM5 15l.8 1.7L7.5 17.5l-1.7.8L5 20l-.8-1.7-1.7-.8 1.7-.8L5 15Z" /></>,
  logout: <><path d="M10 17l5-5-5-5m5 5H3" /><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" /></>,
  refresh: <><path d="M20 11a8 8 0 0 0-14.7-4L3 10m0-4v4h4M4 13a8 8 0 0 0 14.7 4L21 14m0 4v-4h-4" /></>,
  mapPin: <><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8h.01" /></>,
  trash: <><path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6m4-6v6" /></>,
};

export function Icon({ name, size = 20, strokeWidth = 1.8, className = "" }) {
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name] || iconPaths.sparkles}</svg>;
}
