import test from "node:test";
import assert from "node:assert/strict";
import { getApiHealth, getStores } from "./api.js";

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

