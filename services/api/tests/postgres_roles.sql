-- Local and CI disposable PostgreSQL ONLY. Never run against existing or hosted data.
-- The isolated container's administrator runs this before migrations.
CREATE ROLE axiom_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE axiom_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT CONNECT ON DATABASE axiom_test TO axiom_migrator, axiom_runtime;
GRANT CREATE ON DATABASE axiom_test TO axiom_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO axiom_migrator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
