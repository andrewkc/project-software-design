import test from "node:test";
import assert from "node:assert/strict";
import { applyQuery, FIELDS, OPERATORS, matchesFilter, ROLE_LABELS } from "./adminTable.js";

const rows = [
  { id: "1", name: "Ana Torres", email: "ana@demo.example", role: "OWNER", store_name: "Mercado Verde", is_active: true, last_login: "2026-11-10T09:00:00Z", created_at: "2026-10-01T10:00:00Z" },
  { id: "2", name: "Bruno Díaz", email: "bruno@demo.example", role: "EMPLOYEE", store_name: "Mercado Verde", is_active: false, last_login: null, created_at: "2026-10-05T10:00:00Z" },
  { id: "3", name: "carla Ruiz", email: "carla@demo.example", role: "OWNER", store_name: "Dulce y Fresco", is_active: true, last_login: "2026-11-12T09:00:00Z", created_at: "2026-09-20T10:00:00Z" },
  { id: "4", name: "Diego Paz", email: "diego@correo.pe", role: "CUSTOMER", store_name: null, is_active: true, last_login: null, created_at: "2026-11-01T10:00:00Z" },
];
const ids = (list) => list.map((row) => row.id);

test("every field has operators for its type", () => {
  for (const field of FIELDS) assert.ok(OPERATORS[field.type]?.length, field.key);
  assert.equal(ROLE_LABELS.OWNER, "Jefe de bodega");
});

test("empty query returns every row in original order", () => {
  assert.deepEqual(ids(applyQuery(rows, {})), ["1", "2", "3", "4"]);
});

test("search matches name, email or store ignoring case and accents", () => {
  assert.deepEqual(ids(applyQuery(rows, { search: "DIAZ" })), ["2"]);
  assert.deepEqual(ids(applyQuery(rows, { search: "verde" })), ["1", "2"]);
  assert.deepEqual(ids(applyQuery(rows, { search: "correo.pe" })), ["4"]);
});

test("view role restricts rows before other filters", () => {
  assert.deepEqual(ids(applyQuery(rows, { role: "OWNER" })), ["1", "3"]);
});

test("text operators", () => {
  assert.ok(matchesFilter(rows[0], { field: "name", operator: "contains", value: "torr" }));
  assert.ok(!matchesFilter(rows[0], { field: "name", operator: "not_contains", value: "torr" }));
  assert.ok(matchesFilter(rows[0], { field: "email", operator: "starts_with", value: "ANA@" }));
  assert.ok(matchesFilter(rows[0], { field: "store_name", operator: "equals", value: "mercado verde" }));
  assert.ok(matchesFilter(rows[3], { field: "store_name", operator: "is_empty" }));
  assert.ok(!matchesFilter(rows[3], { field: "store_name", operator: "is_not_empty" }));
});

test("select, boolean and date operators", () => {
  assert.ok(matchesFilter(rows[1], { field: "role", operator: "is", value: "EMPLOYEE" }));
  assert.ok(matchesFilter(rows[1], { field: "role", operator: "is_not", value: "OWNER" }));
  assert.ok(matchesFilter(rows[1], { field: "is_active", operator: "is", value: "false" }));
  assert.ok(matchesFilter(rows[0], { field: "created_at", operator: "before", value: "2026-10-02" }));
  assert.ok(matchesFilter(rows[3], { field: "created_at", operator: "after", value: "2026-10-31" }));
  assert.ok(matchesFilter(rows[2], { field: "last_login", operator: "on", value: "2026-11-12" }));
  assert.ok(matchesFilter(rows[1], { field: "last_login", operator: "is_empty" }));
});

test("incomplete filters are ignored, like in Notion", () => {
  assert.deepEqual(ids(applyQuery(rows, { filters: [{ field: "name", operator: "contains", value: "" }] })), ["1", "2", "3", "4"]);
});

test("filters combine with AND", () => {
  const filters = [
    { field: "role", operator: "is", value: "OWNER" },
    { field: "last_login", operator: "after", value: "2026-11-11" },
  ];
  assert.deepEqual(ids(applyQuery(rows, { filters })), ["3"]);
});

test("sort by text is case and accent insensitive", () => {
  assert.deepEqual(ids(applyQuery(rows, { sorts: [{ field: "name", direction: "asc" }] })), ["1", "2", "3", "4"]);
  assert.deepEqual(ids(applyQuery(rows, { sorts: [{ field: "name", direction: "desc" }] })), ["4", "3", "2", "1"]);
});

test("empty values sort last in both directions", () => {
  assert.deepEqual(ids(applyQuery(rows, { sorts: [{ field: "last_login", direction: "desc" }] })).slice(2).sort(), ["2", "4"]);
  assert.deepEqual(ids(applyQuery(rows, { sorts: [{ field: "last_login", direction: "asc" }] })).slice(0, 2), ["1", "3"]);
});

test("multiple sorts break ties in order", () => {
  const sorts = [{ field: "store_name", direction: "asc" }, { field: "name", direction: "desc" }];
  assert.deepEqual(ids(applyQuery(rows, { sorts })), ["3", "2", "1", "4"]);
});

test("does not mutate the input", () => {
  const copy = structuredClone(rows);
  applyQuery(rows, { sorts: [{ field: "name", direction: "desc" }] });
  assert.deepEqual(rows, copy);
});
