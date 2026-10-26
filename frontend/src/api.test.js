import test from "node:test";
import assert from "node:assert/strict";
import { apiPost, getApiHealth, getStores } from "./api.js";

test("health calls same-origin Python API", async () => {
  const calls = [];
  const result = await getApiHealth(async (...args) => {
    calls.push(args);
    return { ok: true, json: async () => ({ status: "ok", phase: 1 }) };
  });
  assert.deepEqual(result, { status: "ok", phase: 1 });
  assert.deepEqual(calls, [["/api/v1/health", { credentials: "same-origin" }]]);
});

test("stores returns server-owned list", async () => {
  const result = await getStores(async () => ({ ok: true, json: async () => [{ name: "Tienda A" }] }));
  assert.deepEqual(result, [{ name: "Tienda A" }]);
});

test("API errors do not pretend to be success", async () => {
  await assert.rejects(getApiHealth(async () => ({ ok: false, status: 503 })), /API 503/);
});

test("POST fetches CSRF token and sends session cookie", async () => {
  const calls = [];
  const fetcher = async (path, options) => {
    calls.push([path, options]);
    return path.endsWith("/csrf")
      ? { ok: true, json: async () => ({ csrf_token: "safe-token" }) }
      : { ok: true, status: 201, json: async () => ({ id: "saved" }) };
  };
  assert.deepEqual(await apiPost("/store/products", { name: "Manzana" }, fetcher), { id: "saved" });
  assert.equal(calls[1][0], "/api/v1/store/products");
  assert.equal(calls[1][1].headers["X-CSRFToken"], "safe-token");
  assert.equal(calls[1][1].credentials, "same-origin");
  assert.equal(JSON.parse(calls[1][1].body).name, "Manzana");
});

test("POST surfaces backend validation message", async () => {
  let count = 0;
  const fetcher = async () => {
    count += 1;
    return count === 1
      ? { ok: true, json: async () => ({ csrf_token: "token" }) }
      : { ok: false, status: 409, json: async () => ({ error: { message: "Sin stock" } }) };
  };
  await assert.rejects(apiPost("/store/local-sales", {}, fetcher), /Sin stock/);
});

