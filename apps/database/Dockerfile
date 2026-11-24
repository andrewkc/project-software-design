
FROM postgres:17

# Copy the database initialization script
COPY database.sql /docker-entrypoint-initdb.d/01-database.sql

# Default PostgreSQL port
EXPOSE 5432
