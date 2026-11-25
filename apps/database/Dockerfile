
FROM postgres:17

# Copy the database initialization and seed scripts in order
COPY database.sql /docker-entrypoint-initdb.d/01-database.sql
COPY seed.sql /docker-entrypoint-initdb.d/02-seed.sql

# Default PostgreSQL port
EXPOSE 5432
