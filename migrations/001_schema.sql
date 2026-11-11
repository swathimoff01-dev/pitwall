CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS pitwall;
SET search_path = pitwall,public;

-- ---------- Race data ----------
CREATE TABLE races (
  race_id     SERIAL PRIMARY KEY,
  season      INT NOT NULL,
  round       INT NOT NULL,
  name        TEXT NOT NULL,
  circuit     TEXT,
  race_date   DATE,
  UNIQUE (season, round)
);

CREATE TABLE drivers (
  driver_id   TEXT PRIMARY KEY,          -- Jolpica driverId, e.g. 'hamilton'
  code        TEXT,
  given_name  TEXT,
  family_name TEXT,
  number      INT,
  nationality TEXT
);

CREATE TABLE constructors (
  constructor_id TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  nationality    TEXT
);

CREATE TABLE results (
  race_id        INT REFERENCES races,
  driver_id      TEXT REFERENCES drivers,
  constructor_id TEXT REFERENCES constructors,
  grid           INT,
  position       INT,                    -- NULL if not classified
  position_text  TEXT,
  points         NUMERIC,
  status         TEXT,
  laps           INT,
  PRIMARY KEY (race_id, driver_id)
);

CREATE TABLE pit_stops (
  race_id    INT REFERENCES races,
  driver_id  TEXT REFERENCES drivers,
  stop_no    INT,
  lap        INT,
  duration_s NUMERIC,
  PRIMARY KEY (race_id, driver_id, stop_no)
);

CREATE TABLE laps (
  race_id     INT REFERENCES races,
  driver_id   TEXT REFERENCES drivers,
  lap_no      INT,
  lap_time_s  NUMERIC,
  sector1_s   NUMERIC,
  sector2_s   NUMERIC,
  sector3_s   NUMERIC,
  compound    TEXT,
  tyre_life   INT,
  stint_no    INT,
  position    INT,
  is_accurate BOOLEAN,
  PRIMARY KEY (race_id, driver_id, lap_no)
);

CREATE TABLE stints (
  race_id   INT REFERENCES races,
  driver_id TEXT REFERENCES drivers,
  stint_no  INT,
  compound  TEXT,
  start_lap INT,
  end_lap   INT,
  PRIMARY KEY (race_id, driver_id, stint_no)
);

CREATE TABLE race_control_messages (
  msg_id   BIGSERIAL PRIMARY KEY,
  race_id  INT REFERENCES races,
  lap      INT,
  ts       TIMESTAMPTZ,
  category TEXT,
  flag     TEXT,
  message  TEXT NOT NULL
);

-- ---------- Retrieval corpora (384-dim = bge-small-en-v1.5) ----------
CREATE TABLE regulation_articles (
  chunk_id    BIGSERIAL PRIMARY KEY,
  doc_version TEXT NOT NULL,             -- e.g. '2025 Sporting Regulations, Issue 4'
  article_no  TEXT NOT NULL,             -- e.g. '33.4'
  title       TEXT,
  body        TEXT NOT NULL,
  embedding   vector(384)
);

CREATE TABLE stewards_decisions (
  decision_id      BIGSERIAL PRIMARY KEY,
  race_id          INT REFERENCES races,
  doc_ref          TEXT,                 -- source PDF / document number
  car_no           INT,
  driver_id        TEXT REFERENCES drivers,
  incident_summary TEXT NOT NULL,
  articles_cited   TEXT[],
  penalty          TEXT,
  penalty_points   INT,
  reasoning        TEXT,
  embedding        vector(384)
);

-- ---------- Agent output (the only table the publisher role writes) ----------
CREATE TABLE rulings (
  ruling_id    BIGSERIAL PRIMARY KEY,
  incident     TEXT NOT NULL,
  draft        JSONB NOT NULL,           -- article, penalty, points, reasoning
  status       TEXT NOT NULL DEFAULT 'draft'
               CHECK (status IN ('draft','approved','rejected','published')),
  approved_by  TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ
);

-- ---------- Indexes ----------
CREATE INDEX ON laps (race_id, driver_id);
CREATE INDEX ON race_control_messages (race_id, lap);
CREATE INDEX ON regulation_articles USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON stewards_decisions  USING hnsw (embedding vector_cosine_ops);