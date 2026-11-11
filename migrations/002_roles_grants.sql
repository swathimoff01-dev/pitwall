-- Nobody may create objects in the shared "public" schema.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Both roles may enter the pitwall schema (the "room"); tables are separate doors.
GRANT USAGE ON SCHEMA pitwall TO pitwall_agent, pitwall_publisher;

-- Agent: read everything, now and for tables added in future steps.
GRANT SELECT ON ALL TABLES IN SCHEMA pitwall TO pitwall_agent;
ALTER DEFAULT PRIVILEGES IN SCHEMA pitwall GRANT SELECT ON TABLES TO pitwall_agent;

-- Publisher: read and write the rulings notebook, nothing else.
GRANT SELECT, INSERT, UPDATE ON pitwall.rulings TO pitwall_publisher;
GRANT USAGE, SELECT ON SEQUENCE pitwall.rulings_ruling_id_seq TO pitwall_publisher;

-- Convenience and safety nets.
ALTER ROLE pitwall_agent     SET search_path = pitwall, public;
ALTER ROLE pitwall_publisher SET search_path = pitwall, public;
ALTER ROLE pitwall_agent SET default_transaction_read_only = on;
ALTER ROLE pitwall_agent SET statement_timeout = '5s';