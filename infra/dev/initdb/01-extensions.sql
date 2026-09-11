-- Executed once when the development database is created.
-- The same extensions are also created by the first migration (they are trusted extensions,
-- so the application role can create them in databases it owns, e.g. test databases).
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;
