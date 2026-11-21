import { expect, test } from "@playwright/test";

const demoPassword = "LocalDemoPass123!";

async function signIn(page, email) {
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Contraseña").fill(demoPassword);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
}

test("buyer reserves one offer, pays locally and stock falls once", async ({ page }) => {
  const response = await page.request.get("/api/v1/offers");
  const offers = await response.json();
  const offer = offers.find((item) => item.available_steps >= 2);
  expect(offer).toBeTruthy();

  await page.goto("/");
  await signIn(page, "cliente.1@demo.example");
  await page.getByLabel("Bodega").selectOption(offer.store_id);
  const card = page.locator("article.buyer-card").filter({ hasText: offer.product_name }).first();
  await card.getByRole("button", { name: "Añadir" }).click();
  await page.getByRole("button", { name: "Crear pedido y reservar" }).click();
  await expect(page.getByText("Estado:").first()).toContainText("PENDING");
  await page.getByRole("button", { name: "Simular pago aprobado" }).click();
  await expect(page.getByText("Estado:").first()).toContainText("PAID");
  const after = await (await page.request.get("/api/v1/offers")).json();
  expect(after.find((item) => item.id === offer.id).available_steps).toBe(offer.available_steps - 1);
});

test("owner adds and disables an employee without losing the record", async ({ page }) => {
  const email = `browser-${Date.now()}@example.test`;
  await page.goto("/");
  await page.getByRole("button", { name: "Gestión de bodega" }).click();
  await signIn(page, "dueno.1@demo.example");
  const form = page.locator(".ops-card").filter({ hasText: "Personal de la bodega" }).locator("form");
  await form.getByLabel("Nombre").fill("Empleado navegador");
  await form.getByLabel("Correo").fill(email);
  await form.getByLabel("Contraseña inicial").fill("StrongStaff123!");
  await form.getByRole("button", { name: "Agregar empleado" }).click();
  const row = page.locator("tr").filter({ hasText: email });
  await expect(row).toContainText("Activo");
  await row.getByRole("button", { name: "Desactivar" }).click();
  await expect(row).toContainText("Inactivo");
});

test("administrator creates a store and an owner through the browser", async ({ page }) => {
  const name = `Bodega navegador ${Date.now()}`;
  const email = `new-owner-${Date.now()}@example.test`;
  await page.goto("/");
  await page.getByRole("button", { name: "Gestión de bodega" }).click();
  await signIn(page, "admin@demo.example");
  const storeForm = page.locator("form.ops-card").filter({ hasText: "Nueva bodega" });
  await storeForm.getByLabel("Nombre").fill(name);
  await storeForm.getByLabel("Dirección").fill("Calle de prueba 1");
  await storeForm.getByRole("button", { name: "Crear bodega" }).click();
  await expect(page.locator("tr").filter({ hasText: name })).toBeVisible();
  await page.locator("tr").filter({ hasText: name }).getByRole("button", { name: "Editar" }).click();
  const editStore = page.locator("form.ops-card").filter({ hasText: "Editar bodega" });
  await editStore.getByLabel("Horario").fill("09:00–18:00");
  await editStore.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.locator("tr").filter({ hasText: name })).toContainText("09:00–18:00");
  const userForm = page.locator("form.ops-card").filter({ hasText: "Nueva cuenta" });
  await userForm.getByLabel("Nombre").fill("Dueño navegador");
  await userForm.getByLabel("Correo").fill(email);
  await userForm.getByLabel("Contraseña inicial").fill("StrongOwner123!");
  await userForm.getByLabel("Rol").selectOption("OWNER");
  await userForm.getByLabel("Bodega para dueño o empleado").selectOption({ label: name });
  await userForm.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page.locator("tr").filter({ hasText: email })).toContainText(name);
  await page.locator("tr").filter({ hasText: email }).getByRole("button", { name: "Editar" }).click();
  const editUser = page.locator("form.ops-card").filter({ hasText: "Editar cuenta" });
  await editUser.getByLabel("Nombre").fill("Dueño editado");
  await editUser.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.locator("tr").filter({ hasText: email })).toContainText("Dueño editado");
});
