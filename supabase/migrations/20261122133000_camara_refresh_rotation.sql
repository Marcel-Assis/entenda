BEGIN;

ALTER TABLE camara_ingestion.proposals
    ADD COLUMN last_refresh_at timestamptz;

CREATE INDEX proposals_refresh_order
    ON camara_ingestion.proposals (source, last_refresh_at NULLS FIRST, official_id);

-- Only one automatically selected batch can be pending at a time.
CREATE UNIQUE INDEX runs_one_pending_automatic_refresh
    ON camara_ingestion.runs (mode)
    WHERE mode = 'refresh' AND cursor IS NOT NULL AND scope @> '{"automatic":true}';

COMMIT;
