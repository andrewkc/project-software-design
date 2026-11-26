import { useMemo } from "react";

export function useInventorySummary(products) {
  const expiringProducts = useMemo(() => products.filter((product) => {
    if (!product.expires) return false;
    const days = Math.ceil((new Date(`${product.expires}T00:00:00`) - new Date(new Date().toDateString())) / 86400000);
    return days >= 0 && days <= 7;
  }), [products]);

  const stockTotal = useMemo(() => products.reduce((total, product) => total + Number(product.stock), 0), [products]);
  const categoryTotals = useMemo(() => {
    const totals = products.reduce((result, product) => {
      result[product.category] = (result[product.category] || 0) + Number(product.stock);
      return result;
    }, {});
    return Object.entries(totals).sort(([, first], [, second]) => second - first);
  }, [products]);

  return { expiringProducts, stockTotal, categoryTotals };
}
