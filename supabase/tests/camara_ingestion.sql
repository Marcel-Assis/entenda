\set ON_ERROR_STOP on

BEGIN;
SET LOCAL search_path TO camara_ingestion, pg_catalog;

INSERT INTO runs (mode, scope, state, cursor)
VALUES ('discovery', '{"type":"PL"}', 'running', 'page:1')
RETURNING id AS run_id \gset

INSERT INTO runs (mode, scope, state, cursor)
VALUES ('discovery', '{"type":"PL"}', 'running', 'page:1')
RETURNING id AS other_run_id \gset

INSERT INTO bodies (payload) VALUES ('A'), ('B');
INSERT INTO observations (run_id, url, fetched_at, http_status, body_sha256)
SELECT :run_id, 'https://dadosabertos.camara.leg.br/api/v2/proposicoes/42',
    clock_timestamp(), 200, sha256(payload)
FROM (VALUES ('A'::bytea), ('B'::bytea), ('A'::bytea)) AS samples(payload);

INSERT INTO proposals VALUES ('camara', 42, 1);
INSERT INTO proposal_versions
SELECT 'camara', 42, row_number() OVER (ORDER BY id), id, 1,
    body_sha256, jsonb_build_object('sample', encode(body_sha256, 'hex'))
FROM observations;
UPDATE proposals SET current_version = 3 WHERE official_id = 42;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT set_config('test.run_id', :'run_id', true);
SELECT set_config('test.other_run_id', :'other_run_id', true);

DO $$
DECLARE
    tested_run bigint := current_setting('test.run_id')::bigint;
    other_run bigint := current_setting('test.other_run_id')::bigint;
    evidence bigint := (SELECT min(id) FROM observations);
BEGIN
    IF (SELECT count(*) FROM bodies) <> 2 OR (SELECT count(*) FROM observations) <> 3
        OR (SELECT count(*) FROM proposal_versions) <> 3
        OR (SELECT normalized_sha256 FROM proposal_versions WHERE version = 1)
            IS DISTINCT FROM (SELECT normalized_sha256 FROM proposal_versions WHERE version = 3)
    THEN
        RAISE EXCEPTION 'Expected two bodies, three observations and history A → B → A';
    END IF;

    BEGIN
        INSERT INTO proposals VALUES ('camara', 42, 3);
        RAISE EXCEPTION 'Duplicate proposal accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;

    BEGIN
        UPDATE proposals SET current_version = 99 WHERE official_id = 42;
        RAISE EXCEPTION 'Missing current version accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO proposal_versions
        VALUES ('camara', 42, 4, -1, 1, sha256('A'::bytea), '{}');
        RAISE EXCEPTION 'Missing evidence accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO confirmed_pages VALUES (other_run, 'page:1', evidence);
        RAISE EXCEPTION 'Evidence from a different run accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO confirmed_pages VALUES (tested_run, 'page:1', evidence);
        UPDATE runs SET cursor = 'page:2', confirmed_pages = 1 WHERE id = tested_run;
        RAISE SQLSTATE 'P9001';
    EXCEPTION WHEN SQLSTATE 'P9001' THEN NULL;
    END;

    IF EXISTS (SELECT FROM confirmed_pages)
        OR NOT EXISTS (
            SELECT FROM runs WHERE id = tested_run AND cursor = 'page:1' AND confirmed_pages = 0
        )
    THEN
        RAISE EXCEPTION 'A failed transaction advanced the checkpoint or left a confirmed page';
    END IF;

    INSERT INTO confirmed_pages VALUES (tested_run, 'page:1', evidence);
    UPDATE runs SET cursor = 'page:2', confirmed_pages = 1
    WHERE id = tested_run AND cursor = 'page:1';
    IF NOT FOUND OR NOT EXISTS (
        SELECT FROM confirmed_pages WHERE run_id = tested_run AND cursor_key = 'page:1'
    ) THEN
        RAISE EXCEPTION 'Page confirmation did not advance the checkpoint';
    END IF;

    BEGIN
        INSERT INTO confirmed_pages VALUES (tested_run, 'page:1', evidence);
        RAISE EXCEPTION 'Repeated page accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;
END;
$$;

CREATE ROLE camara_test_unprivileged;
SET LOCAL ROLE camara_test_unprivileged;
DO $$
BEGIN
    BEGIN
        PERFORM id FROM camara_ingestion.runs;
        RAISE EXCEPTION 'Private schema readable by an unprivileged role';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END;
$$;
RESET ROLE;

GRANT USAGE ON SCHEMA camara_ingestion TO camara_test_unprivileged;
GRANT SELECT ON camara_ingestion.runs TO camara_test_unprivileged;
SET LOCAL ROLE camara_test_unprivileged;
DO $$
BEGIN
    IF EXISTS (SELECT FROM camara_ingestion.runs) THEN
        RAISE EXCEPTION 'Row-level security exposed ingestion runs';
    END IF;
END;
$$;
RESET ROLE;

ROLLBACK;
