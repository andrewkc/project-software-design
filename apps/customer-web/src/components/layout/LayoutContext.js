import { createContext, useContext } from "react";

export const LayoutContext = createContext({ user: null, activeTab: "", onNavigate: () => {}, cartCount: 0 });

export function useLayout() {
  return useContext(LayoutContext);
}
