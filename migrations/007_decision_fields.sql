SET search_path = pitwall, public;

ALTER TABLE stewards_decisions
  ADD COLUMN season         INT  NOT NULL,
  ADD COLUMN source_file    TEXT NOT NULL UNIQUE,
  ADD COLUMN title          TEXT,
  ADD COLUMN category       TEXT,   -- the FIA's label: 'Decision' or 'Infringement'
  ADD COLUMN doc_no         INT,
  ADD COLUMN doc_date       DATE,
  ADD COLUMN competitor     TEXT,
  ADD COLUMN session        TEXT,
  ADD COLUMN infringement   TEXT,   -- the rule breach, as the stewards wrote it
  ADD COLUMN penalty_type   TEXT,   -- no_further_action, time_penalty, grid_penalty, fine, ...
  ADD COLUMN time_penalty_s INT,
  ADD COLUMN parse_status   TEXT NOT NULL;  -- full, partial, unparsed

INSERT INTO data_coverage (table_name, first_season, source, reason, notes) VALUES
('stewards_decisions', 2023, 'FIA stewards'' decision documents (PDF)',
 'Collected for 2023 onward to match the detailed race data. The FIA site''s bot protection stopped the automated download after about 120 documents (first half of 2023); the rest are being added gradually.',
 'One row per decision document. incident_summary = Fact, penalty = Decision, reasoning = Reason. parse_status shows whether all fields were extracted. doc_ref is the FIA link. The rules in force are regulation_articles for the same season.');