--
-- Copyright contributors to the agentic-ai-cyberres project
--

-- PostgreSQL validation script for psql
-- This script validates database integrity including tables, indexes, and constraints

\set ON_ERROR_STOP on
\timing off
\pset format unaligned
\pset tuples_only on

-- Variables will be passed via psql -v flag (safer than shell expansion)
-- Example: psql -d mydb -v dbname=mydb -v tablename=mytable
-- Note: Connection is established via psql -d flag, not via \c command

-- Output validation header
\pset format aligned
\pset tuples_only off
SELECT 'Validating database ' || :'dbname' || ' and table ' || :'tablename' AS status;
\echo

-- Build the validation result as JSON
\pset format unaligned
\pset tuples_only on

WITH validation_results AS (
  -- Check if table exists
  SELECT
    :'dbname' AS database_name,
    :'tablename' AS table_name,
    CASE
      WHEN EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname || '.' || tablename = :'tablename'
        OR tablename = :'tablename'
      ) THEN true
      ELSE false
    END AS table_exists
),
table_stats AS (
  -- Get table statistics
  SELECT
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
  FROM pg_stat_user_tables
  WHERE schemaname || '.' || relname = :'tablename'
    OR relname = :'tablename'
),
index_validation AS (
  -- Validate indexes using pg_class
  SELECT
    json_agg(
      json_build_object(
        'index_name', i.relname,
        'is_valid', idx.indisvalid,
        'is_ready', idx.indisready
      )
    ) AS indexes
  FROM pg_index idx
  JOIN pg_class i ON i.oid = idx.indexrelid
  JOIN pg_class t ON t.oid = idx.indrelid
  WHERE t.relname = :'tablename' OR (t.relnamespace::regnamespace::text || '.' || t.relname) = :'tablename'
),
constraint_validation AS (
  -- Check constraints validity
  SELECT
    json_agg(
      json_build_object(
        'constraint_name', con.conname,
        'constraint_type', con.contype,
        'is_valid', con.convalidated
      )
    ) AS constraints
  FROM pg_constraint con
  JOIN pg_class t ON t.oid = con.conrelid
  WHERE t.relname = :'tablename' OR (t.relnamespace::regnamespace::text || '.' || t.relname) = :'tablename'
)
SELECT json_build_object(
  'database', vr.database_name,
  'table', vr.table_name,
  'table_exists', vr.table_exists,
  'live_tuples', COALESCE(ts.live_tuples, 0),
  'dead_tuples', COALESCE(ts.dead_tuples, 0),
  'last_vacuum', ts.last_vacuum,
  'last_analyze', ts.last_analyze,
  'indexes', COALESCE(iv.indexes, '[]'::json),
  'constraints', COALESCE(cv.constraints, '[]'::json),
  'valid', CASE
    WHEN vr.table_exists
      AND COALESCE((
        SELECT bool_and(indisvalid AND indisready)
        FROM pg_index idx
        JOIN pg_class t ON t.oid = idx.indrelid
        WHERE t.relname = :'tablename' OR (t.relnamespace::regnamespace::text || '.' || t.relname) = :'tablename'
      ), true)
      AND COALESCE((
        SELECT bool_and(convalidated)
        FROM pg_constraint con
        JOIN pg_class t ON t.oid = con.conrelid
        WHERE t.relname = :'tablename' OR (t.relnamespace::regnamespace::text || '.' || t.relname) = :'tablename'
      ), true)
    THEN true
    ELSE false
  END,
  'warnings', CASE
    WHEN ts.dead_tuples > ts.live_tuples * 0.2
    THEN json_build_array('High dead tuple ratio - consider VACUUM')
    ELSE '[]'::json
  END,
  'errors', CASE
    WHEN NOT vr.table_exists THEN json_build_array('Table does not exist')
    WHEN EXISTS (
      SELECT 1 FROM pg_index idx
      JOIN pg_class t ON t.oid = idx.indrelid
      WHERE (t.relname = :'tablename' OR (t.relnamespace::regnamespace::text || '.' || t.relname) = :'tablename')
      AND (NOT idx.indisvalid OR NOT idx.indisready)
    ) THEN json_build_array('Invalid or unready indexes detected')
    ELSE '[]'::json
  END,
  'ok', CASE WHEN vr.table_exists THEN 1 ELSE 0 END
)
FROM validation_results vr
LEFT JOIN table_stats ts ON true
LEFT JOIN index_validation iv ON true
LEFT JOIN constraint_validation cv ON true;
