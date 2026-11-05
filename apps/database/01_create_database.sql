
-- 1. CREATE DATABASE
CREATE DATABASE software_project;

-- 2. CONNECT TO THE DATABASE
\c software_project

-- 3. CREATE USERS TABLE
CREATE TABLE users (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. INSERT SAMPLE DATA
INSERT INTO users (name, email)
VALUES
  ('Kelvin', 'kelvin@example.com'),
  ('Alice', 'alice@example.com'),
  ('Bob', 'bob@example.com');

-- 5. VERIFY DATA
SELECT * FROM users;

-- psql -U postgres -h localhost -f "C:\path\to\01_setup_database.sql"