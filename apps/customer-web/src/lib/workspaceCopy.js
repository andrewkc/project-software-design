import { isCliente, isJefe } from "./permissions";

export function workspaceCopy(user) {
  const jefe = isJefe(user);
  return {
    storeName: user?.store || (jefe ? "Mi bodega" : "Bodega asignada"),
    storeCaption: isCliente(user) ? "Bodega vinculada" : jefe ? "Mi negocio" : "Bodega asignada",
    inventoryTitle: jefe ? "Todo tu inventario" : "Inventario de la bodega",
    inventorySubtitle: jefe ? "Busca, filtra y ordena tus productos." : "Busca, filtra y ordena los productos.",
    noCategoriesTitle: jefe ? "Aún no tienes categorías" : "Aún no hay categorías",
    noCategoriesText: jefe ? "Registra un producto para empezar a organizar tu inventario." : "Registra un producto para empezar a organizar el inventario.",
    profileSubtitle: jefe ? "Administra la información de tu cuenta y tu bodega." : "Administra la información de tu cuenta.",
    storeFieldLabel: isCliente(user) ? "Bodega vinculada" : jefe ? "Bodega" : "Bodega asignada",
    registerSubtitle: jefe ? "Elige cómo quieres agregar un producto a tu inventario." : "Elige cómo quieres agregar un producto al inventario de la bodega.",
    registerFormHint: jefe ? "Completa la información necesaria para guardarlo en tu inventario." : "Completa la información necesaria para guardarlo en el inventario de la bodega.",
    modalHint: jefe ? "Agrega los datos básicos para actualizar tu inventario." : "Agrega los datos básicos para actualizar el inventario de la bodega.",
    addedTarget: jefe ? "tu inventario" : "el inventario de la bodega",
  };
}
