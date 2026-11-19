import { createContext, useContext } from "react";

export const LayoutContext = createContext({ user: null, activeTab: "", onNavigate: () => {} });

export function useLayout() {
  return useContext(LayoutContext);
}
