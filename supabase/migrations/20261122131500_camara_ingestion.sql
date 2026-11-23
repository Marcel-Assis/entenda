BEGIN;

CREATE SCHEMA camara_ingestion;
REVOKE ALL ON SCHEMA camara_ingestion FROM PUBLIC;

CREATE TABLE camara_ingestion.runs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mode text NOT NULL CHECK (mode IN ('discovery', 'refresh')),
    scope jsonb NOT NULL CHECK (jsonb_typeof(scope) = 'object'),
    state text NOT NULL CHECK (state IN ('running', 'paused', 'failed', 'completed')),
    cursor text,
    confirmed_pages integer NOT NULL DEFAULT 0 CHECK (confirmed_pages >= 0),
    started_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((state = 'completed') = (cursor IS NULL)),
    CHECK (cursor IS NULL OR cursor <> '')
);

CREATE TABLE camara_ingestion.bodies (
    payload bytea NOT NULL,
    sha256 bytea GENERATED ALWAYS AS (sha256(payload)) STORED PRIMARY KEY
);

CREATE TABLE camara_ingestion.observations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES camara_ingestion.runs,
    url text NOT NULL CHECK (url <> ''),
    fetched_at timestamptz NOT NULL,
    http_status smallint CHECK (http_status BETWEEN 100 AND 599),
    body_sha256 bytea REFERENCES camara_ingestion.bodies,
    transport_error text,
    CHECK (
        (http_status IS NOT NULL AND transport_error IS NULL)
        OR (http_status IS NULL AND transport_error IS NOT NULL AND body_sha256 IS NULL)
    ),
    UNIQUE (run_id, id)
);

CREATE TABLE camara_ingestion.proposals (
    source text NOT NULL CHECK (source = 'camara'),
    official_id bigint NOT NULL CHECK (official_id > 0),
    current_version integer NOT NULL,
    PRIMARY KEY (source, official_id)
);

CREATE TABLE camara_ingestion.proposal_versions (
    source text NOT NULL,
    official_id bigint NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    observation_id bigint NOT NULL REFERENCES camara_ingestion.observations,
    normalizer_version integer NOT NULL CHECK (normalizer_version > 0),
    normalized_sha256 bytea NOT NULL CHECK (octet_length(normalized_sha256) = 32),
    fields jsonb NOT NULL CHECK (jsonb_typeof(fields) = 'object'),
    PRIMARY KEY (source, official_id, version),
    FOREIGN KEY (source, official_id) REFERENCES camara_ingestion.proposals
);

-- The first proposal and its first version are inserted in the same transaction.
ALTER TABLE camara_ingestion.proposals
    ADD FOREIGN KEY (source, official_id, current_version)
    REFERENCES camara_ingestion.proposal_versions
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE camara_ingestion.confirmed_pages (
    run_id bigint NOT NULL REFERENCES camara_ingestion.runs,
    cursor_key text NOT NULL CHECK (cursor_key <> ''),
    observation_id bigint NOT NULL,
    PRIMARY KEY (run_id, cursor_key),
    FOREIGN KEY (run_id, observation_id)
        REFERENCES camara_ingestion.observations (run_id, id)
);

CREATE TABLE camara_ingestion.quarantine (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL,
    observation_id bigint NOT NULL,
    item_index integer CHECK (item_index >= 0),
    official_id bigint CHECK (official_id > 0),
    reason text NOT NULL CHECK (reason <> ''),
    FOREIGN KEY (run_id, observation_id)
        REFERENCES camara_ingestion.observations (run_id, id)
);

ALTER TABLE camara_ingestion.runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE camara_ingestion.bodies ENABLE ROW LEVEL SECURITY;
ALTER TABLE camara_ingestion.observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE camara_ingestion.proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE camara_ingestion.proposal_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE camara_ingestion.confirmed_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE camara_ingestion.quarantine ENABLE ROW LEVEL SECURITY;

COMMIT;
