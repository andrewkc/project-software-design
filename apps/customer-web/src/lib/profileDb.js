import { readSaved } from "./storage";

const SQL_JS_URL = "https://esm.sh/sql.js@1.13.0";
const WASM_URL = "https://cdn.jsdelivr.net/npm/sql.js@1.13.0/dist/sql-wasm.wasm";
const DB_STORAGE_KEY = "bodega-profile-db";

let databasePromise = null;

function bytesToBase64(bytes) {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
  }
  return btoa(binary);
}

function base64ToBytes(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function persist(database) {
  localStorage.setItem(DB_STORAGE_KEY, bytesToBase64(database.export()));
}

function run(database, sql, params = []) {
  const statement = database.prepare(sql);
  try {
    statement.run(params);
  } finally {
    statement.free();
  }
  persist(database);
}

function toProfile(row) {
  return {
    id: row.id,
    role: row.role,
    name: row.name,
    nombres: row.nombres || "",
    apellidos: row.apellidos || "",
    email: row.email,
    password: row.password || "",
    store: row.store,
    activo: row.activo === 1,
    creadoEn: row.creado_en || "",
    revocadoEn: row.revocado_en || "",
  };
}

function insertRow(database, profile) {
  run(database, `INSERT OR REPLACE INTO profiles
    (id, role, name, nombres, apellidos, email, password, store, activo, creado_en, revocado_en)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, [
    profile.id,
    profile.role,
    profile.name,
    profile.nombres || "",
    profile.apellidos || "",
    profile.email,
    profile.password || "",
    profile.store || "",
    profile.activo === false ? 0 : 1,
    profile.creadoEn || new Date().toISOString(),
    profile.revocadoEn || "",
  ]);
}

function seedLegacyProfiles(database) {
  const result = database.exec("SELECT COUNT(*) AS total FROM profiles");
  if (result[0].values[0][0] > 0) return;

  const jefe = readSaved("bodega-jefe", null) || readSaved("bodega-user", null);
  if (jefe && jefe.role !== "empleado" && jefe.email) {
    insertRow(database, { ...jefe, role: "jefe", id: jefe.id || "user-jefe" });
  }
  const savedEmployees = readSaved("bodega-employees", []);
  if (Array.isArray(savedEmployees)) {
    savedEmployees.filter((employee) => employee.email).forEach((employee) => insertRow(database, { ...employee, role: "empleado" }));
  }
}

async function getDatabase() {
  if (!databasePromise) {
    databasePromise = (async () => {
      const initSqlJs = (await import(/* @vite-ignore */ SQL_JS_URL)).default;
      const SQL = await initSqlJs({ locateFile: () => WASM_URL });
      const saved = localStorage.getItem(DB_STORAGE_KEY);
      const database = saved ? new SQL.Database(base64ToBytes(saved)) : new SQL.Database();
      database.run(`CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        nombres TEXT,
        apellidos TEXT,
        email TEXT NOT NULL UNIQUE,
        password TEXT,
        store TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        creado_en TEXT,
        revocado_en TEXT
      )`);
      seedLegacyProfiles(database);
      persist(database);
      return database;
    })().catch((error) => {
      databasePromise = null;
      throw error;
    });
  }
  return databasePromise;
}

function queryProfiles(database, sql, params = []) {
  const result = database.exec(sql, params)[0];
  if (!result) return [];
  return result.values.map((values) => toProfile(Object.fromEntries(result.columns.map((column, index) => [column, values[index]]))));
}

export async function listProfiles() {
  const database = await getDatabase();
  return queryProfiles(database, "SELECT * FROM profiles ORDER BY creado_en");
}

export async function findProfileByEmail(email) {
  const database = await getDatabase();
  const rows = queryProfiles(database, "SELECT * FROM profiles WHERE lower(email) = lower(?)", [email]);
  return rows[0] || null;
}

export async function saveProfile(profile) {
  const database = await getDatabase();
  insertRow(database, profile);
  return profile;
}

export async function updateProfile(id, changes) {
  const database = await getDatabase();
  const columns = Object.keys(changes);
  if (columns.length === 0) return;
  const values = columns.map((column) => changes[column]);
  run(database, `UPDATE profiles SET ${columns.map((column) => `${column} = ?`).join(", ")} WHERE id = ?`, [...values, id]);
}

export async function deleteProfile(id) {
  const database = await getDatabase();
  run(database, "DELETE FROM profiles WHERE id = ?", [id]);
}

export function isSqliteAvailable() {
  return databasePromise !== null;
}
