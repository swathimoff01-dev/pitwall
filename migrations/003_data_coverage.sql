SET search_path = pitwall, public;

CREATE TABLE data_coverage (
  table_name   TEXT PRIMARY KEY,
  first_season INT  NOT NULL,
  last_season  INT,                -- NULL means "up to the latest season loaded"
  source       TEXT NOT NULL,
  reason       TEXT NOT NULL,      -- why earlier seasons are missing, in plain words
  notes        TEXT
);

INSERT INTO data_coverage (table_name, first_season, source, reason, notes) VALUES
('races', 1999, 'Jolpica-F1 (Ergast-compatible)',
 'We chose to load from 1999. The source itself goes back to 1950.',
 'Race calendar and basic race details.'),
('results', 1999, 'Jolpica-F1 (Ergast-compatible)',
 'We chose to load from 1999. The source itself goes back to 1950.',
 'Finishing position, grid, points, status. position_text holds R, D, W for non-classified.'),
('pit_stops', 2012, 'Jolpica-F1 (Ergast-compatible)',
 'The source only began recording pit stops in 2012. Earlier races have no rows, which does NOT mean no stops happened.',
 'Stop number, lap, duration in seconds.');