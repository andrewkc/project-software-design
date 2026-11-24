import { describe, expect, test } from "vitest";
import { OrderError, acceptOrder, cancelOrder, createOrder, pendingOrders, rejectOrder, visibleOrders } from "./orders";
import { SaleError } from "./sales";

const today = "2026-11-24";
const now = "2026-11-24T15:00:00.000Z";
const products = [
  { id: 1, name: "Leche Gloria", stock: 8, unit: "unid.", price: 4.5, expires: "2099-01-01", activo: true },
  { id: 2, name: "Arroz extra", stock: 3, unit: "unid.", price: 4.2, expires: "", activo: true },
  { id: 3, name: "Yogurt vencido", stock: 5, unit: "unid.", price: 3.8, expires: "2020-01-01", activo: true },
  { id: 4, name: "Atún", stock: 0, unit: "unid.", price: 6.4, expires: "", activo: true },
];
const cliente = { id: "cli-1", role: "cliente", name: "Diego Paz", store: "Bodega San Martín" };
const otroCliente = { id: "cli-2", role: "cliente", name: "Rosa Ríos", store: "Bodega San Martín" };
const empleado = { id: "emp-1", role: "empleado", name: "Ana Torres", store: "Bodega San Martín" };
const options = { now, today, id: "ped-1" };

function order(cart = [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }], user = cliente, id = "ped-1") {
  return createOrder(products, cart, user, { ...options, id });
}

describe("createOrder", () => {
  test("arma un pedido pendiente con líneas, total y bodega del cliente sin tocar el stock", () => {
    const result = order();
    expect(result).toEqual({
      id: "ped-1", store: "Bodega San Martín", clienteId: "cli-1", clienteNombre: "Diego Paz", creadoEn: now, estado: "pendiente", total: 13.2,
      lineas: [
        { productoId: 1, productoNombre: "Leche Gloria", cantidad: 2, unidad: "unid.", precio: 4.5, subtotal: 9 },
        { productoId: 2, productoNombre: "Arroz extra", cantidad: 1, unidad: "unid.", precio: 4.2, subtotal: 4.2 },
      ],
    });
    expect(products[0].stock).toBe(8);
  });

  test("solo un cliente puede enviar pedidos", () => {
    expect(() => order(undefined, empleado)).toThrow(OrderError);
  });

  test("rechaza un pedido vacío", () => {
    expect(() => order([])).toThrow("Tu pedido está vacío.");
  });

  test("no acepta productos vencidos ni agotados", () => {
    expect(() => order([{ productId: 3, quantity: 1 }])).toThrow("Yogurt vencido ya no está disponible.");
    expect(() => order([{ productId: 4, quantity: 1 }])).toThrow("Atún ya no está disponible.");
  });

  test("no deja pedir más de lo que hay en stock", () => {
    expect(() => order([{ productId: 2, quantity: 4 }])).toThrow("Solo quedan 3 unid. de Arroz extra.");
  });
});

describe("atención del pedido", () => {
  test("al aceptarlo se registra la venta, se descuenta el stock y queda el responsable", () => {
    const result = acceptOrder(order(), products, empleado, { now, today, id: "mov-9" });
    expect(result.products.find((item) => item.id === 1).stock).toBe(6);
    expect(result.products.find((item) => item.id === 2).stock).toBe(2);
    expect(result.movement).toMatchObject({ id: "mov-9", tipo: "salida", motivo: "Venta", total: 13.2, responsable: "emp-1", pedidoId: "ped-1", clienteNombre: "Diego Paz" });
    expect(result.order).toMatchObject({ estado: "aceptado", atendidoPor: "emp-1", atendidoPorNombre: "Ana Torres", atendidoEn: now, ventaId: "mov-9" });
  });

  test("si el stock ya no alcanza, la venta no se registra", () => {
    const pedido = order([{ productId: 2, quantity: 3 }]);
    const afterOtherSale = products.map((item) => item.id === 2 ? { ...item, stock: 1 } : item);
    expect(() => acceptOrder(pedido, afterOtherSale, empleado, { now, today })).toThrow(SaleError);
  });

  test("un pedido atendido no se puede volver a atender", () => {
    const accepted = acceptOrder(order(), products, empleado, { now, today }).order;
    expect(() => acceptOrder(accepted, products, empleado, { now, today })).toThrow("Este pedido ya fue atendido.");
    expect(() => rejectOrder(accepted, empleado, "Sin stock", { now })).toThrow(OrderError);
  });

  test("el cliente no puede aceptar pedidos", () => {
    expect(() => acceptOrder(order(), products, cliente, { now, today })).toThrow(SaleError);
  });

  test("rechazar exige un motivo y lo guarda", () => {
    expect(() => rejectOrder(order(), empleado, "  ", { now })).toThrow("Indica el motivo del rechazo.");
    expect(rejectOrder(order(), empleado, "Cerramos temprano", { now })).toMatchObject({ estado: "rechazado", motivoRechazo: "Cerramos temprano", atendidoPor: "emp-1" });
    expect(() => rejectOrder(order(), cliente, "No", { now })).toThrow(OrderError);
  });

  test("el cliente puede cancelar solo su pedido pendiente", () => {
    expect(cancelOrder(order(), cliente, { now })).toMatchObject({ estado: "cancelado", canceladoEn: now });
    expect(() => cancelOrder(order(), otroCliente, { now })).toThrow(OrderError);
  });
});

describe("visibilidad", () => {
  const orders = [
    order(undefined, cliente, "ped-1"),
    { ...order(undefined, otroCliente, "ped-2"), creadoEn: "2026-11-24T16:00:00.000Z" },
    { ...order(undefined, cliente, "ped-3"), store: "Otra bodega" },
    { ...order(undefined, cliente, "ped-4"), estado: "aceptado" },
  ];

  test("el cliente ve solo sus pedidos y el personal los de su bodega", () => {
    expect(visibleOrders(orders, cliente).map((item) => item.id)).toEqual(["ped-1", "ped-3", "ped-4"]);
    expect(visibleOrders(orders, empleado).map((item) => item.id)).toEqual(["ped-2", "ped-1", "ped-4"]);
    expect(visibleOrders(orders, { id: "adm-1", role: "admin" })).toEqual([]);
  });

  test("cuenta los pendientes de la bodega", () => {
    expect(pendingOrders(orders, empleado).map((item) => item.id)).toEqual(["ped-2", "ped-1"]);
  });
});
