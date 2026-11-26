import { useMemo } from "react";

const MAX_POINTS = 8;

function dayKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function shortLabel(value) {
  return new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "short" }).format(new Date(value));
}

/** Serie acumulada calculada solo con las compras pagadas que llegan de /sales. */
export function buildSalesSeries(sales = []) {
  const byDay = new Map();
  sales.forEach((sale) => {
    const key = dayKey(sale.fechaPago);
    if (!key) return;
    const entry = byDay.get(key) || { key, fechaPago: sale.fechaPago, total: 0, count: 0 };
    entry.total += Number(sale.total) || 0;
    entry.count += 1;
    byDay.set(key, entry);
  });

  const days = [...byDay.values()].sort((first, second) => new Date(first.fechaPago) - new Date(second.fechaPago));
  let running = 0;
  const cumulativeDays = days.map((day) => {
    running += day.total;
    return { ...day, cumulative: running };
  });
  const total = running;
  const max = total || 1;
  const visible = cumulativeDays.slice(-MAX_POINTS);
  const points = visible.map((day, index) => ({
    ...day,
    label: shortLabel(day.fechaPago),
    x: visible.length > 1 ? 20 + (index * 260) / (visible.length - 1) : 150,
    y: 118 - (day.cumulative / max) * 86,
  }));

  return {
    points,
    polyline: points.map((point) => `${point.x},${point.y}`).join(" "),
    total,
    purchaseCount: days.reduce((sum, day) => sum + day.count, 0),
    dayCount: days.length,
    hiddenDayCount: Math.max(days.length - visible.length, 0),
  };
}

export function useSalesSummary(sales) {
  return useMemo(() => buildSalesSeries(sales), [sales]);
}
